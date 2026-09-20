from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
import os
import threading

# Importaciones del núcleo
from core.cerebro import charlar_con_lia
from core.tools import leer_archivo_local
from core.memoria_rag import MemoriaRAG
from core import database
from core import contexto

memoria_rag = MemoriaRAG()

app = FastAPI(title="L-IA API Bridge", version="3.2.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite que la interfaz de Tauri se conecte
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIG DEL SEMÁFORO ---
TIMEOUT_AUTORIZACION_SEGUNDOS = 120  # tiempo máximo esperando clic del usuario

# --- VARIABLES GLOBALES DEL SEMÁFORO ---
esperando_autorizacion = threading.Event()
autorizacion_concedida = False
alerta_actual = None

# ARREGLO #2: lock para que solo un /chat a la vez use el semáforo global.
# Evita que dos peticiones simultáneas se pisen la alerta o la respuesta.
lock_semaforo = threading.Lock()


class MensajeUsuario(BaseModel):
    texto: str


class RespuestaSemaforo(BaseModel):
    autorizado: bool


# --- ENDPOINTS DEL SEMÁFORO PARA REACT ---
@app.get("/semaforo")
async def verificar_semaforo():
    """React llama aquí cada segundo para ver si L-IA está pausada esperando permiso"""
    if alerta_actual:
        return {
            "activa": True,
            "herramienta": alerta_actual["herramienta"],
            "argumentos": alerta_actual["argumentos"],
        }
    return {"activa": False}


@app.post("/semaforo/responder")
async def responder_semaforo(respuesta: RespuestaSemaforo):
    """React llama aquí cuando el usuario hace clic en Autorizar o Denegar"""
    global autorizacion_concedida
    autorizacion_concedida = respuesta.autorizado
    esperando_autorizacion.set()  # 🔓 Baja la barrera y deja que Python continúe
    return {"status": "ok"}


@app.post("/chat")
def recibir_chat(mensaje: MensajeUsuario):  # def normal: FastAPI lo corre en threadpool, no bloquea el event loop
    entrada = mensaje.texto
    print(f"\n[Usuario] -> {entrada}")

    def stream_consola(fragmento):
        print(fragmento, end="", flush=True)

    def permiso_interfaz(herramienta, argumentos):
        global alerta_actual, autorizacion_concedida

        # ARREGLO #2: solo un semáforo activo a la vez en todo el servidor
        with lock_semaforo:
            alerta_actual = {"herramienta": herramienta, "argumentos": str(argumentos)}
            esperando_autorizacion.clear()

            print(f"\n[SEMÁFORO] Esperando autorización del usuario para: {herramienta}...")

            # ARREGLO #1: timeout para no bloquear el hilo para siempre si
            # el usuario nunca responde (cierra la app, pierde conexión, etc.)
            respondio_a_tiempo = esperando_autorizacion.wait(timeout=TIMEOUT_AUTORIZACION_SEGUNDOS)

            alerta_actual = None

            if not respondio_a_tiempo:
                print(f"\n[SEMÁFORO] Tiempo agotado esperando autorización para: {herramienta}. Abortando por defecto.")
                return False

            return autorizacion_concedida

    try:
        respuesta, origen = charlar_con_lia(
            entrada,
            callback_ui=permiso_interfaz,
            callback_stream=stream_consola,
        )

        # Capturar el documento en la mira
        doc_activo = contexto.obtener_ventana_activa()
        if doc_activo in ["Escritorio / Desconocido", ""]:
            doc_activo = None

        # Enviamos el origen (Local/Nube) y el documento activo a React
        return {
            "rol": "ia",
            "texto": respuesta,
            "origen": origen,
            "documento": doc_activo,
        }

    except Exception as e:
        return {"rol": "sistema", "texto": f"Error interno: {str(e)}"}


@app.post("/ingestar")
async def ingestar_archivo(archivo: UploadFile = File(...)):
    print(f"\n[API] Recibiendo archivo: {archivo.filename}")

    # ARREGLO #4: nunca confiar en el nombre de archivo tal cual lo manda el
    # cliente; os.path.basename evita que algo como "../../algo.txt" escriba
    # fuera de la carpeta temp_rag.
    nombre_seguro = os.path.basename(archivo.filename or "archivo_sin_nombre")
    if not nombre_seguro:
        return {"status": "error", "mensaje": "Nombre de archivo inválido."}

    os.makedirs("temp_rag", exist_ok=True)
    ruta_temporal = os.path.join("temp_rag", nombre_seguro)

    # ARREGLO #3: try/except alrededor de todo el proceso de ingesta para que
    # un fallo (parser, vectorización, IO) devuelva un mensaje limpio al chat
    # en vez de un 500 crudo.
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
        else:
            mensaje_final = f"Error al extraer el texto de {nombre_seguro}. Revisa el formato."

        return {
            "status": "completado",
            "mensaje": mensaje_final,
        }

    except Exception as e:
        print(f"\n[ERROR /ingestar] {e}")
        return {
            "status": "error",
            "mensaje": f"Fallo al procesar {nombre_seguro}: {str(e)}",
        }
    finally:
        archivo.file.close()