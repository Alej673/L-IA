"""
Suite de pruebas rápidas de L-IA.

Cubre dos cosas independientes:

  1. Semáforo de intenciones (cerebro._detectar_intenciones) -- regex puras,
     no llama a Ollama ni a Gemini.
  2. Flujo Workspace Activo + Resumen técnico (database.py -> prompt_builder.py),
     Fase 7 -- usa una base de datos SQLite temporal y aislada, así que NO
     toca ni borra tu lia_memory.db real.

Uso:
    python test_lia.py                 # corre todo
    python test_lia.py intenciones     # solo la suite 1
    python test_lia.py workspace       # solo la suite 2

Requiere que cerebro.py, database.py y prompt_builder.py estén en el mismo
directorio (o en el PYTHONPATH), y que los imports externos de cerebro.py
(dotenv, google.genai, mss, PIL, ollama, etc.) estén instalados -- aunque no
se usen en este test, cerebro.py los importa al cargar el módulo.
"""

import os
import sys
import tempfile


# ============================================================
# SUITE 1: Semáforo de intenciones (cerebro.py)
# ============================================================

CASOS_INTENCIONES = [

    # --- Falsos positivos que el regex viejo/actualizado debe EVITAR ---
    ("Nos vemos en abril para el evento",                  {"abrir_app": False}),
    ("Hace frío, ponte un abrigo",                          {"abrir_app": False}),
    ("Te mando un abrazo grande",                           {"abrir_app": False}),
    ("Necesito comprar un cargador nuevo para el celular",  {"abrir_app": False}),
    ("Fuimos de excursión a la montaña",                    {"abrir_app": False}),
    ("Vi el montaje del evento en el salón",                {"abrir_app": False}),
    ("Hubo un levantamiento de protesta ayer",              {"abrir_app": False}),
    ("Vino a hacer una procesión religiosa",                {"estado_pc": False}),
    ("Tiene un temperamento explosivo",                     {"clima": False}),

    # --- Verdaderos positivos: abrir_app (con las conjugaciones nuevas) ---
    ("Abre Visual Studio Code",                             {"abrir_app": True}),
    ("Carga el proyecto de bastones",                       {"abrir_app": True}),
    ("Levanta el servidor local",                           {"abrir_app": True}),
    ("Monta la aplicación de Laravel",                      {"abrir_app": True}),
    ("Lanza el Unreal Engine",                              {"abrir_app": True}),

    # --- Verdaderos positivos: vision (con las conjugaciones nuevas) ---
    ("Mira mi pantalla y dime qué ves",                     {"vision": True}),
    ("Chequea la pantalla por mí",                          {"vision": True}),
    ("Escanea lo que tengo abierto ahorita",                {"vision": True}),
    ("Fíjate en lo que estoy viendo",                       {"vision": True}),

    # --- Verdaderos positivos: estado_pc ---
    ("¿Cómo está el estado de mi PC?",                      {"estado_pc": True}),
    ("Dame un diagnóstico de rendimiento",                  {"estado_pc": True}),
    ("¿Cuánta batería me queda?",                           {"estado_pc": True}),
    ("Revisa las especificaciones de mi equipo",            {"estado_pc": True}),

    # --- Verdaderos positivos: codigo (con conjugaciones nuevas) ---
    ("Audita este código por favor",                        {"codigo": True}),
    ("Mejora este código que te paso",                      {"codigo": True}),
    ("Prueba esta función a ver si compila",                {"codigo": True}),
    ("Refactoriza este archivo",                            {"codigo": True}),

    # --- Verdaderos positivos: web ---
    ("Investiga sobre frameworks de PHP en 2026",           {"web": True}),
    ("Indaga sobre el nuevo modelo de Gemini",               {"web": True}),
    ("Busca en internet quién ganó el mundial",              {"web": True}),

    # --- Verdaderos positivos: clima (con conjugaciones nuevas) ---
    ("¿Va a llover hoy en Pacto?",                          {"clima": True}),
    ("¿Está soleado en Quito ahorita?",                     {"clima": True}),
    ("Dame el pronóstico del clima para mañana",            {"clima": True}),

    # --- Colisión código vs web (código debe ganar y apagar web) ---
    ("Investiga por qué este $variable no funciona en PHP", {"codigo": True, "web": False}),

    # --- Git ---
    ("Revisa el estado de mi repositorio git",              {"git": True}),
    ("¿Qué cambios hay en el repo?",                        {"git": True}),
    ("Guarda los cambios y sube el commit",                 {"guardar_git": True}),

    # --- Workspace Fase 7 ---
    ("Estoy trabajando en el proyecto de bastones",         {"fijar_workspace": True}),
    ("Ya no estamos en ese archivo, olvídalo",              {"limpiar_workspace": True}),

    # --- Entorno activo ---
    ("¿Qué ventana tengo abierta ahora mismo?",             {"entorno_activo": True}),
    ("¿Qué programa estoy usando en la pantalla?",          {"entorno_activo": True}),

    # --- Guía de capacidades (Fase 8) ---
    ("¿Qué puedes hacer por mí?",                           {"guia_capacidades": True}),
    ("Estoy perdido, no sé qué pedirte",                    {"guia_capacidades": True}),
    ("¿Qué comandos tienes disponibles?",                   {"guia_capacidades": True}),
    # Debe seguir funcionando el pedido normal, sin disparar la guía:
    ("Ayúdame a refactorizar este archivo",                 {"guia_capacidades": False, "codigo": True}),

    # --- Uncensored ---
    ("Activa el modo sin censura, dolphin",                 {"uncensored": True}),

    # --- Hora / calendario ---
    ("¿Qué hora es?",                                       {"hora": True}),
    ("¿Qué tengo en mi agenda hoy?",                        {"calendario": True}),

    # --- Portapapeles ---
    ("Analiza lo que tengo copiado en el portapapeles",     {"portapapeles": True}),
]


def test_intenciones():
    """Corre CASOS_INTENCIONES contra cerebro._detectar_intenciones(). Devuelve (pasados, total, fallos)."""
    import cerebro

    total = len(CASOS_INTENCIONES)
    fallos = []

    for mensaje, esperado in CASOS_INTENCIONES:
        msg_lower = mensaje.lower()
        intenciones = cerebro._detectar_intenciones(msg_lower)

        # Replicamos los mismos filtros de colisión que hace charlar_con_lia,
        # porque algunos casos de prueba dependen de ellos (código vs web).
        if intenciones.get("codigo") or "{" in mensaje or "function " in msg_lower or "$" in mensaje:
            intenciones["web"] = False
        if intenciones.get("git"):
            intenciones["estado_pc"] = False

        for clave, valor_esperado in esperado.items():
            valor_real = intenciones.get(clave)
            if valor_real != valor_esperado:
                fallos.append(
                    f"❌ '{mensaje}'\n     -> {clave} esperado={valor_esperado} obtenido={valor_real}"
                )

    return total - len(fallos), total, fallos


# ============================================================
# SUITE 2: Workspace activo + Resumen técnico (database.py + prompt_builder.py)
# ============================================================
#
# Corre contra una copia temporal de la base de datos (no la real), para que
# puedas correr esto las veces que quieras sin ensuciar lia_memory.db.

def test_workspace():
    """
    Verifica el flujo completo de Fase 7:
      - establecer_workspace_activo() -> la ruta aparece en el prompt.
      - guardar_hecho('workspace_resumen', ...) -> el resumen aparece en el prompt
        (esta es la regresión del bug: antes se filtraba por categoría
        'contexto_fase7' y el resumen nunca llegaba al texto final).
      - el resumen NO se duplica fuera del bloque [ENTORNO DE TRABAJO...].
      - limpiar_workspace_activo() / limpiar_workspace_resumen() -> ambos
        desaparecen del prompt.
    Devuelve (pasados, total, fallos).
    """
    fallos = []
    checks_totales = 0

    # Base de datos aislada: apuntamos database.DB_NAME a un archivo temporal
    # ANTES de importar database, para no tocar la BD real del usuario.
    tmp_dir = tempfile.mkdtemp(prefix="lia_test_")
    tmp_db = os.path.join(tmp_dir, "lia_memory_test.db")

    # Import diferido para poder inyectar la ruta temporal.
    if "database" in sys.modules:
        del sys.modules["database"]
    if "prompt_builder" in sys.modules:
        del sys.modules["prompt_builder"]

    import database
    database.DB_NAME = tmp_db
    database.inicializar_base_datos()

    import prompt_builder

    def check(nombre, condicion):
        nonlocal checks_totales
        checks_totales += 1
        if not condicion:
            fallos.append(f"❌ [workspace] {nombre}")

    # --- Paso 1: fijar workspace activo, sin resumen todavía ---
    database.establecer_workspace_activo("C:\\ruta\\de\\prueba")
    texto = prompt_builder.obtener_instrucciones_sistema()

    check("la ruta activa aparece en el prompt",
          "C:\\ruta\\de\\prueba" in texto)
    check("sin resumen guardado, no aparece la etiqueta 'Resumen técnico en caché'",
          "Resumen técnico en caché" not in texto)

    # --- Paso 2: guardar el resumen técnico (categoría contexto_fase7) ---
    database.guardar_hecho("workspace_resumen", "Resumen de prueba XYZ", categoria="contexto_fase7")
    texto = prompt_builder.obtener_instrucciones_sistema()

    check("el resumen técnico aparece en el prompt (regresión del bug de filtrado)",
          "Resumen de prueba XYZ" in texto)
    check("la etiqueta 'Resumen técnico en caché' aparece exactamente una vez",
          texto.count("Resumen técnico en caché") == 1)
    check("el resumen NO se duplica fuera del bloque de Fase 7 "
          "(no debe aparecer también como línea suelta en DATOS APRENDIDOS DEL USUARIO)",
          texto.count("Resumen de prueba XYZ") == 1)

    # --- Paso 3: limpiar workspace activo y resumen ---
    database.limpiar_workspace_activo()
    database.limpiar_workspace_resumen()
    texto = prompt_builder.obtener_instrucciones_sistema()

    check("tras limpiar, ya no aparece la ruta vieja",
          "C:\\ruta\\de\\prueba" not in texto)
    check("tras limpiar, ya no aparece el resumen viejo",
          "Resumen de prueba XYZ" not in texto)
    check("tras limpiar, ya no aparece el bloque de Fase 7",
          "[ENTORNO DE TRABAJO Y ARCHIVO ACTIVO (FASE 7)]" not in texto)

    return checks_totales - len(fallos), checks_totales, fallos


# ============================================================
# RUNNER
# ============================================================

def _imprimir_resultado(nombre_suite, pasados, total, fallos):
    print(f"\n{'='*60}")
    print(f"{nombre_suite}: {pasados}/{total} casos correctos")
    print(f"{'='*60}")
    if fallos:
        print()
        for f in fallos:
            print(f)
    else:
        print("✅ Todos los casos pasaron.")
    print()


def main():
    suites_a_correr = sys.argv[1:] or ["intenciones", "workspace"]
    resultados = {}

    if "intenciones" in suites_a_correr:
        pasados, total, fallos = test_intenciones()
        _imprimir_resultado("SEMÁFORO DE INTENCIONES (cerebro.py)", pasados, total, fallos)
        resultados["intenciones"] = (pasados, total)

    if "workspace" in suites_a_correr:
        pasados, total, fallos = test_workspace()
        _imprimir_resultado("WORKSPACE + RESUMEN (database.py / prompt_builder.py)", pasados, total, fallos)
        resultados["workspace"] = (pasados, total)

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