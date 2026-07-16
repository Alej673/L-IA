import os
import subprocess
import psutil

def abrir_aplicacion(nombre_app: str) -> str:
    """
    Busca de forma dinámica y abre cualquier aplicación instalada en Windows
    escaneando los directorios del Menú de Inicio de forma automática.
    """
    nombre_app = nombre_app.lower()
    
    # 1. Definir rutas del Menú de Inicio (Para todos los usuarios y el usuario actual)
    rutas_inicio = [
        r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
        os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs")
    ]
    
    print(f"🔍 [Buscando '{nombre_app}' en el sistema...]")
    
    # 2. Escanear las carpetas buscando un archivo .lnk que coincida con la búsqueda
    for ruta_base in rutas_inicio:
        if not os.path.exists(ruta_base):
            continue
            
        # os.walk recorre todas las subcarpetas automáticamente
        for raiz, _, archivos in os.walk(ruta_base):
            for archivo in archivos:
                # Comparamos si es un acceso directo y si contiene el nombre de lo que buscamos
                if archivo.lower().endswith(".lnk") and nombre_app in archivo.lower():
                    ruta_completa = os.path.join(raiz, archivo)
                    try:
                        # Hacemos el "doble clic virtual" nativo de Windows
                        os.startfile(ruta_completa)
                        # Retornamos el nombre real del archivo que encontramos para que L-IA lo sepa
                        nombre_limpio = archivo.replace(".lnk", "")
                        return f"Éxito: Se encontró y abrió '{nombre_limpio}'."
                    except Exception as e:
                        return f"Error al abrir '{archivo}': {str(e)}"
                        
    # 3. Si no encuentra nada en el Menú de Inicio, intentamos usar comandos del sistema tradicionales
    comandos_rapidos = {
        "vscode": "code",
        "chrome": "start chrome"
    }
    
    if nombre_app in comandos_rapidos:
        try:
            subprocess.Popen(comandos_rapidos[nombre_app], shell=True)
            return f"Éxito: Se ejecutó el comando alternativo para {nombre_app}."
        except Exception as e:
            return f"Error con comando alternativo: {str(e)}"

    return f"Error: No se encontró ningún programa llamado '{nombre_app}' en el menú de inicio."

def obtener_estado_sistema():
    """
    Lee los sensores de hardware (CPU, RAM, Batería, SSD) y audita los 3 procesos
    que más memoria RAM están consumiendo en el sistema operativo.
    """
    try:
        # 1. Medir CPU 
        cpu_porcentaje = psutil.cpu_percent(interval=0.5)
        
        # 2. Medir RAM
        ram_info = psutil.virtual_memory()
        ram_total = round(ram_info.total / (1024**3), 1)
        ram_usada = round(ram_info.used / (1024**3), 1)
        ram_porcentaje = ram_info.percent
        
        # 3. Medir Batería
        bateria = psutil.sensors_battery()
        if bateria:
            estado_enchufe = "Conectada a la corriente" if bateria.power_plugged else "Usando batería"
            bateria_txt = f"{bateria.percent}% ({estado_enchufe})"
        else:
            bateria_txt = "No se detectó batería"
            
        # 4. Medir Almacenamiento (Discos)
        discos_txt = ""
        particiones = psutil.disk_partitions()
        
        for particion in particiones:
            if 'cdrom' in particion.opts or particion.fstype == '':
                continue
            try:
                uso_disco = psutil.disk_usage(particion.mountpoint)
                total_gb = round(uso_disco.total / (1024**3), 1)
                libre_gb = round(uso_disco.free / (1024**3), 1)
                porcentaje_uso = uso_disco.percent
                discos_txt += f"[{particion.device} Total: {total_gb}GB, Libre: {libre_gb}GB ({porcentaje_uso}% usado)] "
            except PermissionError:
                continue 

        if not discos_txt:
            discos_txt = "Información de discos no disponible."

        # 5. NUEVO: Auditar los procesos más "tragones" de RAM
        procesos = []
        for proc in psutil.process_iter(['name', 'memory_info']):
            try:
                # Extraemos el consumo en MB de cada proceso activo
                mem_usada_mb = proc.info['memory_info'].rss / (1024**2)
                procesos.append({
                    'nombre': proc.info['name'],
                    'memoria_mb': round(mem_usada_mb, 1)
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Ignoramos procesos que se cierren durante el escaneo o protegidos por Windows
                continue

        # Ordenamos la lista de mayor a menor consumo de RAM
        procesos_ordenados = sorted(procesos, key=lambda x: x['memoria_mb'], reverse=True)
        
        # Tomamos los 3 primeros de la lista
        top_3_procesos = procesos_ordenados[:3]
        procesos_txt = ", ".join([f"{p['nombre']} ({p['memoria_mb']}MB)" for p in top_3_procesos])

        # 6. Reporte definitivo consolidado
        reporte = (
            f"DIAGNÓSTICO DE HARDWARE: "
            f"CPU al {cpu_porcentaje}%. "
            f"RAM consumida: {ram_usada}GB de {ram_total}GB ({ram_porcentaje}%). "
            f"Energía: {bateria_txt}. "
            f"Almacenamiento SSD: {discos_txt.strip()}. "
            f"Procesos que más RAM consumen actualmente: {procesos_txt}."
        )
        return reporte
        
    except Exception as e:
        return f"Error al intentar leer los sensores del sistema: {e}"

# Aquí más adelante agregaremos:
# - reproducir_musica(genero) -> Para Spotify
# - controlar_luces() -> Para IoT (Home Assistant)