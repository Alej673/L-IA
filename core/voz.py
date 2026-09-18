import asyncio
import os
import time
import threading
import json
import sys
import queue
import wave
import edge_tts
import pygame
import sounddevice as sd
import numpy as np
import soundfile as sf
from vosk import Model, KaldiRecognizer
from faster_whisper import WhisperModel

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
CARPETA_SONIDOS = "sonidos"
os.makedirs(CARPETA_SONIDOS, exist_ok=True)

RUTAS_SONIDOS = {
    "activacion": os.path.join(CARPETA_SONIDOS, "ksjsbwuil-ui-beep-4-513914.mp3"),
    "apagado": os.path.join(CARPETA_SONIDOS, "universfield-ui-interface-03-277552.mp3"),
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
# del wake word), para la transcripción real de la orden.
print("🧠 Cargando modelo auditivo Whisper (puede tardar la primera vez)...")
try:
    _whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
except Exception as e:
    print(f"⚠️ Warning: No se pudo cargar Whisper: {e}")
    _whisper_model = None

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
    event loop corriendo en el hilo actual."""
    try:
        asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(coro)
        finally:
            loop.close()


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
    """Reproduce un MP3 ya generado. Bloquea hasta que termina de sonar."""
    if not ruta or not os.path.exists(ruta):
        return
    try:
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
    """Modo simple (sin pipeline): sintetiza y reproduce de una sola vez."""
    ruta = sintetizar_a_archivo(texto)
    if ruta:
        reproducir_archivo(ruta)


def _reproducir_tono(frecuencia, duracion):
    """Genera un bip sintético en vivo (sin archivo). Se mantiene disponible
    para pruebas puntuales."""
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


def escuchar(
    duracion_maxima: float = 20.0,
    silencio_para_cortar: float = 1.2,
    timeout_inicio: float = 6.0,
    umbral_voz: float = 0.015,
) -> str:
    """
    Graba el micrófono con detección de silencio (VAD por energía RMS) en
    vez de una duración fija: sigue escuchando mientras detecta voz, y
    corta recién cuando hay 'silencio_para_cortar' segundos de silencio
    DESPUÉS de que la persona ya empezó a hablar.
    """
    if not _whisper_model:
        print("❌ Modelo Whisper no disponible.")
        return ""

    reproducir_efecto("activacion")
    print("🎤 Escuchando (se corta sola al detectar silencio)...")

    bloques = []
    estado = {
        "hablando": False,
        "ultimo_momento_con_voz": None,
        "inicio": time.time(),
    }
    evento_corte = threading.Event()

    def callback(indata, frames, time_info, status):
        if status:
            print(status, file=sys.stderr)

        ahora = time.time()
        bloques.append(indata.copy())

        rms = float(np.sqrt(np.mean(indata.astype(np.float64) ** 2)))

        if rms >= umbral_voz:
            estado["hablando"] = True
            estado["ultimo_momento_con_voz"] = ahora

        if not estado["hablando"] and (ahora - estado["inicio"]) >= timeout_inicio:
            evento_corte.set()
            return

        if estado["hablando"]:
            silencio_actual = ahora - estado["ultimo_momento_con_voz"]
            if silencio_actual >= silencio_para_cortar:
                evento_corte.set()
                return

        if (ahora - estado["inicio"]) >= duracion_maxima:
            evento_corte.set()

    with sd.InputStream(
        samplerate=SAMPLE_RATE_STT, channels=1, dtype='float32',
        callback=callback, blocksize=int(SAMPLE_RATE_STT * 0.1)
    ):
        evento_corte.wait()

    reproducir_efecto("apagado")

    if not estado["hablando"]:
        print("🤫 No se detectó voz, cancelando.")
        return ""

    grabacion = np.concatenate(bloques, axis=0)
    sf.write(AUDIO_MIC_TEMP, grabacion, SAMPLE_RATE_STT)

    print("🧠 Whisper procesando el audio...")
    segments, info = _whisper_model.transcribe(
        AUDIO_MIC_TEMP,
        language="es",
        beam_size=5,
        condition_on_previous_text=False,
        initial_prompt="Comandos comunes: busca en internet, estado de la laptop, abre el proyecto, quién fue el campeón."
    )

    texto_final = " ".join(segment.text for segment in segments).strip()

    try:
        os.remove(AUDIO_MIC_TEMP)
    except OSError:
        pass

    return texto_final


def esperar_palabra_clave(palabra_clave="oye lía"):
    """
    Abre un micrófono en segundo plano que escucha infinitamente gastando lo mínimo.
    Solo se detiene y devuelve True cuando escucha la palabra clave.
    """
    if not _vosk_model:
        return False

    q = queue.Queue()

    def callback(indata, frames, time, status):
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

                variaciones = ["oye lia", "oye lía", "oyelia", "oye dia", "oye guía", "lia", "liaa", "lira"]
                if any(variacion in texto_detectado for variacion in variaciones):
                    print("\n🔥 ¡Palabra clave detectada!")
                    return True


def medir_rms(duracion=5):
    """Utilidad de calibración: imprime el RMS por bloques de 100ms para
    que puedas ver qué valores da tu ambiente en silencio vs. hablando, y
    así ajustar 'umbral_voz' en escuchar(). Solo se ejecuta si la llamás
    a propósito -- no corre sola al importar el módulo."""
    grabacion = sd.rec(int(duracion * SAMPLE_RATE_STT), samplerate=SAMPLE_RATE_STT, channels=1, dtype='float32')
    sd.wait()
    for i in range(0, len(grabacion), 1600):
        bloque = grabacion[i:i + 1600]
        print(round(float(np.sqrt(np.mean(bloque ** 2))), 4))


if __name__ == "__main__":
    print("🔊 Probando módulo voz.py: TTS por pipeline + STT con Whisper...")
    hablar("Módulo de voz actualizado. Ahora entiendo mejor lo que dices.")
    texto_capturado = escuchar()
    print(f"📝 Dijiste: '{texto_capturado}'")
    if texto_capturado:
        hablar(f"Entendí que dijiste: {texto_capturado}")