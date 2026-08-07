import asyncio
import edge_tts
import pygame
import time

VOZ_NEURONAL = "es-MX-DaliaNeural"
TEXTO_PRUEBA = "Hola Alejandro. El error de FFmpeg ya no será un problema. Ahora puedo reproducir mi voz neuronal sin crashear."
ARCHIVO_SALIDA = "prueba_edge.mp3"

async def probar_edge_tts():
    print(f"\n--- Probando Edge TTS ({VOZ_NEURONAL}) ---")
    communicate = edge_tts.Communicate(TEXTO_PRUEBA, VOZ_NEURONAL)
    
    # Generar el archivo
    await communicate.save(ARCHIVO_SALIDA)
    print("✅ Audio generado. Reproduciendo...")
    
    # Reproducir usando pygame (sin necesidad de ffmpeg)
    pygame.mixer.init()
    pygame.mixer.music.load(ARCHIVO_SALIDA)
    pygame.mixer.music.play()
    
    # Esperar a que termine de hablar
    while pygame.mixer.music.get_busy():
        time.sleep(0.1)
        
    # Limpiar el motor de audio
    pygame.mixer.quit()
    print("🔊 Prueba finalizada.")

if __name__ == "__main__":
    asyncio.run(probar_edge_tts())