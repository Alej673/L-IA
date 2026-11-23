"""
gestor_memoria.py — El Orquestador del Segundo Cerebro.
Sincroniza las escrituras, lecturas y borrados entre ChromaDB (vectores) y SQLite (metadatos).
"""
import uuid
from core import database
from core import tools
from core import config

# Carga perezosa del motor vectorial para no bloquear el arranque general de L-IA
_rag_instancia = None

def _obtener_rag():
    global _rag_instancia
    if _rag_instancia is None:
        from core.memoria_rag import MemoriaRAG
        _rag_instancia = MemoriaRAG()
    return _rag_instancia

def asimilar_archivo(ruta_absoluta, grupo="general", tipo="documento"):
    """Lee un archivo, lo vectoriza en ChromaDB y registra la metadata en SQLite."""
    print(f"\n🧠 [Gestor] Iniciando asimilación de: {ruta_absoluta}")
    
    # 1. Lectura física del archivo
    datos = tools.leer_archivo_local(ruta_absoluta)
    if isinstance(datos, str) or "error" in datos:
        return f"❌ Error al leer el archivo: {datos}"

    contenido = datos.get("contenido", "")
    nombre_archivo = datos.get("nombre", "archivo_desconocido")
    doc_id = f"doc_{uuid.uuid4().hex[:8]}"

    # 2. Vectorización Matemática (ChromaDB)
    rag = _obtener_rag()
    try:
        total_chunks = rag.indexar_documento(
            doc_id=doc_id,
            texto_completo=contenido,
            titulo=nombre_archivo,
            grupo=grupo,
            tipo=tipo,
            origen=nombre_archivo
        )
    except Exception as e:
        return f"❌ Error vectorial al indexar en ChromaDB: {e}"

    # 3. Registro Administrativo (SQLite)
    database.registrar_documento_rag(
        doc_id=doc_id,
        titulo=nombre_archivo,
        grupo=grupo,
        tipo=tipo,
        ruta_archivo=ruta_absoluta,
        total_chunks=total_chunks
    )

    # NUEVO: Devolvemos un diccionario en lugar de un string
    return {
        "estado": "ok",
        "archivo": nombre_archivo,
        "chunks": total_chunks
    }

def consultar_memoria(consulta, n_resultados=config.MAX_RAG_RESULTS):
    """Busca en ChromaDB, filtra por distancia y actualiza estadísticas."""
    rag = _obtener_rag()
    resultados = rag.buscar_contexto(consulta, n_resultados=n_resultados)

    if not resultados or not resultados['documents'][0]:
        return None

    # FILTRO DE CORDURA VECTORIAL (Distancia L2)
    docs_validos = []
    metas_validas = []
    
    for i, distancia in enumerate(resultados['distances'][0]):
        print(f"📊 [RAG Debug] Fragmento {i} - Distancia matemática calculada: {distancia}")
        if distancia <= config.SIMILARITY_THRESHOLD:
            docs_validos.append(resultados['documents'][0][i])
            metas_validas.append(resultados['metadatas'][0][i])

    if not docs_validos:
        print(f"⚠️ [RAG] Fragmentos descartados por exceder el umbral de distancia ({config.SIMILARITY_THRESHOLD}).")
        return None

    # Registrar estadísticas SOLO de los fragmentos que sí sirvieron
    docs_consultados = set()
    for meta in metas_validas:
        if 'doc_id' in meta:
            docs_consultados.add(meta['doc_id'])

    for doc_id in docs_consultados:
        database.incrementar_uso_documento_rag(doc_id)

    # Reconstruimos el diccionario con la estructura exacta que espera cerebro.py
    return {
        'documents': [docs_validos],
        'metadatas': [metas_validas]
    }

def olvidar_documento(doc_id):
    """Elimina el rastro total del documento en ambas bases de datos simultáneamente."""
    # 1. Destrucción de vectores
    rag = _obtener_rag()
    rag.eliminar_vectores_por_doc(doc_id)

    # 2. Destrucción de metadatos
    conexion = database.obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM documentos_memoria WHERE doc_id = ?", (doc_id,))
    conexion.commit()
    conexion.close()

    print(f"🧹 [Gestor] Documento {doc_id} erradicado permanentemente de ambas memorias.")
    return True