"""
Test de prompts de L-IA -- dos fases independientes.

  FASE A ("texto"): construye distintos escenarios de base de datos y
  verifica que prompt_builder.obtener_instrucciones_sistema() arme el
  texto correctamente. NO llama a ninguna IA -- corre en segundos.

  FASE B ("real"): usa cerebro.charlar_con_lia() de punta a punta contra
  Ollama/Gemini reales, y verifica que la respuesta cumpla las reglas
  estrictas que el propio prompt le exige a L-IA (sin acotaciones
  actorales, sin prefijo de nombre, ruta de enrutamiento correcta).
  Gasta tokens/tiempo real y requiere Ollama corriendo (modelo 'gemma2'
  descargado) y GEMINI_API_KEY configurada.

Ambas fases usan una base de datos SQLite TEMPORAL (nunca tu lia_memory.db
real), así que puedes correrlas las veces que quieras sin miedo.

Uso:
    python test_prompts.py            # solo Fase A (por defecto, no gasta nada)
    python test_prompts.py texto      # solo Fase A
    python test_prompts.py real       # solo Fase B
    python test_prompts.py texto real # ambas
"""

import os
import re
import sys
import tempfile
import importlib


# ============================================================
# Utilidad común: BD temporal aislada
# ============================================================

def _bd_temporal():
    """Redirige database.DB_NAME a un archivo temporal ANTES de inicializar,
    y devuelve los módulos ya importados/recargados sobre esa BD limpia."""
    tmp_dir = tempfile.mkdtemp(prefix="lia_test_prompts_")
    tmp_db = os.path.join(tmp_dir, "lia_memory_test.db")

    for mod in ("database", "prompt_builder", "cerebro"):
        if mod in sys.modules:
            del sys.modules[mod]

    import database
    database.DB_NAME = tmp_db
    database.inicializar_base_datos()

    import prompt_builder
    return database, prompt_builder


# ============================================================
# FASE A: prompt_builder en distintos escenarios (sin IA)
# ============================================================

def test_prompt_texto():
    fallos = []
    checks_totales = 0

    def check(nombre, condicion):
        nonlocal checks_totales
        checks_totales += 1
        if not condicion:
            fallos.append(f"❌ [texto] {nombre}")

    database, prompt_builder = _bd_temporal()

    # --- Escenario 1: estado base (seed por defecto, sin hechos, sin workspace) ---
    texto = prompt_builder.obtener_instrucciones_sistema()

    check("aparece el nombre de la IA (self_state.nombre)",
          "L-IA" in texto)
    check("aparece la sección de SELF-STATE",
          "[TU ESTADO INTERNO Y ARQUITECTURA (SELF-STATE)]" in texto)
    check("aparece la sección de PERSONALIDAD",
          "[PERSONALIDAD Y TONO]" in texto)
    check("aparece la sección de REGLAS ESTRICTAS",
          "[REGLAS ESTRICTAS DE OPERACIÓN]" in texto)
    check("sin hechos guardados, NO aparece el bloque 'DATOS APRENDIDOS DEL USUARIO'",
          "[DATOS APRENDIDOS DEL USUARIO]" not in texto)
    check("sin workspace activo, NO aparece el bloque de Fase 7",
          "[ENTORNO DE TRABAJO Y ARCHIVO ACTIVO (FASE 7)]" not in texto)
    check("las herramientas activas del seed aparecen listadas",
          "vision_pantalla" in texto and "obtener_clima" in texto)

    # --- Escenario 2: todas las herramientas desactivadas ---
    for h in database.listar_herramientas(solo_activas=True):
        database.establecer_estado_herramienta(h["nombre"], activa=False)
    texto = prompt_builder.obtener_instrucciones_sistema()

    check("con 0 herramientas activas, el prompt no revienta y sigue trayendo el resto de secciones",
          "[TU ESTADO INTERNO Y ARQUITECTURA (SELF-STATE)]" in texto)
    check("con 0 herramientas activas, la lista de herramientas queda vacía entre corchetes",
          "[]" in texto)

    # Reactivamos para los siguientes escenarios
    for h in database.listar_herramientas(solo_activas=False):
        database.establecer_estado_herramienta(h["nombre"], activa=True)

    # --- Escenario 3: hechos generales (categoría normal, no fase7) ---
    database.guardar_hecho("comida_favorita", "encebollado", categoria="preferencias")
    database.guardar_hecho("horario_trabajo", "9am a 6pm", categoria="rutina")
    texto = prompt_builder.obtener_instrucciones_sistema()

    check("los hechos generales SÍ aparecen en 'DATOS APRENDIDOS DEL USUARIO'",
          "[DATOS APRENDIDOS DEL USUARIO]" in texto and "encebollado" in texto and "9am a 6pm" in texto)

    # --- Escenario 4: workspace activo + resumen con caracteres problemáticos ---
    # Backslashes, comillas y llaves -- para confirmar que no rompen el f-string
    # de prompt_builder ni se comen contenido al insertarse.
    ruta_rara = 'C:\\Proyectos\\"L-IA"\\módulo_ñ.py'
    resumen_raro = 'Usa dict {"clave": "valor"} y f-strings; cuidado con \\n literales.'
    database.establecer_workspace_activo(ruta_rara)
    database.guardar_hecho("workspace_resumen", resumen_raro, categoria="contexto_fase7")
    texto = prompt_builder.obtener_instrucciones_sistema()

    check("la ruta con comillas/backslashes/ñ aparece intacta",
          ruta_rara in texto)
    check("el resumen con llaves y backslashes aparece intacto (el f-string no lo rompe)",
          resumen_raro in texto)
    check("el bloque de Fase 7 aparece exactamente una vez",
          texto.count("[ENTORNO DE TRABAJO Y ARCHIVO ACTIVO (FASE 7)]") == 1)
    check("el resumen no se duplica fuera del bloque de Fase 7",
          texto.count(resumen_raro) == 1)

    # --- Escenario 5: proyecto_actual vacío/None no debe imprimir la palabra 'None' ---
    database.actualizar_proyecto("")
    texto = prompt_builder.obtener_instrucciones_sistema()
    check("proyecto_actual vacío no imprime literalmente 'None' en el prompt",
          "\nProyecto actual: None" not in texto)

    return checks_totales - len(fallos), checks_totales, fallos


# ============================================================
# FASE B: respuestas reales vía cerebro.charlar_con_lia()
# ============================================================

_REGEX_ASTERISCO_ACCION = re.compile(r'\*[^*\n]{2,80}\*')
_REGEX_CORCHETE_ACCION = re.compile(r'^\s*\[[^\]\n]{2,80}\]\s*$', re.MULTILINE)
_REGEX_PREFIJO_NOMBRE = re.compile(r'^\s*L-IA\s*:', re.IGNORECASE)


def _verificar_ollama():
    """Devuelve (ok: bool, motivo: str). Ollama es OBLIGATORIO para la Fase B:
    incluso los casos que enrutan a 'Nube' pasan primero por armar el prompt
    localmente, y varios casos de prueba enrutan directo a Local."""
    try:
        import ollama
        modelos = ollama.list()
        nombres = [m.get("model", m.get("name", "")) for m in modelos.get("models", [])]
        if not any("gemma2" in n for n in nombres):
            return False, (
                "Ollama está corriendo pero no encuentro el modelo 'gemma2' descargado. "
                "Corre: ollama pull gemma2"
            )
    except Exception as e:
        return False, f"No pude conectar con Ollama (¿está corriendo el servicio?): {e}"
    return True, ""


def _verificar_gemini():
    """Devuelve (ok: bool, motivo: str). Gemini es OPCIONAL: si no está disponible
    (sin API key, bloqueo regional, cupo agotado, etc.) simplemente se omiten
    los casos de prueba que necesitan ruta 'Nube', sin cancelar toda la Fase B."""
    if not os.getenv("GEMINI_API_KEY"):
        return False, "No hay GEMINI_API_KEY configurada en el entorno (.env)."
    return True, ""


def test_prompt_real():
    fallos = []
    checks_totales = 0
    saltados = []

    def check(nombre, condicion):
        nonlocal checks_totales
        checks_totales += 1
        if not condicion:
            fallos.append(f"❌ [real] {nombre}")

    ok_ollama, motivo_ollama = _verificar_ollama()
    if not ok_ollama:
        print(f"⏭️  [Fase real omitida por completo] {motivo_ollama}")
        return 0, 0, []

    ok_gemini, motivo_gemini = _verificar_gemini()
    if not ok_gemini:
        print(f"⚠️  [Casos de ruta 'Nube' se omitirán] {motivo_gemini}")

    database, prompt_builder = _bd_temporal()
    import cerebro

    # Casos representativos: cada uno debe enrutar a una ruta esperada
    # y la respuesta debe cumplir el formato exigido por el prompt.
    CASOS_REALES = [
        ("Hola, ¿cómo estás?", "Local"),
        ("Ábreme el bloc de notas", "Local"),
        ("¿Va a llover hoy en Quito?", "Nube"),
    ]

    for mensaje, ruta_esperada in CASOS_REALES:
        if ruta_esperada == "Nube" and not ok_gemini:
            print(f"⏭️  [Omitido] '{mensaje}' (requiere Gemini/Nube)")
            continue
        try:
            texto_respuesta, ruta_real = cerebro.charlar_con_lia(mensaje)
        except Exception as e:
            fallos.append(f"❌ [real] '{mensaje}' -> excepción al llamar a charlar_con_lia: {e}")
            checks_totales += 1
            continue

        check(f"'{mensaje}' -> enruta a '{ruta_esperada}' (obtuvo '{ruta_real}')",
              ruta_real == ruta_esperada)

        check(f"'{mensaje}' -> respuesta sin acotaciones tipo *acción*",
              not _REGEX_ASTERISCO_ACCION.search(texto_respuesta))

        check(f"'{mensaje}' -> respuesta sin acotaciones tipo [acción] en línea propia",
              not _REGEX_CORCHETE_ACCION.search(texto_respuesta))

        check(f"'{mensaje}' -> respuesta sin prefijo 'L-IA:'",
              not _REGEX_PREFIJO_NOMBRE.match(texto_respuesta))

        check(f"'{mensaje}' -> la respuesta no está vacía",
              bool(texto_respuesta and texto_respuesta.strip()))

    return checks_totales - len(fallos), checks_totales, fallos


# ============================================================
# RUNNER
# ============================================================

def _imprimir_resultado(nombre_suite, pasados, total, fallos):
    print(f"\n{'='*60}")
    if total == 0:
        print(f"{nombre_suite}: omitida")
    else:
        print(f"{nombre_suite}: {pasados}/{total} casos correctos")
    print(f"{'='*60}")
    if fallos:
        print()
        for f in fallos:
            print(f)
    elif total > 0:
        print("✅ Todos los casos pasaron.")
    print()


def main():
    suites_a_correr = sys.argv[1:] or ["texto"]
    resultados = {}

    if "texto" in suites_a_correr:
        pasados, total, fallos = test_prompt_texto()
        _imprimir_resultado("FASE A -- PROMPT_BUILDER (texto, sin IA)", pasados, total, fallos)
        resultados["texto"] = (pasados, total)

    if "real" in suites_a_correr:
        pasados, total, fallos = test_prompt_real()
        _imprimir_resultado("FASE B -- RESPUESTAS REALES (cerebro.charlar_con_lia)", pasados, total, fallos)
        resultados["real"] = (pasados, total)

    total_pasados = sum(p for p, _ in resultados.values())
    total_casos = sum(t for _, t in resultados.values())
    exito = total_pasados == total_casos

    print(f"{'#'*60}")
    print(f"TOTAL GENERAL: {total_pasados}/{total_casos}"
          f" {'✅' if exito else '❌'}")
    print(f"{'#'*60}\n")

    return exito


if __name__ == "__main__":
    exito = main()
    exit(0 if exito else 1)