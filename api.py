"""
main.py — API Bridge de L-IA

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
memoria_rag = MemoriaRAG()

app = FastAPI(title="L-IA API Bridge", version="3.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite que la interfaz de Tauri (webview local) se conecte.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Endpoints del semáforo (usados por React)
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
# Endpoint principal de chat (Streaming SSE)
# ---------------------------------------------------------------------------
@app.post("/chat")
def recibir_chat(mensaje: MensajeUsuario):
    entrada = mensaje.texto
    logger.info("[Usuario] -> %s", entrada)

    # 1. Creamos la cola por donde viajarán los fragmentos de texto
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
            respuesta, origen = charlar_con_lia(
                entrada,
                callback_ui=permiso_interfaz,
                callback_stream=stream_consola,
                callback_estado=estado_interfaz,
            )

            # Recuperamos el documento activo al terminar de pensar
            doc_activo = None
            try:
                doc_activo = database.obtener_hecho("workspace_activo")
            except Exception:
                pass

            # Avisamos a React que terminamos y le pasamos las etiquetas holográficas
            cola_streaming.put({"tipo": "fin", "origen": origen, "documento": doc_activo})
            
        except Exception as e:
            logger.exception("Error al procesar el mensaje de chat.")
            cola_streaming.put({"tipo": "error", "texto": str(e)})

    # Disparamos el cerebro en segundo plano
    threading.Thread(target=hilo_ia, daemon=True).start()

    # 3. Generador asíncrono que "bombea" los datos hacia el frontend
    def generador_sse():
        while True:
            item = cola_streaming.get()
            yield f"data: {json.dumps(item)}\n\n"
            if item["tipo"] in ["fin", "error"]:
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
# Endpoint de ingesta de archivos (RAG)
# ---------------------------------------------------------------------------
@app.post("/ingestar")
async def ingestar_archivo(archivo: UploadFile = File(...)):
    """
    Recibe un archivo subido desde el frontend, lo guarda temporalmente,
    extrae su texto y lo indexa en la memoria RAG para que L-IA pueda
    consultarlo luego.
    """
    logger.info("Recibiendo archivo: %s", archivo.filename)

    # Nunca confiar en el nombre de archivo tal cual lo manda el cliente:
    # os.path.basename() evita un path traversal (ej. "../../etc/passwd")
    # que escriba fuera de la carpeta temp_rag.
    nombre_seguro = os.path.basename(archivo.filename or "archivo_sin_nombre")
    if not nombre_seguro:
        return {"status": "error", "mensaje": "Nombre de archivo inválido."}

    os.makedirs(CARPETA_TEMP_RAG, exist_ok=True)
    ruta_temporal = os.path.join(CARPETA_TEMP_RAG, nombre_seguro)

    try:
        with open(ruta_temporal, "wb") as buffer:
            shutil.copyfileobj(archivo.file, buffer)

        ruta_absoluta = os.path.abspath(ruta_temporal)
        datos = leer_archivo_local(ruta_absoluta)

        if isinstance(datos, dict) and "contenido" in datos:
            texto_a_vectorizar = datos["contenido"]

            cantidad_fragmentos = memoria_rag.indexar_documento(
                texto_completo=texto_a_vectorizar,
                nombre_origen=nombre_seguro,
            )

            database.establecer_workspace_activo(ruta_absoluta)

            mensaje_final = (
                f"Archivo asimilado. Dividido en {cantidad_fragmentos} fragmentos en el RAG y "
                f"fijado en mi entorno de trabajo. Ya puedes pedirme que lo resuma o analice."
            )
            return {"status": "completado", "mensaje": mensaje_final}

        return {
            "status": "error",
            "mensaje": f"Error al extraer el texto de {nombre_seguro}. Revisa el formato.",
        }

    except Exception as e:
        logger.exception("Fallo al procesar el archivo %s", nombre_seguro)
        return {"status": "error", "mensaje": f"Fallo al procesar {nombre_seguro}: {e}"}
    finally:
        archivo.file.close()