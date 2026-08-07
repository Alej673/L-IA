import asyncio
import os
import time
import threading
import json

import edge_tts
import pygame
import sounddevice as sd
import numpy as np
from vosk import Model, KaldiRecognizer

# --- CONFIGURACIÓN DE RUTAS ---
VOSK_MODEL_PATH = "vosk-model-small-es-0.42"
VOZ_NEURONAL = "es-MX-DaliaNeural"  # Voz principal de L-IA (Neuronales de Microsoft)
CARPETA_TEMP_AUDIO = "temp_audio"
SAMPLE_RATE_STT = 16000

os.makedirs(CARPETA_TEMP_AUDIO, exist_ok=True)

# --- CAMBIO CLAVE #1 ---
# Antes: pygame.mixer.init() / .quit() en CADA frase.
# Eso reabre el dispositivo de audio en cada bloque -> "clicks" y latencia
# extra justo en el punto donde más nos importa la fluidez. Ahora se
# inicializa una sola vez, al importar el módulo.
pygame.mixer.init()

# Carga silenciosa del modelo Vosk (Oídos)
try:
    _vosk_model = Model(VOSK_MODEL_PATH)
except Exception as e:
    print(f"⚠️ Warning: No se pudo cargar Vosk desde '{VOSK_MODEL_PATH}': {e}")
    _vosk_model = None

_contador_audio = 0
_lock_contador = threading.Lock()


def _siguiente_ruta_audio() -> str:
    """Genera un nombre de archivo único por frase (evita pisar el archivo
    que el hilo de reproducción todavía podría estar leyendo)."""
    global _contador_audio
    with _lock_contador:
        _contador_audio += 1
        idx = _contador_audio
    return os.path.join(CARPETA_TEMP_AUDIO, f"lia_{idx}.mp3")


async def _sintetizar_async(texto: str, ruta: str):
    communicate = edge_tts.Communicate(texto, VOZ_NEURONAL)
    await communicate.save(ruta)


def _run_async(coro):
    """Ejecuta una corrutina de forma segura sin importar si ya hay un
    event loop corriendo en el hilo actual (p. ej. si esto se llama desde
    un hilo distinto al principal, que es justamente nuestro caso)."""
    try:
        asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(coro)
        finally:
            loop.close()


# --- CAMBIO CLAVE #2 ---
# Se separa "sintetizar" de "reproducir". Esto es lo que permite el
# pipeline en cerebro.py: un hilo sintetiza la frase N+1 MIENTRAS otro
# hilo reproduce la frase N. Sin esta separación, la latencia de red de
# Edge TTS (que no es instantánea) se traduce en silencios entre bloques.
def sintetizar_a_archivo(texto: str) -> str | None:
    """Convierte texto a un MP3 y devuelve la ruta del archivo generado.
    NO reproduce nada."""
    if not texto or not texto.strip():
        return None
    ruta = _siguiente_ruta_audio()
    try:
        _run_async(_sintetizar_async(texto, ruta))
        return ruta
    except Exception as e:
        print(f"❌ Error sintetizando voz: {e}")
        return None


def reproducir_archivo(ruta: str, borrar_despues: bool = True):
    """Reproduce un MP3 ya generado. Bloquea hasta que termina de sonar
    (por eso debe llamarse desde el hilo de reproducción, nunca desde el
    hilo principal de generación de texto)."""
    if not ruta or not os.path.exists(ruta):
        return
    try:
        pygame.mixer.music.load(ruta)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
    except Exception as e:
        print(f"❌ Error reproduciendo audio: {e}")
    finally:
        pygame.mixer.music.unload()
        if borrar_despues:
            try:
                os.remove(ruta)
            except OSError:
                pass

def hablar(texto: str):
    """Modo simple (sin pipeline): sintetiza y reproduce de una sola vez.
    Útil para un mensaje suelto o para pruebas (ver __main__), pero para
    streaming por bloques usa sintetizar_a_archivo() + reproducir_archivo()
    en hilos separados, como hace cerebro.py."""
    ruta = sintetizar_a_archivo(texto)
    if ruta:
        reproducir_archivo(ruta)


def escuchar(duracion_segundos: int = 5) -> str:
    """
    Graba el micrófono por N segundos y devuelve el texto transcrito por Vosk.
    """
    if not _vosk_model:
        print("❌ Modelo de Vosk no disponible.")
        return ""

    rec = KaldiRecognizer(_vosk_model, SAMPLE_RATE_STT)
    grabacion = sd.rec(int(duracion_segundos * SAMPLE_RATE_STT), samplerate=SAMPLE_RATE_STT, channels=1, dtype='int16')
    sd.wait()

    audio_bytes = grabacion.tobytes()
    if rec.AcceptWaveform(audio_bytes):
        resultado = json.loads(rec.Result())
    else:
        resultado = json.loads(rec.FinalResult())

    return resultado.get("text", "").strip()


if __name__ == "__main__":
    print("🔊 Probando módulo voz.py con pipeline síntesis/reproducción...")
    hablar("Módulo de voz actualizado a inteligencia neuronal. Te escucho.")
    print("🎤 Escuchando 5 segundos...")
    texto_capturado = escuchar(5)
    print(f"📝 Dijiste: '{texto_capturado}'")
    if texto_capturado:
        hablar(f"Entendí que dijiste: {texto_capturado}")