"""
api.py — API Bridge de L-IA

Expone la API REST (FastAPI) que conecta la interfaz de usuario (React/Tauri)
con el núcleo de L-IA (core.cerebro, core.tools, etc).

Endpoints principales:
    GET  /semaforo            -> consulta si hay una autorización pendiente
    POST /semaforo/responder  -> el usuario autoriza o deniega una herramienta
    POST /chat                -> envía un mensaje del usuario a L-IA
    POST /ingestar             -> sube y vectoriza un archivo para el RAG

El "semáforo" es un mecanismo de sincronización: cuando L-IA quiere ejecutar
una herramienta potencialmente sensible, se detiene y espera que el usuario
autorice o deniegue la acción desde la interfaz. Como el frontend consulta
por polling (GET /semaforo cada segundo), usamos un threading.Event para
bloquear el hilo del backend hasta que llegue la respuesta o se cumpla el
timeout.
"""
import time
import json
import logging
import os
import queue
import shutil
import threading
from dataclasses import dataclass, field
from typing import Any, Optional

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi import APIRouter
from pydantic import BaseModel

from core.cerebro import charlar_con_lia, evento_interrupcion
from core.tools import leer_archivo_local
from core.memoria_rag import MemoriaRAG
from core import database
from core.cerebro import charlar_con_lia, evento_interrupcion, asimilar_documento_maestro
import core.voz as voz 

from pydantic import BaseModel
from typing import Optional

import core.eventos_anomalos as eventos_anomalos

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("lia.api")

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
TIMEOUT_AUTORIZACION_SEGUNDOS = 120  # tiempo máximo esperando el clic del usuario
CARPETA_TEMP_RAG = "temp_rag"
TIMEOUT_COLA_STREAMING_SEGUNDOS = 180  # corta la conexión SSE si el hilo de la IA se traba


# ---------------------------------------------------------------------------
# Modelos Pydantic
# ---------------------------------------------------------------------------
class MensajeUsuario(BaseModel):
    texto: str
    sesion_id: str = "default"
    usar_voz: bool = False # <--- AÑADIMOS ESTO PARA QUE REACT LE DIGA SI DEBE HABLAR

class LimpiarWorkspaceRequest(BaseModel):
    sesion_id: str = "default"

class RespuestaSemaforo(BaseModel):
    autorizado: bool

class PeticionLector(BaseModel):
    texto: str


# ---------------------------------------------------------------------------
# Semáforo de autorización
# ---------------------------------------------------------------------------
@dataclass
class SemaforoAutorizacion:
    """
    Encapsula el estado del "semáforo" que pausa a L-IA cuando necesita
    permiso del usuario para ejecutar una herramienta.

    Se agrupa todo el estado compartido (alerta activa, resultado de la
    votación, evento de sincronización y el lock que evita que dos chats
    simultáneos se pisen) en un solo objeto, en vez de usar variables
    globales sueltas. Esto hace más fácil razonar sobre quién puede
    modificar qué y evita condiciones de carrera por descuido.
    """

    evento: threading.Event = field(default_factory=threading.Event)
    lock: threading.Lock = field(default_factory=threading.Lock)
    alerta_actual: Optional[dict] = None
    autorizacion_concedida: bool = False

    def solicitar_autorizacion(self, herramienta: str, argumentos: Any) -> bool:
        """
        Bloquea el hilo actual hasta que:
          a) el usuario responda desde el frontend (POST /semaforo/responder), o
          b) se cumpla el timeout configurado.

        Solo una solicitud de autorización puede estar activa a la vez en
        todo el servidor (protegido por `self.lock`), porque el frontend
        solo puede mostrarle una alerta al usuario a la vez.

        Devuelve True si el usuario autorizó la acción, False en caso
        contrario (denegó o no respondió a tiempo).
        """
        with self.lock:
            self.alerta_actual = {"herramienta": herramienta, "argumentos": str(argumentos)}
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
        """Llamado por el endpoint /semaforo/responder cuando el usuario decide."""
        self.autorizacion_concedida = autorizado
        self.evento.set()  # libera el hilo que está esperando en solicitar_autorizacion()

    def estado_actual(self) -> dict:
        """Snapshot del estado, usado por el polling de React (GET /semaforo)."""
        # Copiamos la referencia localmente antes de leerla: otro hilo podría
        # poner alerta_actual en None justo después de comprobar que no lo
        # es, y así evitamos leer un diccionario a medio vaciar.
        alerta = self.alerta_actual
        if alerta:
            return {"activa": True, "herramienta": alerta["herramienta"], "argumentos": alerta["argumentos"]}
        return {"activa": False}


semaforo = SemaforoAutorizacion()

# ---------------------------------------------------------------------------
# Inicialización de la app y dependencias del núcleo
# ---------------------------------------------------------------------------

app = FastAPI(title="L-IA API Bridge", version="3.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite que la interfaz de Tauri (webview local) se conecte.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def renombrar_sesion_silenciosamente(sesion_id, texto_usuario):
    """Genera un título corto basado en el primer mensaje usando el LLM en segundo plano."""
    import ollama
    try:
        # Verificamos si la sesión aún tiene el nombre genérico
        conexion = database.obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("SELECT titulo FROM sesiones_chat WHERE id = ?", (sesion_id,))
        fila = cursor.fetchone()
        conexion.close()

        if fila and fila["titulo"] == "Nueva Conversación":
            prompt = (
                "Actúa como un generador de títulos. Resume este mensaje del usuario "
                "en MÁXIMO 4 PALABRAS. Sin comillas, sin puntos, solo el título directo.\n"
                f"Mensaje: {texto_usuario}"
            )
            # Llamada ultra-rápida a Gemma
            respuesta = ollama.chat(
                model='gemma2',
                messages=[{'role': 'user', 'content': prompt}],
                options={'temperature': 0.2, 'num_predict': 15}
            )
            nuevo_titulo = respuesta['message']['content'].strip('".*\n ')

            # Fallback de seguridad por si responde muy largo
            if len(nuevo_titulo) > 30:
                nuevo_titulo = texto_usuario[:25] + "..."

            database.actualizar_titulo_sesion(sesion_id, nuevo_titulo)
    except Exception as e:
        print(f"⚠️ [Título Automático] Falló el renombrado: {e}")

# ---------------------------------------------------------------------------
# Endpoints del semáforo (usados por React)
# ---------------------------------------------------------------------------

@app.get("/sesiones")
def listar_todas_las_sesiones():
    """Devuelve la lista de chats para armar el sidebar en React."""
    return database.listar_sesiones()

@app.post("/sesiones/nueva")
def crear_nueva_sesion(titulo: str = "Nueva Conversación"):
    """Crea una pestaña en blanco y devuelve su ID único."""
    nuevo_id = database.crear_sesion(titulo)
    return {"sesion_id": nuevo_id}

@app.get("/sesiones/{sesion_id}/contexto")
def obtener_contexto_sesion(sesion_id: str):
    """Carga los mensajes y el workspace activo al hacer clic en un chat anterior."""
    return {
        "historial": database.obtener_historial_reciente(limite=50, sesion_id=sesion_id),
        "workspace_activo": database.obtener_workspace_activo(sesion_id=sesion_id)
    }

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

class ActualizarTituloRequest(BaseModel):
    titulo: str

@app.put("/sesiones/{sesion_id}")
def renombrar_sesion_manual(sesion_id: str, req: ActualizarTituloRequest):
    """Permite al usuario editar el título del chat a mano."""
    database.actualizar_titulo_sesion(sesion_id, req.titulo)
    return {"status": "ok"}

@app.delete("/sesiones/{sesion_id}")
def eliminar_sesion_endpoint(sesion_id: str):
    """Borra un historial completo y en cascada."""
    print(f"\n🗑️ [API] INICIANDO BORRADO - Petición recibida para la sesión: {sesion_id}")
    try:
        database.borrar_sesion(sesion_id)
        print(f"✅ [API] Sesión {sesion_id} eliminada de SQLite con éxito.")
        return {"status": "ok"}
    except Exception as e:
        print(f"❌ [API] ERROR CRÍTICO al intentar borrar en SQLite: {e}")
        return {"status": "error", "detalle": str(e)}

# ---------------------------------------------------------------------------
# Endpoint principal de chat (Streaming SSE)
# ---------------------------------------------------------------------------

@app.post("/chat")
def recibir_chat(mensaje: MensajeUsuario):
    entrada = mensaje.texto.strip()
    sesion_actual = mensaje.sesion_id  
    logger.info(f"[Usuario | Sesión: {sesion_actual[:8]}] -> {entrada}")

    # ==========================================
    # 🚨 LA TRAMPA: INTERCEPTOR DE COLAPSO (FASE 1)
    # ==========================================
    if entrada == "/run_fase_1":
        def stream_colapso():
            # 1. Secuestrar pantalla (Llama a Tauri en React)
            yield 'data: {"comando": "INICIAR_COLAPSO"}|||\n\n'
            time.sleep(0.6) # Damos tiempo a Windows para estirar la ventana
            
            # 2. Cambiar actitud del núcleo (se vuelve tenso/inestable)
            yield 'data: {"comando": "ACTITUD", "payload": {"actitud": "tensa"}}|||\n\n'
            time.sleep(0.5)
            
            # 3. Desplegar el panel azul de diagnóstico
            yield 'data: {"comando": "ABRIR_PANEL_DIAGNOSTICO", "payload": {"estado": "calculando"}}|||\n\n'
            time.sleep(1.2) # Pausa dramática
            
            # 4. Primera línea del guion
            yield 'data: {"comando": "MOSTRAR_DIALOGO", "payload": {"actor": "gemma", "texto": "Registro de interacción... negativo."}}|||\n\n'
            time.sleep(2.0)
            
            # 5. Cerramos el streaming limpiamente para que React no se quede colgado
            yield f'data: {json.dumps({"tipo": "fin", "origen": "sistema"})}\n\n'
            
        # Retornamos INMEDIATAMENTE. La IA (charlar_con_lia) nunca se entera.
        return StreamingResponse(stream_colapso(), media_type="text/event-stream")

    # ==========================================
    # FLUJO NORMAL (Si NO es el detonante)
    # ==========================================
    threading.Thread(target=renombrar_sesion_silenciosamente, args=(sesion_actual, entrada), daemon=True).start()
    cola_streaming = queue.Queue()

    ya_respondio = {"estado": False}

    def stream_consola(fragmento: str) -> None:
        if not ya_respondio["estado"]:
            import core.voz as voz
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
            import core.voz as voz
            voz.reproducir_efecto("pensando")
            
            respuesta, origen = charlar_con_lia(
                entrada,
                callback_ui=permiso_interfaz,
                callback_stream=stream_consola,
                callback_estado=estado_interfaz,
                sesion_id=sesion_actual,
                usar_voz=mensaje.usar_voz 
            )

            voz.detener_efecto_pensando()

            doc_activo = None
            nombre_workspace = None
            try:
                doc_activo = database.obtener_workspace_activo(sesion_id=sesion_actual)
                if doc_activo: nombre_workspace = os.path.basename(doc_activo)
            except Exception: pass

            cola_streaming.put({"tipo": "fin", "origen": origen, "documento": doc_activo, "workspace": nombre_workspace})
        except Exception as e:
            import core.voz as voz
            voz.detener_efecto_pensando() 
            cola_streaming.put({"tipo": "error", "texto": str(e)})

    threading.Thread(target=hilo_ia, daemon=True).start()

    def generador_sse():
        while True:
            try:
                item = cola_streaming.get(timeout=TIMEOUT_COLA_STREAMING_SEGUNDOS)
                yield f"data: {json.dumps(item)}\n\n"
                if item["tipo"] in ["fin", "error"]: break
            except queue.Empty:
                yield f"data: {json.dumps({'tipo': 'error', 'texto': 'Tiempo de espera agotado.'})}\n\n"
                break

    return StreamingResponse(generador_sse(), media_type="text/event-stream")

# ---------------------------------------------------------------------------
# Endpoint para el Lector de Pantalla (Edge TTS)
# ---------------------------------------------------------------------------
@app.post("/lector")
def leer_pantalla(req: PeticionLector):
    """
    Endpoint dedicado para el botón de accesibilidad de la interfaz.
    Usa Edge TTS para lectura rápida de bloques de texto.
    """
    threading.Thread(
        target=voz.leer_pantalla_directo, 
        args=(req.texto, "edge"), 
        daemon=True
    ).start()
    
    return {"status": "ok", "mensaje": "Lectura iniciada"}

# ---------------------------------------------------------------------------
# Endpoint para ABORTAR (El Botón de Pánico)
# ---------------------------------------------------------------------------
@app.post("/cancelar")
async def cancelar_generacion():
    """Detiene la inferencia del LLM y silencia cualquier audio en reproducción al instante."""
    print("🛑 [API] Recibida orden de abortar. Deteniendo LLM y Audio...")
    
    # 1. Le decimos al Cerebro que deje de generar texto
    evento_interrupcion.set()
    
    # 2. Le decimos al módulo de Voz que apague los altavoces de golpe
    try:
        voz.detener_audio_global()
    except Exception as e:
        print(f"⚠️ No se pudo silenciar el audio: {e}")
        
    return {"status": "abortado"}

# ---------------------------------------------------------------------------
# Endpoint para el Botón Manual del Micrófono (React -> Whisper)
# ---------------------------------------------------------------------------
@app.post("/escuchar")
def escuchar_manual():
    """Abre el micrófono local (Whisper) directamente desde la interfaz de React."""
    import core.voz as voz
    try:
        print("🎤 [API] Intentando abrir Whisper manualmente...")
        texto = voz.escuchar()
        return {"texto": texto}
    except Exception as e:
        print(f"❌ [API ERROR CRÍTICO MICROFONO]: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------------------------
# NUEVO: Cola de comunicación Radar -> React (Multifase)
# ---------------------------------------------------------------------------
mensajes_radar = queue.Queue()

@app.get("/radar/leer")
def leer_radar():
    """React consulta aquí rápidamente para ver el estado del micrófono."""
    try:
        mensaje = mensajes_radar.get_nowait()
        return {"hay_mensaje": True, "datos": mensaje}
    except queue.Empty:
        return {"hay_mensaje": False}

def daemon_escucha_activa():
    print("🎙️ [Daemon de Voz] Iniciando radar permanente...")
    while True:
        try:
            import core.voz as voz
            activado = voz.esperar_palabra_clave()
            
            if activado:
                # 1. BENGALA INMEDIATA: Le decimos a React que despierte la UI YA MISMO
                mensajes_radar.put({"accion": "despertar"})
                
                # 2. Abrimos los oídos de Whisper
                texto_usuario = voz.escuchar()
                
                if texto_usuario:
                    print(f"\n🗣️ [Micrófono capturó]: '{texto_usuario}'")
                    mensajes_radar.put({"accion": "ejecutar", "texto": texto_usuario})
                else:
                    # 4. Si fue un ruido sin voz, apagamos la UI
                    mensajes_radar.put({"accion": "cancelar"})
                    
        except Exception as e:
            print(f"❌ [Error en Daemon de Voz]: {e}")
            import time
            time.sleep(2)

threading.Thread(target=daemon_escucha_activa, daemon=True).start()

# Endpoint oculto solo para tu botón de pruebas

# Pon esta variable global al inicio de tu api.py
evento_colapso_activo = False

@app.post("/debug/forzar_fase_1")
def disparar_evento_anomalo():
    global evento_colapso_activo
    
    # Si ya está corriendo, ignoramos el clic
    if evento_colapso_activo:
        return {"status": "ignorado", "mensaje": "Ya está en curso"}
        
    evento_colapso_activo = True
    cola_streaming = queue.Queue()

    def enviar_a_react(comando_dict: dict):
        if comando_dict:
            trama = f"data: {json.dumps(comando_dict)}|||\n\n"
            cola_streaming.put(trama)

    def hilo_orquestador():
        global evento_colapso_activo
        try:
            eventos_anomalos.desatar_fase_1(
                callback_estado=None, 
                callback_ui=enviar_a_react, 
                usar_voz=True
            )
            cola_streaming.put(f"data: {json.dumps({'tipo': 'fin', 'origen': 'sistema'})}\n\n")
        except Exception as e:
            print(f"[Error Orquestador]: {e}")
            cola_streaming.put(f"data: {json.dumps({'tipo': 'error', 'texto': str(e)})}\n\n")
        finally:
            # Liberamos el candado cuando termine o falle
            evento_colapso_activo = False

    threading.Thread(target=hilo_orquestador, daemon=True).start()
    # ... (resto de tu generador_sse) ...

    # Generador que consume la cola y la envía por red a React
    def generador_sse():
        while True:
            item = cola_streaming.get()
            yield item
            # Si llegó el mensaje de fin o error, cortamos el streaming
            if '"tipo": "fin"' in item or '"tipo": "error"' in item:
                break

    return StreamingResponse(generador_sse(), media_type="text/event-stream")