import time
import sys
import ollama
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

MODELO_TEST = 'gemma2'

def barra_separadora(titulo):
    print("\n" + "=" * 60)
    print(f" 🧪 {titulo}")
    print("=" * 60)

def test_1_ollama_puro_sin_contexto():
    barra_separadora("TEST 1: Inferencia Pura de Ollama (Sin System Prompt)")
    print(f"Probando respuesta a 'Hola' en modelo '{MODELO_TEST}'...")
    
    t_inicio = time.perf_counter()
    primer_token = True
    t_primer_token = 0.0
    conteo_tokens = 0

    try:
        stream = ollama.chat(
            model=MODELO_TEST,
            messages=[{'role': 'user', 'content': 'Hola'}],
            stream=True
        )

        print("\n[SALIDA EN VIVO]: ", end="", flush=True)
        for chunk in stream:
            token = chunk['message']['content']
            if token:
                if primer_token:
                    t_primer_token = time.perf_counter() - t_inicio
                    primer_token = False
                conteo_tokens += 1
                print(token, end="", flush=True)

        t_total = time.perf_counter() - t_inicio
        t_gen = t_total - t_primer_token
        v = (conteo_tokens / t_gen) if t_gen > 0 else 0

        print("\n\n📊 RESULTADOS TEST 1:")
        print(f" - Tiempo al primer token (TTFT): {t_primer_token:.2f}s")
        print(f" - Tokens generados: {conteo_tokens}")
        print(f" - Tiempo total: {t_total:.2f}s")
        print(f" - Velocidad pura: {v:.1f} t/s")
        
        if t_primer_token > 2.5:
            print(" ⚠️ ALERTA: El arranque del modelo es lento. Puede deberse a que el modelo estaba descargado de VRAM.")
        if v < 15.0:
            print(" ⚠️ ALERTA: La tasa de generación está baja. Es posible que el modelo esté usando CPU en lugar de la GPU (VRAM).")
        else:
            print(" ✅ Rendimiento de hardware y Ollama nominal.")

    except Exception as e:
        print(f"\n❌ Error conectando con Ollama: {e}")

def test_2_cerebro_completo():
    barra_separadora("TEST 2: Canal de Cerebro Local Completo")
    print("Cargando cerebro y evaluando 'hola' con prompt de sistema...")

    try:
        from core.cerebro import responder_con_local
        import core.prompt_builder as prompt_builder

        instrucciones = prompt_builder.obtener_instrucciones_sistema("casual")
        historial = "Usuario: hola"

        t_inicio = time.perf_counter()
        primer_token = True
        t_primer_token = 0.0
        conteo_tokens = 0

        def capturador_stream(fragmento):
            nonlocal primer_token, t_primer_token, conteo_tokens
            if primer_token:
                t_primer_token = time.perf_counter() - t_inicio
                primer_token = False
            conteo_tokens += 1
            sys.stdout.write(fragmento)
            sys.stdout.flush()

        print("\n[STREAM CEREBRO]: ", end="", flush=True)
        resultado = responder_con_local(
            instrucciones_sistema=instrucciones,
            contexto_historico=historial,
            quiere_abrir=False,
            quiere_estado=False,
            callback_stream=capturador_stream
        )

        t_total = time.perf_counter() - t_inicio
        t_gen = t_total - t_primer_token
        v = (conteo_tokens / t_gen) if t_gen > 0 else 0

        print("\n\n📊 RESULTADOS TEST 2 (CEREBRO):")
        print(f" - Tiempo al primer token: {t_primer_token:.2f}s")
        print(f" - Tiempo total: {t_total:.2f}s")
        print(f" - Velocidad observada: {v:.1f} t/s")

    except Exception as e:
        print(f"\n❌ Error ejecutando cerebro: {e}")

if __name__ == "__main__":
    test_1_ollama_puro_sin_contexto()
    test_2_cerebro_completo()