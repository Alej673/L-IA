import sys
import os
import time

# Forzamos a Python a reconocer la carpeta principal de L-IA
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from core.memoria_rag import MemoriaRAG
from core.database import registrar_documento_rag, listar_documentos_rag

# 1. Simulación de un documento real (Un controlador de Laravel para tu proyecto Arte Titi_Val)
codigo_laravel = """<?php
namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\MaterialesIgnorables;
use App\Models\Kardex;

class InventarioController extends Controller
{
    /**
     * Calcula el costo total basado en el Kardex.
     * Ignora los materiales configurados por el usuario.
     */
    public function calcularCosto(Request $request)
    {
        $ignorables = MaterialesIgnorables::pluck('nombre')->toArray();
        $items = Kardex::whereNotIn('material', $ignorables)->get();
        
        $total = 0;
        foreach($items as $item) {
            $total += $item->cantidad * $item->precio_unitario;
        }
        
        return response()->json(['total' => $total, 'moneda' => 'USD']);
    }

    /**
     * Genera el PDF del reporte de movimientos.
     * Requiere la librería DomPDF configurada.
     */
    public function exportarPDF()
    {
        $datos = Kardex::all();
        $pdf = \\PDF::loadView('reportes.kardex', compact('datos'));
        return $pdf->download('reporte_inventario.pdf');
    }
}
"""

print("\n--- 1. INICIANDO CEREBRO RAG ---")
print("Observa el Administrador de Tareas: ChromaDB descargará el modelo multilingüe (~120MB) si es la primera vez y usará solo CPU.")
t_inicio = time.perf_counter()
cerebro = MemoriaRAG()
print(f"✅ Cerebro cargado en {time.perf_counter() - t_inicio:.2f}s\n")

print("--- 2. PRUEBA DE FRAGMENTACIÓN INTELIGENTE ---")
# Probamos solo la fragmentación antes de guardar
chunks = cerebro._fragmentar_texto_inteligente(codigo_laravel, max_chars=400) # Forzamos un límite bajo para ver los cortes

for i, chunk in enumerate(chunks):
    print(f"\n[FRAGMENTO {i+1} | Tamaño: {len(chunk)} caracteres]")
    print(chunk)
    print("-" * 40)

print("\n--- 3. PRUEBA DE INGESTA Y RECUPERACIÓN ---")
doc_id = "doc_kardex_001"

# Indexamos en ChromaDB
cantidad = cerebro.indexar_documento(
    doc_id=doc_id,
    texto_completo=codigo_laravel,
    titulo="Controlador de Inventario Laravel",
    grupo="sistema bastones",
    tipo="codigo",
    origen="InventarioController.php"
)

# Simulamos guardar en SQLite (Fase 2)
registrar_documento_rag(doc_id, "Controlador de Inventario Laravel", "sistema bastones", "codigo", "C:/laragon/www/sistema-bastones/app/Http/Controllers/InventarioController.php", cantidad)

# Buscamos por concepto (no por nombre de variable)
consulta = "¿Cómo se genera el archivo descargable de los reportes?"
print(f"\nPregunta: '{consulta}'")
resultados = cerebro.buscar_contexto(consulta, n_resultados=1)

print(f"\nTexto Recuperado:\n{resultados['documents'][0][0]}")
print(f"Distancia Vectorial: {resultados['distances'][0][0]:.4f}")

print("\n--- 4. PRUEBA DE LIMPIEZA EN CASCADA ---")
cerebro.eliminar_vectores_por_doc(doc_id)
print("Prueba completada con éxito.")