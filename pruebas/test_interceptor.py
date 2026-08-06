"""
Test del Interceptor de Archivos (Fase 7.2)
Este script aísla la lógica de lectura de ventanas y búsqueda automática
para ver exactamente dónde se rompe la extracción antes de llegar a la IA.

Uso:
    python test_interceptor.py
"""

import re
import tools

def simular_interceptor(titulo_ventana_simulado):
    print(f"\n{'='*60}")
    print(f"🕵️ SIMULANDO VENTANA: '{titulo_ventana_simulado}'")
    print(f"{'='*60}")
    
    nombre_archivo = None
    
    # 1. Prueba de Regex
    match_archivo = re.search(r'([a-zA-Z0-9_\-\s]+\.(html|php|js|css|py|docx|pdf|txt|md))', titulo_ventana_simulado, re.IGNORECASE)
    
    if match_archivo:
        nombre_archivo = match_archivo.group(1).strip()
        print(f"✅ [Paso 1] Regex detectó extensión explícita: '{nombre_archivo}'")
    elif " - Word" in titulo_ventana_simulado:
        nombre_base = titulo_ventana_simulado.split(" - Word")[0].replace("*", "").strip()
        nombre_archivo = f"{nombre_base}.docx"
        print(f"✅ [Paso 1] Deducción de Word exitosa: '{nombre_archivo}'")
    else:
        print("❌ [Paso 1] No se pudo deducir ningún nombre de archivo.")
        return

    # 2. Prueba de tools.py
    print(f"🔍 [Paso 2] Llamando a tools.leer_archivo_local('{nombre_archivo}', busqueda_automatica=True)...")
    
    try:
        resultado = tools.leer_archivo_local(nombre_archivo)
        
        # 3. Análisis de la respuesta de tools.py
        print(f"📦 [Paso 3] Tipo de dato devuelto por tools: {type(resultado)}")
        
        if isinstance(resultado, dict):
            if "error" in resultado:
                print(f"❌ FALLO LOGICO: tools.py devolvió un diccionario con error: {resultado['error']}")
            elif "contenido" in resultado:
                texto_preview = resultado['contenido'][:100].replace('\n', ' ')
                print(f"✅ EXITO: tools.py devolvió contenido válido. Preview: '{texto_preview}...'")
            else:
                print(f"⚠️ EXTRAÑO: El diccionario no tiene 'error' ni 'contenido'. Claves: {resultado.keys()}")
        elif isinstance(resultado, str):
            print(f"❌ FALLO ESTRUCTURAL: tools.py devolvió un String puro en lugar de un diccionario.")
            print(f"Contenido del String:\n{resultado}")
        else:
            print(f"❌ FALLO DESCONOCIDO: tools.py devolvió algo inesperado: {resultado}")
            
    except Exception as e:
        print(f"💥 CRASH CRÍTICO en tools.py: {e}")

def main():
    # Casos de prueba que imitan lo que arroja Windows
    casos = [
        "inventario.html - Visual Studio Code",
        "FacturaVF.html - VS Code",
        "BItacora Avance 2 - Word",
        "BItacora Avance 2* - Word", # Simulando que el archivo no está guardado
        "Ventana de YouTube - Google Chrome" # No debería atrapar nada
    ]
    
    for caso in casos:
        simular_interceptor(caso)
        
    print(f"\n{'#'*60}")
    print("FIN DE LAS PRUEBAS")
    print(f"{'#'*60}\n")

if __name__ == "__main__":
    main()