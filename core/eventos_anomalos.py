import time
import core.control_iot as control_iot
from guiones.colapso_fase1 import FASE_1 # Importas tu libreto

def _orquestar_evento(libreto, callback_ui, usar_voz=True):
    """
    Lee el libreto y dispara las acciones síncronamente.
    callback_ui: Función que envía el JSON por WebSocket a React/Tauri.
    """
    if usar_voz:
        try:
            import core.voz as voz
        except ImportError as e:
            print(f"⚠️ [Voz no disponible: {e}]")
            usar_voz = False

    for accion in libreto:
        tipo = accion.get("tipo")

        # --- EVENTO IOT ---
        if tipo == "iot":
            control_iot.aplicar_escena(accion.get("escena"))
            
        # --- EVENTO DE INTERFAZ (Glitches, cambios de actitud, consolas) ---
        elif tipo == "comando_ui":
            if callback_ui:
                # Enviamos el JSON puro que React espera leer
                callback_ui(accion.get("json"))
            # Breve pausa para que la animación fluya en frontend
            time.sleep(0.3)

        # --- EVENTO DE DIÁLOGO (Voz + Interfaz) ---
        elif tipo == "dialogo":
            actor = accion.get("actor")
            texto = accion.get("texto")
            motor = accion.get("motor_voz", "kokoro")
            
            # 1. Notificar a React para que pinte la línea y mueva la boca
            if callback_ui:
                callback_ui(accion.get("json_ui"))

            # 2. Generar y reproducir el audio
            if usar_voz:
                try:
                    archivo = voz.preparar_voz(texto, motor=motor)
                    if archivo:
                        # Asumiendo que esta función bloquea (espera a que termine el audio)
                        # Esto es perfecto porque sincroniza mágicamente la UI con la voz.
                        voz.reproducir_voz(archivo)
                except Exception as e:
                    print(f"Error reproduciendo voz de {actor}: {e}")
                    # Si falla la voz, hacemos un sleep simulado basado en el largo del texto
                    time.sleep(len(texto) * 0.08)
            else:
                # Si la voz está apagada, solo esperamos para que se lea el texto
                time.sleep(len(texto) * 0.08)
                
            # Micro-pausa natural entre diálogos
            time.sleep(0.2)


def desatar_fase_1(callback_estado, callback_ui, usar_voz=True):
    """Secuestra el flujo del sistema e inicia la Fase 1: La Paradoja Logarítmica"""
    print("\n⚠️ INICIANDO COLAPSO: FASE 1...")
    
    # Notificación general al sistema (opcional)
    if callback_estado:
        callback_estado({"estado": "CRITICO", "fase": 1})
        
    # Ejecutamos el libreto de la Fase 1
    _orquestar_evento(FASE_1, callback_ui, usar_voz)
    
    return "Fase 1 completada. Sistema en bucle lógico."