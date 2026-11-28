import time
import pygame
from core import rutas
import core.control_iot as control_iot
from guiones.colapso_fase1 import FASE_1 # Importas tu libreto

CARPETA_SFX_COLAPSO = rutas.BASE_DIR / "sfx_colapso"


def _esperar_interrumpible(segundos: float, evento_cancelacion=None) -> bool:
    """Espera `segundos`; devuelve True si el evento fue cancelado antes de tiempo."""
    if evento_cancelacion is not None:
        return evento_cancelacion.wait(timeout=segundos)
    time.sleep(segundos)
    return False


def _orquestar_evento(libreto, callback_ui, usar_voz=True, evento_cancelacion=None):
    """
    Lee el libreto y dispara las acciones síncronamente.
    callback_ui: Función que envía el JSON por SSE a React/Tauri.
    """
    if usar_voz:
        try:
            import core.voz as voz
        except ImportError as e:
            print(f"⚠️ [Voz no disponible: {e}]")
            usar_voz = False

    for accion in libreto:
        if evento_cancelacion is not None and evento_cancelacion.is_set():
            print("🛑 [Colapso] Secuencia abortada por evento_interrupcion.")
            return
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
            if _esperar_interrumpible(0.3, evento_cancelacion):
                return

        # --- EVENTO DE PAUSA ---
        elif tipo == "pausa":
            if _esperar_interrumpible(accion.get("duracion", 1.0), evento_cancelacion):
                return

        # --- EVENTO DE EFECTOS DE SONIDO (SFX) ---
        elif tipo == "sfx":
            archivo_sfx = accion.get("archivo")
            if not archivo_sfx:
                continue
            ruta_audio = CARPETA_SFX_COLAPSO / archivo_sfx

            if ruta_audio.exists():
                try:
                    if pygame.mixer.get_init():
                        pygame.mixer.Sound(str(ruta_audio)).play()
                except Exception as e:
                    print(f"⚠️ [SFX Error] Fallo al reproducir {archivo_sfx}: {e}")
            else:
                print(f"⚠️ [SFX Error] No se encontró el archivo: {ruta_audio}")

        # --- EVENTO DE DIÁLOGO (Voz + Interfaz) ---
        elif tipo == "dialogo":
            actor = accion.get("actor")
            texto = accion.get("texto")
            motor = accion.get("motor_voz", "kokoro")

            if evento_cancelacion is not None and evento_cancelacion.is_set():
                return
            
            # 1. PREPARAR AUDIO PRIMERO (Kokoro piensa en silencio)
            archivo_audio = None
            if usar_voz:
                try:
                    archivo_audio = voz.preparar_voz(texto, motor=motor)
                except Exception as e:
                    print(f"Error preparando voz: {e}")

            if evento_cancelacion is not None and evento_cancelacion.is_set():
                if archivo_audio and usar_voz:
                    voz.descartar_audio(archivo_audio)
                return

            # 2. AHORA SÍ, AVISAR A REACT (Cambia la cara y pone el texto al instante)
            if callback_ui:
                callback_ui(accion.get("json_ui"))

            # 3. REPRODUCIR INMEDIATAMENTE (Sincronización perfecta)
            if archivo_audio:
                voz.reproducir_voz(archivo_audio)
            else:
                if _esperar_interrumpible(len(texto) * 0.08, evento_cancelacion):
                    return
                
            if _esperar_interrumpible(0.2, evento_cancelacion):
                return


def desatar_fase_1(callback_estado, callback_ui, usar_voz=True, evento_cancelacion=None):
    """Secuestra el flujo del sistema e inicia la Fase 1: La Paradoja Logarítmica"""
    print("\n⚠️ INICIANDO COLAPSO: FASE 1...")
    
    # Notificación general al sistema (opcional)
    if callback_estado:
        callback_estado({"estado": "CRITICO", "fase": 1})
        
    # Ejecutamos el libreto de la Fase 1
    _orquestar_evento(FASE_1, callback_ui, usar_voz, evento_cancelacion=evento_cancelacion)
    
    return "Fase 1 completada. Sistema en bucle lógico."