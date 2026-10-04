import soundfile as sf
import pygame
import time
import os
import numpy as np
from kokoro import KPipeline

print("⏳ Cargando el modelo Kokoro...")
pipeline = KPipeline(lang_code='e') 

TEXTO_PRUEBA = """
¿Que si sueno monótona? ¡Por supuesto que no! 
A veces puedo hablar de forma muy seria, como cuando hay un error en el servidor. 
Pero otras veces, ¡me emociona muchísimo cuando el código compila a la primera! 
¿Notas cómo fluye mi voz ahora que el código está optimizado?
"""
ARCHIVO_SALIDA = "prueba_fluida.wav"

def probar_kokoro_fluido():
    pygame.mixer.init()
    print("\n🎬 Generando audio completo para máxima fluidez...\n")
    
    generador = pipeline(
        TEXTO_PRUEBA, 
        voice="ef_dora",
        speed=1.0,
        split_pattern=r'\n+'
    )
    
    tiempo_inicio = time.time()
    audios = []
    
    # 1. Recolectamos todas las partes de audio primero
    for i, (grafemas, fonemas, audio) in enumerate(generador):
        audios.append(audio)
        
    # 2. Unimos todo en un solo bloque fluido
    audio_completo = np.concatenate(audios)
    tiempo_total = time.time() - tiempo_inicio
    
    print(f"⚡ Audio total generado en {round(tiempo_total, 2)} segundos.")
    
    sf.write(ARCHIVO_SALIDA, audio_completo, 24000)
    print("▶️ Reproduciendo de forma continua...")
    
    pygame.mixer.music.load(ARCHIVO_SALIDA)
    pygame.mixer.music.play()
    
    while pygame.mixer.music.get_busy():
        time.sleep(0.1)
        
    pygame.mixer.music.unload()
    try:
        os.remove(ARCHIVO_SALIDA)
    except OSError:
        pass

if __name__ == "__main__":
    probar_kokoro_fluido()