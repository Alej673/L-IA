import pygetwindow as gw

def obtener_ventana_activa(titulo_excluir="L-IA Asistente"):
    """
    Escanea las ventanas en orden Z ignorando overlays, basura de Windows
    y limpia sufijos de aplicaciones para aislar el nombre del archivo.
    """
    try:
        ventanas = gw.getAllWindows()

        ventanas_basura = [
            titulo_excluir,
            "QA OSD", "Program Manager", "NVIDIA GeForce Overlay", 
            "NVIDIA ShadowPlay Helper", "Windows Default Lock Screen", 
            "Taskbar", "Configuración", "Settings", 
            "Experiencia de entrada de Windows", "Windows Input Experience", 
            "Zoom", "Zoom Workplace"
        ]
        
        # Sufijos que las apps le pegan al nombre del archivo
        sufijos_app = [
            " - Word", " - Excel", " - PowerPoint", 
            " - Visual Studio Code", " - Notepad++", " - Bloc de notas",
            " - Google Chrome", " - Brave", " - Mozilla Firefox"
        ]

        for v in ventanas:
            titulo = v.title.strip()

            if titulo and v.visible and not v.isMinimized and not any(basura in titulo for basura in ventanas_basura):
                
                titulo_limpio = titulo
                # Limpiamos el ruido del programa
                for sufijo in sufijos_app:
                    if sufijo in titulo_limpio:
                        titulo_limpio = titulo_limpio.replace(sufijo, "")
                
                # Limpiamos etiquetas molestas de Office
                titulo_limpio = titulo_limpio.replace(" [Modo de compatibilidad]", "")
                titulo_limpio = titulo_limpio.strip()
                
                return titulo_limpio

        return "Escritorio / Desconocido"
    except Exception as e:
        return f"Error leyendo ventana: {e}"

def _bloque_contexto_ventana():
    """
    Fuente única de verdad para el bloque de contexto de entorno.
    Usado tanto por inyectar_contexto_implicito() (si app.py la llama
    antes de entrar a cerebro.py) como por cerebro.py::_procesar_entorno_automatico()
    directamente, para que la instrucción anti-alucinación de rutas
    nunca dependa de que alguien recuerde llamarla en dos sitios distintos.
    """
    ventana_actual = obtener_ventana_activa()
    return (
        f"\n\n[DATO DEL ENTORNO (Invisible para el usuario)]"
        f"\n- El usuario está viendo esta ventana en su monitor: '{ventana_actual}'\n"
        "- INSTRUCCIÓN CRÍTICA: Si el usuario te pide resumir, leer, analizar o refactorizar 'este archivo' "
        "o 'este documento', NO le pidas la ruta. Deduce el nombre del archivo a partir del título de la ventana "
        "actual. Inmediatamente ejecuta tu herramienta de lectura de archivos pasándole ÚNICAMENTE ese nombre "
        "para que el sistema lo busque automáticamente en el disco duro, lo lea y puedas darle la respuesta."
    )


def inyectar_contexto_implicito(mensaje_usuario):
    """Para quien construya el mensaje ANTES de entrar a cerebro.py (ej. app.py)."""
    return f"{mensaje_usuario}{_bloque_contexto_ventana()}"