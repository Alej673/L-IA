import os
import chromadb
from datetime import datetime

# 1. CLASE MEMORIA RAG REFACTORIZADA
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

    def indexar_documento(self, texto_completo, nombre_origen, grupo="general", tipo="documento", titulo_corto=""):
        chunks = self._fragmentar_texto(texto_completo)
        ids = []
        metadatos = []
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for i in range(len(chunks)):
            id_chunk = f"{nombre_origen.replace(' ', '_')}_chunk_{i}"
            ids.append(id_chunk)
            
            titulo_nodo = titulo_corto if titulo_corto else f"{nombre_origen} - Parte {i+1}"
            
            metadatos.append({
                "origen": nombre_origen,
                "grupo": grupo,
                "tipo": tipo,
                "titulo": titulo_nodo,
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

# 2. BLOQUE DE PRUEBA
if __name__ == "__main__":
    print("\n--- INICIANDO PRUEBA DE MEMORIA RAG ---\n")
    
    # Instanciamos usando una base de datos de prueba
    cerebro = MemoriaRAG("chroma_spike_db")

    # Inyectamos datos
    cerebro.indexar_documento(
        texto_completo="El sistema de armas modulares y locomoción en Unreal Engine 5 está desarrollado usando C++ y Blueprints. Utiliza EQS para lógica de cobertura.",
        nombre_origen="Log_UE5_Shooter",
        grupo="unreal_engine",
        tipo="codigo",
        titulo_corto="Mecánicas de Armas y EQS"
    )

    cerebro.indexar_documento(
        texto_completo="El interceptor del asistente en Python utiliza pygetwindow. El script control_iot.py controla la cerradura DIEL N191A y las luces Tuya.",
        nombre_origen="Modulo_Hardware_IoT",
        grupo="domotica",
        tipo="script",
        titulo_corto="Controladores Tuya y Cerradura"
    )

    # Probamos la recuperación
    consulta = "¿Qué herramientas usas para la lógica de los enemigos y físicas de disparos?"
    print(f"\n--- BUSCANDO CONCEPTO: '{consulta}' ---")

    resultados = cerebro.buscar_contexto(consulta, n_resultados=1)

    print("\n[RESULTADO ENCONTRADO]")
    if resultados['documents'] and resultados['documents'][0]:
        print(f"Texto: {resultados['documents'][0][0]}")
        print(f"Metadatos (Para el Grafo): {resultados['metadatas'][0][0]}")
        print(f"Distancia: {resultados['distances'][0][0]:.4f}")
    else:
        print("No se encontraron resultados.")