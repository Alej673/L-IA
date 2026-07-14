import os
import time
from dotenv import load_dotenv
from google import genai
from mss import mss
from PIL import Image

# 1. Cargar variables de entorno y cliente
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("No se encontró la variable GEMINI_API_KEY")

client = genai.Client(api_key=api_key)

# 2. Función optimizada de captura 100% en Memoria RAM
def tomar_captura_en_memoria():
    print("\n[OJO] Capturando pantalla directamente en memoria RAM...")
    with mss() as sct:
        monitor = sct.monitors[1]
        sct_img = sct.grab(monitor)
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        img.thumbnail((1024, 576)) 
        return img

# 3. Flujo principal con reintentos para evitar el Error 503
imagen_en_ram = tomar_captura_en_memoria()

max_reintentos = 3
espera = 2  # Segundos iniciales de espera

for intento in range(max_reintentos):
    try:
        print(f"[CEREBRO] Enviando carga a Gemini (Intento {intento + 1}/{max_reintentos})...")
        
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=[
                imagen_en_ram,
                "Analiza mi pantalla de forma ultra resumida. ¿Qué programa principal tengo activo?"
            ]
        )
        
        print("\n=== RESPUESTA VELOZ ===")
        print(response.text)
        print("========================\n")
        break  # Si tiene éxito, rompemos el ciclo y salimos

    except Exception as e:
        # Si es un error de servidor (503, 500, etc.), reintentamos
        if intento < max_reintentos - 1:
            print(f"⚠️ El servidor está ocupado o dio un error ({e}). Reintentando en {espera} segundos...")
            time.sleep(espera)
            espera *= 2  # Duplicamos el tiempo de espera para el siguiente intento
        else:
            print(f"\n❌ Error definitivo tras {max_reintentos} intentos: {e}")