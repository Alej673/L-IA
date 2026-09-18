import os
import chromadb

class MemoriaRAG:
    def __init__(self, db_path="lia_chroma_db"):
        # Crea la base de datos persistente en la carpeta del proyecto
        ruta_absoluta = os.path.join(os.getcwd(), db_path)
        self.cliente = chromadb.PersistentClient(path=ruta_absoluta)
        
        # Colección principal para tu documentación técnica
        self.coleccion = self.cliente.get_or_create_collection(name="documentos_tecnicos")

    def _fragmentar_texto(self, texto, tamaño_chunk=600, solapamiento=100):
        """
        Divide un texto largo en fragmentos más pequeños.
        El solapamiento evita que una idea se corte abruptamente a la mitad.
        """
        chunks = []
        inicio = 0
        while inicio < len(texto):
            fin = inicio + tamaño_chunk
            chunks.append(texto[inicio:fin])
            inicio += tamaño_chunk - solapamiento
        return chunks

    def indexar_documento(self, texto_completo, nombre_origen):
        """
        Fragmenta el texto e inyecta los metadatos (nombre del archivo).
        """
        chunks = self._fragmentar_texto(texto_completo)
        ids = []
        metadatos = []
        
        for i in range(len(chunks)):
            # Genera un ID único para cada párrafo
            id_chunk = f"{nombre_origen.replace(' ', '_')}_chunk_{i}"
            ids.append(id_chunk)
            
            # Guarda el nombre del archivo para que L-IA sepa la fuente
            metadatos.append({"origen": nombre_origen})
            
        print(f"Indexando {len(chunks)} fragmentos del archivo '{nombre_origen}'...")
        
        self.coleccion.add(
            documents=chunks,
            metadatas=metadatos,
            ids=ids
        )
        return len(chunks)

    def buscar_contexto(self, consulta, n_resultados=3):
        """
        Busca los párrafos más relevantes a la consulta.
        """
        resultados = self.coleccion.query(
            query_texts=[consulta],
            n_results=n_resultados
        )
        return resultados