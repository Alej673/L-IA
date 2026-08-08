import asyncio
import os
import time
import threading
import json
import sys
import wave
import edge_tts
import pygame
import sounddevice as sd
import numpy as np
import soundfile as sf
from vosk import Model, KaldiRecognizer
from faster_whisper import WhisperModel
import queue
import wave

# --- CONFIGURACIÓN DE RUTAS ---
VOSK_MODEL_PATH = "vosk-model-small-es-0.42"
VOZ_NEURONAL = "es-MX-DaliaNeural"  # Voz principal de L-IA (Neuronales de Microsoft)
CARPETA_TEMP_AUDIO = "temp_audio"
AUDIO_MIC_TEMP = "temp_mic.wav"  # Archivo temporal para grabar tu voz (Whisper)
SAMPLE_RATE_STT = 16000

os.makedirs(CARPETA_TEMP_AUDIO, exist_ok=True)

# --- CAMBIO CLAVE #1 ---
# Antes: pygame.mixer.init() / .quit() en CADA frase.
# Eso reabre el dispositivo de audio en cada bloque -> "clicks" y latencia
# extra justo en el punto donde más nos importa la fluidez. Ahora se
# inicializa una sola vez, al importar el módulo.
pygame.mixer.init()

# --- RUTAS DE EFECTOS DE SONIDO (UI) ---
# Generador automático de .wav de respaldo: si no tienes tus propios audios
# descargados en la carpeta 'sonidos', se crean tonos sintéticos la primera
# vez que se importa el módulo, y luego se reutilizan (no se regeneran en
# cada corrida). Así reproducir_efecto() siempre tiene un archivo real que
# cargar y no necesita un fallback de tono en tiempo de reproducción.
# --- RUTAS DE EFECTOS DE SONIDO (UI) ---
CARPETA_SONIDOS = "sonidos"
os.makedirs(CARPETA_SONIDOS, exist_ok=True)

RUTAS_SONIDOS = {
    "activacion": os.path.join(CARPETA_SONIDOS, "ksjsbwuil-ui-beep-4-513914.mp3"),
    "apagado": os.path.join(CARPETA_SONIDOS, "universfield-ui-interface-03-277552.mp3"), # Conservamos el viejo para el apagado por ahora
    "pensando": os.path.join(CARPETA_SONIDOS, "fnx_sound-digital-awakening_fnx-sound-287658.mp3"),
}


# --- OÍDOS: DOS MODELOS, DOS TRABAJOS DISTINTOS ---
# Vosk se queda EXCLUSIVAMENTE para el wake word ("oye lía"): es liviano
# y puede correr escuchando en segundo plano de forma indefinida sin
# gastar CPU/RAM como lo haría Whisper corriendo 24/7.
try:
    _vosk_model = Model(VOSK_MODEL_PATH)
except Exception as e:
    print(f"⚠️ Warning: No se pudo cargar Vosk desde '{VOSK_MODEL_PATH}': {e}")
    _vosk_model = None

# Whisper entra SOLO cuando ya sabemos que el usuario quiere hablar (después
# del wake word), para la transcripción real de la orden. Es más pesado
# pero mucho más preciso que Vosk para comprensión, así que vale la pena
# pagar ese costo solo en el momento puntual en que hace falta.
print("🧠 Cargando modelo auditivo Whisper (puede tardar la primera vez)...")
try:
    _whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
except Exception as e:
    print(f"⚠️ Warning: No se pudo cargar Whisper: {e}")
    _whisper_model = None

_contador_audio = 0
_lock_contador = threading.Lock()

def reproducir_efecto(nombre_efecto):
    """Reproduce un efecto de sonido de la interfaz sin bloquear la ejecución."""
    ruta = RUTAS_SONIDOS.get(nombre_efecto)
    if ruta and os.path.exists(ruta):
        try:
            efecto = pygame.mixer.Sound(ruta)
            efecto.play()
        except Exception as e:
            print(f"⚠️ Error reproduciendo efecto '{nombre_efecto}': {e}")


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
    """Reproduce un MP3 ya generado. Bloquea hasta que termina de sonar..."""
    if not ruta or not os.path.exists(ruta):
        return
    try:
        # --- NUEVO: Cortar el efecto de fondo justo antes de abrir la boca ---
        detener_efecto_pensando() 
        
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


def _reproducir_tono(frecuencia, duracion):
    """Genera un bip sintético en vivo (sin archivo). Se mantiene disponible
    para pruebas puntuales, pero reproducir_efecto() ya no depende de esto:
    ahora siempre hay un .wav real en disco gracias a _crear_wav_sintetico()."""
    fs = 44100
    t = np.linspace(0, duracion, int(fs * duracion), False)
    nota = np.sin(2 * np.pi * frecuencia * t) * 0.3
    sd.play(nota, samplerate=fs)
    sd.wait()


_canal_pensando = None

def reproducir_efecto(nombre_efecto):
    """Reproduce un efecto de sonido de la interfaz sin bloquear la ejecución."""
    global _canal_pensando
    ruta = RUTAS_SONIDOS.get(nombre_efecto)
    if ruta and os.path.exists(ruta):
        try:
            efecto = pygame.mixer.Sound(ruta)
            canal = efecto.play()
            
            # Si es el sonido de "pensando", guardamos su canal para cortarlo después
            if nombre_efecto == "pensando" and canal:
                _canal_pensando = canal
                
        except Exception as e:
            print(f"⚠️ Error reproduciendo efecto '{nombre_efecto}': {e}")

def detener_efecto_pensando():
    """Corta el sonido de 'pensando' instantáneamente si todavía está sonando."""
    global _canal_pensando
    if _canal_pensando:
        _canal_pensando.stop()
        _canal_pensando = None


# --- CAMBIO CLAVE #3: STT REAL CON WHISPER ---
# Antes esta función usaba Vosk también para transcribir la orden
# completa, pero Vosk es un motor liviano pensado para detección rápida
# de palabras clave, no para precisión de dictado. Ahora graba igual con
# sounddevice, pero delega la transcripción a faster-whisper, que entiende
# mucho mejor acentos, pausas y frases largas.
def escuchar(duracion_segundos: int = 9) -> str:
    """
    Graba el micrófono por N segundos y transcribe usando Whisper de alta precisión.
    Incluye efectos de sincronización para evitar comerse la primera sílaba.
    """
    if not _whisper_model:
        print("❌ Modelo Whisper no disponible.")
        return ""

    # 1. Sonido de "¡Habla ahora!"
    reproducir_efecto("activacion")

    print(f"🎤 Grabando {duracion_segundos} segundos...")
    grabacion = sd.rec(
        int(duracion_segundos * SAMPLE_RATE_STT),
        samplerate=SAMPLE_RATE_STT, channels=1, dtype='float32'
    )
    sd.wait()

    # 2. Sonido de "Terminé de grabar"
    reproducir_efecto("apagado")

    sf.write(AUDIO_MIC_TEMP, grabacion, SAMPLE_RATE_STT)

    print("🧠 Whisper procesando el audio...")
    # 3. Parámetros estrictos anti-alucinaciones
    segments, info = _whisper_model.transcribe(
        AUDIO_MIC_TEMP,
        language="es",
        beam_size=5,
        condition_on_previous_text=False,
        initial_prompt="Comandos comunes: busca en internet, estado de la laptop, abre el proyecto, quién fue el campeón."
    )

    # Los segmentos vienen como un generador; los unimos en un solo texto.
    texto_final = " ".join(segment.text for segment in segments).strip()

    # Limpieza del archivo temporal para no ir acumulando .wav en el disco
    try:
        os.remove(AUDIO_MIC_TEMP)
    except OSError:
        pass

    return texto_final


def esperar_palabra_clave(palabra_clave="oye lía"):
    """
    Abre un micrófono en segundo plano que escucha infinitamente gastando lo mínimo.
    Solo se detiene y devuelve True cuando escucha la palabra clave.
    Sigue usando Vosk a propósito: es el motor correcto para esto porque
    puede quedarse escuchando indefinidamente sin el costo de Whisper.
    """
    if not _vosk_model:
        return False

    q = queue.Queue()

    def callback(indata, frames, time, status):
        """Mete los pedacitos de audio a la cola en tiempo real"""
        if status:
            print(status, file=sys.stderr)
        q.put(bytes(indata))

    print(f"👂 [Centinela Vosk activo] Esperando la frase: '{palabra_clave}'...")

    rec = KaldiRecognizer(_vosk_model, SAMPLE_RATE_STT)
    with sd.RawInputStream(samplerate=SAMPLE_RATE_STT, blocksize=8000,
                           dtype='int16', channels=1, callback=callback):
        while True:
            data = q.get()
            if rec.AcceptWaveform(data):
                resultado = json.loads(rec.Result())
                texto_detectado = resultado.get("text", "").strip().lower()
                
                # Ampliamos la red de captura para errores comunes de Vosk
                variaciones = ["oye lia", "oye lía", "oyelia", "oye dia", "oye guía", "lia", "liaa", "lira",]
                if any(variacion in texto_detectado for variacion in variaciones):
                    print("\n🔥 ¡Palabra clave detectada!")
                    return True


if __name__ == "__main__":
    print("🔊 Probando módulo voz.py: TTS por pipeline + STT con Whisper...")
    hablar("Módulo de voz actualizado. Ahora entiendo mejor lo que dices.")
    texto_capturado = escuchar(5)
    print(f"📝 Dijiste: '{texto_capturado}'")
    if texto_capturado:
        hablar(f"Entendí que dijiste: {texto_capturado}")