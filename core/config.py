"""
config.py — Parámetros lógicos, modelos y umbrales de L-IA.
Si necesitas cambiar de hardware, de modelo LLM o ajustar la memoria,
solo tocas este archivo.
"""

# =========================================================
# 1. MODELOS DE LENGUAJE (Cerebro)
# =========================================================
MODELO_LOCAL = "gemma2"                # Cerebro cotidiano (rápido, censurado)
MODELO_UNCENSORED = "dolphin-mistral"  # Especialista sin filtros (bajo demanda)
MODELO_NUBE_FLASH = "gemini-3.7-flash" # Analista rápido (visión, web, contexto medio)
MODELO_NUBE_PRO = "gemini-3.1-pro"     # Artillería pesada (contexto enorme / análisis profundo)
OPCIONES_GPU_LOCAL = {"num_gpu": 31}   # Unificado en todas las llamadas a Ollama para evitar recargas de VRAM

# =========================================================
# 2. MEMORIA RAG Y VECTORIZACIÓN (ChromaDB + SQLite)
# =========================================================
# Interruptor de hardware: "local_cpu" (no gasta VRAM), "local_gpu" o "gemini_api"
EMBEDDING_PROVIDER = "local_cpu"

# Modelo multilingüe ligero (~120MB) optimizado para español y código
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

# Nombre de la colección principal en ChromaDB
CHROMA_COLLECTION_NAME = "memoria_largo_plazo"

# Límites de fragmentación y protección de VRAM
CHUNK_SIZE = 600             # Caracteres máx. por fragmento
CHUNK_OVERLAP = 100          # Solapamiento para no cortar ideas
MAX_RAG_RESULTS = 3          # Máximo de recuerdos inyectados al prompt de Gemma 2
SIMILARITY_THRESHOLD = 0.85  # Distancia L2 máxima permitida (menor = más estricto; >1.6 se ignora)

# =========================================================
# 3. AUDIO, ESCUCHA Y MOTORES DE VOZ (STT / TTS)
# =========================================================
SAMPLE_RATE_STT = 16000

# --- Escucha (Whisper) y Radar (Vosk) ---
UMBRAL_VOZ_ESCUCHA = 0.015
GRACIA_MAX_PITIDO = 0.6
UMBRAL_RUIDO_RADAR = 0.018
BLOQUES_GRACIA_RADAR = 3
VARIANTES_ACTIVACION = ("oye lia", "oye lía", "oye elia", "oye día", "oye guia")

# --- Reglas de enrutamiento de Voz ---
MOTOR_VOZ_DEFAULT = "kokoro"          # Respuestas cortas y cotidianas (CPU local)
MOTOR_VOZ_PESADO = "google"           # Cuando entra RAG técnico, visión o código pesado
MOTOR_VOZ_UNCENSORED = "google"       # Voz asignada a Dolphin
MOTOR_TEXTOS_LARGOS = "edge"          # Fallback cuando un texto supera MAX_PALABRAS_KOKORO
MAX_PALABRAS_KOKORO = 30

# --- Perfiles de Voz ---
VOICE_KOKORO = "ef_dora"
VELOCIDAD_KOKORO = 0.9

VOICE_NUBE = "es-AR-ElenaNeural"      # Alternativa local: "es-EC-AndreaNeural"
RATE_EDGE = "+0%"

VOICE_DOLPHIN = "es-US-Wavenet-A"
VELOCIDAD_GOOGLE = 1.0

# --- Canales Pygame y Formato ---
CANAL_VOZ = 0
CANAL_EFECTOS = 7
AUDIO_EXTENSION = {"kokoro": ".wav", "edge": ".mp3", "google": ".mp3"}

# --- Motivos que disparan el MOTOR_VOZ_PESADO ---
MOTIVOS_RUTA_PESADOS = {
    "codigo_pesado", "analisis_profundo", "vision",
    "web", "contexto_grande", "codigo_contexto_grande",
}