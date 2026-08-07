import time
import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np

# Configuración de grabación
FS = 16000  # Frecuencia de muestreo requerida por Vosk
DURATION = 5  # Segundos de grabación
AUDIO_FILE = "prueba_stt.wav"

def grabar_audio():
    print(f"\n🎤 Grabando por {DURATION} segundos... ¡Habla ahora!")
    grabacion = sd.rec(int(DURATION * FS), samplerate=FS, channels=1, dtype='int16')
    sd.wait()
    write(AUDIO_FILE, FS, grabacion)
    print("✅ Audio guardado.")

def probar_vosk():
    from vosk import Model, KaldiRecognizer
    import wave
    
    print("\n--- Iniciando prueba con VOSK (CPU) ---")
    start_load = time.time()
    # Asegúrate de descargar un modelo ligero de Vosk y ponerlo en la carpeta 'vosk-model'
    try:
        model = Model("vosk-model-small-es-0.42")
    except Exception as e:
        print("❌ Error: No se encontró el modelo de Vosk. Descárgalo de https://alphacephei.com/vosk/models")
        return

    rec = KaldiRecognizer(model, FS)
    print(f"⏱️ Tiempo de carga del modelo: {time.time() - start_load:.2f}s")
    
    wf = wave.open(AUDIO_FILE, "rb")
    start_infer = time.time()
    
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        rec.AcceptWaveform(data)
        
    resultado = rec.FinalResult()
    print(f"⏱️ Tiempo de inferencia: {time.time() - start_infer:.2f}s")
    print(f"📝 Resultado Vosk: {resultado}")

def probar_faster_whisper():
    from faster_whisper import WhisperModel
    
    print("\n--- Iniciando prueba con FASTER-WHISPER ---")
    start_load = time.time()
    # Usamos CPU e INT8 para no tocar la VRAM, simulando el peor escenario de carga
    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    print(f"⏱️ Tiempo de carga del modelo: {time.time() - start_load:.2f}s")
    
    start_infer = time.time()
    segments, info = model.transcribe(AUDIO_FILE, beam_size=5, language="es")
    
    texto = "".join([segment.text for segment in segments])
    print(f"⏱️ Tiempo de inferencia: {time.time() - start_infer:.2f}s")
    print(f"📝 Resultado Whisper: {texto}")

if __name__ == "__main__":
    grabar_audio()
    probar_vosk()
    probar_faster_whisper()