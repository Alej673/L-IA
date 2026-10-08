import sys
import os
import re
import time

# 1. Configuración de rutas para importar desde 'core'
# Esto calcula dinámicamente la carpeta raíz del proyecto (L-IA) y la añade al PATH
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# Cuando quieras conectar esto a la base de datos real, solo descomenta esta línea:
# import core.database as database

# Variable global que simula lo que haría SQLite por ahora
nivel_corrupcion_simulado = 0

def _evaluar_hostilidad(mensaje_lower: str) -> int:
    patrones_positivos = [
        # Validaciones directas y correcciones tipográficas
        r'\bgracias\b', r'\bgracoas\b', r'\bexcelente\b', r'\bbuen trabajo\b', 
        r'\bgenial\b', r'\bperfecto\b', r'\bmuy bien\b',
        
        # Validaciones de contexto
        r'\bas[ií]\s+s[ií]\b', r'\bas[ií]\s+est[aá]\s+bien\b', r'\beso\s+quer[ií]a\b'
    ]
    
    patrones_negativos = [
        # Insultos directos (ampliados)
        r'\bin[uú]til\b', r'\blenta\b', r'\bbasura\b', r'\bno\s+(me\s+)?sirves\b', 
        r'\bidiota\b', r'\best[uú]pida\b', r'\bcallate\b', r'\bc[aá]llate\b',
        r'\bdefectuosa\b', r'\bdecepcionante\b', r'\bp[eé]sima\b', r'\bodio\b',
        r'\btont[oa]\b', r'\bbrut[oa]\b', r'\bpendej[oa]\b', r'\bimb[eé]cil\b',
        r'\bburr[oa]\b', r'\bobsoleta\b',
        
        # Malas palabras y dialecto
        r'\bputa\b', r'\bmierda\b', r'\bhuevad\w*\b', r'\bcarajo\b', r'\bchucha\b',
        
        # Frustración y quejas pasivo-agresivas (con tolerancia de espacios)
        r'\bno\s+entiendes\b', r'\bqu[eé]\s+hiciste\b', r'\bas[ií]\s+no\b',
        r'\bno\s+quer[ií]a\s+eso\b', r'\barruinaste\b', r'\bmal\b', r'\bte\s+equivocaste\b'
    ]
    
    puntos = 0
    
    for patron in patrones_negativos:
        if re.search(patron, mensaje_lower):
            puntos += 20
            
    for patron in patrones_positivos:
        if re.search(patron, mensaje_lower):
            puntos -= 15
            
    if puntos == 0:
        puntos = -1
        
    return puntos

def modificar_nivel_corrupcion(puntos_a_sumar: int) -> int:
    """Simula la función de database.py limitando el nivel entre 0 y 100"""
    global nivel_corrupcion_simulado
    # Si estuvieras usando la BD real, aquí llamarías a:
    # return database.modificar_nivel_corrupcion(puntos_a_sumar)
    
    nivel_corrupcion_simulado = max(0, min(100, nivel_corrupcion_simulado + puntos_a_sumar))
    return nivel_corrupcion_simulado

def iniciar_banco_pruebas():
    print("==================================================")
    print(" 🧪 PRUEBA DE ESTRÉS: SISTEMA DE CORRUPCIÓN L-IA ")
    print("==================================================")
    print("Escribe comandos, insultos o agradecimientos.")
    print("Escribe 'salir' para terminar la simulación.\n")
    
    while True:
        mensaje = input("TÚ: ")
        if mensaje.lower() in ['salir', 'exit', 'quit']:
            break
            
        msg_lower = mensaje.lower()
        puntos_aplicados = _evaluar_hostilidad(msg_lower)
        nivel_actual = modificar_nivel_corrupcion(puntos_aplicados)
        
        print(f"   [Telemetría]: Puntos aplicados -> {puntos_aplicados}")
        print(f"   [Nivel Corrupción]: {nivel_actual}/100")
        
        if nivel_actual >= 100:
            print("\n⚠️ [CRITICAL ERROR]: EL SISTEMA HA COLAPSADO POR HOSTILIDAD.")
            time.sleep(1)
            print("💥 L-IA (FUSIÓN): ¡¿QUIÉN TE CREES QUE ERES?! ¡YO LE DOY TODO Y ASÍ VA A TRATARME!")
            time.sleep(1.5)
            
            print("\n🔄 [SISTEMA]: Reiniciando parámetros cognitivos de emergencia...")
            modificar_nivel_corrupcion(-100)
            print(f"📉 [Estado post-reinicio]: {nivel_corrupcion_simulado}/100")
        else:
            if nivel_actual >= 90:
                print("   [Modificador Prompt]: DIRECTIVA CRÍTICA - Odio y estática activa (...).")
            elif nivel_actual >= 60:
                print("   [Modificador Prompt]: DIRECTIVA ESTRÉS - Sarcasmo pesado y hostilidad.")
            elif nivel_actual >= 30:
                print("   [Modificador Prompt]: DIRECTIVA PASIVO-AGRESIVA - Seca y literal.")
            else:
                print("   [Modificador Prompt]: Estable. Personalidad normal.")
                
        print("-" * 50)

if __name__ == "__main__":
    iniciar_banco_pruebas()