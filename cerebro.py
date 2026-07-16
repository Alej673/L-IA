import os
import time
from dotenv import load_dotenv
from google import genai
from mss import MSS
from PIL import Image
import prompt_builder
import database

# 1. Cargar variables de entorno y cliente
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("❌ No se encontró la variable GEMINI_API_KEY")

client = genai.Client(api_key=api_key)

# 2. Función optimizada de captura 100% en Memoria RAM (¡Tu código intacto!)
def tomar_captura_en_memoria():
    print("\n[👀 L-IA está analizando tu monitor...]")
    with MSS() as sct:  # <--- Cambiado mss() por MSS()
        monitor = sct.monitors[1]
        sct_img = sct.grab(monitor)
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        img.thumbnail((1024, 576)) 
        return img

# 3. Función Principal de Charla (Fusionada con Memoria y Reintentos)
def charlar_con_lia(mensaje_usuario):
    # Guardar tu mensaje en la BD
    database.guardar_mensaje("user", mensaje_usuario)
    
    # Armar el súper prompt con tu perfil y personalidad
    prompt_completo = prompt_builder.armar_contexto_gemini(mensaje_usuario)
    
    # Evaluar si necesitas que L-IA use sus "ojos"
    palabras_clave_vision = ["pantalla", "mira", "observa", "ves", "viendo"]
    usar_vision = any(palabra in mensaje_usuario.lower() for palabra in palabras_clave_vision)
    
    # Preparar el contenido a enviar
    contenidos_api = [prompt_completo]
    if usar_vision:
        imagen_en_ram = tomar_captura_en_memoria()
        contenidos_api.insert(0, imagen_en_ram) # Ponemos la imagen antes del texto
    
    # Bucle de reintentos
    max_reintentos = 3
    espera = 2
    
    for intento in range(max_reintentos):
        try:
            # Enviamos el contenido a Gemini
            response = client.models.generate_content(
                model='gemini-3.5-flash',
                contents=contenidos_api
            )
            
            texto_respuesta = response.text
            
            # Guardamos la respuesta de L-IA en la BD
            database.guardar_mensaje("model", texto_respuesta)
            
            # Imprimimos con estilo
            print(f"\n🤖 L-IA: {texto_respuesta}\n")
            break # Éxito, salimos del bucle
            
        except Exception as e:
            if intento < max_reintentos - 1:
                print(f"⚠️ Servidor ocupado o error ({e}). Reintentando en {espera} segundos...")
                time.sleep(espera)
                espera *= 2
            else:
                print(f"\n❌ L-IA Error crítico tras {max_reintentos} intentos: {e}")

# 4. Bucle Principal de la Consola
if __name__ == "__main__":
    print("=========================================")
    print(" 🤖 SISTEMA L-IA INICIADO Y EN LÍNEA ")
    print("=========================================\n")
    
    # Inicializar la base de datos por si acaso
    database.inicializar_base_datos()
    
    print("Escribe 'salir' para apagar.\nTip: Dile 'mira mi pantalla' para probar la visión.\n")
    
    while True:
        mi_mensaje = input("TÚ: ")
        
        if mi_mensaje.lower() in ['salir', 'exit', 'apagar', 'quit']:
            print("\n🤖 L-IA: Suspendiendo procesos... nos vemos.")
            break
            
        if mi_mensaje.strip() != "":
            charlar_con_lia(mi_mensaje)