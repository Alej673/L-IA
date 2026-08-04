import os
import glob

# Detecta automáticamente el usuario y la ruta de Descargas
ruta_descargas = os.path.join(os.path.expanduser('~'), 'Downloads')
limite_peso_mb = 100 # Puedes ajustar el umbral aquí

print(f"Iniciando purga agresiva en: {ruta_descargas}")

archivos_borrados = 0
espacio_liberado = 0

for archivo in glob.glob(os.path.join(ruta_descargas, '*')):
    if os.path.isfile(archivo):
        tamano_mb = os.path.getsize(archivo) / (1024 * 1024)
        
        # Si supera el límite de peso, se elimina sin preguntar
        if tamano_mb > limite_peso_mb:
            try:
                os.remove(archivo) # Eliminación directa (bypass de la papelera)
                print(f"🗑️ Eliminado: {archivo} ({tamano_mb:.2f} MB)")
                archivos_borrados += 1
                espacio_liberado += tamano_mb
            except Exception as e:
                print(f"❌ Error de permisos al intentar borrar {archivo}: {e}")

print(f"\nResumen: {archivos_borrados} archivos eliminados.")
print(f"Espacio total liberado: {espacio_liberado:.2f} MB")