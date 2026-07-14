import os
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

# 2. Función optimizada para capturar la pantalla
def tomar_captura():
    print("\n[OJO] Tomando captura de pantalla optimizada...")
    with mss() as sct:
        monitor = sct.monitors[1]
        sct_img = sct.grab(monitor)
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        img.thumbnail((1280, 720))  # Redimensionar
        
        # OPTIMIZACIÓN: Guardar como JPEG con compresión del 70%
        img.save("captura_temp.jpg", "JPEG", quality=70) 
        
    return "captura_temp.jpg"

# 3. Flujo principal
try:
    # Tomamos la captura antes de llamar a la IA
    ruta_imagen = tomar_captura()
    
    # Abrimos la imagen guardada usando Pillow
    imagen_procesada = Image.open(ruta_imagen)
    
    print("[CEREBRO] Enviando imagen y pregunta a Gemini...")
    
    # Pasamos la imagen directamente en la lista de contenidos
    response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents=[
            imagen_procesada, 
            "Mira detenidamente esta captura de pantalla de mi computadora. Describe brevemente qué programas o ventanas tengo abiertos y en qué parece que estoy trabajando."
        ]
    )
    
    print("\n=== ANÁLISIS VISUAL DEL ASISTENTE ===")
    print(response.text)
    print("======================================\n")

except Exception as e:
    print(f"\nOcurrió un error: {e}")