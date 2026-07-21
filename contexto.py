import pygetwindow as gw
import pyautogui
import pyperclip
import time

def obtener_ventana_activa():
    """
    Detecta qué ventana está usando el usuario actualmente.
    Retorna el título de la ventana en texto.
    """
    try:
        ventana = gw.getActiveWindow()
        if ventana is not None:
            return ventana.title
        return "Escritorio / Desconocido"
    except Exception as e:
        return f"Error leyendo ventana: {e}"

def capturar_texto_resaltado():
    """
    Simula 'Ctrl + C' de forma invisible para atrapar el código o texto 
    que el usuario tiene sombreado en su editor.
    """
    # 1. Guardar lo que haya en el portapapeles actualmente para no borrarlo por accidente
    portapapeles_previo = pyperclip.paste()
    
    # 2. Limpiar el portapapeles para asegurarnos de capturar lo nuevo
    pyperclip.copy('') 
    
    # 3. Simular las teclas
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(0.1) # Pequeña pausa para que Windows reaccione
    
    # 4. Leer el texto nuevo
    texto_capturado = pyperclip.paste()
    
    # Si no se capturó nada (el usuario no tenía nada sombreado), restauramos lo anterior
    if not texto_capturado:
        pyperclip.copy(portapapeles_previo)
        return None
        
    return texto_capturado

def inyectar_contexto_implicito(mensaje_usuario):
    """
    Toma el mensaje del usuario y le inyecta información invisible sobre
    lo que está viendo y seleccionando en pantalla.
    """
    ventana_actual = obtener_ventana_activa()
    texto_seleccionado = capturar_texto_resaltado()
    
    contexto = f"\n\n[CONTEXTO DEL SISTEMA (Invisible para el usuario)]"
    contexto += f"\n- Ventana activa: {ventana_actual}"
    
    if texto_seleccionado:
        contexto += f"\n- Texto/Código resaltado en pantalla:\n```\n{texto_seleccionado}\n```"
    else:
        contexto += "\n- No hay texto resaltado."

    # Unimos el mensaje original con este contexto oculto
    return f"{mensaje_usuario} {contexto}"