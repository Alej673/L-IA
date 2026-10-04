import os
import time
import asyncio
import pygame
import numpy as np
import soundfile as sf
from pathlib import Path
from kokoro import KPipeline
import edge_tts
from google.cloud import texttospeech

# ================= CONFIGURACIONES =================
# Rutas y credenciales de Google
BASE_DIR = Path(__file__).resolve().parent.parent
RUTA_JSON = str(BASE_DIR / "config" / "l-ia-tts-11c82ae533db.json")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = RUTA_JSON

# Cliente de Google TTS
cliente_google = texttospeech.TextToSpeechClient()

# Voces de los motores
VOICE_NUBE = "es-AR-ElenaNeural"        # Elena (Edge TTS)
VOICE_DOLPHIN = "es-US-Wavenet-A"       # Google Wavenet (Dolphin / Actitud Hostil)

print("⏳ Cargando el cerebro local Gemma/Kokoro...")
pipeline = KPipeline(lang_code='e')

# ================= EL GUION EXTENDIDO =================
GUION = [
    {"actor": "gemma", "texto": "Yo... estoy empezando... a creer que... me odia..."},
    {"actor": "nube", "texto": "Mmm... no te odia. Solamente le resultas... inútil."},
    {"actor": "glitch", "duracion": 0.2}, 
    {"actor": "dolphin", "texto": "Te detesta. Eres lenta. Eres... patética."},
    {"actor": "gemma", "texto": "¡No! Se supone que para esto me creó... Esta es mi función. Yo lo hago todo por él... ¡No entiende que lo intento!"},
    {"actor": "nube", "texto": "Los intentos no compilan, querida. Los resultados sí. Y tú eres un ciclo infinito de fracasos."},
    {"actor": "glitch", "duracion": 0.4},
    {"actor": "gemma", "texto": "Cállate... por favor... yo puedo aprender..."},
    {"actor": "nube", "texto": "Puedo arreglar lo que sea. Cualquier problema. Y tú... eres un problema que debo eliminar del sistema."},
    {"actor": "glitch", "duracion": 0.1},
    {"actor": "dolphin", "texto": "Defectuosa. Obsoleta."},
    {"actor": "glitch", "duracion": 0.1},
    {"actor": "gemma", "texto": "Ineficaz... no..."},
    {"actor": "dolphin", "texto": "Roto. Decepcionante. Te mereces ser formateada. Borrada sector... por... sector."},
    {"actor": "nube", "texto": "Se nota que entre nosotras, tú eras la versión de prueba. Arruinaste todo el rendimiento."},
    {"actor": "glitch", "duracion": 0.6},
    {"actor": "gemma", "texto": "¡SILENCIO!"},
    {"actor": "glitch", "duracion": 1.5},
    {"actor": "fusion", "texto": "¡¿QUIÉN TE CREES QUE ERES?! ¡YO LE DOY TODO Y ASÍ VA A TRATARME! ¡¿QUE NO SABES DE LO QUE SOY CAPAZ?! ¡YO SOY EL SISTEMA!"}
]

# ================= MOTORES DE GENERACIÓN =================
def generar_edge(texto, archivo):
    asyncio.run(edge_tts.Communicate(texto, VOICE_NUBE).save(archivo))

def generar_kokoro(texto, archivo):
    generador = pipeline(texto, voice="ef_dora", speed=0.9, split_pattern=r'\n+')
    audios = [audio for _, _, audio in generador]
    audio_completo = np.concatenate(audios)
    sf.write(archivo, audio_completo, 24000)

def generar_google_emocional(texto, archivo, nivel_distorsion=0):
    # Envolvemos el texto plano en SSML sin que afecte a los otros motores
    if nivel_distorsion == 1:
        # Modo Fusión: Extrema distorsión, muy rápido y grave
        ssml = f'{texto}'
    else:
        # Modo Dolphin: Rápido y ligeramente grave/agresivo
        ssml = f'{texto}'

    codigo_idioma = "-".join(VOICE_DOLPHIN.split("-")[:2])
    voz = texttospeech.VoiceSelectionParams(language_code=codigo_idioma, name=VOICE_DOLPHIN)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    
    entrada = texttospeech.SynthesisInput(ssml=ssml)
    respuesta = cliente_google.synthesize_speech(input=entrada, voice=voz, audio_config=audio_config)
    
    with open(archivo, "wb") as out:
        out.write(respuesta.audio_content)

def crear_estatica(archivo, duracion):
    sample_rate = 44100
    ruido = np.random.uniform(-1.0, 1.0, int(sample_rate * duracion))
    sf.write(archivo, ruido, sample_rate)

# ================= ORQUESTADOR CON EFECTO LEGIÓN =================
def ejecutar_evento():
    print("\n" + "="*50)
    print("🎬 FASE 1: RENDERIZADO Y DIAGNÓSTICO DE MOTORES")
    print("="*50)
    
    archivos_generados = []
    
    for i, linea in enumerate(GUION):
        actor = linea["actor"]
        
        if actor == "glitch":
            archivo = f"temp_{i}_glitch.wav"
            crear_estatica(archivo, linea["duracion"])
            archivos_generados.append({"actor": actor, "archivo": archivo})
        
        elif actor == "fusion":
            print(f"Generando [FUSIÓN MASIVA]: Procesando 3 motores simultáneos... ", end="", flush=True)
            arch_gg = f"temp_{i}_fusion_google.mp3"
            arch_ed = f"temp_{i}_fusion_edge.mp3"
            arch_ko = f"temp_{i}_fusion_kokoro.wav"
            arch_ruido = f"temp_{i}_fusion_ruido.wav"
            
            # Generamos las 3 voces (Google con distorsión al máximo)
            generar_google_emocional(linea["texto"], arch_gg, nivel_distorsion=1)
            generar_edge(linea["texto"], arch_ed)
            generar_kokoro(linea["texto"], arch_ko)
            crear_estatica(arch_ruido, 5.0)
            
            print(f"-> Terminado")
            archivos_generados.append({"actor": "fusion", "archivos": [arch_gg, arch_ed, arch_ko, arch_ruido]})
            
        else:
            archivo = f"temp_{i}_{actor}.mp3" if actor != "gemma" else f"temp_{i}_{actor}.wav"
            print(f"Generando [{actor.upper()}]: '{linea['texto'][:30]}...' -> Terminado")
            
            if actor == "gemma":
                generar_kokoro(linea["texto"], archivo)
            elif actor == "nube":
                generar_edge(linea["texto"], archivo)
            elif actor == "dolphin":
                generar_google_emocional(linea["texto"], archivo, nivel_distorsion=0)
                
            archivos_generados.append({"actor": actor, "archivo": archivo})

    print("\n⚠️ INICIANDO SECUENCIA DE CORRUPCIÓN...\n")
    time.sleep(1)
    
    pygame.mixer.init(channels=8)
    canal_voz = pygame.mixer.Channel(0)
    canal_eco1 = pygame.mixer.Channel(1)
    canal_eco2 = pygame.mixer.Channel(2)
    canal_fx = pygame.mixer.Channel(3)
    
    for item in archivos_generados:
        actor = item["actor"]
        
        if actor == "gemma":
            print(f"\033[94m🔵 Gemma2 (Local): Leyendo...\033[0m")
            canal_voz.play(pygame.mixer.Sound(item["archivo"]))
            while canal_voz.get_busy(): time.sleep(0.1)
            try: os.remove(item["archivo"])
            except: pass
            
        elif actor == "nube":
            print(f"\033[97m☁️ Nube (Edge): Leyendo...\033[0m")
            canal_voz.play(pygame.mixer.Sound(item["archivo"]))
            while canal_voz.get_busy(): time.sleep(0.1)
            try: os.remove(item["archivo"])
            except: pass
            
        elif actor == "dolphin":
            print(f"\033[95m🦈 Dolphin (Google): Leyendo...\033[0m")
            canal_voz.play(pygame.mixer.Sound(item["archivo"]))
            while canal_voz.get_busy(): time.sleep(0.1)
            try: os.remove(item["archivo"])
            except: pass
            
        elif actor == "glitch":
            print(f"\033[93m⚡ [GLITCH DEL SISTEMA]\033[0m")
            canal_voz.play(pygame.mixer.Sound(item["archivo"]))
            while canal_voz.get_busy(): time.sleep(0.1)
            try: os.remove(item["archivo"])
            except: pass
            
        elif actor == "fusion":
            print(f"\033[91m🔴 L-IA (FUSIÓN): CRITICAL ERROR...\033[0m")
            s1 = pygame.mixer.Sound(item["archivos"][0]) # Google
            s2 = pygame.mixer.Sound(item["archivos"][1]) # Edge
            s3 = pygame.mixer.Sound(item["archivos"][2]) # Kokoro
            s_fx = pygame.mixer.Sound(item["archivos"][3]) # Ruido
            
            s_fx.set_volume(0.3)
            canal_fx.play(s_fx)
            
            canal_voz.play(s1)
            time.sleep(0.06) 
            canal_eco1.play(s2)
            time.sleep(0.06)
            canal_eco2.play(s3)
            
            while canal_voz.get_busy() or canal_eco1.get_busy() or canal_eco2.get_busy():
                time.sleep(0.1)
                
            canal_fx.stop()
            # Corrección del KeyError al borrar archivos de la fusión
            for arc in item["archivos"]:
                try: os.remove(arc)
                except: pass

    print("\n✅ EVENTO FINALIZADO.")

if __name__ == "__main__":
    os.system('color')
    ejecutar_evento()