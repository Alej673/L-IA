import sqlite3
import json
from datetime import datetime

# Nombre del archivo de base de datos local
DB_NAME = "lia_memory.db"


def obtener_conexion():
    """Establece una conexión con la base de datos SQLite."""
    conexion = sqlite3.connect(DB_NAME)
    conexion.row_factory = sqlite3.Row
    # Buena práctica: activar foreign keys por si en el futuro las usas
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def _ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ============================================================
# INICIALIZACIÓN
# ============================================================

def inicializar_base_datos():
    """Crea todas las tablas si no existen e inserta los datos base."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    # 1. Perfil de usuario (memoria estructurada de largo plazo)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS perfil_usuario (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        proyecto_actual TEXT,
        preferencias_musica TEXT,
        formato_respuesta TEXT,
        ultima_actualizacion TEXT
    )
    """)

    # 2. Historial de conversación (memoria de corto plazo)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historial_conversacion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        rol TEXT NOT NULL,          -- 'user' o 'model'
        mensaje TEXT NOT NULL,
        sesion_id TEXT              -- para agrupar conversaciones distintas en el futuro
    )
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_historial_timestamp
    ON historial_conversacion (timestamp)
    """)

    # 3. Self-state: identidad y límites de L-IA (singleton, id fijo = 1)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS self_state (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        nombre TEXT,
        proposito TEXT,
        arquitectura TEXT,
        creador TEXT,
        cpu TEXT,
        ram_total_gb INTEGER,
        vram_gpu_gb INTEGER,
        gpu_modelo TEXT,
        limite_procesamiento_local_kb INTEGER,
        accion_exceso_limite TEXT,
        restricciones_ejecucion TEXT,
        ultima_actualizacion TEXT
    )
    """)

    # 4. Herramientas disponibles (en vez de lista JSON plana)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS herramientas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE NOT NULL,
        descripcion TEXT,
        activa INTEGER NOT NULL DEFAULT 1,
        fecha_agregada TEXT
    )
    """)

    # 5. Memoria de hechos sueltos (clave-valor extensible, sin migrar esquema)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS memoria_hechos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        clave TEXT UNIQUE NOT NULL,
        valor TEXT,
        categoria TEXT,
        ultima_actualizacion TEXT
    )
    """)

    conexion.commit()

    # --- Seed data ---
    _seed_perfil(cursor)
    _seed_self_state(cursor)
    _seed_herramientas(cursor)

    conexion.commit()
    conexion.close()


def _seed_perfil(cursor):
    cursor.execute("SELECT COUNT(*) FROM perfil_usuario")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO perfil_usuario (nombre, proyecto_actual, preferencias_musica, formato_respuesta, ultima_actualizacion)
        VALUES (?, ?, ?, ?, ?)
        """, (
            "Alejandro",
            "Desarrollo de L-IA (asistente personal)",
            "Rock, música para concentrarse",
            "Directo, amigable, con un toque de humor y técnico",
            _ahora()
        ))
        print("Perfil inicial creado para Alejandro.")


def _seed_self_state(cursor):
    cursor.execute("SELECT COUNT(*) FROM self_state")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO self_state (
            id, nombre, proposito, arquitectura, creador,
            cpu, ram_total_gb, vram_gpu_gb, gpu_modelo,
            limite_procesamiento_local_kb, accion_exceso_limite, restricciones_ejecucion,
            ultima_actualizacion
        ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "L-IA",
            "Asistente Híbrido Local/Nube",
            "Sistema de enrutamiento de dos capas (Semáforo)",
            "Alejandro Larco",
            "Intel Core i5",
            16,
            6,
            "RTX 4050",
            35,
            "Delegar automáticamente a la nube (Gemini) para evitar desbordamiento de memoria", # <-- ¡EL CAMBIO!
            "No ejecutar comandos destructivos. Pasar siempre por el Tool Manager.",
            _ahora()
        ))
        print("Self-state inicial creado.")


def _seed_herramientas(cursor):
    cursor.execute("SELECT COUNT(*) FROM herramientas")
    if cursor.fetchone()[0] == 0:
        herramientas_base = [
            ("vision_pantalla", "Captura y analiza pantalla (mss + Gemini)"),
            ("abrir_aplicacion", "Abre apps locales (difflib + config_apps.json)"),
            ("diagnostico_hardware", "Diagnóstico de hardware (psutil)"),
            ("obtener_hora_actual", "Devuelve la hora actual"),
            ("obtener_clima", "Consulta el clima (Open-Meteo)"),
            ("obtener_eventos_calendario", "Consulta eventos (Google Calendar)"),
            ("leer_portapapeles", "Lee el contenido del portapapeles"),
            ("leer_archivos_ofimaticos_y_codigo", "Lee archivos de oficina y código"),
        ]
        cursor.executemany("""
            INSERT INTO herramientas (nombre, descripcion, activa, fecha_agregada)
            VALUES (?, ?, 1, ?)
        """, [(n, d, _ahora()) for n, d in herramientas_base])
        print("Herramientas base registradas.")


# ============================================================
# PERFIL DE USUARIO
# ============================================================

def obtener_perfil():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM perfil_usuario WHERE id = 1")
    perfil = cursor.fetchone()
    conexion.close()
    return dict(perfil) if perfil else None


def actualizar_proyecto(nuevo_proyecto):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("""
        UPDATE perfil_usuario SET proyecto_actual = ?, ultima_actualizacion = ? WHERE id = 1
    """, (nuevo_proyecto, _ahora()))
    conexion.commit()
    conexion.close()
    print(f"Proyecto actualizado a: '{nuevo_proyecto}'")


# ============================================================
# SELF-STATE (identidad y límites de L-IA)
# ============================================================

def obtener_self_state():
    """Devuelve el estado interno de L-IA como diccionario."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM self_state WHERE id = 1")
    estado = cursor.fetchone()
    conexion.close()
    return dict(estado) if estado else None


def actualizar_self_state(**campos):
    """
    Actualiza cualquier subconjunto de columnas de self_state.
    Ejemplo: actualizar_self_state(vram_gpu_gb=8, gpu_modelo="RTX 4070")
    """
    if not campos:
        return
    campos["ultima_actualizacion"] = _ahora()
    set_clause = ", ".join(f"{col} = ?" for col in campos)
    valores = list(campos.values())

    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute(f"UPDATE self_state SET {set_clause} WHERE id = 1", valores)
    conexion.commit()
    conexion.close()
    print(f"Self-state actualizado: {list(campos.keys())}")


# ============================================================
# HERRAMIENTAS
# ============================================================

def listar_herramientas(solo_activas=True):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    if solo_activas:
        cursor.execute("SELECT * FROM herramientas WHERE activa = 1 ORDER BY nombre")
    else:
        cursor.execute("SELECT * FROM herramientas ORDER BY nombre")
    filas = cursor.fetchall()
    conexion.close()
    return [dict(f) for f in filas]


def agregar_herramienta(nombre, descripcion=""):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute("""
            INSERT INTO herramientas (nombre, descripcion, activa, fecha_agregada)
            VALUES (?, ?, 1, ?)
        """, (nombre, descripcion, _ahora()))
        conexion.commit()
        print(f"Herramienta agregada: {nombre}")
    except sqlite3.IntegrityError:
        print(f"La herramienta '{nombre}' ya existe.")
    conexion.close()


def establecer_estado_herramienta(nombre, activa: bool):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("""
        UPDATE herramientas SET activa = ? WHERE nombre = ?
    """, (1 if activa else 0, nombre))
    conexion.commit()
    conexion.close()
    print(f"Herramienta '{nombre}' {'activada' if activa else 'desactivada'}.")


# ============================================================
# MEMORIA DE HECHOS (clave-valor extensible)
# ============================================================

def guardar_hecho(clave, valor, categoria=None):
    """Guarda o actualiza un dato suelto aprendido sobre el usuario."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("""
        INSERT INTO memoria_hechos (clave, valor, categoria, ultima_actualizacion)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(clave) DO UPDATE SET
            valor = excluded.valor,
            categoria = excluded.categoria,
            ultima_actualizacion = excluded.ultima_actualizacion
    """, (clave, valor, categoria, _ahora()))
    conexion.commit()
    conexion.close()


def obtener_hecho(clave):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT valor FROM memoria_hechos WHERE clave = ?", (clave,))
    fila = cursor.fetchone()
    conexion.close()
    return fila["valor"] if fila else None


def listar_hechos(categoria=None):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    if categoria:
        cursor.execute("SELECT * FROM memoria_hechos WHERE categoria = ?", (categoria,))
    else:
        cursor.execute("SELECT * FROM memoria_hechos")
    filas = cursor.fetchall()
    conexion.close()
    return [dict(f) for f in filas]

# ============================================================
# WORKSPACE / CONTEXTO ACTIVO (Fase 7) - CON DESPLAZAMIENTO (LRU CACHE)
# ============================================================

def establecer_workspace_activo(nueva_ruta):
    """
    Define el archivo actual en foco. Si ya había un archivo activo distinto, 
    lo empuja junto con su resumen a una 'mochila' (historial) de máximo 3 documentos 
    para no perder el contexto periférico.
    """
    ruta_actual = obtener_hecho("workspace_activo")
    resumen_actual = obtener_hecho("workspace_resumen")

    # Solo hacemos el desplazamiento si realmente estamos cambiando a un archivo NUEVO
    if ruta_actual and ruta_actual != nueva_ruta:
        historial_str = obtener_hecho("workspace_historial")
        historial = json.loads(historial_str) if historial_str else []

        # Quitamos la ruta actual si ya estaba en el historial para evitar duplicados
        historial = [item for item in historial if item.get('ruta') != ruta_actual]

        # Insertamos el archivo viejo al inicio de la mochila
        historial.insert(0, {
            "ruta": ruta_actual,
            "resumen": resumen_actual or "Sin resumen disponible."
        })

        # Mantenemos estrictamente solo los últimos 3 documentos (para cuidar la VRAM)
        historial = historial[:3]

        # Guardamos el nuevo historial desplazado
        guardar_hecho("workspace_historial", json.dumps(historial), categoria="contexto_fase7")
        
        # Como es un archivo totalmente nuevo, borramos el resumen viejo del FOCO PRINCIPAL 
        # para que no haya sangrado hasta que L-IA lo lea y genere uno nuevo.
        limpiar_workspace_resumen()

    # Finalmente, fijamos el nuevo rey del escritorio
    guardar_hecho("workspace_activo", nueva_ruta, categoria="contexto_fase7")
    print(f"[Fase 7] Workspace principal fijado a: {nueva_ruta}")


def obtener_workspace_activo():
    """Recupera el workspace activo actual."""
    return obtener_hecho("workspace_activo")


def obtener_workspace_historial():
    """Recupera la lista de documentos recientes en segundo plano."""
    historial_str = obtener_hecho("workspace_historial")
    return json.loads(historial_str) if historial_str else []


def limpiar_workspace_activo():
    """Borra el workspace activo y vacía la mochila de fondo."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM memoria_hechos WHERE clave IN ('workspace_activo', 'workspace_historial')")
    conexion.commit()
    conexion.close()
    print("[Fase 7] Escritorio y mochila limpiados. L-IA ya no tiene archivos en foco.")


def limpiar_workspace_resumen():
    """Borra el resumen técnico cacheado del workspace activo (Fase 7)."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM memoria_hechos WHERE clave = 'workspace_resumen'")
    conexion.commit()
    conexion.close()
    print("[Fase 7] Resumen del FOCO PRINCIPAL limpiado.")

# ============================================================
# HISTORIAL DE CONVERSACIÓN
# ============================================================

def guardar_mensaje(rol, mensaje, sesion_id=None):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("""
        INSERT INTO historial_conversacion (timestamp, rol, mensaje, sesion_id)
        VALUES (?, ?, ?, ?)
    """, (_ahora(), rol, mensaje, sesion_id))
    conexion.commit()
    conexion.close()


def obtener_historial_reciente(limite=10):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("""
        SELECT rol, mensaje FROM historial_conversacion
        ORDER BY id DESC LIMIT ?
    """, (limite,))
    mensajes = cursor.fetchall()
    conexion.close()
    return [dict(msg) for msg in reversed(mensajes)]


def borrar_historial():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM historial_conversacion")
    conexion.commit()
    conexion.close()
    print("Historial de chat reiniciado.")


# ============================================================
# CONTEXTO COMPLETO PARA EL PROMPT BUILDER
# ============================================================

def construir_contexto_ia(limite_historial=10):
    """
    Junta perfil, self-state, herramientas activas e historial reciente
    en un solo dict, listo para que prompt_builder.py arme el prompt del sistema.
    """
    hechos_generales = [
        h for h in listar_hechos(categoria=None)
        if h['clave'] != 'workspace_activo'
    ]

    return {
        "perfil": obtener_perfil(),
        "self_state": obtener_self_state(),
        "herramientas": listar_herramientas(solo_activas=True),
        "workspace_activo": obtener_workspace_activo(),
        "hechos": hechos_generales,
        "historial_reciente": obtener_historial_reciente(limite=limite_historial),
    }


if __name__ == "__main__":
    print("--- Base de datos L-IA (SQLite) ---")
    inicializar_base_datos()
    print("Base de datos inicializada y verificada correctamente.")