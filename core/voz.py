import os
import time
import threading
import json
import queue

import pygame
import sounddevice as sd
import numpy as np
import soundfile as sf
from vosk import Model, KaldiRecognizer
from faster_whisper import WhisperModel

# --- 1. IMPORTAMOS TUS RUTAS CENTRALIZADAS ---
from rutas import (
    CARPETA_TEMP_AUDIO,
    SONIDO_ACTIVACION,
    SONIDO_APAGADO,
    SONIDO_PENSANDO,
    SONIDO_ERROR,
    VOSK_MODEL_PATH
)

# Diccionario para acceso rápido a los efectos
RUTAS_SONIDOS = {
    "activacion": str(SONIDO_ACTIVACION),
    "apagado": str(SONIDO_APAGADO),
    "pensando": str(SONIDO_PENSANDO),
    "error": str(SONIDO_ERROR)
}

# --- CONFIGURACIÓN DE MODELOS Y STT ---
VOZ_NEURONAL = "es-MX-DaliaNeural"  
AUDIO_MIC_TEMP = str(CARPETA_TEMP_AUDIO / "temp_mic.wav")  
SAMPLE_RATE_STT = 16000

# --- INICIALIZACIÓN DE PYGAME ---
pygame.mixer.init()
_canal_pensando = None

# --- OÍDOS: MODELO WHISPER ---
print("🧠 Cargando modelo auditivo Whisper (puede tardar la primera vez)...")
try:
    _whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
except Exception as e:
    print(f"⚠️ Warning: No se pudo cargar Whisper: {e}")
    _whisper_model = None

# ---------------------------------------------------------
# FUNCIONES DE EFECTOS DE SONIDO 
# ---------------------------------------------------------
def reproducir_efecto(nombre_efecto):
    global _canal_pensando
    ruta = RUTAS_SONIDOS.get(nombre_efecto)
    if ruta and os.path.exists(ruta):
        try:
            efecto = pygame.mixer.Sound(ruta)
            canal = efecto.play()
            if nombre_efecto == "pensando" and canal:
                _canal_pensando = canal
        except Exception as e:
            print(f"⚠️ Error reproduciendo efecto '{nombre_efecto}': {e}")

def detener_efecto_pensando():
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
    Graba el micrófono con detección de silencio (VAD).
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
            pass # Ignoramos warnings menores en consola

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

def esperar_palabra_clave():
    """
    Centinela Vosk con GRAMÁTICA CERRADA.
    """
    print("👂 [Centinela Vosk] Iniciando en modo estricto... Cargando modelo ligero...")
    try:
        modelo = Model(str(VOSK_MODEL_PATH))
    except Exception as e:
        print(f"❌ Error al cargar modelo Vosk. ¿Está bien la ruta en VOSK_MODEL_PATH? Error: {e}")
        return False

    # AQUI ESTA LA MAGIA: Obligamos a Vosk a conocer SOLO estas palabras
    gramatica_estricta = '["oye lía", "oye", "lía", "[unk]"]'
    reconocedor = KaldiRecognizer(modelo, 16000, gramatica_estricta)
    
    q = queue.Queue()

    def callback(indata, frames, time_info, status):
        if status:
            pass
        q.put(bytes(indata))

    print("📡 Radar Activo. Esperando 'Oye Lía'...")

    with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                           channels=1, callback=callback):
        while True:
            data = q.get()
            if reconocedor.AcceptWaveform(data):
                resultado = json.loads(reconocedor.Result())
                texto = resultado.get("text", "")
                
                # Verificamos si logramos capturar la frase completa o parcial
                if "oye lía" in texto or "oye lia" in texto:
                    print("\n🔥 ¡Palabra clave detectada!")
                    return True
            else:
                parcial = json.loads(reconocedor.PartialResult())
                texto_parcial = parcial.get("partial", "")
                # Pequeño feedback visual en la misma línea
                if texto_parcial:
                    print(f"📡 Radar escuchando: {texto_parcial}       ", end='\r', flush=True)

if __name__ == "__main__":
    print("🔊 Probando módulo voz.py (Centinela Vosk Restringido + Oídos Whisper)...")
    
    while True:
        activado = esperar_palabra_clave()
        
        if activado:
            texto_capturado = escuchar()
            if texto_capturado:
                print(f"📝 Dijiste: '{texto_capturado}'")
                print(f"🧠 El texto está listo para enviarse al enrutador TTS.\n")