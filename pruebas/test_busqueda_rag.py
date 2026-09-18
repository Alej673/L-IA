import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.memoria_rag import MemoriaRAG

rag = MemoriaRAG()

# Pregunta sobre un problema documentado en tu bitácora
consulta = "¿Qué ocurrió con el incidente de las descargas y cómo se solucionó?"
print(f"Consulta: {consulta}\n")

resultados = rag.buscar_contexto(consulta, n_resultados=2)

for i in range(len(resultados['documents'][0])):
    doc = resultados['documents'][0][i]
    meta = resultados['metadatas'][0][i]
    distancia = resultados['distances'][0][i] if 'distances' in resultados else 'N/A'
    
    print(f"--- Fragmento {i+1} [Origen: {meta.get('origen')}] ---")
    print(f"Distancia: {distancia}")
    print(f"Contenido:\n{doc.strip()}\n")