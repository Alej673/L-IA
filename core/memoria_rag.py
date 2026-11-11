"""
memoria_rag.py — Segundo Cerebro Vectorial de L-IA (ChromaDB)
Solo administra textos crudos y vectores matemáticos. Operado al 100% en CPU.
"""
import os
import re
from datetime import datetime
import chromadb
from chromadb.utils import embedding_functions

from core import config
from core import rutas

class MemoriaRAG:
    def __init__(self):
        # 1. Configurar ruta de ChromaDB usando la fuente centralizada
        ruta_absoluta = str(rutas.CHROMA_DB_PATH)
        self.cliente = chromadb.PersistentClient(path=ruta_absoluta)
        
        # 2. Forzar Embeddings en CPU (Protección estricta de VRAM para Gemma 2)
        print(f"🧠 [ChromaDB] Cargando modelo de embeddings en CPU ({config.EMBEDDING_MODEL})...")
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=config.EMBEDDING_MODEL,
            device="cpu" 
        )
        
        # 3. Conectar a la colección principal
        self.coleccion = self.cliente.get_or_create_collection(
            name=config.CHROMA_COLLECTION_NAME,
            embedding_function=self.embedding_fn
        )

    def _fragmentar_texto_inteligente(self, texto, max_chars=config.CHUNK_SIZE):
        """
        Divide el texto priorizando saltos lógicos (párrafos dobles y líneas).
        Evita cortar funciones de código o ideas a la mitad.
        """
        parrafos = re.split(r'\n\n+', texto)
        chunks = []
        chunk_actual = ""

        for parrafo in parrafos:
            if len(chunk_actual) + len(parrafo) < max_chars:
                chunk_actual += parrafo + "\n\n"
            else:
                if chunk_actual:
                    chunks.append(chunk_actual.strip())
                
                # Si un solo bloque de código/texto es más grande que el máximo permitido
                if len(parrafo) > max_chars:
                    lineas = parrafo.split('\n')
                    sub_chunk = ""
                    for linea in lineas:
                        if len(sub_chunk) + len(linea) < max_chars:
                            sub_chunk += linea + "\n"
                        else:
                            chunks.append(sub_chunk.strip())
                            sub_chunk = linea + "\n"
                    chunk_actual = sub_chunk + "\n\n"
                else:
                    chunk_actual = parrafo + "\n\n"
        
        if chunk_actual:
            chunks.append(chunk_actual.strip())
            
        return chunks

    def indexar_documento(self, doc_id, texto_completo, titulo, grupo="general", tipo="documento", origen="archivo"):
        chunks = self._fragmentar_texto_inteligente(texto_completo)
        ids = []
        metadatos = []
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for i in range(len(chunks)):
            id_chunk = f"{doc_id}_chunk_{i}"
            ids.append(id_chunk)
            
            titulo_nodo = f"{titulo} - Parte {i+1}"
            
            # Estos metadatos alimentarán los colores y filtros del frontend 3D
            metadatos.append({
                "doc_id": doc_id,
                "origen": origen,
                "grupo": grupo,
                "tipo": tipo,
                "titulo": titulo_nodo,
                "fecha": fecha_actual
            })
            
        print(f"📦 [RAG] Indexando {len(chunks)} fragmentos para '{titulo}' (Grupo: {grupo})...")
        
        self.coleccion.add(
            documents=chunks,
            metadatas=metadatos,
            ids=ids
        )
        return len(chunks)

    def buscar_contexto(self, consulta, n_resultados=config.MAX_RAG_RESULTS):
        """Busca los conceptos similares en el espacio vectorial."""
        return self.coleccion.query(
            query_texts=[consulta],
            n_results=n_resultados
        )

    def eliminar_vectores_por_doc(self, doc_id):
        """Elimina en cascada todos los fragmentos que pertenezcan a un documento."""
        self.coleccion.delete(where={"doc_id": doc_id})
        print(f"🗑️ [ChromaDB] Memoria vectorial eliminada para ID: {doc_id}")

    def obtener_todo_para_grafo(self):
        """Puente API: Extrae los nodos y tensores matemáticos para renderizar en Three.js"""
        return self.coleccion.get(include=['embeddings', 'documents', 'metadatas'])