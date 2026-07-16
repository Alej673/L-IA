import os
import time
import json
import re
from dotenv import load_dotenv
from google import genai
from mss import MSS
from PIL import Image
import prompt_builder
import database
import tools
import ollama

# ==========================================
# 1. CONFIGURACIÓN INICIAL
# ==========================================
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("❌ No se encontró la variable GEMINI_API_KEY")

client = genai.Client(api_key=api_key)

MODELO_LOCAL = 'gemma2'

PALABRAS_CLAVE_VISION = ["pantalla", "mira", "observa", "ves", "viendo"]
PALABRAS_CLAVE_ABRIR = ["abre", "abrir", "inicia", "ejecuta", "lanza"]

# NUEVO: Añadimos las palabras clave para que el enrutador detecte cuándo quieres un diagnóstico.
PALABRAS_CLAVE_ESTADO = ["estado", "diagnostico", "ram", "cpu", "bateria", "sistema", "computadora", "pc"]

# ==========================================
# 2. HERRAMIENTAS DE VISIÓN
# ==========================================
def tomar_captura_en_memoria():
    print("\n[👀 L-IA está analizando tu monitor...]")
    with MSS() as sct:
        monitor = sct.monitors[1]
        sct_img = sct.grab(monitor)
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        img.thumbnail((1024, 576))
        return img


# ==========================================
# 3. RUTA A: LA NUBE (Gemini - Visión + Tools nativas)
# ==========================================
def responder_con_nube(contexto_historico):
    print("\n[☁️ Enrutando a la Nube (Gemini 3.5 Flash)...]")
    contenidos_api = [contexto_historico]
    imagen_en_ram = tomar_captura_en_memoria()
    contenidos_api.insert(0, imagen_en_ram)

    max_reintentos = 3
    espera = 4
    texto_respuesta = None

    for intento in range(max_reintentos):
        try:
            response = client.models.generate_content(
                model='gemini-3.5-flash',
                contents=contenidos_api,
                config={"tools": [tools.abrir_aplicacion]}
            )

            if response.function_calls:
                llamada = response.function_calls[0]
                nombre_funcion = llamada.name
                argumentos = llamada.args

                print(f"\n⚙️ [L-IA Cloud ejecutando: '{nombre_funcion}']")
                if nombre_funcion == "abrir_aplicacion":
                    nombre_app = argumentos.get("nombre_app", "")
                    resultado_sistema = tools.abrir_aplicacion(nombre_app)
                    print(f"✅ [Sistema: {resultado_sistema}]")

                    contenidos_api.append(f"RESULTADO: {resultado_sistema}. Confirma la acción con sarcasmo.")
                    respuesta_final = client.models.generate_content(
                        model='gemini-3.5-flash',
                        contents=contenidos_api
                    )
                    texto_respuesta = respuesta_final.text
                else:
                    texto_respuesta = "No reconozco esa herramienta, pero aquí ando."
            else:
                texto_respuesta = response.text

            break

        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                print("\n🛑 [L-IA Nube]: Límite de la API gratuita alcanzado. Por favor, espera 1 minuto.")
                break
            elif "503" in error_str or "UNAVAILABLE" in error_str:
                if intento < max_reintentos - 1:
                    print(f"⚠️ Servidor de Google saturado. Reintentando en {espera}s...")
                    time.sleep(espera)
                    espera *= 2
                else:
                    print("\n🛑 [L-IA Nube]: Imposible conectar. Los servidores de Google siguen saturados.")
            else:
                print(f"\n❌ L-IA Error crítico en la Nube: {e}")
                break

    return texto_respuesta


# ==========================================
# 4. RUTA B: CEREBRO LOCAL (gemma2 - tool calling manual)
# ==========================================
def _extraer_llamada_manual(texto):
    """
    Busca un bloque JSON dentro del texto de respuesta.
    Ahora no solo busca 'abrir_aplicacion', sino cualquier 'accion'.
    """
    match = re.search(r'\{[^{}]*"accion"[^{}]*\}', texto, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


# MODIFICADO: Ahora recibimos también 'quiere_estado' como parámetro
def responder_con_local(instrucciones_sistema, contexto_historico, quiere_abrir_algo, quiere_estado):
    print(f"\n[🏠 Enrutando al Cerebro Local ({MODELO_LOCAL})...]")

    instrucciones_finales = instrucciones_sistema
    
    # MODIFICADO: El "Bozal Dinámico". Dependiendo de lo que el usuario pida,
    # le enseñamos a gemma2 cómo debe ser el formato de su JSON.
    if quiere_abrir_algo:
        instrucciones_finales += (
            "\n\nSi el usuario pide abrir una aplicación, responde ÚNICAMENTE "
            "con este JSON exacto (sin texto extra, sin markdown):\n"
            '{"accion": "abrir_aplicacion", "nombre_app": "<nombre_de_la_app>"}'
        )
    elif quiere_estado:
        instrucciones_finales += (
            "\n\nSi el usuario pide un diagnóstico, revisión o estado del sistema, responde ÚNICAMENTE "
            "con este JSON exacto (sin texto extra, sin markdown):\n"
            '{"accion": "obtener_estado_sistema"}'
        )

    mensajes_estructurados = [
        {'role': 'system', 'content': instrucciones_finales},
        {'role': 'user', 'content': contexto_historico}
    ]

    try:
        response = ollama.chat(model=MODELO_LOCAL, messages=mensajes_estructurados)
        contenido_bruto = response['message']['content']

        # MODIFICADO: Extraemos el JSON solo si el usuario pidió abrir o ver el estado.
        llamada_manual = _extraer_llamada_manual(contenido_bruto) if (quiere_abrir_algo or quiere_estado) else None

        if llamada_manual:
            accion = llamada_manual.get("accion")
            
            # --- RAMA 1: ABRIR APLICACIÓN ---
            if accion == "abrir_aplicacion":
                nombre_app = llamada_manual.get("nombre_app", "")
                print(f"\n⚙️ [L-IA Local ejecutando: 'abrir_aplicacion']")
                resultado_sistema = tools.abrir_aplicacion(nombre_app)
                print(f"✅ [Sistema: {resultado_sistema}]")

                mensajes_estructurados.append({'role': 'assistant', 'content': contenido_bruto})
                mensajes_estructurados.append({
                    'role': 'user',
                    'content': f'RESULTADO: {resultado_sistema}. Confirma brevemente con sarcasmo, sin JSON esta vez.'
                })
                
                respuesta_final = ollama.chat(model=MODELO_LOCAL, messages=mensajes_estructurados)
                texto_respuesta = respuesta_final['message']['content']
                
            # --- RAMA 2: DIAGNÓSTICO DEL SISTEMA ---
            elif accion == "obtener_estado_sistema":
                print(f"\n⚙️ [L-IA Local ejecutando: 'obtener_estado_sistema']")
                resultado_sistema = tools.obtener_estado_sistema()
                print(f"✅ [Sistema: Capturando métricas de hardware...]")

                # Le inyectamos los datos de la PC al modelo para que los comente
                mensajes_estructurados.append({'role': 'assistant', 'content': contenido_bruto})
                mensajes_estructurados.append({
                    'role': 'user',
                    'content': f'El sistema reporta esto: {resultado_sistema}. Dáselo al usuario con tu sarcasmo habitual, burlándote si consume mucho o poco. No uses JSON esta vez.'
                })
                
                respuesta_final = ollama.chat(model=MODELO_LOCAL, messages=mensajes_estructurados)
                texto_respuesta = respuesta_final['message']['content']
                
            else:
                # Si alucina otra acción
                texto_respuesta = contenido_bruto
                
        else:
            # Si no hubo llamada a herramienta, responde normal
            texto_respuesta = contenido_bruto

        return texto_respuesta

    except ollama.ResponseError as e:
        print(f"\n❌ Error en el cerebro local (Ollama): {e}")
        return None
    except Exception as e:
        print(f"\n❌ Error inesperado en el cerebro local: {e}")
        return None


# ==========================================
# 5. ENRUTADOR PRINCIPAL
# ==========================================
def charlar_con_lia(mensaje_usuario):
    database.guardar_mensaje("user", mensaje_usuario)

    instrucciones_sistema = prompt_builder.obtener_instrucciones_sistema()
    contexto_historico = prompt_builder.armar_historial_usuario(mensaje_usuario)

    usar_vision = any(p in mensaje_usuario.lower() for p in PALABRAS_CLAVE_VISION)

    if usar_vision:
        texto_respuesta = responder_con_nube(contexto_historico)
    else:
        # Evaluamos qué intenciones locales tiene el usuario
        quiere_abrir_algo = any(p in mensaje_usuario.lower() for p in PALABRAS_CLAVE_ABRIR)
        quiere_estado = any(p in mensaje_usuario.lower() for p in PALABRAS_CLAVE_ESTADO)
        
        # Pasamos ambas intenciones a la función local
        texto_respuesta = responder_con_local(instrucciones_sistema, contexto_historico, quiere_abrir_algo, quiere_estado)

    if texto_respuesta:
        database.guardar_mensaje("model", texto_respuesta)
        origen = "Nube" if usar_vision else "Local"
        print(f"\n🤖 L-IA ({origen}): {texto_respuesta}\n")


# ==========================================
# 6. BUCLE DE EJECUCIÓN
# ==========================================
if __name__ == "__main__":
    print("=========================================")
    print(" 🤖 SISTEMA L-IA HÍBRIDO EN LÍNEA ")
    print("=========================================\n")

    database.inicializar_base_datos()

    while True:
        mi_mensaje = input("TÚ: ")
        if mi_mensaje.lower() in ['salir', 'exit', 'apagar', 'quit']:
            print("\n🤖 L-IA: Suspendiendo procesos... nos vemos.")
            break
        if mi_mensaje.strip() != "":
            charlar_con_lia(mi_mensaje)