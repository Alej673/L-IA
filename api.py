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
from pydantic import BaseModel

from core.cerebro import charlar_con_lia, evento_interrupcion
from core.tools import leer_archivo_local
from core.memoria_rag import MemoriaRAG
from core import database
from core.cerebro import charlar_con_lia, evento_interrupcion, asimilar_documento_maestro

from pydantic import BaseModel
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("lia.api")

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
TIMEOUT_AUTORIZACION_SEGUNDOS = 120  # tiempo máximo esperando el clic del usuario
CARPETA_TEMP_RAG = "temp_rag"
TIMEOUT_COLA_STREAMING_SEGUNDOS = 180  # corta la conexión SSE si el hilo de la IA se traba


# ---------------------------------------------------------------------------
# Modelos Pydantic (contratos de entrada/salida de la API)
# ---------------------------------------------------------------------------
class MensajeUsuario(BaseModel):
    texto: str
    sesion_id: str = "default"

class LimpiarWorkspaceRequest(BaseModel):
    sesion_id: str = "default"

class RespuestaSemaforo(BaseModel):
    autorizado: bool

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
    entrada = mensaje.texto
    sesion_actual = mensaje.sesion_id  
    logger.info(f"[Usuario | Sesión: {sesion_actual[:8]}] -> {entrada}")

    # ---> DISPARAMOS EL AUTONOMBRE EN SEGUNDO PLANO <---
    threading.Thread(target=renombrar_sesion_silenciosamente, args=(sesion_actual, entrada), daemon=True).start()

    cola_streaming = queue.Queue()

    def stream_consola(fragmento: str) -> None:
        """Imprime en consola y envía el fragmento a React al instante."""
        print(fragmento, end="", flush=True)
        cola_streaming.put({"tipo": "chunk", "texto": fragmento})

    def permiso_interfaz(herramienta: str, argumentos: Any) -> bool:
        """Delega la autorización al semáforo de tu nueva clase."""
        return semaforo.solicitar_autorizacion(herramienta, argumentos)

    def estado_interfaz(info: dict) -> None:
        """
        Recibe de core.cerebro la ficha de la ruta elegida (perfil, etiqueta,
        motivo y mensaje_espera) ANTES de que llegue el primer token, y la
        reenvía a React como un evento SSE propio ("estado"), separado de
        los chunks de texto. Así el frontend puede, por ejemplo, mostrar
        "Analizando arquitectura..." mientras Gemini Pro procesa una tarea
        de código pesado, sin tener que adivinar el motivo a partir del
        texto que ya llegó.

        Si el frontend todavía no sabe leer este tipo de evento, simplemente
        lo ignora (igual que cualquier `item["tipo"]` desconocido) y el chat
        sigue funcionando exactamente igual que antes.
        """
        cola_streaming.put({"tipo": "estado", **info})

    # 2. Envolvemos a L-IA en un hilo secundario para no congelar a FastAPI
    def hilo_ia():
        try:
            # IMPORTANTE: Debemos pasar el sesion_id al cerebro para que no mezcle historiales
            respuesta, origen = charlar_con_lia(
                entrada,
                callback_ui=permiso_interfaz,
                callback_stream=stream_consola,
                callback_estado=estado_interfaz,
                sesion_id=sesion_actual  # <-- Pasamos la sesión al núcleo
            )

            # Recuperamos el documento de esta sesión específica
            doc_activo = None
            nombre_workspace = None
            try:
                doc_activo = database.obtener_workspace_activo(sesion_id=sesion_actual)
                if doc_activo:
                    nombre_workspace = os.path.basename(doc_activo)
            except Exception:
                pass

            cola_streaming.put({
                "tipo": "fin", 
                "origen": origen, 
                "documento": doc_activo,
                "workspace": nombre_workspace
            })
            
        except Exception as e:
            logger.exception("Error al procesar el mensaje de chat.")
            cola_streaming.put({"tipo": "error", "texto": str(e)})

    threading.Thread(target=hilo_ia, daemon=True).start()

    # 3. Generador asíncrono que "bombea" los datos hacia el frontend
    def generador_sse():
        import queue
        while True:
            try:
                # Agregamos el timeout para evitar que React se quede colgado
                item = cola_streaming.get(timeout=TIMEOUT_COLA_STREAMING_SEGUNDOS)
                yield f"data: {json.dumps(item)}\n\n"
                if item["tipo"] in ["fin", "error"]:
                    break
            except queue.Empty:
                logger.error("Timeout agotado esperando datos del hilo de IA.")
                yield f"data: {json.dumps({'tipo': 'error', 'texto': 'Tiempo de espera agotado.'})}\n\n"
                break

    # Retornamos el flujo abierto en formato Server-Sent Events
    return StreamingResponse(generador_sse(), media_type="text/event-stream")

# ---------------------------------------------------------------------------
# Endpoint para cancelar la inferencia de la GPU o el stream de la Nube
# ---------------------------------------------------------------------------
@app.post("/cancelar")
async def cancelar_generacion():
    """Detiene la inferencia de la GPU o el stream de la Nube al instante."""
    evento_interrupcion.set()
    return {"status": "abortado"}

# ---------------------------------------------------------------------------
# Endpoint de ingesta de archivos (RAG + Workspace)
# ---------------------------------------------------------------------------
@app.post("/ingestar")
async def ingestar_archivo(archivo: UploadFile = File(...)):
    logger.info("Recibiendo archivo: %s", archivo.filename)

    nombre_seguro = os.path.basename(archivo.filename or "archivo_sin_nombre")
    if not nombre_seguro:
        return {"status": "error", "mensaje": "Nombre de archivo inválido."}

    os.makedirs(CARPETA_TEMP_RAG, exist_ok=True)
    ruta_temporal = os.path.join(CARPETA_TEMP_RAG, nombre_seguro)

    try:
        with open(ruta_temporal, "wb") as buffer:
            shutil.copyfileobj(archivo.file, buffer)

        ruta_absoluta = os.path.abspath(ruta_temporal)

        # Llamada directa a la función importada
        mensaje_resultado = asimilar_documento_maestro(ruta_absoluta)

        if mensaje_resultado.startswith("Error") or "Fallo crítico" in mensaje_resultado:
            return {"status": "error", "mensaje": mensaje_resultado}

        return {"status": "completado", "mensaje": mensaje_resultado}

    except Exception as e:
        logger.exception("Fallo al procesar el archivo %s", nombre_seguro)
        return {"status": "error", "mensaje": f"Fallo al procesar {nombre_seguro}: {e}"}
    finally:
        archivo.file.close()

# ---------------------------------------------------------------------------
# Endpoint para liberar el Workspace Activo
# ---------------------------------------------------------------------------
@app.post("/workspace/limpiar")
def limpiar_workspace(req: LimpiarWorkspaceRequest):
    """Libera el archivo activo solo para la sesión solicitada."""
    database.limpiar_workspace_activo(sesion_id=req.sesion_id)
    return {"status": "ok", "mensaje": f"Workspace liberado en sesión {req.sesion_id}"}