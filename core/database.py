import sqlite3
import json
import os
import uuid
from datetime import datetime

# 1. Calculamos la ruta absoluta de la carpeta raíz del proyecto (L-IA)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 2. Obligamos a que la base de datos viva SIEMPRE dentro de la carpeta "data"
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True) 

# 3. Ruta absoluta e inamovible de la base de datos
DB_NAME = os.path.join(DATA_DIR, "lia_memory.db")

def obtener_conexion():
    """Establece una conexión con la base de datos SQLite."""
    conexion = sqlite3.connect(DB_NAME)
    conexion.row_factory = sqlite3.Row
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

    # 1. Perfil de usuario
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

    # 2. Sesiones de Chat (NUEVO: Compartimentación del contexto)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sesiones_chat (
        id TEXT PRIMARY KEY,
        titulo TEXT,
        workspace_activo TEXT,
        workspace_resumen TEXT,
        workspace_historial TEXT,
        fecha_creacion TEXT,
        ultima_actualizacion TEXT
    )
    """)

    # 3. Historial de conversación (Vinculado a la sesión)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historial_conversacion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        rol TEXT NOT NULL,
        mensaje TEXT NOT NULL,
        sesion_id TEXT NOT NULL,
        FOREIGN KEY(sesion_id) REFERENCES sesiones_chat(id) ON DELETE CASCADE
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_historial_timestamp ON historial_conversacion (timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_historial_sesion ON historial_conversacion (sesion_id)")

    # 4. Self-state
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

    # 5. Herramientas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS herramientas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE NOT NULL,
        descripcion TEXT,
        activa INTEGER NOT NULL DEFAULT 1,
        fecha_agregada TEXT
    )
    """)

    # 6. Memoria de hechos sueltos
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
    _seed_sesiones(cursor)
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

def _seed_sesiones(cursor):
    """Garantiza que siempre exista una sesión por defecto al arrancar."""
    cursor.execute("SELECT COUNT(*) FROM sesiones_chat WHERE id = 'default'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO sesiones_chat (id, titulo, fecha_creacion, ultima_actualizacion)
        VALUES (?, ?, ?, ?)
        """, ("default", "Chat Principal", _ahora(), _ahora()))

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
            "Delegar automáticamente a la nube (Gemini) para evitar desbordamiento de memoria",
            "No ejecutar comandos destructivos. Pasar siempre por el Tool Manager.",
            _ahora()
        ))

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

# ============================================================
# GESTIÓN DE SESIONES DE CHAT
# ============================================================

def crear_sesion(titulo="Nueva Conversación"):
    """Crea un nuevo hilo de conversación aislado."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    sesion_id = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO sesiones_chat (id, titulo, fecha_creacion, ultima_actualizacion)
        VALUES (?, ?, ?, ?)
    """, (sesion_id, titulo, _ahora(), _ahora()))
    conexion.commit()
    conexion.close()
    return sesion_id

def listar_sesiones():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT id, titulo, workspace_activo, fecha_creacion FROM sesiones_chat ORDER BY ultima_actualizacion DESC")
    filas = cursor.fetchall()
    conexion.close()
    return [dict(f) for f in filas]

def actualizar_titulo_sesion(sesion_id, nuevo_titulo):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("UPDATE sesiones_chat SET titulo = ?, ultima_actualizacion = ? WHERE id = ?", 
                   (nuevo_titulo, _ahora(), sesion_id))
    conexion.commit()
    conexion.close()

# ============================================================
# WORKSPACE / CONTEXTO ACTIVO - AISLADO POR SESIÓN
# ============================================================

def establecer_workspace_activo(nueva_ruta, sesion_id="default"):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    cursor.execute("SELECT workspace_activo, workspace_resumen, workspace_historial FROM sesiones_chat WHERE id = ?", (sesion_id,))
    sesion = cursor.fetchone()
    if not sesion:
        conexion.close()
        return

    ruta_actual = sesion["workspace_activo"]
    resumen_actual = sesion["workspace_resumen"]
    
    if ruta_actual and ruta_actual != nueva_ruta:
        historial_str = sesion["workspace_historial"]
        historial = json.loads(historial_str) if historial_str else []
        historial = [item for item in historial if item.get('ruta') != ruta_actual]
        historial.insert(0, {
            "ruta": ruta_actual,
            "resumen": resumen_actual or "Sin resumen disponible."
        })
        historial = historial[:3]
        
        cursor.execute("""
            UPDATE sesiones_chat 
            SET workspace_activo = ?, workspace_historial = ?, workspace_resumen = NULL, ultima_actualizacion = ? 
            WHERE id = ?
        """, (nueva_ruta, json.dumps(historial), _ahora(), sesion_id))
    else:
        cursor.execute("""
            UPDATE sesiones_chat 
            SET workspace_activo = ?, ultima_actualizacion = ? 
            WHERE id = ?
        """, (nueva_ruta, _ahora(), sesion_id))

    conexion.commit()
    conexion.close()
    print(f"[Fase 7 - Sesión {sesion_id[:8]}] Workspace fijado a: {nueva_ruta}")

def obtener_workspace_activo(sesion_id="default"):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT workspace_activo FROM sesiones_chat WHERE id = ?", (sesion_id,))
    fila = cursor.fetchone()
    conexion.close()
    return fila["workspace_activo"] if fila else None

def limpiar_workspace_activo(sesion_id="default"):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("""
        UPDATE sesiones_chat 
        SET workspace_activo = NULL, workspace_resumen = NULL, workspace_historial = NULL, ultima_actualizacion = ? 
        WHERE id = ?
    """, (_ahora(), sesion_id))
    conexion.commit()
    conexion.close()

# ============================================================
# HISTORIAL DE CONVERSACIÓN
# ============================================================
def guardar_mensaje(rol, mensaje, sesion_id="default"):
    # Paracaídas de seguridad: si llega un None o cadena vacía, forzamos el default
    if not sesion_id:
        sesion_id = "default"
        
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("""
        INSERT INTO historial_conversacion (timestamp, rol, mensaje, sesion_id)
        VALUES (?, ?, ?, ?)
    """, (_ahora(), rol, mensaje, sesion_id))
    
    # Actualiza la fecha de la sesión para ordenamiento
    cursor.execute("UPDATE sesiones_chat SET ultima_actualizacion = ? WHERE id = ?", (_ahora(), sesion_id))
    conexion.commit()
    conexion.close()

def obtener_historial_reciente(limite=10, sesion_id="default"):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("""
        SELECT rol, mensaje FROM historial_conversacion
        WHERE sesion_id = ?
        ORDER BY id DESC LIMIT ?
    """, (sesion_id, limite))
    mensajes = cursor.fetchall()
    conexion.close()
    return [dict(msg) for msg in reversed(mensajes)]

# ============================================================
# (RESTO DE FUNCIONES DE HERRAMIENTAS, PERFIL, Y HECHOS IGUALES)
# ============================================================

def obtener_perfil():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM perfil_usuario WHERE id = 1")
    perfil = cursor.fetchone()
    conexion.close()
    return dict(perfil) if perfil else None

def obtener_self_state():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM self_state WHERE id = 1")
    estado = cursor.fetchone()
    conexion.close()
    return dict(estado) if estado else None

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

def construir_contexto_ia(limite_historial=10, sesion_id="default"):
    """
    Ahora el contexto se arma aislando el workspace y el historial de la pestaña actual.
    """
    hechos_generales = [h for h in listar_hechos(categoria=None) if not h['clave'].startswith('workspace_')]
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT workspace_activo, workspace_resumen FROM sesiones_chat WHERE id = ?", (sesion_id,))
    sesion = cursor.fetchone()
    conexion.close()

    return {
        "perfil": obtener_perfil(),
        "self_state": obtener_self_state(),
        "herramientas": listar_herramientas(solo_activas=True),
        "workspace_activo": sesion["workspace_activo"] if sesion else None,
        "workspace_resumen": sesion["workspace_resumen"] if sesion else None,
        "hechos": hechos_generales,
        "historial_reciente": obtener_historial_reciente(limite=limite_historial, sesion_id=sesion_id),
    }

if __name__ == "__main__":
    print("--- Base de datos L-IA (SQLite) Compartimentada ---")
    inicializar_base_datos()
    print("Base de datos estructurada con soporte multi-sesión.")