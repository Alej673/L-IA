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

Mecanismos de fondo (arrancan y se apagan en el lifespan de la app):
  * Semáforo: cuando L-IA quiere ejecutar una herramienta sensible, se pausa
    y espera que el usuario autorice o deniegue desde la interfaz. El frontend
    hace polling (GET /semaforo cada segundo), así que se usa un
    threading.Event para bloquear el hilo del backend hasta que llegue la
    respuesta o se cumpla el timeout.
  * Vigilante de RAM: si pasan 5 minutos sin usar el LLM, se descarga el
    modelo de Ollama (keep_alive=0) para liberar memoria.
  * Daemon de voz (radar): escucha la palabra clave y avisa a React.
  * Orquestador de microservicios: lanza los ejecutables Go de ./microservicios
    (misma altura que este archivo) y los detiene al cerrar la API.

Organización del archivo:
  1. Configuración          5. Orquestador de microservicios
  2. Modelos Pydantic       6. Lifespan y app
  3. Semáforo               7. Helpers compartidos (SSE, colapso, títulos)
  4. Vigilante de RAM       8. Routers (sesiones, semáforo, chat, voz, debug)
"""
import json
import logging
import os
import queue
import subprocess
import threading
import time
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator, Optional

import ollama
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import core.eventos_anomalos as eventos_anomalos
import core.voz as voz
from core import database
from core.cerebro import charlar_con_lia, evento_interrupcion

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("lia.api")


# ===========================================================================
# 1. Configuración
# ===========================================================================
BASE_DIR = Path(__file__).resolve().parent
DIRECTORIO_MICROSERVICIOS = BASE_DIR / "microservicios"

# nombre lógico -> ejecutable dentro de ./microservicios
MICROSERVICIOS_GO = {
    "motor_go_principal": "sensor.exe",
}

TIMEOUT_AUTORIZACION_SEGUNDOS = 120    # tiempo máximo esperando el clic del usuario
TIMEOUT_COLA_STREAMING_SEGUNDOS = 180  # corta la conexión SSE si el hilo de la IA se traba
MODELO_OLLAMA = "gemma2"               # debe coincidir con el modelo que usa core.cerebro
INACTIVIDAD_RAM_SEGUNDOS = 300         # 5 min sin uso -> se descarga el modelo
INTERVALO_VIGILANTE_SEGUNDOS = 30      # cada cuánto revisa el centinela

TRIGGER_COLAPSO = "TRIGGER_COLAPSO_FASE_1"
COMANDO_DEBUG_COLAPSO = "/run_fase_1"
TITULO_SESION_POR_DEFECTO = "Nueva Conversación"

# Orígenes desde los que el frontend puede llamar a la API. Ajusta según tu
# puerto de desarrollo (Vite: 5173, Tauri dev: 1420).
ORIGENES_PERMITIDOS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:1420",
    "http://127.0.0.1:1420",
    "tauri://localhost",
    "http://tauri.localhost",
]


# ===========================================================================
# 2. Modelos Pydantic
# ===========================================================================
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

class RespuestaSeleccionArchivo(BaseModel):
    ruta: Optional[str] = None

class SolicitudDesambiguacion(BaseModel):
    opciones: list[dict]

# ===========================================================================
# 3. Semáforos de Interfaz (Autorizaciones y Desambiguación)
# ===========================================================================

# --- SEMÁFORO 1: Seguridad (Espera True/False) ---
@dataclass
class SemaforoAutorizacion:
    """Pausa a L-IA cuando necesita permiso del usuario para ejecutar Nivel 2."""
    evento: threading.Event = field(default_factory=threading.Event)
    lock: threading.Lock = field(default_factory=threading.Lock)
    alerta_actual: Optional[dict] = None
    autorizacion_concedida: bool = False

    def solicitar_autorizacion(self, herramienta: str, argumentos: Any) -> bool:
        with self.lock:
            self.autorizacion_concedida = False
            self.evento.clear()
            self.alerta_actual = {"herramienta": herramienta, "argumentos": str(argumentos)}

            logger.info("Esperando autorización del usuario para: %s", herramienta)
            try:
                respondio_a_tiempo = self.evento.wait(timeout=TIMEOUT_AUTORIZACION_SEGUNDOS)
            finally:
                self.alerta_actual = None

            if not respondio_a_tiempo:
                logger.warning("Tiempo agotado para: %s. Abortando por defecto.", herramienta)
                return False

            return self.autorizacion_concedida

    def registrar_respuesta(self, autorizado: bool) -> bool:
        if self.alerta_actual is None:
            return False
        self.autorizacion_concedida = autorizado
        self.evento.set()
        return True

    def estado_actual(self) -> dict:
        alerta = self.alerta_actual
        if alerta:
            return {"activa": True, "herramienta": alerta["herramienta"], "argumentos": alerta["argumentos"]}
        return {"activa": False}

semaforo = SemaforoAutorizacion()


# --- SEMÁFORO 2: Buscador de Archivos (Espera una ruta de texto) ---
@dataclass
class SemaforoArchivos:
    """Pausa a L-IA para que el usuario elija entre múltiples archivos en la UI."""
    evento: threading.Event = field(default_factory=threading.Event)
    lock: threading.Lock = field(default_factory=threading.Lock)
    opciones_actuales: Optional[list] = None
    ruta_seleccionada: Optional[str] = None

    def solicitar_seleccion(self, opciones: list) -> Optional[str]:
        with self.lock:
            self.ruta_seleccionada = None
            self.opciones_actuales = opciones
            self.evento.clear()

            logger.info("Esperando selección de archivo desde React...")
            self.evento.wait(timeout=TIMEOUT_AUTORIZACION_SEGUNDOS)
            
            self.opciones_actuales = None
            return self.ruta_seleccionada

    def registrar_respuesta(self, ruta: Optional[str]) -> bool:
        if self.opciones_actuales is None:
            return False
        self.ruta_seleccionada = ruta
        self.evento.set()
        return True

    def estado_actual(self) -> dict:
        if self.opciones_actuales:
            return {"activa": True, "opciones": self.opciones_actuales}
        return {"activa": False}

semaforo_archivos = SemaforoArchivos()

# ===========================================================================
# 4. Vigilante de RAM (descarga el modelo de Ollama tras inactividad)
# ===========================================================================
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
            logger.info("[Daemon RAM] %s descargado, RAM liberada.", self.modelo)
        except Exception as e:
            logger.warning("[Daemon RAM] Error al intentar limpiar la RAM: %s", e)

    def correr(self, detener: threading.Event) -> None:
        logger.info(
            "[Daemon RAM] Centinela de inactividad (%d min) activado.",
            int(self.inactividad_s // 60),
        )
        while not detener.wait(self.intervalo_s):
            if self._debe_descargar():
                logger.info("[Daemon RAM] Inactividad prolongada. Descargando %s...", self.modelo)
                self._descargar_modelo()


vigilante_ram = VigilanteRAM(MODELO_OLLAMA, INACTIVIDAD_RAM_SEGUNDOS, INTERVALO_VIGILANTE_SEGUNDOS)


# ===========================================================================
# Radar de voz (Daemon -> React)
# ===========================================================================
mensajes_radar: "queue.Queue[dict]" = queue.Queue()


def daemon_escucha_activa(detener: threading.Event) -> None:
    logger.info("[Daemon de Voz] Iniciando radar permanente...")
    while not detener.is_set():
        try:
            if voz.esperar_palabra_clave():
                # Bengala inmediata: React despierta la UI ya mismo
                mensajes_radar.put({"accion": "despertar"})

                texto_usuario = voz.escuchar()
                if texto_usuario:
                    logger.info("[Micrófono capturó]: '%s'", texto_usuario)
                    mensajes_radar.put({"accion": "ejecutar", "texto": texto_usuario})
                else:
                    # Ruido sin voz: se apaga la UI
                    mensajes_radar.put({"accion": "cancelar"})
        except Exception as e:
            logger.error("[Daemon de Voz] Error: %s", e)
            time.sleep(2)


# ===========================================================================
# 5. Orquestador de microservicios (Go)
# ===========================================================================
class OrquestadorMicroservicios:
    """Lanza y detiene los ejecutables de ./microservicios junto con la API."""

    def __init__(self, directorio: Path, servicios: dict[str, str]):
        self.directorio = directorio
        self.servicios = servicios
        self._procesos: list[tuple[str, subprocess.Popen]] = []

    def iniciar(self) -> None:
        # CREATE_NO_WINDOW solo existe en Windows; en otros sistemas se ignora.
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

        for nombre, ejecutable in self.servicios.items():
            ruta_exe = self.directorio / ejecutable
            if not ruta_exe.exists():
                logger.warning("[Orquestador] No se encontró el ejecutable en: %s", ruta_exe)
                continue
            try:
                # cwd = carpeta del exe, por si lee archivos con rutas relativas
                proc = subprocess.Popen([str(ruta_exe)], cwd=self.directorio, creationflags=flags)
                self._procesos.append((nombre, proc))
                logger.info("[Orquestador] Microservicio Go '%s' iniciado (pid %s).", nombre, proc.pid)
            except Exception as e:
                logger.error("[Orquestador] Falló el inicio de '%s': %s", nombre, e)

    def detener(self) -> None:
        for nombre, proc in self._procesos:
            if proc.poll() is not None:
                continue  # ya había terminado
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning("[Orquestador] '%s' no respondió a terminate(); forzando kill.", nombre)
                    proc.kill()
                    proc.wait()
                logger.info("[Orquestador] Microservicio '%s' detenido.", nombre)
            except Exception as e:
                logger.warning("[Orquestador] No se pudo detener '%s': %s", nombre, e)
        self._procesos.clear()


orquestador = OrquestadorMicroservicios(DIRECTORIO_MICROSERVICIOS, MICROSERVICIOS_GO)


# ===========================================================================
# 6. Lifespan y app
# ===========================================================================
_detener_daemons = threading.Event()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Arranque
    _detener_daemons.clear()
    orquestador.iniciar()
    threading.Thread(
        target=daemon_escucha_activa, args=(_detener_daemons,), name="daemon-voz", daemon=True
    ).start()
    threading.Thread(
        target=vigilante_ram.correr, args=(_detener_daemons,), name="vigilante-ram", daemon=True
    ).start()

    try:
        yield
    finally:
        # Apagado (también si el arranque se interrumpe)
        _detener_daemons.set()
        orquestador.detener()


app = FastAPI(title="L-IA API Bridge", version="3.4.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENES_PERMITIDOS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===========================================================================
# 7. Helpers compartidos
# ===========================================================================
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

        if not (fila and fila["titulo"] == TITULO_SESION_POR_DEFECTO):
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
        logger.warning("[Título Automático] Falló el renombrado: %s", e)


def crear_puente_ui(cola: queue.Queue) -> Callable[[dict], None]:
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


def respuesta_sse(cola: queue.Queue) -> StreamingResponse:
    return StreamingResponse(generador_sse(cola), media_type="text/event-stream")


def _lanzar_colapso(cola: queue.Queue) -> None:
    """Ejecuta la Fase 1 (Voz + IoT + UI) volcando la UI a la cola. Puede lanzar excepciones."""
    eventos_anomalos.desatar_fase_1(
        callback_estado=None,
        callback_ui=crear_puente_ui(cola),
        usar_voz=True,
    )


def _colapso_y_cerrar(cola: queue.Queue) -> None:
    """Corre el colapso y cierra el stream con 'fin' o 'error'."""
    try:
        _lanzar_colapso(cola)
        cola.put({"tipo": "fin", "origen": "sistema"})
    except Exception as e:
        logger.error("[Colapso] Error: %s", e)
        cola.put({"tipo": "error", "texto": str(e)})


def _colapso_en_hilo(cola: queue.Queue, al_terminar: Optional[Callable[[], None]] = None) -> None:
    """Lanza el colapso en un hilo; `al_terminar` se ejecuta siempre (éxito o fallo)."""

    def tarea() -> None:
        try:
            _colapso_y_cerrar(cola)
        finally:
            if al_terminar:
                al_terminar()

    threading.Thread(target=tarea, name="colapso-fase-1", daemon=True).start()


def _workspace_activo(sesion_id: str) -> tuple[Optional[str], Optional[str]]:
    """Devuelve (ruta, nombre de archivo) del workspace activo, o (None, None)."""
    try:
        doc_activo = database.obtener_workspace_activo(sesion_id=sesion_id)
        if doc_activo:
            return doc_activo, os.path.basename(doc_activo)
    except Exception as e:
        logger.debug("No se pudo leer el workspace activo de %s: %s", sesion_id, e)
    return None, None


def _hilo_chat(entrada: str, mensaje: MensajeUsuario, cola: queue.Queue) -> None:
    """Cuerpo del hilo que conversa con L-IA y vuelca el resultado a la cola SSE."""
    sesion_id = mensaje.sesion_id
    ya_respondio = False

    def stream_consola(fragmento: str) -> None:
        nonlocal ya_respondio
        if not ya_respondio:
            voz.detener_efecto_pensando()
            ya_respondio = True
        print(fragmento, end="", flush=True)
        cola.put({"tipo": "chunk", "texto": fragmento})

    def permiso_interfaz(herramienta: str, argumentos: Any) -> bool:
        return semaforo.solicitar_autorizacion(herramienta, argumentos)

    def estado_interfaz(info: dict) -> None:
        cola.put({"tipo": "estado", **info})

    try:
        voz.reproducir_efecto("pensando")

        # Mientras dure la respuesta, el vigilante no descarga el modelo
        with vigilante_ram.generacion_activa():
            _, origen = charlar_con_lia(
                entrada,
                callback_ui=permiso_interfaz,
                callback_stream=stream_consola,
                callback_estado=estado_interfaz,
                sesion_id=sesion_id,
                usar_voz=mensaje.usar_voz,
            )

        voz.detener_efecto_pensando()

        doc_activo, nombre_workspace = _workspace_activo(sesion_id)
        cola.put(
            {"tipo": "fin", "origen": origen, "documento": doc_activo, "workspace": nombre_workspace}
        )

    except Exception as e:
        voz.detener_efecto_pensando()

        # Colapso orgánico lanzado desde cerebro.py
        if str(e) == TRIGGER_COLAPSO:
            logger.warning("¡Hostilidad al máximo! Disparando Fase 1 orgánica...")
            _colapso_y_cerrar(cola)
        else:
            logger.error("[Chat] Error: %s", e)
            cola.put({"tipo": "error", "texto": str(e)})


# ===========================================================================
# 8. Routers
# ===========================================================================

# --- Sesiones ---------------------------------------------------------------
router_sesiones = APIRouter(prefix="/sesiones", tags=["sesiones"])


@router_sesiones.get("")
def listar_todas_las_sesiones():
    """Devuelve la lista de chats para armar el sidebar en React."""
    return database.listar_sesiones()


@router_sesiones.post("/nueva")
def crear_nueva_sesion(titulo: str = TITULO_SESION_POR_DEFECTO):
    """Crea una pestaña en blanco y devuelve su ID único."""
    return {"sesion_id": database.crear_sesion(titulo)}


@router_sesiones.get("/{sesion_id}/contexto")
def obtener_contexto_sesion(sesion_id: str):
    """Carga los mensajes y el workspace activo al hacer clic en un chat anterior."""
    return {
        "historial": database.obtener_historial_reciente(limite=50, sesion_id=sesion_id),
        "workspace_activo": database.obtener_workspace_activo(sesion_id=sesion_id),
    }


@router_sesiones.put("/{sesion_id}")
def renombrar_sesion_manual(sesion_id: str, req: ActualizarTituloRequest):
    """Permite al usuario editar el título del chat a mano."""
    database.actualizar_titulo_sesion(sesion_id, req.titulo)
    return {"status": "ok"}


@router_sesiones.delete("/{sesion_id}")
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


# --- Semáforo (usado por React) --------------------------------------------
router_semaforo = APIRouter(prefix="/semaforo", tags=["semaforo"])


@router_semaforo.get("")
async def verificar_semaforo():
    """React llama aquí cada segundo (polling) para saber si L-IA está
    pausada esperando que el usuario autorice o deniegue una herramienta."""
    return semaforo.estado_actual()


@router_semaforo.post("/responder")
async def responder_semaforo(respuesta: RespuestaSemaforo):
    """React llama aquí cuando el usuario hace clic en "Autorizar" o "Denegar"."""
    aceptada = semaforo.registrar_respuesta(respuesta.autorizado)
    return {"status": "ok" if aceptada else "ignorado"}


# --- Chat principal (Streaming SSE) ----------------------------------------
router_chat = APIRouter(tags=["chat"])


@router_chat.post("/chat")
def recibir_chat(mensaje: MensajeUsuario):
    vigilante_ram.marcar_uso()  # reinicia el reloj de inactividad

    entrada = mensaje.texto.strip()
    sesion_actual = mensaje.sesion_id
    logger.info("[Usuario | Sesión: %s] -> %s", sesion_actual[:8], entrada)

    cola_streaming: queue.Queue = queue.Queue()

    if entrada == COMANDO_DEBUG_COLAPSO:
        # Trigger manual (comando de debug)
        _colapso_en_hilo(cola_streaming)
    else:
        # Flujo normal y trigger orgánico. Se limpia una posible cancelación
        # previa para que /cancelar no deje cortados los chats siguientes.
        evento_interrupcion.clear()
        threading.Thread(
            target=renombrar_sesion_silenciosamente,
            args=(sesion_actual, entrada),
            name="renombrar-sesion",
            daemon=True,
        ).start()
        threading.Thread(
            target=_hilo_chat,
            args=(entrada, mensaje, cola_streaming),
            name="chat-ia",
            daemon=True,
        ).start()

    return respuesta_sse(cola_streaming)


# --- Voz: lector, micrófono manual, radar, abortar --------------------------
router_voz = APIRouter(tags=["voz"])


@router_voz.post("/lector")
def leer_pantalla(req: PeticionLector):
    """Botón de accesibilidad: lectura rápida de bloques de texto con Edge TTS."""
    threading.Thread(
        target=voz.leer_pantalla_directo, args=(req.texto, "edge"), name="lector-tts", daemon=True
    ).start()
    return {"status": "ok", "mensaje": "Lectura iniciada"}


@router_voz.post("/cancelar")
async def cancelar_generacion():
    """Botón de pánico: detiene la inferencia del LLM y silencia cualquier audio."""
    logger.info("[API] Orden de abortar recibida. Deteniendo LLM y audio...")
    evento_interrupcion.set()  # el Cerebro deja de generar texto
    try:
        voz.detener_audio_global()  # apaga los altavoces de golpe
    except Exception as e:
        logger.warning("No se pudo silenciar el audio: %s", e)
    return {"status": "abortado"}


@router_voz.post("/escuchar")
def escuchar_manual():
    """Abre el micrófono local (Whisper) directamente desde la interfaz de React."""
    try:
        logger.info("[API] Abriendo Whisper manualmente...")
        return {"texto": voz.escuchar()}
    except Exception as e:
        logger.error("[API] Error crítico de micrófono: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router_voz.get("/radar/leer")
def leer_radar():
    """React consulta aquí rápidamente para ver el estado del micrófono."""
    try:
        return {"hay_mensaje": True, "datos": mensajes_radar.get_nowait()}
    except queue.Empty:
        return {"hay_mensaje": False}


# --- Debug: disparar el evento anómalo desde un botón de pruebas -----------
router_debug = APIRouter(tags=["debug"])
_candado_colapso = threading.Lock()


@router_debug.post("/debug/forzar_fase_1")
def disparar_evento_anomalo():
    # Si ya está corriendo, se ignora el clic
    if not _candado_colapso.acquire(blocking=False):
        return {"status": "ignorado", "mensaje": "Ya está en curso"}

    cola_streaming: queue.Queue = queue.Queue()
    # El candado se libera al terminar o fallar el colapso
    _colapso_en_hilo(cola_streaming, al_terminar=_candado_colapso.release)
    return respuesta_sse(cola_streaming)


# --- Registro de routers ----------------------------------------------------
for _router in (router_sesiones, router_semaforo, router_chat, router_voz, router_debug):
    app.include_router(_router)

@router_semaforo.get("/archivos")
async def verificar_semaforo_archivos():
    """React hace polling aquí para saber si debe mostrar el modal de archivos."""
    return semaforo_archivos.estado_actual()

@router_semaforo.post("/archivos/responder")
async def responder_semaforo_archivos(respuesta: RespuestaSeleccionArchivo):
    """React envía la ruta exacta que el usuario clickeó en el modal."""
    aceptada = semaforo_archivos.registrar_respuesta(respuesta.ruta)
    return {"status": "ok" if aceptada else "ignorado"}

@router_semaforo.post("/interno/esperar_archivo")
def esperar_archivo_interno(req: SolicitudDesambiguacion):
    """tools.py llama a este endpoint interno y se queda congelado esperando a React."""
    ruta = semaforo_archivos.solicitar_seleccion(req.opciones)
    return {"ruta": ruta}