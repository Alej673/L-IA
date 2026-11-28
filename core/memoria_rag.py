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

    def _fragmentar_texto_inteligente(self, texto, max_chars=config.CHUNK_SIZE, overlap=config.CHUNK_OVERLAP):
        """
        Divide el texto priorizando saltos lógicos (párrafos y líneas), troceando
        bloques o líneas largas con ventana deslizante y solapamiento (`overlap`),
        sin producir fragmentos vacíos.
        """
        if not texto or not texto.strip():
            return []

        max_chars = max(1, int(max_chars))
        overlap = max(0, min(int(overlap), max_chars // 2))

        def _trocear_con_solapamiento(bloque: str) -> list[str]:
            bloque = bloque.strip()
            if not bloque:
                return []
            if len(bloque) <= max_chars:
                return [bloque]
            partes = []
            paso = max(1, max_chars - overlap)
            inicio = 0
            n = len(bloque)
            while inicio < n:
                fin = min(n, inicio + max_chars)
                fragmento = bloque[inicio:fin].strip()
                if fragmento:
                    partes.append(fragmento)
                if fin >= n:
                    break
                inicio += paso
            return partes

        unidades = []
        for parrafo in re.split(r'\n\n+', texto.strip()):
            parrafo = parrafo.strip()
            if not parrafo:
                continue
            if len(parrafo) <= max_chars:
                unidades.append(parrafo)
            else:
                sub_chunk = ""
                for linea in parrafo.split('\n'):
                    if len(linea) > max_chars:
                        if sub_chunk.strip():
                            unidades.append(sub_chunk.strip())
                            sub_chunk = ""
                        unidades.extend(_trocear_con_solapamiento(linea))
                    elif not sub_chunk:
                        sub_chunk = linea
                    elif len(sub_chunk) + 1 + len(linea) <= max_chars:
                        sub_chunk += "\n" + linea
                    else:
                        if sub_chunk.strip():
                            unidades.append(sub_chunk.strip())
                        sub_chunk = linea
                if sub_chunk.strip():
                    unidades.append(sub_chunk.strip())

        chunks = []
        chunk_actual = ""
        for unidad in unidades:
            if not chunk_actual:
                chunk_actual = unidad
            elif len(chunk_actual) + 2 + len(unidad) <= max_chars:
                chunk_actual += "\n\n" + unidad
            else:
                chunks.append(chunk_actual)
                solape = chunk_actual[-overlap:].lstrip() if overlap > 0 else ""
                if (
                    solape
                    and not unidad.startswith(solape[: min(20, len(solape))])
                    and len(solape) + 2 + len(unidad) <= max_chars
                ):
                    chunk_actual = f"{solape}\n\n{unidad}"
                else:
                    chunk_actual = unidad

        if chunk_actual:
            chunks.append(chunk_actual)

        return [c for c in chunks if c]

    def indexar_documento(self, doc_id, texto_completo, titulo, grupo="general", tipo="documento", origen="archivo", chunks=None):
        chunks = chunks if chunks is not None else self._fragmentar_texto_inteligente(texto_completo)
        if not chunks:
            return 0
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