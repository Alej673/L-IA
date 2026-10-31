import os
import chromadb
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

class MemoriaRAG:
    def __init__(self, db_path="lia_chroma_db"):
        os.makedirs(DATA_DIR, exist_ok=True)
        ruta_absoluta = os.path.join(DATA_DIR, db_path)
        self.cliente = chromadb.PersistentClient(path=ruta_absoluta)
        self.coleccion = self.cliente.get_or_create_collection(name="documentos_tecnicos")

    def _fragmentar_texto(self, texto, tamaño_chunk=600, solapamiento=100):
        chunks = []
        inicio = 0
        while inicio < len(texto):
            fin = inicio + tamaño_chunk
            chunks.append(texto[inicio:fin])
            inicio += tamaño_chunk - solapamiento
        return chunks

    # 1. REFACTORIZACIÓN: Añadimos parámetros para el grafo visual
    def indexar_documento(self, texto_completo, nombre_origen, grupo="general", tipo="documento", titulo_corto=""):
        chunks = self._fragmentar_texto(texto_completo)
        ids = []
        metadatos = []
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for i in range(len(chunks)):
            id_chunk = f"{nombre_origen.replace(' ', '_')}_chunk_{i}"
            ids.append(id_chunk)
            
            # Generamos un título legible para el nodo si no se provee uno
            titulo_nodo = titulo_corto if titulo_corto else f"{nombre_origen} - Parte {i+1}"
            
            # 2. METADATOS ENRIQUECIDOS: Esto alimenta los colores y filtros en React
            metadatos.append({
                "origen": nombre_origen,
                "grupo": grupo,         # Ej: "iot", "unreal", "personal" (Color del nodo)
                "tipo": tipo,           # Ej: "script", "pdf", "charla" (Icono o forma)
                "titulo": titulo_nodo,  # Etiqueta visible al pasar el mouse
                "fecha": fecha_actual
            })
            
        print(f"Indexando {len(chunks)} fragmentos del archivo '{nombre_origen}' (Grupo: {grupo})...")
        
        self.coleccion.add(
            documents=chunks,
            metadatas=metadatos,
            ids=ids
        )
        return len(chunks)

    def buscar_contexto(self, consulta, n_resultados=3):
        return self.coleccion.query(
            query_texts=[consulta],
            n_results=n_resultados
        )

    # 3. NUEVO MÉTODO: El puente para la interfaz de React/Three.js
    def obtener_todo_para_grafo(self):
        """
        Extrae toda la colección (textos, metadatos y vectores).
        FastAPI usará esto para calcular las líneas de conexión (links) del mapa visual.
        """
        return self.coleccion.get(include=['embeddings', 'documents', 'metadatas'])