"""
rutas.py — Rutas centralizadas de L-IA.

Este archivo DEBE vivir en <proyecto>/core/: BASE_DIR sube dos niveles
(core/rutas.py -> core -> raíz del proyecto).
Todas las rutas son objetos Path (antes dos eran str y el resto Path).
Si algún otro módulo concatena VOSK_MODEL_PATH o RUTA_GOOGLE_JSON como texto
(ruta + "algo"), envuélvelo con str(...).
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# --- 1. Carpetas base ---
CARPETA_SONIDOS = BASE_DIR / "sonidos"
CARPETA_TEMP_AUDIO = BASE_DIR / "temp_audio"
CARPETA_DATA = BASE_DIR / "data"
CARPETA_CONFIG = BASE_DIR / "config"

# --- 2. Archivos ---
SONIDO_ACTIVACION = CARPETA_SONIDOS / "activacion.wav"
SONIDO_ERROR = CARPETA_SONIDOS / "error.wav"
SONIDO_PENSANDO = CARPETA_SONIDOS / "fnx_sound-digital-awakening_fnx-sound-287658.mp3"
SONIDO_APAGADO = CARPETA_SONIDOS / "universfield-ui-interface-03-277552.mp3"

VOSK_MODEL_PATH = BASE_DIR / "vosk-model-small-es-0.42"
RUTA_GOOGLE_JSON = CARPETA_CONFIG / "l-ia-tts-11c82ae533db.json"

# --- 3. Carpetas que el programa puede crear solo ---
# (sonidos/ y config/ NO se crean: si faltan, es un error real que debes ver)
for _carpeta in (CARPETA_TEMP_AUDIO, CARPETA_DATA):
    _carpeta.mkdir(parents=True, exist_ok=True)

# --- 4. Verificación de recursos ---
_RECURSOS = {
    "sonido de activación": SONIDO_ACTIVACION,
    "sonido de apagado": SONIDO_APAGADO,
    "sonido de pensando": SONIDO_PENSANDO,
    "sonido de error": SONIDO_ERROR,
    "modelo Vosk": VOSK_MODEL_PATH,
    "credenciales de Google TTS": RUTA_GOOGLE_JSON,
}


def verificar_rutas():
    """Devuelve una lista de (nombre, ruta) con los recursos que NO existen."""
    return [(nombre, ruta) for nombre, ruta in _RECURSOS.items() if not ruta.exists()]


if __name__ == "__main__":
    print(f"BASE_DIR = {BASE_DIR}")
    faltan = verificar_rutas()
    if faltan:
        for nombre, ruta in faltan:
            print(f"❌ Falta {nombre}: {ruta}")
    else:
        print("✅ Todas las rutas existen.")