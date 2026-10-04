import os
import pygame
import time
from pathlib import Path
from google.cloud import texttospeech

BASE_DIR = Path(__file__).resolve().parent.parent
RUTA_JSON = str(BASE_DIR / "config" / "l-ia-tts-11c82ae533db.json")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = RUTA_JSON

VOCES_PREMIUM = [
    "es-US-Wavenet-A",  # Femenina, acento neutro/latino
    "es-ES-Wavenet-C",  # Femenina, España
]

# SSML Avanzado: Uso de semitonos (st), velocidades extremas y énfasis fuerte.
TEXTOS_EMOCIONALES = {
    "Alegría": """
        ¡Qué increíble! 
        
        ¡Todo el código compiló a la primera y sin un solo error!
    """,
    
    "Enojo y Frustración": """
        Otra vez. 
         
        El mismo error de dependencias. 
        
        Estoy harta de que estas actualizaciones rompan todo.
    """,
    
    "Duda y Tristeza": """
        No estoy segura de qué pasó... 
         
        Pensé que habíamos guardado el archivo,  pero no lo encuentro por ninguna parte.
    """
}

def probar_emociones():
    print("🎭 Probando Wavenet con inyección de SSML avanzado...\n")
    cliente = texttospeech.TextToSpeechClient()
    pygame.mixer.init()

    for nombre_voz in VOCES_PREMIUM:
        print("\n" + "="*40)
        print(f"🎙️ Evaluando voz: {nombre_voz}")
        codigo_idioma = "-".join(nombre_voz.split("-")[:2])
        
        voz = texttospeech.VoiceSelectionParams(language_code=codigo_idioma, name=nombre_voz)
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

        for emocion, ssml in TEXTOS_EMOCIONALES.items():
            print(f"  -> Interpretando: {emocion}")
            
            entrada = texttospeech.SynthesisInput(ssml=ssml)
            try:
                respuesta = cliente.synthesize_speech(input=entrada, voice=voz, audio_config=audio_config)
                
                archivo_salida = "temp_audio.mp3"
                with open(archivo_salida, "wb") as out:
                    out.write(respuesta.audio_content)
                    
                pygame.mixer.music.load(archivo_salida)
                pygame.mixer.music.play()
                
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                    
                pygame.mixer.music.unload()
                os.remove(archivo_salida)
            except Exception as e:
                print(f"❌ Error con {emocion}: {e}")
            time.sleep(0.5)

if __name__ == "__main__":
    probar_emociones()