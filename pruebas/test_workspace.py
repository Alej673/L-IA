"""
Test de Caza-Fugas: Limpiador de Títulos y Rastreador de Extensiones
Evalúa si L-IA puede sobrevivir al ruido de Windows y encontrar archivos ocultos.
"""

import re
import difflib

# =================================================================
# 1. COPIA EXACTA DE LA LÓGICA DE LIMPIEZA (De tu contexto.py)
# =================================================================
def simular_limpieza_ventana(titulo_bruto):
    sufijos_app = [
        " - Word", " - Excel", " - PowerPoint", 
        " - Visual Studio Code", " - Notepad++", " - Bloc de notas",
        " - Google Chrome", " - Brave", " - Mozilla Firefox"
    ]
    titulo_limpio = titulo_bruto
    for sufijo in sufijos_app:
        if sufijo in titulo_limpio:
            titulo_limpio = titulo_limpio.replace(sufijo, "")
            
    titulo_limpio = titulo_limpio.replace(" [Modo de compatibilidad]", "")
    return titulo_limpio.strip()

# =================================================================
# 2. COPIA EXACTA DEL RASTREADOR (De tu cerebro.py)
# =================================================================
def simular_encontrar_ruta(mensaje_lower, rutas_conocidas):
    mensaje_limpio = re.sub(r'\b(mi|el|la|de|carpeta|proyecto|repositorio|repo|archivo|documento|doc)\b', '', mensaje_lower).strip()

    # 1. Alias exacto
    for alias, ruta in rutas_conocidas.items():
        if alias in mensaje_lower:
            return alias, ruta

    palabras = mensaje_limpio.split()
    
    # 2. Basename match
    for ruta in rutas_conocidas.values():
        nombre_archivo = ruta.split('\\')[-1].lower() # Simulamos os.path.basename
        nombre_sin_ext = nombre_archivo.rsplit('.', 1)[0]
        
        for palabra in palabras:
            if len(palabra) > 2 and (palabra == nombre_sin_ext or palabra == nombre_archivo):
                return nombre_archivo, ruta

    # 3. Fuzzy match
    for palabra in palabras:
        if len(palabra) < 3:
            continue
        coincidencias = difflib.get_close_matches(palabra, rutas_conocidas.keys(), n=1, cutoff=0.6)
        if coincidencias:
            return coincidencias[0], rutas_conocidas[coincidencias[0]]
            
    # 4. Adivinador de extensiones (Fuzzy Extensions)
    extensiones_comunes = ['.docx', '.php', '.cpp', '.h', '.js', '.css', '.html', '.pdf', '.txt']
    # Mock de archivos en el disco duro para la prueba
    archivos_falsos_en_disco = ['bdd.docx', 'ventascontroller.php', 'app.js'] 
    
    for palabra in palabras:
        if len(palabra) > 2:
            for ext in extensiones_comunes:
                posible_archivo = palabra + ext
                if posible_archivo in archivos_falsos_en_disco:
                    return posible_archivo, f"C:\\Simulacion\\{posible_archivo}"

    return None, None

# =================================================================
# 3. BATERÍA DE PRUEBAS
# =================================================================
def ejecutar_pruebas():
    print("="*70)
    print(" 🕵️ TEST DE LIMPIEZA DE ENTORNO Y RASTREO INTELIGENTE ")
    print("="*70)

    # --- PRUEBA 1: LIMPIEZA DE VENTANAS ---
    print("\n[FASE 1: LIMPIADOR DE TÍTULOS DE WINDOWS]")
    casos_ventanas = [
        ("BDD - Word", "BDD"),
        ("Qué es CRUD [Modo de compatibilidad] - Word", "Qué es CRUD"),
        ("VentasController.php - Visual Studio Code", "VentasController.php"),
        ("Buscando IA - Google Chrome", "Buscando IA")
    ]
    
    for bruto, esperado in casos_ventanas:
        resultado = simular_limpieza_ventana(bruto)
        if resultado == esperado:
            print(f"✅ EXCELENTE: '{bruto}' -> '{resultado}'")
        else:
            print(f"❌ FALLO: '{bruto}' -> Dio '{resultado}', se esperaba '{esperado}'")

    # --- PRUEBA 2: RASTREO INTELIGENTE DE RUTAS ---
    print("\n[FASE 2: RASTREADOR DE ARCHIVOS Y EXTENSIONES]")
    rutas_mock = {
        "taller": "C:\\Proyectos\\ERP_Taller",
        "crud_doc": "C:\\Documentos\\Qué es CRUD_2.docx",
        "ventas_ctrl": "C:\\Proyectos\\ERP_Taller\\VentasController.php"
    }

    casos_rutas = [
        ("revisa el archivo ventascontroller", "ventascontroller.php", "Basename Match ignorando la extensión"),
        ("abre el proyecto taller", "taller", "Detección de Alias Exacto"),
        ("resume el documento bdd", "bdd.docx", "Adivinador de Extensiones (.docx)"),
        ("analiza el archivo app", "app.js", "Adivinador de Extensiones (.js)")
    ]

    for mensaje, alias_esperado, tipo in casos_rutas:
        alias, ruta = simular_encontrar_ruta(mensaje, rutas_mock)
        if alias == alias_esperado:
            print(f"✅ EXCELENTE ({tipo}): '{mensaje}' -> Encontró '{alias}'")
        else:
            print(f"❌ FALLO ({tipo}): '{mensaje}' -> Encontró '{alias}', se esperaba '{alias_esperado}'")

    print("\n" + "="*70)
    print(" REPORTE FINALIZADO ")
    print("="*70)

if __name__ == "__main__":
    ejecutar_pruebas()