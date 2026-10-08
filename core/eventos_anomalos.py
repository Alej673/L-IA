import time
import core.control_iot as control_iot
from guiones.colapso_fase1 import FASE_1 # Importas tu libreto
import os
import pygame


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

        # --- EVENTO DE PAUSA ---
        elif tipo == "pausa":
            time.sleep(accion.get("duracion", 1.0))

        # --- EVENTO DE EFECTOS DE SONIDO (SFX) ---
        elif tipo == "sfx":
            archivo_sfx = accion.get("archivo")
            
            if archivo_sfx == "generar_estatica":
                # Tu función matemática para ruido blanco
                archivo_temp = "temp_glitch_estatica.wav"
                
                # Asumo que crear_estatica está en tu módulo de voz o aquí mismo
                import core.voz as voz 
                voz.crear_estatica(archivo_temp, 0.4)
                
                try:
                    pygame.mixer.Sound(archivo_temp).play()
                except Exception as e:
                    print(f"⚠️ [SFX Error] No se pudo reproducir estática: {e}")
            else:
                # Buscar el audio en tu nueva carpeta exclusiva
                ruta_audio = os.path.join("sfx_colapso", archivo_sfx)
                
                if os.path.exists(ruta_audio):
                    try:
                        pygame.mixer.Sound(ruta_audio).play()
                    except Exception as e:
                        print(f"⚠️ [SFX Error] Fallo al reproducir {archivo_sfx}: {e}")
                else:
                    print(f"⚠️ [SFX Error] No se encontró el archivo: {ruta_audio}")

        # --- EVENTO DE DIÁLOGO (Voz + Interfaz) ---
        elif tipo == "dialogo":
            actor = accion.get("actor")
            texto = accion.get("texto")
            motor = accion.get("motor_voz", "kokoro")
            
            # 1. PREPARAR AUDIO PRIMERO (Kokoro piensa en silencio)
            archivo_audio = None
            if usar_voz:
                try:
                    archivo_audio = voz.preparar_voz(texto, motor=motor)
                except Exception as e:
                    print(f"Error preparando voz: {e}")

            # 2. AHORA SÍ, AVISAR A REACT (Cambia la cara y pone el texto al instante)
            if callback_ui:
                callback_ui(accion.get("json_ui"))

            # 3. REPRODUCIR INMEDIATAMENTE (Sincronización perfecta)
            if archivo_audio:
                voz.reproducir_voz(archivo_audio)
            else:
                time.sleep(len(texto) * 0.08)
                
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