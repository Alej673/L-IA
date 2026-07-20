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
PALABRAS_CLAVE_ESTADO = [
    "estado", "diagnostico", "ram", "cpu", "bateria", "sistema",
    "computadora", "pc", "procesos", "recursos", "programas", "consume", "consumiendo"
]
PALABRAS_CLAVE_PORTAPAPELES = ["portapapeles", "copiado", "copie", "copié", "resaltado", "acabo de copiar"]

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

# lectura de lia

def _extraer_ruta_archivo(mensaje):
    """
    Busca una ruta de archivo de Windows dentro del mensaje del usuario.
    Soporta rutas con o sin comillas.
    """
    # Intenta capturar rutas entre comillas (lo típico al arrastrar archivos)
    match_comillas = re.search(r'["\']([a-zA-Z]:\\[^"\']+\.\w+)["\']', mensaje)
    if match_comillas:
        return match_comillas.group(1)
        
    # Intenta capturar rutas directas sin comillas
    match_directo = re.search(r'([a-zA-Z]:\\[^\s]+\.\w+)', mensaje)
    if match_directo:
        return match_directo.group(1)
        
    return None

# ==========================================
# 3. RUTA A: LA NUBE (Gemini - Visión + Tools nativas)
# ==========================================
def responder_con_nube(instrucciones_sistema, contexto_historico, usar_vision):
    print("\n[☁️ Enrutando a la Nube (Gemini 3.5 Flash)...]")

    # La personalidad (system) y el historial (user) viajan juntos como
    # un solo bloque de texto, ya que generate_content no distingue roles
    # del mismo modo que la API de chat.
    texto_completo = f"{instrucciones_sistema}\n\n{contexto_historico}"
    contenidos_api = [texto_completo]

    # La captura de pantalla es costosa (tiempo + tokens): solo se toma si
    # el usuario activó vision explícitamente. Un portapapeles pesado, por
    # ejemplo, fuerza la nube por tamaño de texto, no porque quiera que
    # L-IA vea su monitor.
    if usar_vision:
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
# 4. RUTA B: CEREBRO LOCAL (gemma2 - tool calling manual en dos pasadas)
# ==========================================
def _extraer_llamada_manual(texto):
    """
    gemma2 no genera tool_calls nativos, así que buscamos un bloque JSON
    con la forma {"accion": "..."} dentro del texto de respuesta.
    """
    match = re.search(r'\{[^{}]*"accion"[^{}]*\}', texto, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _instrucciones_clasificador(quiere_abrir_algo, quiere_estado):
    """
    Construye un system prompt "sin alma": convierte a gemma2 en un
    clasificador de intenciones puro para forzar una salida JSON limpia,
    sin que la personalidad sarcástica contamine el formato.
    """
    instrucciones = (
        "Eres un clasificador de intenciones técnico y un generador de JSON estricto.\n"
        "Tu única tarea es analizar el [MENSAJE ACTUAL DEL USUARIO] y mapearlo a la acción correcta.\n"
        "NUNCA respondas con texto conversacional, saludos, explicaciones o markdown.\n"
        "NUNCA uses tu personalidad. Solo responde con el objeto JSON correspondiente."
    )
    if quiere_abrir_algo:
        instrucciones += (
            '\nFormato para abrir aplicaciones: {"accion": "abrir_aplicacion", "nombre_app": "<nombre_de_la_app>"}'
        )
    elif quiere_estado:
        instrucciones += (
            '\nFormato para diagnóstico de hardware y procesos: {"accion": "obtener_estado_sistema"}'
        )
    return instrucciones


def responder_con_local(instrucciones_sistema, contexto_historico, quiere_abrir_algo, quiere_estado):
    print(f"\n[🏠 Enrutando al Cerebro Local ({MODELO_LOCAL})...]")

    requiere_herramienta = quiere_abrir_algo or quiere_estado

    # Primera pasada: si hay intención de acción, usamos el "modo clasificador"
    # (sin personalidad) para asegurar un JSON limpio. Si es charla normal,
    # usamos la personalidad de L-IA desde el inicio.
    instrucciones_finales = (
        _instrucciones_clasificador(quiere_abrir_algo, quiere_estado)
        if requiere_herramienta else instrucciones_sistema
    )

    mensajes_estructurados = [
        {'role': 'system', 'content': instrucciones_finales},
        {'role': 'user', 'content': contexto_historico}
    ]

    try:
        response = ollama.chat(model=MODELO_LOCAL, messages=mensajes_estructurados)
        contenido_bruto = response['message']['content']

        llamada_manual = _extraer_llamada_manual(contenido_bruto) if requiere_herramienta else None

        if not llamada_manual:
            # Charla normal, o el clasificador no detectó ninguna acción real.
            return contenido_bruto

        # Segunda pasada: ya detectamos la herramienta, así que restauramos
        # el "alma" de L-IA para que la confirmación al usuario sí tenga
        # su tono sarcástico habitual.
        mensajes_estructurados[0]['content'] = instrucciones_sistema
        accion = llamada_manual.get("accion")

        if accion == "abrir_aplicacion":
            nombre_app = llamada_manual.get("nombre_app", "")
            print("\n⚙️ [L-IA Local ejecutando: 'abrir_aplicacion']")
            resultado_sistema = tools.abrir_aplicacion(nombre_app)
            print(f"✅ [Sistema: {resultado_sistema}]")

            mensajes_estructurados.append({'role': 'assistant', 'content': contenido_bruto})
            mensajes_estructurados.append({
                'role': 'user',
                'content': f'RESULTADO DEL SISTEMA: {resultado_sistema}. Confírmale al usuario que abriste '
                           'la aplicación usando tu estilo sarcástico habitual, sin usar JSON.'
            })

        elif accion == "obtener_estado_sistema":
            print("\n⚙️ [L-IA Local ejecutando: 'obtener_estado_sistema']")
            resultado_sistema = tools.obtener_estado_sistema()
            print("✅ [Sistema: Analizando sensores y procesos activos...]")

            mensajes_estructurados.append({'role': 'assistant', 'content': contenido_bruto})
            mensajes_estructurados.append({
                'role': 'user',
                'content': (
                    f'El sistema reporta estos datos reales de hardware y procesos: {resultado_sistema}.\n'
                    'Comunícale este diagnóstico real al usuario con tu personalidad ácida y sarcástica.\n'
                    'Búrlate de los programas específicos que estén consumiendo más recursos en su laptop Acer Nitro.\n'
                    'No respondas con JSON esta vez.'
                )
            })

        else:
            # El clasificador alucinó una acción que no reconocemos: no hay
            # nada que ejecutar, devolvemos el texto tal cual.
            return contenido_bruto

        respuesta_final = ollama.chat(model=MODELO_LOCAL, messages=mensajes_estructurados)
        return respuesta_final['message']['content']

    except ollama.ResponseError as e:
        print(f"\n❌ Error en el cerebro local (Ollama): {e}")
        return None
    except Exception as e:
        print(f"\n❌ Error inesperado en el cerebro local: {e}")
        return None


# ==========================================
# 5. HERRAMIENTA: PORTAPAPELES (El Semáforo Híbrido)
# ==========================================
def _procesar_portapapeles(contexto_historico):
    """
    Lee el portapapeles y decide si su peso amerita forzar la ruta de la
    nube. Devuelve el contexto (posiblemente enriquecido) y si se debe
    forzar la nube. La captura de pantalla NO se activa aquí — solo se
    activa por PALABRAS_CLAVE_VISION.
    """
    print("\n📋 [L-IA analizando el portapapeles...]")
    datos_portapapeles = tools.leer_portapapeles()
    forzar_nube = False

    if "error" in datos_portapapeles:
        print(f"❌ [Error del sistema: {datos_portapapeles['error']}]")
        contexto_historico += (
            "\n\n[NOTA DEL SISTEMA: El usuario intentó que leyeras el portapapeles, "
            "pero estaba vacío o hubo un error. Búrlate de él por no copiar nada.]"
        )
        return contexto_historico, forzar_nube

    contenido_copiado = datos_portapapeles["contenido"]
    es_pesado = datos_portapapeles["es_pesado"]
    peso_kb = datos_portapapeles["tamano_kb"]

    contexto_historico += f"\n\n[EL USUARIO HA COPIADO ESTE TEXTO EN SU PORTAPAPELES ({peso_kb} KB)]:\n{contenido_copiado}"

    if es_pesado:
        print(f"☁️ [Texto pesado detectado ({peso_kb} KB). Enrutando a Gemini para análisis profundo...]")
        forzar_nube = True
    else:
        print(f"🏠 [Texto ligero detectado ({peso_kb} KB). Enrutando a Gemma 2 local...]")

    return contexto_historico, forzar_nube

# ==========================================
# 5.5 HERRAMIENTA: LECTURA DE ARCHIVOS
# ==========================================
def _procesar_archivo(ruta, contexto_historico):
    """
    Lee el archivo local y decide si su peso amerita forzar la ruta de la nube.
    """
    print(f"\n📄 [L-IA intentando acceder al archivo en: {ruta}]")
    datos_archivo = tools.leer_archivo_local(ruta)
    forzar_nube = False

    if "error" in datos_archivo:
        print(f"❌ [Error del sistema: {datos_archivo['error']}]")
        contexto_historico += (
            f"\n\n[NOTA DEL SISTEMA: El usuario pidió que leyeras el archivo en '{ruta}', "
            f"pero falló con este error: {datos_archivo['error']}. Búrlate de su incapacidad para darte una ruta válida.]"
        )
        return contexto_historico, forzar_nube

    contenido = datos_archivo["contenido"]
    es_pesado = datos_archivo["es_pesado"]
    peso_kb = datos_archivo["tamano_kb"]
    nombre = datos_archivo["nombre"]

    contexto_historico += f"\n\n[EL USUARIO TE HA COMPARTIDO EL ARCHIVO '{nombre}' ({peso_kb} KB)]:\n{contenido}"

    if es_pesado:
        print(f"☁️ [Archivo pesado detectado ({peso_kb} KB). Enrutando a Gemini para análisis profundo...]")
        forzar_nube = True
    else:
        print(f"🏠 [Archivo ligero detectado ({peso_kb} KB). Enrutando a Gemma 2 local...]")

    return contexto_historico, forzar_nube


# ==========================================
# 6. ENRUTADOR PRINCIPAL
# ==========================================
def charlar_con_lia(mensaje_usuario):
    database.guardar_mensaje("user", mensaje_usuario)

    instrucciones_sistema = prompt_builder.obtener_instrucciones_sistema()
    contexto_historico = prompt_builder.armar_historial_usuario(mensaje_usuario)

    usar_vision = any(p in mensaje_usuario.lower() for p in PALABRAS_CLAVE_VISION)
    quiere_portapapeles = any(p in mensaje_usuario.lower() for p in PALABRAS_CLAVE_PORTAPAPELES)
    quiere_abrir_algo = any(p in mensaje_usuario.lower() for p in PALABRAS_CLAVE_ABRIR)
    quiere_estado = any(p in mensaje_usuario.lower() for p in PALABRAS_CLAVE_ESTADO)
    
    # NUEVO: Extraemos la ruta si existe en el mensaje
    ruta_detectada = _extraer_ruta_archivo(mensaje_usuario)

    forzar_nube = False

    # Intercepciones (Portapapeles o Archivos)
    if quiere_portapapeles:
        contexto_historico, forzar_nube = _procesar_portapapeles(contexto_historico)
    elif ruta_detectada:
        contexto_historico, forzar_nube = _procesar_archivo(ruta_detectada, contexto_historico)

    # Decisión final de enrutamiento
    if usar_vision or forzar_nube:
        texto_respuesta = responder_con_nube(instrucciones_sistema, contexto_historico, usar_vision)
    else:
        texto_respuesta = responder_con_local(instrucciones_sistema, contexto_historico, quiere_abrir_algo, quiere_estado)

    if texto_respuesta:
        database.guardar_mensaje("model", texto_respuesta)
        origen = "Nube" if (usar_vision or forzar_nube) else "Local"
        print(f"\n🤖 L-IA ({origen}): {texto_respuesta}\n")
        
        # NUEVO: Devolvemos los datos para que la interfaz gráfica pueda leerlos
        return texto_respuesta, origen
    
    return "Ocurrió un error en el razonamiento.", "Error"


# ==========================================
# 7. BUCLE DE EJECUCIÓN
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