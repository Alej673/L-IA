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
                enviar_comando_raw(tira_nexxt, True)
                enviar_comando_raw(foco_sylvania, True)

            elif nombre_escena == "trabajo":
                enviar_comando_raw(tira_nexxt, True, 'colour', '0000000003e8')
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
                
            # ---------------------------------------------------------
            # NUEVAS ESCENAS: FASE 1 DE COLAPSO
            # ---------------------------------------------------------
            elif nombre_escena == "blanco_frio_100":
                # 1. LOOP 3 VECES: Desplazamiento ULTRA FLUIDO
                for _ in range(3):
                    # Más pasos (de 100 en 100) para que sea un degradado suave
                    pasos_brillo = [200, 300, 400, 500, 650, 800, 900, 1000]
                    for brillo in pasos_brillo:
                        # Foco principal a blanco frío
                        enviar_comando_raw(foco_sylvania, True, 'white', extra_dps={'22': brillo, '23': 1000})
                        
                        # Tira LED a cian pálido
                        hex_brillo = f"{brillo:04x}" 
                        color_tira = f"00b400c8{hex_brillo}"
                        enviar_comando_raw(tira_nexxt, True, 'colour', color_tira)
                        
                        # Pausa rapidísima para engañar al ojo humano (fluidez)
                        time.sleep(0.06) 
                        
                    # Caída suave en dos tiempos en vez de un solo golpe brusco
                    enviar_comando_raw(foco_sylvania, True, 'white', extra_dps={'22': 500, '23': 1000})
                    enviar_comando_raw(tira_nexxt, True, 'colour', "00b400c801f4") # 500 en hex
                    time.sleep(0.08)
                    enviar_comando_raw(foco_sylvania, True, 'white', extra_dps={'22': 200, '23': 1000})
                    enviar_comando_raw(tira_nexxt, True, 'colour', "00b400c800c8") # 200 en hex
                    time.sleep(0.2)

                # --- 🛑 TRUCO DE ESTABILIZACIÓN ---
                # Le damos al foco 0.4 segundos para "respirar" y vaciar su memoria
                # Esto garantiza que NO ignore el comando de color que viene a continuación.
                time.sleep(0.4)

                # 2. ESTADO FINAL: Cambio drástico de color (Azul -> Rojo -> Blanco)
                
                # DESTELLO AZUL
                color_azul = "00f003e803e8" # Hue 240, Sat 1000, Val 1000
                enviar_comando_raw(foco_sylvania, True, 'colour', color_azul)
                enviar_comando_raw(tira_nexxt, True, 'colour', color_azul)
                time.sleep(0.8) # Lo dejamos casi un segundo para que impacte
                
                # DESTELLO ROJO
                color_rojo = "000003e803e8" # Hue 0, Sat 1000, Val 1000
                enviar_comando_raw(foco_sylvania, True, 'colour', color_rojo)
                enviar_comando_raw(tira_nexxt, True, 'colour', color_rojo)
                time.sleep(0.8) 
                
                # ESTABILIZACIÓN EN BLANCO FRÍO AL 100%
                enviar_comando_raw(foco_sylvania, True, 'white', extra_dps={'22': 1000, '23': 1000})
                enviar_comando_raw(tira_nexxt, True, 'colour', "00b400c803e8")
                    
            elif nombre_escena == "respiracion_ia":
                # Apagamos la tira LED para que todo el foco de atención quede en el foco de la habitación
                enviar_comando_raw(tira_nexxt, False)
                
                # Caída pesada al 10% (100)
                pasos_bajada = [1000, 700, 400, 200, 100]
                for b in pasos_bajada:
                    enviar_comando_raw(foco_sylvania, True, 'white', extra_dps={'22': b, '23': 1000})
                    time.sleep(0.15)
                    
                # El silencio absoluto ("Inhala...")
                time.sleep(0.8) 
                
                # Subida inestable al 37% (370)
                pasos_subida = [150, 220, 280, 330, 370]
                for b in pasos_subida:
                    enviar_comando_raw(foco_sylvania, True, 'white', extra_dps={'22': b, '23': 1000})
                    time.sleep(0.2)
                    
        except Exception as e:
            print(f"⚠️ [IoT Error] Fallo en la escena: {e}")

    # EL TRUCO MAESTRO: Esto evita que Python espere a que Tuya responda
    threading.Thread(target=_cambiar_luces, daemon=True).start()