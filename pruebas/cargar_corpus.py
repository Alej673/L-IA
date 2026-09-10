import sys
import os

# 1. Agregar la raíz del proyecto al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from memoria_rag import MemoriaRAG
from tools import leer_archivo_local

ruta_archivo = r"C:\Users\ACER\Desktop\Documentos\Proyecto de IA\documentos\LIA_Documentacion_Unificada.docx"
nombre_doc = "LIA_Documentacion_Unificada.docx"

print(f"Leyendo el archivo: {nombre_doc}...")
resultado = leer_archivo_local(ruta_archivo)

# Extraer el texto si devuelve dict o string plano
texto_completo = ""
if isinstance(resultado, dict):
    # Claves comunes que suele devolver tools.py
    texto_completo = (
        resultado.get("contenido") 
        or resultado.get("texto") 
        or resultado.get("data") 
        or str(resultado)
    )
    # Si viene un mensaje de error dentro del dict
    if resultado.get("status") == "error" or resultado.get("error"):
        print(f"Error devuelto por tools.py: {resultado}")
        texto_completo = ""
elif isinstance(resultado, str):
    texto_completo = resultado

if texto_completo and not texto_completo.startswith("Error"):
    print("Lectura exitosa. Conectando con el Segundo Cerebro (ChromaDB)...")
    
    rag = MemoriaRAG()
    total_chunks = rag.indexar_documento(texto_completo=texto_completo, nombre_origen=nombre_doc)
    
    print(f"\n¡Operación completada! Se guardaron {total_chunks} fragmentos semánticos.")
else:
    print(f"No se pudo obtener el contenido del archivo. Respuesta: {resultado}")