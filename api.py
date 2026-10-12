"""
api.py — API Bridge de L-IA

Expone la API REST (FastAPI) que conecta la interfaz de usuario (React/Tauri)
con el núcleo de L-IA (core.cerebro, core.voz, core.database, etc).

Endpoints principales:
    GET    /semaforo                 -> consulta si hay una autorización pendiente
    POST   /semaforo/responder       -> el usuario autoriza o deniega una herramienta
    POST   /chat                     -> envía un mensaje del usuario a L-IA (SSE)
    POST   /cancelar                 -> aborta la generación y silencia el audio
    POST   /escuchar                 -> abre el micrófono (Whisper) manualmente
    POST   /lector                   -> lectura en voz alta (Edge TTS)
    GET    /radar/leer               -> cola de eventos del daemon de voz
    GET    /sesiones                 -> lista de chats
    POST   /sesiones/nueva           -> crea un chat
    GET    /sesiones/{id}/contexto   -> historial + workspace del chat
    PUT    /sesiones/{id}            -> renombra un chat
    DELETE /sesiones/{id}            -> borra un chat
    POST   /debug/forzar_fase_1      -> dispara el evento anómalo (pruebas)

Mecanismos de fondo:
  * Semáforo: cuando L-IA quiere ejecutar una herramienta sensible, se pausa
    y espera que el usuario autorice o deniegue desde la interfaz. El frontend
    hace polling (GET /semaforo cada segundo), así que se usa un
    threading.Event para bloquear el hilo del backend hasta que llegue la
    respuesta o se cumpla el timeout.
  * Vigilante de RAM: si pasan 5 minutos sin usar el LLM, se descarga el
    modelo de Ollama (keep_alive=0) para liberar memoria.
  * Daemon de voz (radar): escucha la palabra clave y avisa a React.
"""
import json
import logging
import os
import queue
import threading
import time
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

import ollama
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import core.eventos_anomalos as eventos_anomalos
import core.voz as voz
from core import database
from core.cerebro import charlar_con_lia, evento_interrupcion

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("lia.api")

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
TIMEOUT_AUTORIZACION_SEGUNDOS = 120       # tiempo máximo esperando el clic del usuario
TIMEOUT_COLA_STREAMING_SEGUNDOS = 180     # corta la conexión SSE si el hilo de la IA se traba
MODELO_OLLAMA = "gemma2"                  # debe coincidir con el modelo que usa core.cerebro
INACTIVIDAD_RAM_SEGUNDOS = 300            # 5 min sin uso -> se descarga el modelo
INTERVALO_VIGILANTE_SEGUNDOS = 30         # cada cuánto revisa el centinela
TRIGGER_COLAPSO = "TRIGGER_COLAPSO_FASE_1"


# ---------------------------------------------------------------------------
# Modelos Pydantic
# ---------------------------------------------------------------------------
class MensajeUsuario(BaseModel):
    texto: str
    sesion_id: str = "default"
    usar_voz: bool = False  # React indica si L-IA debe hablar


class RespuestaSemaforo(BaseModel):
    autorizado: bool


class PeticionLector(BaseModel):
    texto: str


class ActualizarTituloRequest(BaseModel):
    titulo: str


# ---------------------------------------------------------------------------
# Semáforo de autorización
# ---------------------------------------------------------------------------
@dataclass
class SemaforoAutorizacion:
    """
    Encapsula el estado del "semáforo" que pausa a L-IA cuando necesita
    permiso del usuario para ejecutar una herramienta.

    Agrupa el estado compartido (alerta activa, resultado de la votación,
    evento de sincronización y el lock que evita que dos chats simultáneos
    se pisen) en un solo objeto en vez de variables globales sueltas.
    """

    evento: threading.Event = field(default_factory=threading.Event)
    lock: threading.Lock = field(default_factory=threading.Lock)
    alerta_actual: Optional[dict] = None
    autorizacion_concedida: bool = False

    def solicitar_autorizacion(self, herramienta: str, argumentos: Any) -> bool:
        """
        Bloquea el hilo actual hasta que el usuario responda desde el frontend
        (POST /semaforo/responder) o se cumpla el timeout. Solo una solicitud
        puede estar activa a la vez en todo el servidor.

        Devuelve True si el usuario autorizó; False si denegó o no respondió.
        """
        with self.lock:
            self.alerta_actual = {"herramienta": herramienta, "argumentos": str(argumentos)}
            self.autorizacion_concedida = False
            self.evento.clear()

            logger.info("Esperando autorización del usuario para: %s", herramienta)
            respondio_a_tiempo = self.evento.wait(timeout=TIMEOUT_AUTORIZACION_SEGUNDOS)

            self.alerta_actual = None

            if not respondio_a_tiempo:
                logger.warning(
                    "Tiempo agotado esperando autorización para: %s. Abortando por defecto.",
                    herramienta,
                )
                return False

            return self.autorizacion_concedida

    def registrar_respuesta(self, autorizado: bool) -> None:
        """Llamado por /semaforo/responder cuando el usuario decide."""
        self.autorizacion_concedida = autorizado
        self.evento.set()  # libera el hilo que espera en solicitar_autorizacion()

    def estado_actual(self) -> dict:
        """Snapshot del estado para el polling de React (GET /semaforo)."""
        # Copia local: otro hilo podría poner alerta_actual en None entre
        # la comprobación y la lectura.
        alerta = self.alerta_actual
        if alerta:
            return {"activa": True, "herramienta": alerta["herramienta"], "argumentos": alerta["argumentos"]}
        return {"activa": False}


semaforo = SemaforoAutorizacion()


# ---------------------------------------------------------------------------
# Vigilante de RAM (descarga el modelo de Ollama tras inactividad)
# ---------------------------------------------------------------------------
class VigilanteRAM:
    """
    Centinela que libera la RAM de Ollama tras un periodo de inactividad.

    - `marcar_uso()` reinicia el reloj y marca el modelo como cargado.
    - `generacion_activa()` es un context manager que evita que el modelo se
      descargue mientras hay una respuesta en curso, y reinicia el reloj al
      terminar (así los 5 minutos cuentan desde el final de la respuesta).
    """

    def __init__(self, modelo: str, inactividad_s: float, intervalo_s: float):
        self.modelo = modelo
        self.inactividad_s = inactividad_s
        self.intervalo_s = intervalo_s
        self._lock = threading.Lock()
        self._ultimo_uso = time.monotonic()
        self._en_ram = False
        self._generaciones_activas = 0

    def marcar_uso(self) -> None:
        with self._lock:
            self._ultimo_uso = time.monotonic()
            self._en_ram = True

    @contextmanager
    def generacion_activa(self) -> Iterator[None]:
        with self._lock:
            self._generaciones_activas += 1
            self._ultimo_uso = time.monotonic()
            self._en_ram = True
        try:
            yield
        finally:
            with self._lock:
                self._generaciones_activas -= 1
                self._ultimo_uso = time.monotonic()

    def _debe_descargar(self) -> bool:
        with self._lock:
            return (
                self._en_ram
                and self._generaciones_activas == 0
                and (time.monotonic() - self._ultimo_uso) > self.inactividad_s
            )

    def _descargar_modelo(self) -> None:
        try:
            # keep_alive=0 le pide a Ollama que saque el modelo de la RAM ya.
            ollama.generate(model=self.modelo, prompt="", keep_alive=0)
            with self._lock:
                self._en_ram = False
            print(f"✅ [Daemon RAM] {self.modelo} descargado, RAM liberada.")
        except Exception as e:
            print(f"⚠️ [Daemon RAM] Error al intentar limpiar la RAM: {e}")

    def correr(self, detener: threading.Event) -> None:
        print(f"🧹 [Daemon RAM] Centinela de inactividad ({int(self.inactividad_s // 60)} min) activado...")
        while not detener.wait(self.intervalo_s):
            if self._debe_descargar():
                print(f"💤 [Daemon RAM] Inactividad prolongada. Descargando {self.modelo} de la RAM...")
                self._descargar_modelo()


vigilante_ram = VigilanteRAM(MODELO_OLLAMA, INACTIVIDAD_RAM_SEGUNDOS, INTERVALO_VIGILANTE_SEGUNDOS)


# ---------------------------------------------------------------------------
# Radar de voz (Daemon -> React)
# ---------------------------------------------------------------------------
mensajes_radar: "queue.Queue[dict]" = queue.Queue()


def daemon_escucha_activa(detener: threading.Event) -> None:
    print("🎙️ [Daemon de Voz] Iniciando radar permanente...")
    while not detener.is_set():
        try:
            if voz.esperar_palabra_clave():
                # Bengala inmediata: React despierta la UI ya mismo
                mensajes_radar.put({"accion": "despertar"})

                texto_usuario = voz.escuchar()
                if texto_usuario:
                    print(f"\n🗣️ [Micrófono capturó]: '{texto_usuario}'")
                    mensajes_radar.put({"accion": "ejecutar", "texto": texto_usuario})
                else:
                    # Ruido sin voz: se apaga la UI
                    mensajes_radar.put({"accion": "cancelar"})
        except Exception as e:
            print(f"❌ [Error en Daemon de Voz]: {e}")
            time.sleep(2)


# ---------------------------------------------------------------------------
# Inicialización de la app (los daemons arrancan en el lifespan)
# ---------------------------------------------------------------------------
_detener_daemons = threading.Event()


@asynccontextmanager
async def lifespan(_: FastAPI):
    _detener_daemons.clear()
    threading.Thread(target=daemon_escucha_activa, args=(_detener_daemons,), daemon=True).start()
    threading.Thread(target=vigilante_ram.correr, args=(_detener_daemons,), daemon=True).start()
    yield
    _detener_daemons.set()


app = FastAPI(title="L-IA API Bridge", version="3.4.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite que la interfaz de Tauri (webview local) se conecte.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Utilidades compartidas
# ---------------------------------------------------------------------------
def renombrar_sesion_silenciosamente(sesion_id: str, texto_usuario: str) -> None:
    """Genera un título corto basado en el primer mensaje usando el LLM en segundo plano."""
    try:
        conexion = database.obtener_conexion()
        try:
            cursor = conexion.cursor()
            cursor.execute("SELECT titulo FROM sesiones_chat WHERE id = ?", (sesion_id,))
            fila = cursor.fetchone()
        finally:
            conexion.close()

        if not (fila and fila["titulo"] == "Nueva Conversación"):
            return

        prompt = (
            "Actúa como un generador de títulos. Resume este mensaje del usuario "
            "en MÁXIMO 4 PALABRAS. Sin comillas, sin puntos, solo el título directo.\n"
            f"Mensaje: {texto_usuario}"
        )
        with vigilante_ram.generacion_activa():
            respuesta = ollama.chat(
                model=MODELO_OLLAMA,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.2, "num_predict": 15},
            )
        nuevo_titulo = respuesta["message"]["content"].strip('".*\n ')

        # Fallback de seguridad por si responde muy largo
        if len(nuevo_titulo) > 30:
            nuevo_titulo = texto_usuario[:25] + "..."

        database.actualizar_titulo_sesion(sesion_id, nuevo_titulo)
    except Exception as e:
        print(f"⚠️ [Título Automático] Falló el renombrado: {e}")


def crear_puente_ui(cola: queue.Queue):
    """Devuelve el callback que inyecta el delimitador '|||' que React espera para el colapso."""

    def enviar(comando_dict: dict) -> None:
        if comando_dict:
            cola.put(f"data: {json.dumps(comando_dict)}|||\n\n")  # string crudo, se emite tal cual

    return enviar


def generador_sse(cola: queue.Queue) -> Iterator[str]:
    """Consume la cola y emite eventos SSE hasta recibir 'fin' o 'error'."""
    while True:
        try:
            item = cola.get(timeout=TIMEOUT_COLA_STREAMING_SEGUNDOS)
        except queue.Empty:
            yield f"data: {json.dumps({'tipo': 'error', 'texto': 'Tiempo de espera agotado.'})}\n\n"
            return

        if isinstance(item, str):  # comando anómalo ya formateado
            yield item
            continue

        yield f"data: {json.dumps(item)}\n\n"
        if item.get("tipo") in ("fin", "error"):
            return


def _lanzar_colapso(cola: queue.Queue) -> None:
    """Ejecuta la Fase 1 (Voz + IoT + UI) volcando la UI a la cola."""
    eventos_anomalos.desatar_fase_1(
        callback_estado=None,
        callback_ui=crear_puente_ui(cola),
        usar_voz=True,
    )


# ---------------------------------------------------------------------------
# Sesiones
# ---------------------------------------------------------------------------
@app.get("/sesiones")
def listar_todas_las_sesiones():
    """Devuelve la lista de chats para armar el sidebar en React."""
    return database.listar_sesiones()


@app.post("/sesiones/nueva")
def crear_nueva_sesion(titulo: str = "Nueva Conversación"):
    """Crea una pestaña en blanco y devuelve su ID único."""
    return {"sesion_id": database.crear_sesion(titulo)}


@app.get("/sesiones/{sesion_id}/contexto")
def obtener_contexto_sesion(sesion_id: str):
    """Carga los mensajes y el workspace activo al hacer clic en un chat anterior."""
    return {
        "historial": database.obtener_historial_reciente(limite=50, sesion_id=sesion_id),
        "workspace_activo": database.obtener_workspace_activo(sesion_id=sesion_id),
    }


@app.put("/sesiones/{sesion_id}")
def renombrar_sesion_manual(sesion_id: str, req: ActualizarTituloRequest):
    """Permite al usuario editar el título del chat a mano."""
    database.actualizar_titulo_sesion(sesion_id, req.titulo)
    return {"status": "ok"}


@app.delete("/sesiones/{sesion_id}")
def eliminar_sesion_endpoint(sesion_id: str):
    """Borra un historial completo y en cascada."""
    logger.info("[API] Borrando sesión %s", sesion_id)
    try:
        database.borrar_sesion(sesion_id)
        logger.info("[API] Sesión %s eliminada de SQLite.", sesion_id)
        return {"status": "ok"}
    except Exception as e:
        logger.error("[API] Error al borrar sesión %s: %s", sesion_id, e)
        return {"status": "error", "detalle": str(e)}


# ---------------------------------------------------------------------------
# Semáforo (usado por React)
# ---------------------------------------------------------------------------
@app.get("/semaforo")
async def verificar_semaforo():
    """React llama aquí cada segundo (polling) para saber si L-IA está
    pausada esperando que el usuario autorice o deniegue una herramienta."""
    return semaforo.estado_actual()


@app.post("/semaforo/responder")
async def responder_semaforo(respuesta: RespuestaSemaforo):
    """React llama aquí cuando el usuario hace clic en "Autorizar" o "Denegar"."""
    semaforo.registrar_respuesta(respuesta.autorizado)
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Chat principal (Streaming SSE)
# ---------------------------------------------------------------------------
@app.post("/chat")
def recibir_chat(mensaje: MensajeUsuario):
    vigilante_ram.marcar_uso()  # reinicia el reloj de inactividad

    entrada = mensaje.texto.strip()
    sesion_actual = mensaje.sesion_id
    logger.info("[Usuario | Sesión: %s] -> %s", sesion_actual[:8], entrada)

    cola_streaming: queue.Queue = queue.Queue()

    # 1. Trigger manual (comando de debug)
    if entrada == "/run_fase_1":

        def hilo_colapso_manual():
            try:
                _lanzar_colapso(cola_streaming)
                cola_streaming.put({"tipo": "fin", "origen": "sistema"})
            except Exception as e:
                cola_streaming.put({"tipo": "error", "texto": str(e)})

        threading.Thread(target=hilo_colapso_manual, daemon=True).start()

    # 2. Flujo normal y trigger orgánico
    else:
        threading.Thread(
            target=renombrar_sesion_silenciosamente, args=(sesion_actual, entrada), daemon=True
        ).start()
        ya_respondio = {"estado": False}

        def stream_consola(fragmento: str) -> None:
            if not ya_respondio["estado"]:
                voz.detener_efecto_pensando()
                ya_respondio["estado"] = True
            print(fragmento, end="", flush=True)
            cola_streaming.put({"tipo": "chunk", "texto": fragmento})

        def permiso_interfaz(herramienta: str, argumentos: Any) -> bool:
            return semaforo.solicitar_autorizacion(herramienta, argumentos)

        def estado_interfaz(info: dict) -> None:
            cola_streaming.put({"tipo": "estado", **info})

        def hilo_ia():
            try:
                voz.reproducir_efecto("pensando")

                # Mientras dure la respuesta, el vigilante no descarga el modelo
                with vigilante_ram.generacion_activa():
                    _, origen = charlar_con_lia(
                        entrada,
                        callback_ui=permiso_interfaz,
                        callback_stream=stream_consola,
                        callback_estado=estado_interfaz,
                        sesion_id=sesion_actual,
                        usar_voz=mensaje.usar_voz,
                    )

                voz.detener_efecto_pensando()

                doc_activo = None
                nombre_workspace = None
                try:
                    doc_activo = database.obtener_workspace_activo(sesion_id=sesion_actual)
                    if doc_activo:
                        nombre_workspace = os.path.basename(doc_activo)
                except Exception:
                    pass

                cola_streaming.put(
                    {"tipo": "fin", "origen": origen, "documento": doc_activo, "workspace": nombre_workspace}
                )

            except Exception as e:
                voz.detener_efecto_pensando()

                # Colapso orgánico lanzado desde cerebro.py
                if str(e) == TRIGGER_COLAPSO:
                    logger.warning("¡Hostilidad al máximo! Disparando Fase 1 orgánica...")
                    try:
                        _lanzar_colapso(cola_streaming)
                        cola_streaming.put({"tipo": "fin", "origen": "sistema"})
                    except Exception as e2:
                        cola_streaming.put({"tipo": "error", "texto": str(e2)})
                else:
                    cola_streaming.put({"tipo": "error", "texto": str(e)})

        threading.Thread(target=hilo_ia, daemon=True).start()

    return StreamingResponse(generador_sse(cola_streaming), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# Lector de pantalla (Edge TTS)
# ---------------------------------------------------------------------------
@app.post("/lector")
def leer_pantalla(req: PeticionLector):
    """Botón de accesibilidad: lectura rápida de bloques de texto con Edge TTS."""
    threading.Thread(target=voz.leer_pantalla_directo, args=(req.texto, "edge"), daemon=True).start()
    return {"status": "ok", "mensaje": "Lectura iniciada"}


# ---------------------------------------------------------------------------
# Abortar (botón de pánico)
# ---------------------------------------------------------------------------
@app.post("/cancelar")
async def cancelar_generacion():
    """Detiene la inferencia del LLM y silencia cualquier audio en reproducción."""
    logger.info("[API] Orden de abortar recibida. Deteniendo LLM y audio...")
    evento_interrupcion.set()  # el Cerebro deja de generar texto
    try:
        voz.detener_audio_global()  # apaga los altavoces de golpe
    except Exception as e:
        logger.warning("No se pudo silenciar el audio: %s", e)
    return {"status": "abortado"}


# ---------------------------------------------------------------------------
# Micrófono manual (React -> Whisper)
# ---------------------------------------------------------------------------
@app.post("/escuchar")
def escuchar_manual():
    """Abre el micrófono local (Whisper) directamente desde la interfaz de React."""
    try:
        logger.info("[API] Abriendo Whisper manualmente...")
        return {"texto": voz.escuchar()}
    except Exception as e:
        logger.error("[API] Error crítico de micrófono: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Radar (Daemon de voz -> React)
# ---------------------------------------------------------------------------
@app.get("/radar/leer")
def leer_radar():
    """React consulta aquí rápidamente para ver el estado del micrófono."""
    try:
        return {"hay_mensaje": True, "datos": mensajes_radar.get_nowait()}
    except queue.Empty:
        return {"hay_mensaje": False}


# ---------------------------------------------------------------------------
# Debug: disparar el evento anómalo desde un botón de pruebas
# ---------------------------------------------------------------------------
_candado_colapso = threading.Lock()


@app.post("/debug/forzar_fase_1")
def disparar_evento_anomalo():
    # Si ya está corriendo, se ignora el clic
    if not _candado_colapso.acquire(blocking=False):
        return {"status": "ignorado", "mensaje": "Ya está en curso"}

    cola_streaming: queue.Queue = queue.Queue()

    def hilo_orquestador():
        try:
            _lanzar_colapso(cola_streaming)
            cola_streaming.put({"tipo": "fin", "origen": "sistema"})
        except Exception as e:
            logger.error("[Error Orquestador]: %s", e)
            cola_streaming.put({"tipo": "error", "texto": str(e)})
        finally:
            _candado_colapso.release()  # libera el candado al terminar o fallar

    threading.Thread(target=hilo_orquestador, daemon=True).start()
    return StreamingResponse(generador_sse(cola_streaming), media_type="text/event-stream")