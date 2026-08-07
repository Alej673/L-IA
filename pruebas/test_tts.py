import subprocess
import time
import sounddevice as sd
import numpy as np

# Rutas actualizadas a tus nuevas carpetas
PIPER_EXE = r"piper\piper.exe"
MODEL_PATH = r"VozLia\es_MX-cortana-19669-epoch-high.onnx" 

# Texto largo para probar el límite del modelo "high"
TEXTO_PRUEBA = "Hola. Soy L-IA, tu asistente virtual. Estoy probando mi nueva voz neuronal desde la carpeta dedicada. Si puedo procesar este párrafo completo, con todas sus comas y pausas, sin ahogar el procesador y en un tiempo razonable, entonces estoy lista para integrarme a la fase cinco."

def prueba_final_cortana():
    print("\n--- PRUEBA DE ESTRÉS: CORTANA (HIGH) ---")
    start_time = time.time()
    
    cmd = [
        PIPER_EXE,
        "--model", MODEL_PATH,
        "--output-raw"
    ]
    
    try:
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Le enviamos el texto largo
        stdout_data, stderr_data = process.communicate(input=TEXTO_PRUEBA.encode('utf-8'))
        
        if process.returncode != 0:
            print(f"❌ Error en Piper EXE: {stderr_data.decode('utf-8')}")
            return
            
    except Exception as e:
        print(f"❌ Error al ejecutar Piper: {e}")
        return

    tiempo_sintesis = time.time() - start_time
    print(f"⏱️ Tiempo total para párrafo largo: {tiempo_sintesis:.2f}s")
    
    print("🔊 Reproduciendo Cortana...")
    # Las voces high suelen usar 22050 o a veces 44100. Probemos con la estándar de Piper.
    sample_rate = 22050
    audio_data = np.frombuffer(stdout_data, dtype=np.int16)
    
    sd.play(audio_data, samplerate=sample_rate)
    sd.wait()
    print("✅ Prueba finalizada.")

if __name__ == "__main__":
    prueba_final_cortana()