import os
import json
import tinytuya
import threading
import time

RUTA_DEVICES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "devices.json")

tira_nexxt = None
foco_sylvania = None

def inicializar_dispositivos():
    global tira_nexxt, foco_sylvania
    try:
        if not os.path.exists(RUTA_DEVICES):
            print(f"⚠️ [IoT] Archivo no encontrado: {RUTA_DEVICES}")
            return

        with open(RUTA_DEVICES, 'r', encoding='utf-8') as f:
            devices = json.load(f)
        
        for dev in devices:
            if dev.get('name') == 'Foco cuarto':
                foco_sylvania = tinytuya.Device(dev['id'], dev['ip'], dev['key'])
                foco_sylvania.set_version(3.4) # FOCO v3.4
                foco_sylvania.set_socketPersistent(True)
                
            elif dev.get('name') == 'Neon Light Strip':
                tira_nexxt = tinytuya.Device(dev['id'], dev['ip'], dev['key'])
                tira_nexxt.set_version(3.5) # LA PIEZA FALTANTE: Tira v3.5
                tira_nexxt.set_socketPersistent(True)
                
        print("✅ [IoT] Foco (v3.4) y Tira LED (v3.5) listos en Modo RAW.")
    except Exception as e:
        print(f"❌ [IoT] Error al cargar dispositivos: {e}")

inicializar_dispositivos()

def enviar_comando_raw(dispositivo, encender: bool, modo=None, color_hex=None, extra_dps=None):
    if not dispositivo:
        return
        
    payload = {'20': encender} 
    if modo:
        payload['21'] = modo   
    if color_hex and modo == 'colour':
        payload['24'] = color_hex 
    if extra_dps:
        payload.update(extra_dps) # Inyecta configuraciones adicionales como el brillo
        
    try:
        dispositivo.set_multiple_values(payload)
    except Exception as e:
        print(f"⚠️ [IoT Error] Fallo al enviar comando RAW: {e}")

def aplicar_escena(nombre_escena: str):
    def _cambiar_luces():
        try:
            if nombre_escena == "encendido":
                # Solo enciende, manteniendo el último color/modo guardado en la memoria del foco
                enviar_comando_raw(tira_nexxt, True)
                enviar_comando_raw(foco_sylvania, True)

            elif nombre_escena == "trabajo":
                # Tira a blanco simulado
                enviar_comando_raw(tira_nexxt, True, 'colour', '0000000003e8')
                # FOCO ARREGLADO: Forzamos el modo blanco y el DP 22 (Brillo al 1000) y DP 23 (Temperatura)
                enviar_comando_raw(foco_sylvania, True, 'white', extra_dps={'22': 1000, '23': 1000})
                
            elif nombre_escena == "gaming":
                enviar_comando_raw(tira_nexxt, True, 'colour', '010e03e803e8')
                enviar_comando_raw(foco_sylvania, True, 'colour', '00b403e803e8')
                
            elif nombre_escena == "descanso":
                enviar_comando_raw(foco_sylvania, False)
                enviar_comando_raw(tira_nexxt, True, 'colour', '001e03e800fa')
                
            elif nombre_escena == "apagado":
                enviar_comando_raw(tira_nexxt, False)
                enviar_comando_raw(foco_sylvania, False)
                
            elif nombre_escena == "corrupcion":
                for _ in range(4):
                    enviar_comando_raw(tira_nexxt, True, 'colour', '000003e803e8')
                    enviar_comando_raw(foco_sylvania, True, 'colour', '000003e803e8')
                    time.sleep(0.15)
                    enviar_comando_raw(tira_nexxt, False)
                    enviar_comando_raw(foco_sylvania, False)
                    time.sleep(0.15)
                enviar_comando_raw(tira_nexxt, True, 'colour', '000003e800c8')
                enviar_comando_raw(foco_sylvania, True, 'colour', '000003e800c8')
                
        except Exception as e:
            print(f"⚠️ [IoT Error] Fallo en la escena: {e}")

    threading.Thread(target=_cambiar_luces, daemon=True).start()