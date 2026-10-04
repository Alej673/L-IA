from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# 1. PRIMERO definimos las carpetas bases
CARPETA_SONIDOS = BASE_DIR / "sonidos"
CARPETA_TEMP_AUDIO = BASE_DIR / "temp_audio"
CARPETA_DATA = BASE_DIR / "data"

# 2. LUEGO asignamos los archivos usando esas carpetas
SONIDO_ACTIVACION = CARPETA_SONIDOS / "activacion.wav"
SONIDO_ERROR = CARPETA_SONIDOS / "error.wav"
SONIDO_PENSANDO = CARPETA_SONIDOS / "pensando.wav"
SONIDO_APAGADO = CARPETA_SONIDOS / "apagado.wav" 

VOSK_MODEL_PATH = str(BASE_DIR / "vosk-model-small-es-0.42")