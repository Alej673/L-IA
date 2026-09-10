import chromadb
import os

# 1. Inicializar cliente persistente
# Esto crea una base de datos local en disco, igual que SQLite.
directorio_db = os.path.join(os.getcwd(), "chroma_spike_db")
cliente = chromadb.PersistentClient(path=directorio_db)

# 2. Crear la colección (equivalente a una tabla SQL)
coleccion = cliente.get_or_create_collection(name="pruebas_tecnicas")

# 3. Documentos de prueba simulando el "chunking" de tu documentación real
documentos = [
    "El sistema Kardex web automatiza los cálculos de inventario y cotizaciones utilizando PHP, Laravel y MySQL.",
    "La interfaz del módulo de inventario está construida con Bootstrap 5 y JavaScript para el sistema de bastones.",
    "El interceptor del asistente en Python utiliza pygetwindow para detectar la ventana activa y extraer su título.",
    "El sistema de armas modulares y locomoción en Unreal Engine 5 está desarrollado usando C++ y Blueprints."
]

# ChromaDB requiere un ID único por cada fragmento
ids = [f"doc_{i}" for i in range(len(documentos))]

print("Indexando documentos... (puede demorar unos segundos si descarga el modelo de CPU)")
coleccion.add(
    documents=documentos,
    ids=ids
)
print("¡Vectores indexados con éxito!\n")

# 4. Prueba de Recuperación Semántica (El "Segundo Cerebro")
# Ojo a la consulta: usamos palabras totalmente distintas a las del texto original.
consulta = "¿Qué tecnologías usaste para armar el frontend de las tablas y los reportes?"
print(f"Pregunta del usuario: '{consulta}'\n")

# 5. Ejecutar la búsqueda
resultados = coleccion.query(
    query_texts=[consulta],
    n_results=2 # Traer solo los 2 fragmentos más relevantes
)

# Mostrar resultados formateados
print("--- RESULTADOS DEVUELTOS POR CHROMADB ---")
for i in range(len(resultados['documents'][0])):
    texto = resultados['documents'][0][i]
    distancia = resultados['distances'][0][i] # Entre más cerca a 0, más similar es el concepto
    id_doc = resultados['ids'][0][i]
    
    print(f"\n[ID: {id_doc}] | Distancia: {distancia:.4f}")
    print(f"Texto recuperado: {texto}")