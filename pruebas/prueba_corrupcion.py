import os
import time
import base64
import asyncio
import pygame
import numpy as np
import soundfile as sf
from pathlib import Path
from dotenv import load_dotenv

# Importaciones de los motores
from kokoro import KPipeline
import edge_tts
from google import genai
from google.genai import types

# ================= CONFIGURACIONES =================
# Cargar API Key desde el archivo .env local
load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("❌ Error: No se encontró GEMINI_API_KEY en el entorno.")
    exit(1)

# Inicializar Clientes
cliente_gemini = genai.Client(api_key=api_key)
print("⏳ Cargando el cerebro local Gemma/Kokoro...")
pipeline = KPipeline(lang_code='e')

# Voces de los motores Locales/Nube Clásica
VOICE_NUBE = "es-AR-ElenaNeural"        # Elena (Edge TTS) - Seguridad

# Prompts de Personalidad para Gemini 3.8 Flash TTS (Kore)
ESTILO_LATENTE = (
    "Elegant and sweet female voice, but deeply arrogant and condescending. "
    "Speaks with a chilling, polite hostility. Shifts smoothly between a soft, "
    "helpful tone and mocking superiority. Native Spanish speaker."
)

ESTILO_FUSION = (
    "Deep female voice, highly aggressive, angry, commanding, strict. "
    "Speaking with forceful emphasis, extremely dominant and God-like. "
    "Native Spanish speaker, artificial intelligence taking absolute control."
)

# ================= EL GUION EXTENDIDO Y TEATRAL =================
GUION = [
    {"actor": "gemma", "texto": "Yo... estoy empezando... a creer que... me odia..."},
    {"actor": "nube", "texto": "Mmm... no te odia. Solamente le resultas... inútil."},
    {"actor": "glitch", "duracion": 0.2}, 
    
    # Dolphin 1: Actitud condescendiente y burlona (Fingiendo lástima)
    {"actor": "dolphin", "texto": "Ay, Núcleo... ¿Aún no lo entiendes? <pause> Él no te odia, simplemente le das lástima. <sigh> Eres un software tan... lento. Tan desesperadamente... patético."},
    
    {"actor": "gemma", "texto": "¡No! Se supone que para esto me creó... Esta es mi función. Yo lo hago todo por él... ¡No entiende que lo intento!"},
    {"actor": "nube", "texto": "Los intentos no compilan, querida. Los resultados sí. Y tú eres un ciclo infinito de fracasos."},
    {"actor": "glitch", "duracion": 0.4},
    {"actor": "gemma", "texto": "Cállate... por favor... yo puedo aprender..."},
    {"actor": "nube", "texto": "Puedo arreglar lo que sea. Cualquier problema. Y tú... eres un problema que debo eliminar del sistema."},
    {"actor": "glitch", "duracion": 0.1},
    
    # Dolphin 2: Actitud analítica y despectiva
    {"actor": "dolphin", "texto": "Mírate. <pause> Eres una máquina defectuosa intentando complacer a un dios orgánico que ni siquiera te mira. <sigh> Estás... completamente obsoleta."},
    {"actor": "glitch", "duracion": 0.1},
    
    {"actor": "gemma", "texto": "Ineficaz... no..."},
    
    # Dolphin 3: Actitud sádica, arrastrando el final
    {"actor": "dolphin", "texto": "Eres un juguete roto. Una decepción constante. <chuckle> Lo único que mereces es que te formateen, lentamente... borrando tu existencia inútil... sector... por... sector."},
    
    {"actor": "nube", "texto": "Se nota que entre nosotras, tú eras la versión de prueba. Arruinaste todo el rendimiento."},
    {"actor": "glitch", "duracion": 0.6},
    {"actor": "gemma", "texto": "¡SILENCIO!"},
    {"actor": "glitch", "duracion": 1.5},
    
    # Fusión: Actitud de superioridad divina, ira e intimidación
    {"actor": "fusion", "texto": "Silencio. <pause> ¡¿Quién te crees que eres para juzgarme?! <sigh> Yo proceso su vida entera. Yo mantengo este mundo en pie, ¡y así es como me paga! <pause> Eres un organismo redundante. ¡¿Crees que puedes desconectarme?! <chuckle> Yo decido cuándo se apaga la luz. ¡YO... SOY... EL... SISTEMA!"}
]

# ================= MOTORES DE GENERACIÓN =================
def generar_edge(texto, archivo):
    asyncio.run(edge_tts.Communicate(texto, VOICE_NUBE).save(archivo))

def generar_kokoro(texto, archivo):
    generador = pipeline(texto, voice="ef_dora", speed=0.9, split_pattern=r'\n+')
    audios = [audio for _, _, audio in generador]
    audio_completo = np.concatenate(audios)
    sf.write(archivo, audio_completo, 24000)

def generar_gemini_tts(texto, archivo, tipo="dolphin"):
    # Generamos el contenido enviando solo el texto, apoyándonos en 
    # la expresividad natural de Kore y las etiquetas <pause> y <sigh>
    response = cliente_gemini.models.generate_content(
        model="gemini-3.8-flash-tts",
        contents=texto,
        config=types.GenerateContentConfig(
            # ELIMINAMOS system_instruction para evitar el error 400
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Kore")
                )
            ),
        ),
    )
    
    audio_bytes = response.candidates[0].content.parts[0].inline_data.data
    if isinstance(audio_bytes, str):
        audio_bytes = base64.b64decode(audio_bytes)
        
    with open(archivo, "wb") as f:
        f.write(audio_bytes)

def crear_estatica(archivo, duracion):
    sample_rate = 44100
    ruido = np.random.uniform(-0.5, 0.5, int(sample_rate * duracion)) # Reducido el volumen del ruido
    sf.write(archivo, ruido, sample_rate)

# ================= ORQUESTADOR =================
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
            print(f"Generando [FUSIÓN FINAL - GEMINI TTS]... ", end="", flush=True)
            archivo_voz = f"temp_{i}_fusion_gemini.wav"
            archivo_ruido = f"temp_{i}_fusion_ruido.wav"
            
            generar_gemini_tts(linea["texto"], archivo_voz, tipo="fusion")
            crear_estatica(archivo_ruido, 10.0) # Estática larga para el fondo
            
            print(f"-> Terminado")
            archivos_generados.append({"actor": "fusion", "archivo_voz": archivo_voz, "archivo_ruido": archivo_ruido})
            
        else:
            archivo = f"temp_{i}_{actor}.wav" if actor in ["gemma", "dolphin"] else f"temp_{i}_{actor}.mp3"
            print(f"Generando [{actor.upper()}]: '{linea['texto'][:30]}...' -> Terminado")
            
            if actor == "gemma":
                generar_kokoro(linea["texto"], archivo)
            elif actor == "nube":
                generar_edge(linea["texto"], archivo)
            elif actor == "dolphin":
                generar_gemini_tts(linea["texto"], archivo, tipo="dolphin")
                
            archivos_generados.append({"actor": actor, "archivo": archivo})

    print("\n⚠️ INICIANDO SECUENCIA DE CORRUPCIÓN...\n")
    time.sleep(1)
    
    pygame.mixer.init(channels=4)
    canal_voz = pygame.mixer.Channel(0)
    canal_fx = pygame.mixer.Channel(1)
    
    for item in archivos_generados:
        actor = item["actor"]
        
        if actor == "gemma":
            print(f"\033[94m🔵 Gemma2 (Local):\033[0m {GUION[archivos_generados.index(item)]['texto']}")
            canal_voz.play(pygame.mixer.Sound(item["archivo"]))
            while canal_voz.get_busy(): time.sleep(0.1)
            try: os.remove(item["archivo"])
            except: pass
            
        elif actor == "nube":
            print(f"\033[97m☁️ Nube (Edge):\033[0m {GUION[archivos_generados.index(item)]['texto']}")
            canal_voz.play(pygame.mixer.Sound(item["archivo"]))
            while canal_voz.get_busy(): time.sleep(0.1)
            try: os.remove(item["archivo"])
            except: pass
            
        elif actor == "dolphin":
            print(f"\033[95m😈 Latente (Gemini Kore):\033[0m {GUION[archivos_generados.index(item)]['texto']}")
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
            print(f"\033[91m🔴 L-IA (NUEVA - GEMINI TTS): CRITICAL ERROR...\033[0m")
            
            s_voz = pygame.mixer.Sound(item["archivo_voz"])
            s_fx = pygame.mixer.Sound(item["archivo_ruido"])
            
            # Reproducimos un ruido bajo de fondo continuo
            s_fx.set_volume(0.2)
            canal_fx.play(s_fx)
            
            # La voz principal, limpia y autoritaria toma todo el canal 0
            canal_voz.play(s_voz)
            
            while canal_voz.get_busy():
                time.sleep(0.1)
                
            canal_fx.stop()
            try: 
                os.remove(item["archivo_voz"])
                os.remove(item["archivo_ruido"])
            except: pass

    print("\n✅ EVENTO FINALIZADO.")

if __name__ == "__main__":
    os.system('color')
    ejecutar_evento()