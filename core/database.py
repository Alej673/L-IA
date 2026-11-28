import sqlite3
import json
import os
import uuid
from contextlib import contextmanager
from datetime import datetime

try:
    from core import rutas
except ModuleNotFoundError:
    import rutas

# Rutas unificadas desde core/rutas.py (SSOT)
BASE_DIR = str(rutas.BASE_DIR)
DATA_DIR = str(rutas.CARPETA_DATA)
os.makedirs(DATA_DIR, exist_ok=True)

DB_NAME = str(rutas.SQLITE_DB_PATH)

def obtener_conexion():
    """Establece una conexión con la base de datos SQLite."""
    conexion = sqlite3.connect(DB_NAME, timeout=15.0)
    try:
        conexion.row_factory = sqlite3.Row
        conexion.execute("PRAGMA foreign_keys = ON")
        conexion.execute("PRAGMA journal_mode = WAL")
        conexion.execute("PRAGMA synchronous = NORMAL")
    except Exception:
        conexion.close()
        raise
    return conexion


@contextmanager
def _conexion(escribir: bool = False):
    """Context manager que garantiza commit/rollback y cierre siempre en finally."""
    conexion = obtener_conexion()
    try:
        yield conexion
        if escribir:
            conexion.commit()
    except Exception:
        if escribir:
            conexion.rollback()
        raise
    finally:
        conexion.close()

def _ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ============================================================
# INICIALIZACIÓN
# ============================================================

def inicializar_base_datos():
    """Crea todas las tablas si no existen e inserta los datos base."""
    with _conexion(escribir=True) as conexion:
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

        # 7. Memoria Relacional RAG (NUEVO)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS documentos_memoria (
            doc_id TEXT PRIMARY KEY,
            titulo TEXT,
            grupo TEXT,
            tipo TEXT,
            ruta_archivo TEXT,
            total_chunks INTEGER,
            veces_consultado INTEGER DEFAULT 0,
            fecha_creacion DATETIME
        )
        """)
        conexion.commit()

        # --- Seed data ---
        _seed_perfil(cursor)
        _seed_sesiones(cursor)
        _seed_self_state(cursor)
        _seed_herramientas(cursor)

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
    sesion_id = str(uuid.uuid4())
    with _conexion(escribir=True) as conexion:
        cursor = conexion.cursor()
        cursor.execute("""
            INSERT INTO sesiones_chat (id, titulo, fecha_creacion, ultima_actualizacion)
            VALUES (?, ?, ?, ?)
        """, (sesion_id, titulo, _ahora(), _ahora()))
    return sesion_id

def listar_sesiones():
    with _conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute("SELECT id, titulo, workspace_activo, fecha_creacion FROM sesiones_chat ORDER BY ultima_actualizacion DESC")
        filas = cursor.fetchall()
    return [dict(f) for f in filas]

def actualizar_titulo_sesion(sesion_id, nuevo_titulo):
    with _conexion(escribir=True) as conexion:
        cursor = conexion.cursor()
        cursor.execute("UPDATE sesiones_chat SET titulo = ?, ultima_actualizacion = ? WHERE id = ?", 
                       (nuevo_titulo, _ahora(), sesion_id))

def borrar_sesion(sesion_id):
    """Elimina una sesión y todo su historial de mensajes (en cascada)."""
    with _conexion(escribir=True) as conexion:
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM sesiones_chat WHERE id = ?", (sesion_id,))
    print(f"🗑️ [Sesión {sesion_id[:8]}] Eliminada correctamente.")

# ============================================================
# WORKSPACE / CONTEXTO ACTIVO - AISLADO POR SESIÓN
# ============================================================

def establecer_workspace_activo(nueva_ruta, sesion_id="default"):
    with _conexion(escribir=True) as conexion:
        cursor = conexion.cursor()
        
        cursor.execute("SELECT workspace_activo, workspace_resumen, workspace_historial FROM sesiones_chat WHERE id = ?", (sesion_id,))
        sesion = cursor.fetchone()
        if not sesion:
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

    print(f"[Fase 7 - Sesión {sesion_id[:8]}] Workspace fijado a: {nueva_ruta}")

def obtener_workspace_activo(sesion_id="default"):
    with _conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute("SELECT workspace_activo FROM sesiones_chat WHERE id = ?", (sesion_id,))
        fila = cursor.fetchone()
    return fila["workspace_activo"] if fila else None

def limpiar_workspace_activo(sesion_id="default"):
    with _conexion(escribir=True) as conexion:
        cursor = conexion.cursor()
        cursor.execute("""
            UPDATE sesiones_chat 
            SET workspace_activo = NULL, workspace_resumen = NULL, workspace_historial = NULL, ultima_actualizacion = ? 
            WHERE id = ?
        """, (_ahora(), sesion_id))

# ============================================================
# HISTORIAL DE CONVERSACIÓN
# ============================================================
def guardar_mensaje(rol, mensaje, sesion_id="default"):
    # Paracaídas de seguridad: si llega un None o cadena vacía, forzamos el default
    if not sesion_id:
        sesion_id = "default"
        
    with _conexion(escribir=True) as conexion:
        cursor = conexion.cursor()
        cursor.execute("""
            INSERT INTO historial_conversacion (timestamp, rol, mensaje, sesion_id)
            VALUES (?, ?, ?, ?)
        """, (_ahora(), rol, mensaje, sesion_id))
        
        # Actualiza la fecha de la sesión para ordenamiento
        cursor.execute("UPDATE sesiones_chat SET ultima_actualizacion = ? WHERE id = ?", (_ahora(), sesion_id))

def obtener_historial_reciente(limite=10, sesion_id="default"):
    with _conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT rol, mensaje FROM historial_conversacion
            WHERE sesion_id = ?
            ORDER BY id DESC LIMIT ?
        """, (sesion_id, limite))
        mensajes = cursor.fetchall()
    return [dict(msg) for msg in reversed(mensajes)]

# ============================================================
# GESTIÓN DE MEMORIA RAG (Índice Maestro)
# ============================================================

def registrar_documento_rag(doc_id, titulo, grupo, tipo, ruta_archivo, total_chunks):
    with _conexion(escribir=True) as conexion:
        cursor = conexion.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO documentos_memoria 
            (doc_id, titulo, grupo, tipo, ruta_archivo, total_chunks, fecha_creacion)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (doc_id, titulo, grupo, tipo, ruta_archivo, total_chunks, _ahora()))

def listar_documentos_rag():
    with _conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute("SELECT * FROM documentos_memoria")
        filas = cursor.fetchall()
    return [dict(f) for f in filas]

def incrementar_uso_documento_rag(doc_id):
    with _conexion(escribir=True) as conexion:
        cursor = conexion.cursor()
        cursor.execute("""
            UPDATE documentos_memoria 
            SET veces_consultado = veces_consultado + 1 
            WHERE doc_id = ?
        """, (doc_id,))

def buscar_ruta_proyecto_rag(nombre_proyecto):
    with _conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT ruta_archivo FROM documentos_memoria 
            WHERE titulo LIKE ? OR grupo LIKE ?
        """, (f"%{nombre_proyecto}%", f"%{nombre_proyecto}%"))
        resultado = cursor.fetchone()
    return resultado["ruta_archivo"] if resultado else None

def actualizar_workspace_resumen(resumen, sesion_id="default"):
    """Guarda el micro-resumen en la tabla de la sesión activa."""
    with _conexion(escribir=True) as conexion:
        cursor = conexion.cursor()
        cursor.execute("UPDATE sesiones_chat SET workspace_resumen = ?, ultima_actualizacion = ? WHERE id = ?", (resumen, _ahora(), sesion_id))

def guardar_hecho(clave, valor, categoria=None):
    """Guarda un dato suelto en la tabla de memoria_hechos."""
    with _conexion(escribir=True) as conexion:
        cursor = conexion.cursor()
        cursor.execute("""
            INSERT INTO memoria_hechos (clave, valor, categoria, ultima_actualizacion)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(clave) DO UPDATE SET 
            valor = excluded.valor, 
            categoria = excluded.categoria,
            ultima_actualizacion = excluded.ultima_actualizacion
        """, (clave, valor, categoria, _ahora()))

# ============================================================
# (RESTO DE FUNCIONES DE HERRAMIENTAS, PERFIL, Y HECHOS IGUALES)
# ============================================================

def obtener_perfil():
    with _conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute("SELECT * FROM perfil_usuario WHERE id = 1")
        perfil = cursor.fetchone()
    return dict(perfil) if perfil else None

def obtener_self_state():
    with _conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute("SELECT * FROM self_state WHERE id = 1")
        estado = cursor.fetchone()
    return dict(estado) if estado else None

def listar_herramientas(solo_activas=True):
    with _conexion() as conexion:
        cursor = conexion.cursor()
        if solo_activas:
            cursor.execute("SELECT * FROM herramientas WHERE activa = 1 ORDER BY nombre")
        else:
            cursor.execute("SELECT * FROM herramientas ORDER BY nombre")
        filas = cursor.fetchall()
    return [dict(f) for f in filas]

def listar_hechos(categoria=None):
    with _conexion() as conexion:
        cursor = conexion.cursor()
        if categoria:
            cursor.execute("SELECT * FROM memoria_hechos WHERE categoria = ?", (categoria,))
        else:
            cursor.execute("SELECT * FROM memoria_hechos")
        filas = cursor.fetchall()
    return [dict(f) for f in filas]

_CLAVES_HECHOS_INTERNAS = {"nivel_corrupcion"}
_CATEGORIAS_HECHOS_INTERNAS = {"estado_emocional", "sistema"}


def construir_contexto_ia(limite_historial=10, sesion_id="default"):
    """
    Ahora el contexto se arma aislando el workspace y el historial de la pestaña actual.
    """
    with _conexion() as conexion:
        cursor = conexion.cursor()

        cursor.execute("SELECT * FROM perfil_usuario WHERE id = 1")
        fila_perfil = cursor.fetchone()
        perfil = dict(fila_perfil) if fila_perfil else None

        cursor.execute("SELECT * FROM self_state WHERE id = 1")
        fila_estado = cursor.fetchone()
        self_state = dict(fila_estado) if fila_estado else None

        cursor.execute("SELECT * FROM herramientas WHERE activa = 1 ORDER BY nombre")
        herramientas = [dict(f) for f in cursor.fetchall()]

        cursor.execute("SELECT * FROM memoria_hechos")
        todos_hechos = [dict(f) for f in cursor.fetchall()]

        cursor.execute(
            "SELECT workspace_activo, workspace_resumen, workspace_historial FROM sesiones_chat WHERE id = ?",
            (sesion_id,),
        )
        sesion = cursor.fetchone()

        cursor.execute(
            """
            SELECT rol, mensaje FROM historial_conversacion
            WHERE sesion_id = ?
            ORDER BY id DESC LIMIT ?
            """,
            (sesion_id, limite_historial),
        )
        historial_reciente = [dict(msg) for msg in reversed(cursor.fetchall())]

    nivel_corrupcion = 0
    hechos_generales = []
    for h in todos_hechos:
        clave = h.get("clave", "")
        categoria = (h.get("categoria") or "").lower()
        if clave == "nivel_corrupcion":
            try:
                nivel_corrupcion = max(0, min(100, int(h.get("valor") or 0)))
            except (ValueError, TypeError):
                nivel_corrupcion = 0
            continue
        if (
            clave.startswith("workspace_")
            or clave in _CLAVES_HECHOS_INTERNAS
            or categoria in _CATEGORIAS_HECHOS_INTERNAS
        ):
            continue
        hechos_generales.append(h)

    return {
        "perfil": perfil,
        "self_state": self_state,
        "herramientas": herramientas,
        "workspace_activo": sesion["workspace_activo"] if sesion else None,
        "workspace_resumen": sesion["workspace_resumen"] if sesion else None,
        "workspace_historial": sesion["workspace_historial"] if sesion else None,
        "nivel_corrupcion": nivel_corrupcion,
        "hechos": hechos_generales,
        "historial_reciente": historial_reciente,
    }

# ============================================================
# ESTADO PSICOLÓGICO / CORRUPCIÓN
# ============================================================
def obtener_nivel_corrupcion():
    """Devuelve el nivel de corrupción actual (0 a 100). Si no existe, devuelve 0."""
    with _conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute("SELECT valor FROM memoria_hechos WHERE clave = 'nivel_corrupcion'")
        fila = cursor.fetchone()
    
    if fila and fila["valor"]:
        try:
            return int(fila["valor"])
        except ValueError:
            return 0
    return 0

def modificar_nivel_corrupcion(puntos_a_sumar):
    """
    Suma o resta puntos a la corrupción de L-IA. 
    Usa valores negativos para calmarla (ej. -10) y positivos para estresarla (ej. +20).
    """
    conexion = obtener_conexion()
    try:
        conexion.isolation_level = None
        cursor = conexion.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        try:
            cursor.execute("SELECT valor FROM memoria_hechos WHERE clave = 'nivel_corrupcion'")
            fila = cursor.fetchone()
            nivel_actual = 0
            if fila and fila["valor"]:
                try:
                    nivel_actual = int(fila["valor"])
                except ValueError:
                    nivel_actual = 0

            # Limitamos estrictamente el nivel entre 0 y 100
            nuevo_nivel = max(0, min(100, nivel_actual + puntos_a_sumar))
            
            # Usamos INSERT ON CONFLICT para crearlo si no existe, o actualizarlo si ya existe
            cursor.execute("""
                INSERT INTO memoria_hechos (clave, valor, categoria, ultima_actualizacion)
                VALUES ('nivel_corrupcion', ?, 'estado_emocional', ?)
                ON CONFLICT(clave) DO UPDATE SET 
                valor = excluded.valor, 
                ultima_actualizacion = excluded.ultima_actualizacion
            """, (str(nuevo_nivel), _ahora()))
            cursor.execute("COMMIT")
        except Exception:
            if conexion.in_transaction:
                cursor.execute("ROLLBACK")
            raise
    finally:
        conexion.close()
    print(f"📉 [Estado Psicológico] Corrupción actualizada a: {nuevo_nivel}/100")
    return nuevo_nivel

if __name__ == "__main__":
    print("--- Base de datos L-IA (SQLite) Compartimentada ---")
    inicializar_base_datos()
    print("Base de datos estructurada con soporte multi-sesión.")