"""
voz.py — Módulo de comunicación de L-IA (oídos: STT / boca: TTS).
"""
import asyncio
import json
import os
import queue
import re
import threading
import time
from xml.sax.saxutils import escape as _escapar_xml

import numpy as np
import pygame
import sounddevice as sd
import soundfile as sf
from vosk import Model, KaldiRecognizer
from faster_whisper import WhisperModel

# --- IMPORTS TTS ---
from kokoro import KPipeline
import edge_tts
from google.cloud import texttospeech

# Funciona si lo importa cerebro.py (core.rutas) o si ejecutas voz.py directo.
try:
    from core import rutas
except ModuleNotFoundError:
    import rutas


# =========================================================
# CONFIGURACIÓN (todo lo ajustable en un solo lugar)
# =========================================================
SAMPLE_RATE_STT = 16000

# --- Escucha (Whisper) ---
UMBRAL_VOZ_ESCUCHA = 0.015     # RMS mínimo para considerar que hablas
GRACIA_MAX_PITIDO = 0.6        # seg. máx. que se ignora el micro tras el pitido (evita que se active con su propio bip)

# --- Radar (Vosk) ---
UMBRAL_RUIDO_RADAR = 0.018     # Súbelo si el ventilador/calle lo activa; bájalo si tienes que gritar
BLOQUES_GRACIA_RADAR = 3       # bloques (0.25 s c/u) que se siguen enviando a Vosk tras oír voz, para que cierre la frase
VARIANTES_ACTIVACION = ("oye lia", "oye lía", "oye elia", "oye día", "oye guia")

# --- Selección de motor TTS ---
MAX_PALABRAS_KOKORO = 30       # antes 50. Kokoro (CPU) solo para textos cortos
MOTOR_TEXTOS_LARGOS = "edge"   # motor para textos que superan el límite

# --- Voces ---
VOICE_KOKORO = "ef_dora"
VELOCIDAD_KOKORO = 0.9
VOICE_NUBE = "es-AR-ElenaNeural"   # alternativa con acento más cercano al tuyo: "es-EC-AndreaNeural"
RATE_EDGE = "+0%"
VOICE_DOLPHIN = "es-US-Wavenet-A"
VELOCIDAD_GOOGLE = 1.0

# --- Canales de pygame ---
CANAL_VOZ = 0
CANAL_EFECTOS = 7

AUDIO_EXTENSION = {"kokoro": ".wav", "edge": ".mp3", "google": ".mp3"}

RUTAS_SONIDOS = {
    "activacion": rutas.SONIDO_ACTIVACION,
    "apagado": rutas.SONIDO_APAGADO,
    "pensando": rutas.SONIDO_PENSANDO,
    "error": rutas.SONIDO_ERROR,
}


# =========================================================
# INICIALIZACIÓN
# =========================================================
# Credenciales de Google: solo se registran si el archivo existe. El cliente se
# crea la primera vez que se usa; si fallan, hablar() cae a Kokoro.
if rutas.RUTA_GOOGLE_JSON.exists():
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(rutas.RUTA_GOOGLE_JSON)
_cliente_google = None

# OJO: en pygame.mixer.init(), `channels` es mono/estéreo (1 o 2), NO la cantidad
# de canales de mezcla. Esa se fija con set_num_channels().
pygame.mixer.init(channels=2)
pygame.mixer.set_num_channels(8)
_canal_pensando = None
_cache_efectos = {}
_lock_kokoro = threading.Lock()  # Kokoro no debe usarse desde dos hilos a la vez


def _cargar(nombre, fabrica):
    """Carga un modelo pesado; si falla, avisa y devuelve None (sin tumbar el módulo)."""
    try:
        return fabrica()
    except Exception as e:
        print(f"⚠️ Warning: No se pudo cargar {nombre}: {e}")
        return None


for _nombre, _ruta in rutas.verificar_rutas():
    print(f"⚠️ Falta {_nombre}: {_ruta}")

print("⏳ Cargando el cerebro local de voz (Kokoro)...")
# En CPU: evita el conflicto de cuDNN y no compite por la VRAM de 6 GB con gemma2/dolphin.
pipeline_kokoro = _cargar("Kokoro", lambda: KPipeline(lang_code="e", device="cpu"))

print("🧠 Cargando modelo auditivo Whisper (puede tardar la primera vez)...")
_whisper_model = _cargar("Whisper", lambda: WhisperModel("small", device="cpu", compute_type="int8"))

print("👂 Cargando modelo centinela Vosk...")
_vosk_model = _cargar("Vosk", lambda: Model(str(rutas.VOSK_MODEL_PATH)))


# =========================================================
# EFECTOS DE SONIDO
# =========================================================
def _obtener_efecto(nombre):
    """Carga cada efecto una sola vez y lo reutiliza."""
    if nombre not in _cache_efectos:
        ruta = RUTAS_SONIDOS.get(nombre)
        try:
            _cache_efectos[nombre] = pygame.mixer.Sound(str(ruta))
        except Exception as e:
            print(f"⚠️ Efecto '{nombre}' no disponible ({ruta}): {e}")
            _cache_efectos[nombre] = None
    return _cache_efectos[nombre]

def reproducir_efecto(nombre_efecto) -> float:
    """Reproduce un efecto. Si es 'pensando', entra en bucle hasta que se detenga."""
    global _canal_pensando
    efecto = _obtener_efecto(nombre_efecto)
    if efecto is None:
        return 0.0
    canal = pygame.mixer.Channel(CANAL_EFECTOS)
    
    if nombre_efecto == "pensando":
        canal.play(efecto, loops=-1)  # Bucle infinito
        _canal_pensando = canal
    else:
        canal.play(efecto)
        
    return efecto.get_length()

def detener_efecto_pensando():
    global _canal_pensando
    if _canal_pensando and _canal_pensando.get_busy():
        _canal_pensando.stop()
    _canal_pensando = None


# =========================================================
# ENTRADA (STT - ESCUCHA)
# =========================================================
def escuchar(duracion_maxima: float = 20.0, silencio_para_cortar: float = 1.2,
             timeout_inicio: float = 6.0, umbral_voz: float = UMBRAL_VOZ_ESCUCHA) -> str:
    if not _whisper_model:
        return ""

    bloques = []
    # gracia_hasta = inf hasta que suene el pitido: el callback ignora el volumen
    # mientras tanto, así el propio bip no cuenta como "voz".
    estado = {"hablando": False, "ultimo_voz": 0.0, "inicio": 0.0, "gracia_hasta": float("inf")}
    evento_corte = threading.Event()

    def callback(indata, frames, time_info, status):
        ahora = time.time()
        bloques.append(indata.copy())  # se graba siempre, para no perder la primera sílaba

        if ahora < estado["gracia_hasta"]:
            return

        rms = float(np.sqrt(np.mean(indata.astype(np.float64) ** 2)))
        if rms >= umbral_voz:
            estado["hablando"] = True
            estado["ultimo_voz"] = ahora

        if not estado["hablando"] and (ahora - estado["inicio"]) >= timeout_inicio:
            evento_corte.set()
        if estado["hablando"] and (ahora - estado["ultimo_voz"]) >= silencio_para_cortar:
            evento_corte.set()
        if (ahora - estado["inicio"]) >= duracion_maxima:
            evento_corte.set()

    print("🎤 Abriendo canal de audio...")
    stream = sd.InputStream(samplerate=SAMPLE_RATE_STT, channels=1, dtype="float32",
                            callback=callback, blocksize=int(SAMPLE_RATE_STT * 0.1))

    with stream:
        # El pitido suena con el micro ya grabando.
        duracion_pitido = min(reproducir_efecto("activacion"), GRACIA_MAX_PITIDO)
        estado["inicio"] = time.time() + duracion_pitido
        estado["gracia_hasta"] = estado["inicio"]
        evento_corte.wait(timeout=duracion_maxima + timeout_inicio + 2)  # red de seguridad

    reproducir_efecto("apagado")

    if not estado["hablando"] or not bloques:
        print("🤫 No se detectó voz, cancelando.")
        return ""

    audio_np = np.concatenate(bloques, axis=0).flatten().astype(np.float32)

    print("🧠 Whisper procesando el audio...")
    segments, _ = _whisper_model.transcribe(
        audio_np, language="es", beam_size=5,
        condition_on_previous_text=False,
        vad_filter=True,  # descarta tramos sin voz (el bip, ruido) y reduce alucinaciones
    )
    return " ".join(segment.text for segment in segments).strip()


def esperar_palabra_clave() -> bool:
    """Centinela Vosk con escudo anti-ruido (noise gate)."""
    if not _vosk_model:
        return False

    reconocedor = KaldiRecognizer(_vosk_model, SAMPLE_RATE_STT)
    q = queue.Queue()

    def callback(indata, frames, time_info, status):
        data = bytes(indata)
        audio = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
        q.put((data, float(np.sqrt(np.mean(audio ** 2)))))

    print("📡 Radar Activo. Esperando activación...")
    bloques_gracia = 0

    with sd.RawInputStream(samplerate=SAMPLE_RATE_STT, blocksize=4000, dtype="int16",
                           channels=1, callback=callback):
        while True:
            data, rms = q.get()

            # 1. Anti-retroalimentación: L-IA no se escucha a sí misma
            if pygame.mixer.get_busy():
                reconocedor.AcceptWaveform(b"\x00" * len(data))
                bloques_gracia = 0
                continue

            # 2. Escudo de ruido con "cola": tras oír voz seguimos alimentando a Vosk
            #    unos bloques más para no cortar sílabas suaves y que cierre la frase.
            if rms >= UMBRAL_RUIDO_RADAR:
                bloques_gracia = BLOQUES_GRACIA_RADAR
            elif bloques_gracia > 0:
                bloques_gracia -= 1
            else:
                continue

            # 3. Reconocimiento
            if reconocedor.AcceptWaveform(data):
                texto = json.loads(reconocedor.Result()).get("text", "")
            else:
                texto = json.loads(reconocedor.PartialResult()).get("partial", "")
            texto = texto.lower()

            if any(variante in texto for variante in VARIANTES_ACTIVACION):
                print(f"\n🔥 ¡Activación limpia! Volumen de voz: {rms:.3f}")
                return True
            if texto:
                print(f"📡 Radar [Vol: {rms:.3f}]: {texto}       ", end="\r", flush=True)


# =========================================================
# LIMPIEZA DE TEXTO PARA LA VOZ
# =========================================================
# La pantalla y el historial conservan emojis y Markdown; solo la voz los ignora.
_PATRON_EMOJIS = re.compile(
    "["
    "\U0001F300-\U0001FAFF"  # emoticonos, pictogramas, transporte, símbolos
    "\U0001F1E6-\U0001F1FF"  # banderas
    "\U00002600-\U000027BF"  # símbolos varios y dingbats
    "\U00002B00-\U00002BFF"  # estrellas y flechas
    "\U0000FE00-\U0000FE0F"  # selectores de variación
    "\U0000200D\U000020E3"   # uniones de emojis compuestos
    "]+",
    flags=re.UNICODE,
)
_PATRON_URL = re.compile(r"https?://\S+")

def limpiar_texto_voz(texto):
    """Quita URLs, emojis, markdown y suaviza siglas para una dicción natural."""
    texto = _PATRON_URL.sub("", texto)
    texto = _PATRON_EMOJIS.sub("", texto)
    texto = re.sub(r"[*_#`~¿¡]", "", texto)

    # --- 1. CURA DE DICCIONES ROBÓTICAS ---
    # Transforma "L-IA" en "Lía" para que no lo deletree "Ele guión I A"
    texto = re.sub(r"\bL-IA\b", "Lía", texto, flags=re.IGNORECASE)
    
    # Elimina números de versión como "v3.2.1" que destruyen el ritmo inicial
    texto = re.sub(r"\bv\d+(\.\d+)+\b", "", texto)

    # --- 2. CURA DE PAUSAS Y TARTAMUDEOS ---
    # Los puntos suspensivos se vuelven una coma simple para una pausa natural
    texto = texto.replace("...", ", ").replace("..", ", ")
    
    # Los saltos de línea y exclamaciones también se aplanan a comas
    texto = re.sub(r"[\n!?]+", ", ", texto)
    
    # --- 3. LIMPIEZA FINAL ---
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"([,.;:])(\s*,)+", r"\1", texto)  # Evita doble coma ",,"
    return texto.strip(" ,")


def contar_palabras(texto) -> int:
    return len(re.findall(r"\w+", texto))


def elegir_motor(texto) -> str:
    """Kokoro (local) para textos cortos; el motor de nube para los largos."""
    if contar_palabras(texto) <= MAX_PALABRAS_KOKORO:
        return "kokoro"
    return MOTOR_TEXTOS_LARGOS


# =========================================================
# SALIDA (TTS - HABLA)
# =========================================================
def generar_kokoro(texto, archivo):
    if pipeline_kokoro is None:
        raise RuntimeError("Kokoro no está cargado")
    with _lock_kokoro:
        # (el texto ya no trae saltos de línea, por eso no se usa split_pattern)
        generador = pipeline_kokoro(texto, voice=VOICE_KOKORO, speed=VELOCIDAD_KOKORO)
        audios = [audio for _, _, audio in generador if audio is not None]
    if not audios:
        raise ValueError("Kokoro no generó audio para este fragmento")
    sf.write(archivo, np.concatenate(audios), 24000)

def generar_edge(texto, archivo):
    """Genera audio con Edge TTS aislando el event loop para que no choque en hilos secundarios."""
    try:
        # 1. Creamos un bucle de eventos completamente nuevo y aislado para este hilo
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 2. Ejecutamos la comunicación asíncrona
        comunicador = edge_tts.Communicate(texto, VOICE_NUBE, rate=RATE_EDGE)
        loop.run_until_complete(comunicador.save(archivo))
        
        # 3. Cerramos el bucle limpiamente
        loop.close()
    except Exception as e:
        print(f"❌ Error crítico en Edge TTS: {e}")

def _obtener_cliente_google():
    global _cliente_google
    if _cliente_google is None:
        _cliente_google = texttospeech.TextToSpeechClient()
    return _cliente_google


def generar_google_emocional(texto, archivo, nivel_distorsion=0):
    # Se escapan &, < y > porque el texto va dentro de SSML (XML).
    texto_seguro = _escapar_xml(texto)
    if nivel_distorsion == 1:
        ssml = f'<speak><prosody pitch="-4st" rate="92%">{texto_seguro}</prosody></speak>'
    else:
        ssml = f"<speak>{texto_seguro}</speak>"

    codigo_idioma = "-".join(VOICE_DOLPHIN.split("-")[:2])
    voz = texttospeech.VoiceSelectionParams(language_code=codigo_idioma, name=VOICE_DOLPHIN)
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=VELOCIDAD_GOOGLE,
    )
    respuesta = _obtener_cliente_google().synthesize_speech(
        input=texttospeech.SynthesisInput(ssml=ssml), voice=voz, audio_config=audio_config
    )
    with open(archivo, "wb") as out:
        out.write(respuesta.audio_content)


def preparar_voz(texto, motor="kokoro", nivel_distorsion=0):
    """
    Fase 1: Solo renderiza el audio y lo guarda en disco.
    No bloquea la reproducción.
    """
    texto = limpiar_texto_voz(texto)
    if not re.search(r"\w", texto):  # Ignora si solo hay emojis o símbolos
        return None

    # CORRECCIÓN: Se usa rutas.CARPETA_TEMP_AUDIO y la extensión correcta
    extension = AUDIO_EXTENSION.get(motor, ".wav")
    archivo_salida = str(rutas.CARPETA_TEMP_AUDIO / f"temp_tts_{int(time.time() * 1000)}{extension}")
    
    print(f"🗣️ L-IA ({motor.upper()}): Sintetizando bloque...")

    try:
        if motor == "edge":
            generar_edge(texto, archivo_salida)
        elif motor == "google":
            generar_google_emocional(texto, archivo_salida, nivel_distorsion)
        else:
            generar_kokoro(texto, archivo_salida)
        return archivo_salida
    except Exception as e:
        print(f"❌ Error en el motor {motor.upper()}: {e}")
        return None


def reproducir_voz(archivo):
    """
    Fase 2: Reproduce el archivo de audio pre-renderizado.
    """
    if not archivo or not os.path.exists(archivo):
        return

    detener_efecto_pensando()

    try:
        sonido = pygame.mixer.Sound(archivo)
        canal_voz = pygame.mixer.Channel(CANAL_VOZ)
        canal_voz.play(sonido)

        # Espera activa hasta que el audio termine de sonar
        while canal_voz.get_busy():
            time.sleep(0.1)
    except Exception as e:
        print(f"❌ Error reproduciendo TTS: {e}")
    finally:
        descartar_audio(archivo)


def descartar_audio(archivo):
    """
    Fase 3: Limpieza del archivo temporal.
    """
    if archivo and os.path.exists(archivo):
        try:
            os.remove(archivo)
        except OSError:
            pass

def precalentar_motores():
    """Carga los tensores de Kokoro en RAM al arrancar, para que el primer mensaje no sea lento."""
    if pipeline_kokoro is None:
        return
    print("🔥 Precalentando cuerdas vocales (Kokoro)...")
    try:
        with _lock_kokoro:
            for _ in pipeline_kokoro("a", voice=VOICE_KOKORO, speed=1.0):
                pass
        print("✅ Kokoro listo para respuesta inmediata.")
    except Exception as e:
        print(f"⚠️ Error en precalentamiento: {e}")


def detener_audio_global():
    """Freno de emergencia: corta cualquier voz o sonido en reproducción."""
    pygame.mixer.stop()

def leer_pantalla_directo(texto, motor="edge"):
    """
    Función envoltorio para el botón del lector de la GUI.
    Renderiza y reproduce de un solo golpe.
    """
    archivo_audio = preparar_voz(texto, motor=motor)
    if archivo_audio:
        reproducir_voz(archivo_audio)

if __name__ == "__main__":
    print("🔊 Iniciando Módulo de Comunicación L-IA...")

    while True:
        if esperar_palabra_clave():
            texto_usuario = escuchar()

            if texto_usuario:
                print(f"👤 Usuario: '{texto_usuario}'")
                
                reproducir_efecto("pensando")
                time.sleep(2)  # Simula el tiempo de respuesta del LLM
                
                respuesta = "Hola, he procesado tu comando correctamente usando el motor local."
                
                # --- NUEVO FLUJO DE AUDIO MODULAR ---
                archivo_audio = preparar_voz(respuesta, motor="kokoro")
                if archivo_audio:
                    reproducir_voz(archivo_audio)