import sqlite3
from datetime import datetime

# Nombre del archivo de base de datos local
DB_NAME = "lia_memory.db"

def obtener_conexion():
    """Establece una conexión con la base de datos SQLite."""
    # Si el archivo .db no existe, SQLite lo creará automáticamente en la carpeta
    conexion = sqlite3.connect(DB_NAME)
    # Esto permite acceder a las columnas por su nombre (como si fuera un diccionario)
    conexion.row_factory = sqlite3.Row
    return conexion

def inicializar_base_datos():
    """Crea las tablas de perfil e historial si no existen, e inserta el perfil inicial."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    # 1. Crear tabla de perfil de usuario (Memoria a largo plazo)
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

    # 2. Crear tabla de historial de conversación (Memoria a corto plazo)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historial_conversacion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        rol TEXT NOT NULL, -- 'user' o 'model'
        mensaje TEXT NOT NULL
    )
    """)

    # 3. Insertar un perfil por defecto de Alejandro si la tabla está vacía
    cursor.execute("SELECT COUNT(*) FROM perfil_usuario")
    if cursor.fetchone()[0] == 0:
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        INSERT INTO perfil_usuario (nombre, proyecto_actual, preferencias_musica, formato_respuesta, ultima_actualizacion)
        VALUES (?, ?, ?, ?, ?)
        """, (
            "Alejandro", 
            "Desarrollo de L-IA (asistente personal)", 
            "Rock, música para concentrarse", 
            "Directo, amigable, con un toque de humor y técnico", 
            ahora
        ))
        print("¡Perfil inicial creado con éxito para Alejandro!")

    conexion.commit()
    conexion.close()

def obtener_perfil():
    """Recupera los datos del perfil de Alejandro."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    # Como solo hay un usuario, traemos el registro con ID 1
    cursor.execute("SELECT * FROM perfil_usuario WHERE id = 1")
    perfil = cursor.fetchone()
    conexion.close()
    return dict(perfil) if perfil else None

def actualizar_proyecto(nuevo_proyecto):
    """Permite actualizar el proyecto en el que estás trabajando actualmente."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        UPDATE perfil_usuario 
        SET proyecto_actual = ?, ultima_actualizacion = ? 
        WHERE id = 1
    """, (nuevo_proyecto, ahora))
    conexion.commit()
    conexion.close()
    print(f"¡Proyecto actualizado a: '{nuevo_proyecto}'!")

def guardar_mensaje(rol, mensaje):
    """Guarda un mensaje en el historial (rol puede ser 'user' o 'model')."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO historial_conversacion (timestamp, rol, mensaje)
        VALUES (?, ?, ?)
    """, (ahora, rol, mensaje))
    conexion.commit()
    conexion.close()

def obtener_historial_reciente(limite=10):
    """Recupera los últimos X mensajes del historial para darle contexto a la IA."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    # Traemos los últimos mensajes ordenados por ID descendente
    cursor.execute("""
        SELECT rol, mensaje FROM historial_conversacion 
        ORDER BY id DESC LIMIT ?
    """, (limite,))
    mensajes = cursor.fetchall()
    conexion.close()
    
    # Invertimos la lista para que queden en orden cronológico correcto (del más viejo al más nuevo)
    return [dict(msg) for msg in reversed(mensajes)]

def borrar_historial():
    """Limpia el historial de conversación (útil para iniciar una nueva sesión limpia)."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM historial_conversacion")
    conexion.commit()
    conexion.close()
    print("¡Historial de chat reiniciado con éxito!")

if __name__ == "__main__":
    print("--- Probando Memoria de L-IA ---")
    inicializar_base_datos()
    
    # 1. Probar lectura de perfil
    perfil = obtener_perfil()
    print(f"\n[Perfil Detectado] Nombre: {perfil['nombre']}, Proyecto: {perfil['proyecto_actual']}")
    
    # 2. Probar actualización de proyecto
    actualizar_proyecto("Desarrollo del cerebro de L-IA paso a paso")
    perfil_actualizado = obtener_perfil()
    print(f"[Perfil Actualizado] Nuevo Proyecto: {perfil_actualizado['proyecto_actual']}")
    
    # 3. Probar escritura de historial
    print("\nSimulando conversación rápida...")
    guardar_mensaje("user", "Hola L-IA, ¿cómo estás?")
    guardar_mensaje("model", "¡Hola Alejandro! Estoy lista para ayudarte con tu nuevo proyecto.")
    
    # 4. Probar lectura de historial
    historial = obtener_historial_reciente(limite=5)
    print("\n--- Historial Reciente de Sesión ---")
    for msg in historial:
        print(f"{msg['rol'].upper()}: {msg['mensaje']}")