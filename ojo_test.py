import time
from mss import mss
from PIL import Image

def capturar_pantalla():
    print("Tomando captura de pantalla...")
    start_time = time.time()
    
    with mss() as sct:
        # Tomar captura del monitor principal (monitor 1)
        monitor = sct.monitors[1]
        sct_img = sct.grab(monitor)
        
        # Convertir los pixeles en bruto a una imagen de Pillow
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        
        # Redimensionar la imagen para que la subida a la API sea ultra rápida
        # Esto reduce el consumo de internet y el tiempo de respuesta de la IA
        img.thumbnail((1280, 720)) 
        
        # Guardar la imagen temporalmente en tu carpeta de proyecto
        img.save("captura_temp.png", "PNG")
        
    end_time = time.time()
    print(f"¡Captura guardada con éxito como 'captura_temp.png' en {end_time - start_time:.4f} segundos!")

if __name__ == "__main__":
    capturar_pantalla()