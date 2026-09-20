import pygetwindow as gw

# --- contexto.py ---

# Mapeo de sufijo de ventana -> extensión real del archivo.
# Antes solo se BORRABA el sufijo (" - Word" -> ""), perdiendo la
# información de qué tipo de archivo es. Ahora se REEMPLAZA por la
# extensión correspondiente, para que cerebro.py pueda deducir el
# nombre completo del archivo sin tener que adivinar por su cuenta
# con una lógica separada y desincronizada.
SUFIJOS_EXTENSION = {
    " - Word": ".docx",
    " - Excel": ".xlsx",
    " - PowerPoint": ".pptx",
    " - Bloc de notas": ".txt",
    " - Visual Studio Code": None,
    " - Notepad++": None,
    " - Google Chrome": None,
    " - Brave": None,
    " - Mozilla Firefox": None,
}


def obtener_ventana_activa(titulo_excluir="L-IA Asistente"):
    try:
        ventanas = gw.getAllWindows()

        # Lista 1: Coincidencia EXACTA (Si se llama exactamente así, se ignora)
        ventanas_basura_exactas = [
            "L-IA",  # <-- Ahora solo ignorará el HUD de Tauri
            titulo_excluir,
            "Program Manager",
            "Taskbar"
        ]

        # Lista 2: Coincidencia PARCIAL (Si contiene este texto, se ignora)
        ventanas_basura_parciales = [
            "QA OSD", "NVIDIA GeForce Overlay",
            "NVIDIA ShadowPlay Helper", "Windows Default Lock Screen",
            "Configuración", "Settings",
            "Experiencia de entrada de Windows", "Windows Input Experience",
            "Zoom", "Zoom Workplace",
            "Barra de herramientas de grabación",
            "Grabación de pantalla",
            "Herramienta Recortes",
            "Herramienta de Recortes",
            "Snipping Tool"
        ]

        for v in ventanas:
            titulo = v.title.strip()

            if titulo and v.visible and not v.isMinimized:
                
                # 1. Filtro Exacto
                if titulo in ventanas_basura_exactas:
                    continue
                
                # 2. Filtro Parcial
                if any(basura in titulo for basura in ventanas_basura_parciales):
                    continue

                # Si pasó ambos filtros, es la ventana válida (Ej: VS Code)
                titulo_limpio = titulo
                extension_inferida = None

                for sufijo, ext in SUFIJOS_EXTENSION.items():
                    if sufijo in titulo_limpio:
                        titulo_limpio = titulo_limpio.replace(sufijo, "")
                        extension_inferida = ext
                        break  # un solo sufijo de app por título

                titulo_limpio = titulo_limpio.replace(" [Modo de compatibilidad]", "")
                titulo_limpio = titulo_limpio.strip()

                # Agregar extensión si no la tiene
                if extension_inferida and not titulo_limpio.lower().endswith(extension_inferida):
                    titulo_limpio = f"{titulo_limpio}{extension_inferida}"

                return titulo_limpio

        return "Escritorio / Desconocido"
    except Exception as e:
        return f"Error leyendo ventana: {e}"

def _bloque_contexto_ventana():
    """
    Fuente única de verdad para el bloque de contexto de entorno.
    """
    ventana_actual = obtener_ventana_activa()
    return (
        f"\n\n[DATO DEL ENTORNO (Invisible para el usuario)]"
        f"\n- El usuario está viendo esta ventana en su monitor: '{ventana_actual}'\n"
        "- Este dato es solo informativo, para que sepas en qué contexto está trabajando el usuario.\n"
        "- IMPORTANTE: Tú NO tienes ninguna herramienta propia para leer archivos. Si el sistema logró "
        "leer el archivo relevante, su contenido ya aparece más abajo entre marcas "
        "<<<INICIO_CONTENIDO_EXTERNO>>> y <<<FIN_CONTENIDO_EXTERNO>>>. Si el usuario pide resumir, leer "
        "o analizar 'este archivo'/'este documento' y NO ves ese contenido en ningún lado del mensaje, "
        "NUNCA inventes una llamada a función, nunca escribas pseudo-código ni menciones nombres de "
        "herramientas internas: simplemente decile con tu personalidad que no lograste identificar o "
        "acceder al archivo, y pedile que te diga el nombre exacto."
    )

def inyectar_contexto_implicito(mensaje_usuario):
    """Para quien construya el mensaje ANTES de entrar a cerebro.py (ej. app.py)."""
    return f"{mensaje_usuario}{_bloque_contexto_ventana()}"