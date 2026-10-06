import os
import json
import tinytuya
import time

tinytuya.set_debug(False) # Apagamos el ruido para ver el resultado limpio

RUTA_DEVICES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "devices.json")

with open(RUTA_DEVICES, 'r', encoding='utf-8') as f:
    devices = json.load(f)
    
tira_data = next((d for d in devices if d.get('name') == 'Neon Light Strip'), None)

print(f"=== PRUEBA MULTIVERSIÓN: TIRA NEXXT ===")
print(f"IP: {tira_data['ip']}\n")

versiones = [3.1, 3.3, 3.4]

for v in versiones:
    print(f"--- PROBANDO VERSIÓN {v} ---")
    tira = tinytuya.Device(tira_data['id'], tira_data['ip'], tira_data['key'])
    tira.set_version(v)
    
    # Enviamos SOLO la orden de encendido (DPS 20) para descartar errores de formato de color
    payload = {'20': True}
    
    try:
        respuesta = tira.set_multiple_values(payload)
        print(f"Respuesta v{v}: {respuesta}\n")
    except Exception as e:
        print(f"Fallo en v{v}: {e}\n")
        
    time.sleep(2)