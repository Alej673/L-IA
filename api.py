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

memoria_rag = MemoriaRAG()

app = FastAPI(title="L-IA API Bridge", version="3.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Permite que la interfaz de Tauri se conecte
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- VARIABLES GLOBALES DEL SEMÁFORO ---
esperando_autorizacion = threading.Event()
autorizacion_concedida = False
alerta_actual = None

class MensajeUsuario(BaseModel):
    texto: str

class RespuestaSemaforo(BaseModel):
    autorizado: bool

# --- ENDPOINTS DEL SEMÁFORO PARA REACT ---
@app.get("/semaforo")
async def verificar_semaforo():
    """React llama aquí cada segundo para ver si L-IA está pausada esperando permiso"""
    if alerta_actual:
        return {"activa": True, "herramienta": alerta_actual["herramienta"], "argumentos": alerta_actual["argumentos"]}
    return {"activa": False}

@app.post("/semaforo/responder")
async def responder_semaforo(respuesta: RespuestaSemaforo):
    """React llama aquí cuando el usuario hace clic en Autorizar o Denegar"""
    global autorizacion_concedida
    autorizacion_concedida = respuesta.autorizado
    esperando_autorizacion.set() # 🔓 Baja la barrera y deja que Python continúe
    return {"status": "ok"}

@app.post("/chat")
def recibir_chat(mensaje: MensajeUsuario): # <-- ELIMINAMOS 'async' DE ESTA LÍNEA
    entrada = mensaje.texto
    print(f"\n[Usuario] -> {entrada}")
    
    def stream_consola(fragmento):
        print(fragmento, end="", flush=True)

    def permiso_interfaz(herramienta, argumentos):
        global alerta_actual, autorizacion_concedida
        alerta_actual = {"herramienta": herramienta, "argumentos": str(argumentos)}
        esperando_autorizacion.clear()
        
        print(f"\n[SEMÁFORO] Esperando autorización del usuario para: {herramienta}...")
        
        # Al ser una función 'def' (no async), este wait() pausa un hilo secundario
        # y deja al servidor principal libre para responderle al frontend.
        esperando_autorizacion.wait() 
        
        alerta_actual = None
        return autorizacion_concedida

    try:
        respuesta, origen = charlar_con_lia(
            entrada,
            callback_ui=permiso_interfaz,
            callback_stream=stream_consola
        )
        return {"rol": "ia", "texto": respuesta, "origen": origen}
    
    except Exception as e:
        return {"rol": "sistema", "texto": f"Error interno: {str(e)}"}

@app.post("/ingestar")
async def ingestar_archivo(archivo: UploadFile = File(...)):
    print(f"\n[API] Recibiendo archivo: {archivo.filename}")
    os.makedirs("temp_rag", exist_ok=True)
    ruta_temporal = f"temp_rag/{archivo.filename}"
    
    # 1. Guardamos el archivo físicamente
    with open(ruta_temporal, "wb") as buffer:
        shutil.copyfileobj(archivo.file, buffer)
        
    ruta_absoluta = os.path.abspath(ruta_temporal)
    
    # 2. Extraemos el texto
    datos = leer_archivo_local(ruta_absoluta)
    
    if isinstance(datos, dict) and "contenido" in datos:
        texto_a_vectorizar = datos["contenido"]
        
        # 3. Vectorizamos en ChromaDB (Para memoria a largo plazo)
        cantidad_fragmentos = memoria_rag.indexar_documento(
            texto_completo=texto_a_vectorizar,
            nombre_origen=archivo.filename
        )
        
        # 4. Fijamos el archivo como Workspace Activo (Para charlar AHORA mismo)
        database.establecer_workspace_activo(ruta_absoluta)
        
        mensaje_final = (
            f"Archivo asimilado. Dividido en {cantidad_fragmentos} fragmentos en el RAG y "
            f"fijado en mi entorno de trabajo. Ya puedes pedirme que lo resuma o analice."
        )
    else:
        mensaje_final = f"Error al extraer el texto de {archivo.filename}. Revisa el formato."
        
    return {
        "status": "completado",
        "mensaje": mensaje_final
    }