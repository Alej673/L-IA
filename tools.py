import os
import json
import shutil
import difflib
import subprocess
import psutil
import pyperclip
import sys
import re  # Necesario para dividir textos complejos
import webbrowser

try:
    import winreg  # Solo existe en Windows; el resto del script sigue siendo Windows-only de todas formas
except ImportError:
    winreg = None


# Diccionario mágico con tus rutinas personalizadas
# Diccionario mágico con tus rutinas personalizadas
# Diccionario mágico con tus rutinas personalizadas
RUTAS_RUTINAS = {
    "trabajo_intenso": {
        "urls": [
            "https://www.youtube.com/watch?v=pAgnJDJN4VA&list=RDpAgnJDJN4VA&start_radio=1",
            "https://gemini.google.com/",
            "https://keep.google.com/",
            "http://127.0.0.1:8000/",
        ],
        "apps": [
            r'code "C:\laragon\www\sistema-bastones"',  # VS Code en el proyecto
            r'C:\laragon\laragon.exe',                   # Abre Laragon
        ],
        "comandos_consola": [
            # Abre una ventana de terminal, entra a la carpeta y ejecuta php artisan serve
            r'start cmd /k "cd /d C:\laragon\www\sistema-bastones && php artisan serve"'
        ],
        "carpetas": [
            r"C:\Users\ACER\Desktop\Documentos\ProyectoComplexivo"
        ]
    },
    "relax": {
        "urls": [
            "https://www.youtube.com/",
            "https://www.twitch.tv/"
        ],
        "apps": [],
        "comandos_consola": [],
        "carpetas": []
    }
}

def ejecutar_rutina(nombre_rutina="trabajo_intenso"):
    rutina = RUTAS_RUTINAS.get(nombre_rutina)
    if not rutina:
        return "No encontré esa rutina."

    # 1. Abrir pestañas en el navegador predeterminado (Brave)
    for url in rutina.get("urls", []):
        webbrowser.open(url)

    # 2. Abrir aplicaciones estándar
    for app in rutina.get("apps", []):
        try:
            subprocess.Popen(app, shell=True)
        except Exception as e:
            print(f"⚠️ Error abriendo {app}: {e}")

    # 3. Ejecutar comandos de consola (como php artisan serve) en ventanas separadas
    for cmd in rutina.get("comandos_consola", []):
        try:
            subprocess.Popen(cmd, shell=True)
        except Exception as e:
            print(f"⚠️ Error ejecutando comando '{cmd}': {e}")

    # 4. Abrir carpetas en el explorador de archivos
    for carpeta in rutina.get("carpetas", []):
        if os.path.exists(carpeta):
            os.startfile(carpeta)

    return "Entorno y servidor Laravel iniciados con éxito."
# ==========================================
# CONFIGURACIÓN EXTERNA (config_apps.json)
# ==========================================
# En vez de hardcodear alias y carpetas dentro del código Python, los
# guardamos en un JSON al lado de este archivo. Así, agregar "mis
# juegos están en D:\Juegos" es editar un archivo de texto plano,
# nunca tocar tools.py. Si el archivo no existe, se crea uno con
# valores de ejemplo la primera vez que se ejecuta.
_RUTA_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config_apps.json")

_CONFIG_POR_DEFECTO = {
    "alias": {
        "unreal engine": "unreal editor",
        "ue5": "unreal editor",
        "github": "github desktop",
        "word": "winword",
        "vs code": "vscode",
        "visual studio code": "vscode",
    },
    "carpetas_windows_nativas": {
        "descargas": "shell:Downloads",
        "documentos": "shell:Personal",
        "escritorio": "shell:Desktop",
        "imagenes": "shell:My Pictures",
        "videos": "shell:My Video",
        "musica": "shell:My Music",
    },
    "carpetas_personalizadas": {
        # Aquí van SOLO las rutas que Windows no puede adivinar solo:
        # tus proyectos, tus juegos, etc. Edita este archivo directo,
        # o usa aprender_carpeta() para que L-IA lo haga por ti.
    },
}


def _cargar_config():
    """Carga config_apps.json, o lo crea con valores de ejemplo si no existe."""
    if not os.path.exists(_RUTA_CONFIG):
        with open(_RUTA_CONFIG, "w", encoding="utf-8") as f:
            json.dump(_CONFIG_POR_DEFECTO, f, ensure_ascii=False, indent=2)
        return json.loads(json.dumps(_CONFIG_POR_DEFECTO))

    try:
        with open(_RUTA_CONFIG, "r", encoding="utf-8") as f:
            config = json.load(f)
        # Rellenamos claves faltantes por si el usuario editó el archivo
        # a mano y borró alguna sección sin querer.
        for clave, valor_defecto in _CONFIG_POR_DEFECTO.items():
            config.setdefault(clave, valor_defecto)
        return config
    except (json.JSONDecodeError, OSError):
        # Si el JSON quedó mal formado, no tumbamos el programa: devolvemos
        # el default en memoria (el archivo en disco lo puede arreglar el usuario).
        print("⚠️ [tools.py] config_apps.json está mal formado. Usando configuración por defecto en memoria.")
        return json.loads(json.dumps(_CONFIG_POR_DEFECTO))


def aprender_alias(nombre_hablado: str, nombre_real: str):
    """
    Permite enseñarle a L-IA un alias nuevo en caliente (ej. desde
    cerebro.py, cuando el usuario diga "cuando diga X quiero decir Y").
    Se guarda directo en config_apps.json, sin tocar código.
    """
    config = _cargar_config()
    config["alias"][nombre_hablado.strip().lower()] = nombre_real.strip().lower()
    with open(_RUTA_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    return f"Aprendido: '{nombre_hablado}' ahora significa '{nombre_real}'."


def aprender_carpeta(nombre_hablado: str, ruta: str):
    """
    Igual que aprender_alias(), pero para carpetas personalizadas
    (ej. "carpeta juegos" -> "D:\\Juegos"). Se guarda en config_apps.json.
    """
    config = _cargar_config()
    config["carpetas_personalizadas"][nombre_hablado.strip().lower()] = ruta.strip()
    with open(_RUTA_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    return f"Aprendido: '{nombre_hablado}' ahora abre '{ruta}'."


# ==========================================
# FUENTES DE BÚSQUEDA DE APLICACIONES
# ==========================================
def _buscar_en_registro_app_paths(nombre_app: str):
    """
    Windows guarda automáticamente la ruta de instalación de la mayoría
    de programas (Chrome, VSCode, Steam, Discord, Spotify, etc.) en:
      HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths
      HKEY_CURRENT_USER\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths
    Consultando esta clave cubrimos programas nuevos SIN necesidad de
    agregarlos a mano en ningún diccionario.
    """
    if winreg is None:
        return None

    claves_raiz = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
    ]

    nombres_candidatos = []
    for raiz, ruta_clave in claves_raiz:
        try:
            with winreg.OpenKey(raiz, ruta_clave) as clave:
                i = 0
                while True:
                    try:
                        subclave_nombre = winreg.EnumKey(clave, i)
                        nombres_candidatos.append((subclave_nombre, raiz, ruta_clave))
                        i += 1
                    except OSError:
                        break
        except FileNotFoundError:
            continue

    # Fuzzy match contra los nombres de .exe registrados (sin la extensión)
    nombres_limpios = [n[0].replace(".exe", "").lower() for n in nombres_candidatos]
    coincidencias = difflib.get_close_matches(nombre_app, nombres_limpios, n=1, cutoff=0.6)

    if not coincidencias:
        return None

    idx = nombres_limpios.index(coincidencias[0])
    subclave_nombre, raiz, ruta_clave = nombres_candidatos[idx]

    try:
        with winreg.OpenKey(raiz, f"{ruta_clave}\\{subclave_nombre}") as clave_app:
            ruta_exe, _ = winreg.QueryValueEx(clave_app, None)  # Valor por defecto = ruta al .exe
            return ruta_exe
    except (FileNotFoundError, OSError):
        return None


def _buscar_en_path(nombre_app: str):
    """
    Busca el ejecutable en el PATH del sistema (cubre herramientas de
    consola/desarrollo: code, git, python, node, php, composer, etc.)
    sin necesidad de hardcodear cada una.
    """
    candidatos = [nombre_app, f"{nombre_app}.exe", nombre_app.replace(" ", "")]
    for candidato in candidatos:
        ruta = shutil.which(candidato)
        if ruta:
            return ruta
    return None


# Cache en memoria del índice del Menú de Inicio: evitamos recorrer el
# disco (os.walk) en CADA petición. Se construye una vez por ejecución
# del programa y se puede forzar su reconstrucción con refrescar=True.
_INDICE_MENU_INICIO = None


def _indexar_menu_inicio(refrescar=False):
    global _INDICE_MENU_INICIO
    if _INDICE_MENU_INICIO is not None and not refrescar:
        return _INDICE_MENU_INICIO

    rutas_inicio = [
        r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
        os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
    ]

    indice = {}  # nombre_sin_extension_lower -> ruta_completa_lnk
    for ruta_base in rutas_inicio:
        if not os.path.exists(ruta_base):
            continue
        for raiz, _, archivos in os.walk(ruta_base):
            for archivo in archivos:
                if archivo.lower().endswith(".lnk"):
                    nombre_limpio = archivo[:-4].lower()  # quita ".lnk"

                    if "uninstall" in nombre_limpio or "desinstalar" in nombre_limpio:
                        continue

                    indice[nombre_limpio] = os.path.join(raiz, archivo)

    _INDICE_MENU_INICIO = indice
    return indice


def _buscar_en_menu_inicio(nombre_app: str):
    """
    Busca en el índice del Menú de Inicio con dos estrategias:
    1. Substring (rápido y exacto, como antes).
    2. Fuzzy match (difflib) para tolerar variaciones, plurales,
       o nombres parecidos que no coinciden letra por letra.
    """
    indice = _indexar_menu_inicio()

    # 1. Substring directo (comportamiento original)
    for nombre_indexado, ruta in indice.items():
        if nombre_app in nombre_indexado:
            return ruta, nombre_indexado

    # 2. Fuzzy match como respaldo
    coincidencias = difflib.get_close_matches(nombre_app, list(indice.keys()), n=1, cutoff=0.6)
    if coincidencias:
        nombre_indexado = coincidencias[0]
        return indice[nombre_indexado], nombre_indexado

    return None, None


# ==========================================
# ABRIR APLICACIÓN / CARPETA (función principal)
# ==========================================
def abrir_aplicacion(nombres_apps: str) -> str:
    """
    Busca y abre una o múltiples aplicaciones o carpetas del sistema,
    separadas por comas o la palabra "y". Orden de búsqueda por cada
    nombre (de más específico/rápido a más costoso):

      1. Alias configurado (config_apps.json) -> traduce el nombre hablado
      2. Carpeta nativa de Windows (shell:Downloads, etc.) -> config_apps.json
      3. Carpeta personalizada tuya (proyectos, juegos, etc.) -> config_apps.json
      4. Registro de Windows (App Paths) -> cubre la mayoría de programas
         instalados automáticamente, sin mantenimiento manual
      5. PATH del sistema -> herramientas de consola/desarrollo
      6. Menú de Inicio (con fuzzy match) -> resto de accesos directos
    """
    separadores = r',|\sy\s'
    lista_apps = [app.strip().lower() for app in re.split(separadores, nombres_apps) if app.strip()]

    config = _cargar_config()
    alias = config.get("alias", {})
    carpetas_nativas = config.get("carpetas_windows_nativas", {})
    carpetas_personalizadas = config.get("carpetas_personalizadas", {})

    resultados = []

    for nombre_original in lista_apps:
        # 1. Aplicamos el alias si el usuario usó un nombre distinto al real
        nombre_app = alias.get(nombre_original, nombre_original)
        print(f"🔍 [Buscando: '{nombre_app}'...]")
        encontrado = False

        # 2. Carpetas nativas de Windows (shell:...)
        if nombre_app in carpetas_nativas:
            try:
                subprocess.Popen(f"explorer {carpetas_nativas[nombre_app]}", shell=True)
                resultados.append(f"Éxito: Se abrió la carpeta '{nombre_original}'.")
                encontrado = True
                continue
            except Exception:
                pass

        # 3. Carpetas personalizadas (tus proyectos, juegos, etc.) con Fuzzy Match
        if not encontrado:
            claves_carpetas = list(carpetas_personalizadas.keys())
            # Comparamos lo que la IA entendió con las claves de tu JSON (60% de similitud)
            coincidencia_carpeta = difflib.get_close_matches(nombre_app, claves_carpetas, n=1, cutoff=0.6)
            
            if coincidencia_carpeta:
                clave_real = coincidencia_carpeta[0]
                ruta_carpeta = carpetas_personalizadas[clave_real]
                
                if os.path.exists(ruta_carpeta):
                    try:
                        os.startfile(ruta_carpeta)
                        resultados.append(f"Éxito: Se abrió la carpeta '{clave_real}'.")
                        encontrado = True
                        continue
                    except Exception as e:
                        resultados.append(f"Error al abrir carpeta '{clave_real}': {e}")
                        encontrado = True
                        continue
                else:
                    resultados.append(
                        f"Error: La carpeta configurada para '{clave_real}' ya no existe en '{ruta_carpeta}'. "
                        f"Revisa config_apps.json."
                    )
                    encontrado = True
                    continue

        # 4. Registro de Windows (App Paths) — cubre programas instalados
        #    sin que tengas que agregarlos a mano
        if not encontrado:
            ruta_registro = _buscar_en_registro_app_paths(nombre_app)
            if ruta_registro:
                try:
                    os.startfile(ruta_registro)
                    resultados.append(f"Éxito: Se ejecutó '{nombre_original}' (detectado en el Registro de Windows).")
                    encontrado = True
                    continue
                except Exception as e:
                    resultados.append(f"Error al abrir '{nombre_original}' desde el Registro: {e}")
                    encontrado = True
                    continue

        # 5. PATH del sistema — herramientas de consola/desarrollo
        if not encontrado:
            ruta_path = _buscar_en_path(nombre_app)
            if ruta_path:
                try:
                    subprocess.Popen([ruta_path], shell=True)
                    resultados.append(f"Éxito: Se ejecutó '{nombre_original}' (encontrado en el PATH).")
                    encontrado = True
                    continue
                except Exception as e:
                    resultados.append(f"Error al ejecutar '{nombre_original}' desde el PATH: {e}")
                    encontrado = True
                    continue

        # 6. Menú de Inicio, con fuzzy match como último recurso
        if not encontrado:
            ruta_lnk, nombre_detectado = _buscar_en_menu_inicio(nombre_app)
            if ruta_lnk:
                try:
                    os.startfile(ruta_lnk)
                    resultados.append(f"Éxito: Se abrió '{nombre_detectado}' (el más parecido a '{nombre_original}').")
                    encontrado = True
                    continue
                except Exception as e:
                    resultados.append(f"Error al abrir '{nombre_original}': {e}")
                    encontrado = True
                    continue

        if not encontrado:
            resultados.append(f"Error: No se encontró '{nombre_original}'.")

    return " | ".join(resultados)


def buscar_archivo_local(nombre_archivo: str) -> str:
    """
    Rastrea 'Zonas Seguras' buscando un archivo por su nombre.
    Ahora lee dinámicamente las carpetas desde config_apps.json.
    """
    nombre_archivo = nombre_archivo.lower()
    usuario_actual = os.path.expanduser("~")
    
    # 1. Rutas base obligatorias de Windows
    zonas_seguras = [
        os.path.join(usuario_actual, "Downloads"),
        os.path.join(usuario_actual, "Desktop"),
        os.path.join(usuario_actual, "Documents")
    ]
    
    # 2. Leer tu JSON y agregar TODAS tus carpetas personalizadas automáticamente
    config = _cargar_config()
    carpetas_personalizadas = config.get("carpetas_personalizadas", {})
    
    for nombre, ruta in carpetas_personalizadas.items():
        # Validamos que la ruta exista y no esté duplicada
        if os.path.exists(ruta) and ruta not in zonas_seguras:
            zonas_seguras.append(ruta)

    coincidencias = []
    print(f"🕵️‍♀️ [L-IA rastreando el archivo '{nombre_archivo}' en tus Zonas Seguras...]")
    
    for zona in zonas_seguras:
        if not os.path.exists(zona):
            continue
            
        for raiz, carpetas, archivos in os.walk(zona):
            # Excluir carpetas pesadas para mantener la búsqueda en milisegundos
            carpetas[:] = [c for c in carpetas if c not in ['node_modules', 'vendor', '.git', 'AppData', 'Saved', 'Intermediate']]
            
            for archivo in archivos:
                # IGNORAR ARCHIVOS TEMPORALES DE WORD/EXCEL Y ARCHIVOS OCULTOS
                if archivo.startswith("~$") or archivo.startswith("."):
                    continue
                    
                if nombre_archivo in archivo.lower():
                    ruta_completa = os.path.join(raiz, archivo)
                    coincidencias.append(ruta_completa)

    # Si la búsqueda exacta no encontró nada, probamos fuzzy match sobre
    # TODOS los nombres de archivo vistos, para tolerar errores de tecleo
    # o nombres parecidos (ej. "avances demo tecnica" vs "Avances_Demo_Tecnica.docx")
    if len(coincidencias) == 0:
        todos_los_archivos = []
        for zona in zonas_seguras:
            if not os.path.exists(zona):
                continue
            for raiz, carpetas, archivos in os.walk(zona):
                carpetas[:] = [c for c in carpetas if c not in ['node_modules', 'vendor', '.git', 'AppData', 'Saved', 'Intermediate']]
                for archivo in archivos:
                    if archivo.startswith("~$") or archivo.startswith("."):
                        continue
                    todos_los_archivos.append(os.path.join(raiz, archivo))

        nombres_base = [os.path.basename(p).lower() for p in todos_los_archivos]
        cercanos = difflib.get_close_matches(nombre_archivo, nombres_base, n=5, cutoff=0.5)
        if cercanos:
            coincidencias = [todos_los_archivos[nombres_base.index(c)] for c in cercanos]

    if len(coincidencias) == 0:
        return f"No se encontró ningún archivo relacionado con '{nombre_archivo}' en tus Zonas Seguras."

    elif len(coincidencias) == 1:
        return leer_archivo_local(coincidencias[0], busqueda_automatica=True)

    else:
        # Añadimos i+1 para que la lista salga numerada: 1., 2., 3.
        lista_sugerencias = "\n".join([f"{i+1}. {ruta}" for i, ruta in enumerate(coincidencias[:5])])
        return (
            f"Encontré múltiples coincidencias para '{nombre_archivo}'. "
            f"Muestra esta lista NUMERADA al usuario y pregúntale cuál quiere leer:\n{lista_sugerencias}"
        )


def leer_archivo_local(ruta_archivo: str, busqueda_automatica=False):
    """
    Lee un archivo de texto, código, Word (.docx) o PDF desde una ruta.
    """
    ruta_limpia = ruta_archivo.strip("'\"").strip()

    if not os.path.exists(ruta_limpia):
        if not busqueda_automatica and "\\" not in ruta_limpia and "/" not in ruta_limpia:
            return buscar_archivo_local(ruta_limpia)
        return {"error": f"No se encontró la ruta: {ruta_limpia}"}

    try:
        tamano_kb = os.path.getsize(ruta_limpia) / 1024
        nombre_archivo = os.path.basename(ruta_limpia)
        _, extension = os.path.splitext(nombre_archivo)

        # 1. Agregamos .docx y .pdf a las extensiones válidas
        extensiones_validas = ['.txt', '.py', '.php', '.js', '.json', '.html', '.css', '.md', '.env', '.cpp', '.h', '.docx', '.pdf']

        if extension.lower() not in extensiones_validas:
            return {"error": f"El formato '{extension}' no está soportado."}

        contenido = ""

        # 2. Lógica para documentos de Word
        if extension.lower() == '.docx':
            try:
                import docx
                doc = docx.Document(ruta_limpia)
                contenido = "\n".join([parrafo.text for parrafo in doc.paragraphs if parrafo.text.strip() != ""])
            except ImportError:
                return {"error": "Falta la librería. Ejecuta en la terminal: pip install python-docx"}

        # 3. Lógica para PDFs
        elif extension.lower() == '.pdf':
            try:
                import PyPDF2
                with open(ruta_limpia, 'rb') as f:
                    lector = PyPDF2.PdfReader(f)
                    for pagina in lector.pages:
                        texto = pagina.extract_text()
                        if texto:
                            contenido += texto + "\n"
            except ImportError:
                return {"error": "Falta la librería. Ejecuta en la terminal: pip install PyPDF2"}

        # 4. Lógica original para texto plano y código
        else:
            with open(ruta_limpia, 'r', encoding='utf-8', errors='ignore') as f:
                contenido = f.read()

        return {
            "nombre": nombre_archivo,
            "contenido": contenido,
            "tamano_kb": round(tamano_kb, 2),
            "es_pesado": tamano_kb > 35.0
        }
    except Exception as e:
        return {"error": f"Error de lectura: {e}"}


def obtener_estado_sistema() -> str:
    """
    Lee los sensores de hardware de la laptop usando psutil.
    Retorna un string con el uso de CPU, RAM, Batería y el Top 3 de procesos.
    """
    try:
        # 1. Lectura de CPU
        cpu_percent = psutil.cpu_percent(interval=1)

        # 2. Lectura de RAM
        ram = psutil.virtual_memory()
        ram_total = round(ram.total / (1024**3), 2)
        ram_usada = round(ram.used / (1024**3), 2)
        ram_percent = ram.percent

        # 3. Lectura de Batería
        bateria_info = "No detectada"
        if hasattr(psutil, "sensors_battery"):
            bateria = psutil.sensors_battery()
            if bateria:
                estado_enchufe = "Conectada a la corriente" if bateria.power_plugged else "Usando batería"
                bateria_info = f"{bateria.percent}% ({estado_enchufe})"

        # 4. Top 3 Procesos que más RAM consumen
        procesos = []
        for proc in psutil.process_iter(['name', 'memory_percent']):
            try:
                if proc.info['memory_percent'] is not None:
                    procesos.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # Ordenamos de mayor a menor y sacamos los primeros 3
        procesos = sorted(procesos, key=lambda p: p['memory_percent'], reverse=True)[:3]
        top_apps = ", ".join([f"{p['name']} ({round(p['memory_percent'], 1)}%)" for p in procesos])

        # 5. Estructurar el reporte
        reporte = (
            f"CPU Uso: {cpu_percent}% | "
            f"RAM Uso: {ram_usada}GB de {ram_total}GB ({ram_percent}%) | "
            f"Batería: {bateria_info} | "
            f"Top Apps consumiendo RAM: {top_apps}"
        )
        return reporte

    except Exception as e:
        return f"Error crítico al leer los sensores de hardware: {str(e)}"


def leer_portapapeles():
    """
    Lee el contenido actual del portapapeles del sistema.
    Devuelve un diccionario estructurado con los límites de seguridad.
    """
    try:
        contenido = pyperclip.paste()
        if not contenido or not str(contenido).strip():
            return {"error": "El portapapeles está vacío o contiene una imagen, no texto."}

        # Calculamos el peso en Kilobytes para proteger la RAM local
        peso_kb = len(contenido.encode('utf-8')) / 1024

        return {
            "contenido": contenido,
            "tamano_kb": round(peso_kb, 2),
            # Usamos el mismo límite de 35 KB que definiste para los archivos
            "es_pesado": peso_kb > 35.0
        }
    except Exception as e:
        return {"error": f"Fallo al leer portapapeles: {str(e)}"}

def leer_repositorio_git(ruta_repo):
    """
    Herramienta de Nivel 1. Ejecuta 'git status' y 'git log' en la ruta especificada
    para que L-IA analice el estado del código sin modificar nada.
    """
    if not os.path.exists(ruta_repo):
        return f"Error: La ruta '{ruta_repo}' no existe en el sistema."

    if not os.path.exists(os.path.join(ruta_repo, '.git')):
        return f"Error: La carpeta '{ruta_repo}' no está inicializada como repositorio Git."

    try:
        status = subprocess.run(
            ['git', 'status'],
            cwd=ruta_repo,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8',
            timeout=10
        )

        log = subprocess.run(
            ['git', 'log', '-3', '--oneline'],
            cwd=ruta_repo,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8',
            timeout=10
        )

        resultado = f"=== ESTADO DEL REPOSITORIO ({ruta_repo}) ===\n"
        resultado += status.stdout + "\n"
        resultado += "=== ÚLTIMOS COMMITS (Historial reciente) ===\n"
        resultado += log.stdout

        return resultado

    except FileNotFoundError:
        return "Error: Git no está instalado o no está disponible en el PATH del sistema."
    except subprocess.TimeoutExpired:
        return f"Error: git tardó demasiado en responder para '{ruta_repo}'."
    except subprocess.CalledProcessError as e:
        return f"Error: git falló al ejecutarse en '{ruta_repo}': {e.stderr.strip()}"
    except Exception as e:
        return f"Error inesperado leyendo el repositorio: {e}"

def hacer_commit_git(ruta_repo, titulo_commit, descripcion_commit=""):
    """Nivel 2: Añade cambios, hace commit y sube al remoto (Push)."""
    if not os.path.exists(ruta_repo):
        return f"Error: La ruta '{ruta_repo}' no existe."

    try:
        # 1. Validar si existen cambios pendientes (¡El parche de seguridad!)
        estado = subprocess.run(
            ['git', 'status', '--porcelain'], 
            cwd=ruta_repo, capture_output=True, text=True, check=True, encoding='utf-8'
        )
        
        if not estado.stdout.strip():
            return "⚠️ Todo está actualizado. No hay cambios pendientes para hacer commit."

        # 2. Añadir al staging
        subprocess.run(['git', 'add', '.'], cwd=ruta_repo, check=True)
        
        # 3. Crear el commit
        comando = ['git', 'commit', '-m', titulo_commit]
        if descripcion_commit:
            comando.extend(['-m', descripcion_commit])
            
        commit = subprocess.run(
            comando, cwd=ruta_repo, capture_output=True, text=True, check=True, encoding='utf-8'
        )
        
        # 4. Subir al servidor remoto (Push)
        push = subprocess.run(
            ['git', 'push'], cwd=ruta_repo, capture_output=True, text=True, check=True, encoding='utf-8'
        )
        
        return f"✅ Cambios guardados y subidos exitosamente.\n\nDetalles del Commit:\n{commit.stdout}\n\nDetalles del Push:\n{push.stderr or push.stdout}"
        
    except subprocess.CalledProcessError as e:
        # Mejora en el mensaje de error para saber exactamente en qué paso falló
        return f"❌ Error ejecutando Git ({' '.join(e.cmd)}):\nSalida: {e.stdout}\nError: {e.stderr}"
    except Exception as e:
        return f"❌ Error inesperado: {e}"

# ==========================================
# TOOL MANAGER (Capa de Permisos y Seguridad)
# ==========================================
# Niveles de riesgo:
# 0 = Segura (lectura pasiva)
# 1 = Local Benigna (ejecutar apps conocidas)
# 2 = Peligrosa (borrar, modificar, comandos de terminal libre)

CATALOGO_HERRAMIENTAS = {
    "obtener_estado_sistema": {"nivel": 0},
    "leer_portapapeles": {"nivel": 0},
    "buscar_archivo_local": {"nivel": 0},
    "leer_archivo_local": {"nivel": 0},
    "abrir_aplicacion": {"nivel": 1},
    "ejecutar_comando_sistema": {"nivel": 2},
    "leer_repositorio_git": {"nivel": 1},
    "hacer_commit_git": {"nivel": 2}
}

def gestor_permisos(nombre_herramienta: str, callback_ui_permiso=None, **kwargs):
    """
    Cortafuegos interno adaptado para interfaz gráfica.
    - callback_ui_permiso: una función externa (idealmente un popup de Tkinter) 
      que recibe el nombre de la herramienta y los argumentos, y retorna True (S) o False (N).
    """
    config = CATALOGO_HERRAMIENTAS.get(nombre_herramienta)
    
    if not config:
        return f"🚫 [Tool Manager]: Herramienta '{nombre_herramienta}' no registrada en el catálogo de seguridad."
        
    nivel_riesgo = config["nivel"]
    
    # Nivel 0 y 1: Ejecución silenciosa o con log benigno
    if nivel_riesgo <= 1:
        if nivel_riesgo == 1:
            print(f"🛡️ [Tool Manager]: Acción benigna permitida automáticamente ({nombre_herramienta})")
        return _ejecutar_dinamico(nombre_herramienta, **kwargs)
        
    # Nivel 2: Intervención humana obligatoria
    if nivel_riesgo == 2:
        print(f"\n⚠️ [ALERTA DE SEGURIDAD L-IA] ⚠️")
        print(f"El modelo intentó ejecutar una herramienta PELIGROSA: '{nombre_herramienta}'")
        print(f"Argumentos detectados: {kwargs}")
        
        autorizado = False
        
        # Si la interfaz gráfica (interfaz_lia.py) pasó una función visual, la usamos
        if callback_ui_permiso and callable(callback_ui_permiso):
            autorizado = callback_ui_permiso(nombre_herramienta, kwargs)
        else:
            # Respaldo por consola si se ejecuta desde terminal pura
            while True:
                respuesta = input("¿Autorizas la ejecución en tu sistema? [S/N]: ").strip().upper()
                if respuesta == 'S':
                    autorizado = True
                    break
                elif respuesta == 'N':
                    autorizado = False
                    break
                else:
                    print("Por favor, responde 'S' para Sí o 'N' para No.")
                    
        if autorizado:
            print("✅ Ejecución autorizada.")
            return _ejecutar_dinamico(nombre_herramienta, **kwargs)
        else:
            print("⛔ Ejecución bloqueada.")
            return f"🚫 [Tool Manager]: El usuario (Alejandro) bloqueó manualmente la ejecución de '{nombre_herramienta}' por razones de seguridad."

def _ejecutar_dinamico(nombre_herramienta, **kwargs):
    """Enrutador interno (dispatch) hacia la función real en tools.py"""
    if nombre_herramienta == "abrir_aplicacion":
        return abrir_aplicacion(kwargs.get("nombres_apps", ""))
    elif nombre_herramienta == "obtener_estado_sistema":
        return obtener_estado_sistema()
    elif nombre_herramienta == "buscar_archivo_local":
        return buscar_archivo_local(kwargs.get("nombre_archivo", ""))
    elif nombre_herramienta == "leer_archivo_local":
        return leer_archivo_local(kwargs.get("ruta_archivo", ""))
    elif nombre_herramienta == "leer_portapapeles":
        return leer_portapapeles()
    elif nombre_herramienta == "ejecutar_comando_sistema":
        # Ejemplo de ejecución futura controlada
        cmd = kwargs.get("comando", "")
        try:
            resultado = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            return resultado.stdout if resultado.returncode == 0 else resultado.stderr
        except Exception as e:
            return f"Error ejecutando comando: {e}"
    # NUEVO CONDICIONAL PARA GIT:
    elif nombre_herramienta == "leer_repositorio_git":
        return leer_repositorio_git(kwargs.get("ruta_repo", ""))
    elif nombre_herramienta == "hacer_commit_git":
        return hacer_commit_git(
            kwargs.get("ruta_repo", ""), 
            kwargs.get("titulo_commit", "Commit sin título"), 
            kwargs.get("descripcion_commit", "")
        )
    else:
        return f"Error: No hay lógica de despacho para {nombre_herramienta}"
# Aquí más adelante agregaremos:
# - reproducir_musica(genero) -> Para Spotify
# - controlar_luces() -> Para IoT (Home Assistant)