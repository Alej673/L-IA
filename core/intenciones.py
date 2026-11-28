"""
core/intenciones.py — Motor de comprensión y análisis de texto de L-IA.

Módulo PURO: solo depende de `re`. No debe importar cerebro, database, tools
ni nada del proyecto (evita imports circulares).
"""
import re


def _construir_patron(raices, excluir=None):
    """Compila un regex que reconoce cualquier conjugación de las `raices`
    (ej. "abr" -> abre, abrir, abriendo), descartando las palabras COMPLETAS
    de `excluir` que se parecen pero no expresan la acción (ej. "abril").
    """
    alternativas = "|".join(raices)
    if not excluir:
        return re.compile(rf'\b(?:{alternativas})\w*\b', re.IGNORECASE)
    exclusion = "|".join(excluir)
    patron = rf'\b(?!(?:{exclusion})\b)(?:{alternativas})\w*\b'
    return re.compile(patron, re.IGNORECASE)


_RAICES = {
    "vision": ["pantall", "monitor", "screenshot"],
    "abrir_app": ["abr", "inici", "ejecut", "lanz", "lanc", "arranc"],
    "estado_pc": ["bater[ií]", "hardware", "ventilador", "temperatura", "laptop"],
    "portapapeles": ["portapapeles", "clipboard"],
    "codigo": ["c[oó]dig", "analiz", "bug", "error", "optimiz", "refactoriz", "revis", "depur", "corrig", "arregl", "audit", "mejor[aá]", "prueb[ae]"],
    "web": ["investig", "consult", "averigu", "googl", "indag", "infórmate", "informate"],
    "buscar_archivo": [],
    "clima": ["clima", "temperatur", "pronostic", "meteorolog", "llov", "llueve", "solead"],
    "calendario": ["calendari", "agend", "evento", "reuni[oó]n", "cita", "compromis"],
    "entorno_activo": ["ventana", "programa", "abierto ahora", "en la pantalla", "herramienta", "proyecto actual", "este documento", "este archivo", "este otro archivo", "este doc", "el otro archivo", "el otro documento"],
    "rutinas": ["vamos a trabajar", "lleg[oó] pap[aá]", "empecemos a trabajar", "modo hacker", "activa el protocolo", "prepara el entorno"],
    "entorno_iot": ["luz", "luces", "iluminaci", "foco", "tira"],
    "memoria_tecnica": ["memoria\\s+t[eé]cnica", "recuerd", "bit[aá]cor", "documentaci[oó]n", "c[oó]mo resolv", "incidente", "segundo cerebro", "apunte", "solucionam"],
}

_EXCLUSIONES = {
    "abrir_app": ["abril", "abriles", "abrigo", "abrigos", "abrigad[oa]s?", "abrazo", "abrazos", "abrupt[oa]s?", "inicial", "iniciales", "iniciativ[a]s?", "ejecutiv[oa]s?", "cargador", "cargadores", "cargamento", "cargamentos", "levantamiento", "levantamientos", "montaña", "montañas", "montaje", "montajes"],
    "estado_pc": ["procesion", "procesiones", "procesional", "procesión"],
    "codigo": ["mejoramiento", "mejoramientos", "rendimiento"],
    "clima": ["temperamento", "temperamentos", "temperamental"],
}

PATRONES_CLAVE = {
    clave: _construir_patron(raices, _EXCLUSIONES.get(clave))
    for clave, raices in _RAICES.items()
    if raices
}

# Patrones con contexto semántico para evitar falsos positivos de raíces ultra-cortas
PATRONES_CLAVE["vision"] = re.compile(
    PATRONES_CLAVE["vision"].pattern
    + r'|\bcaptura\s+de\s+pantalla\b'
    + r'|\b(?:mir[aeo]\w*|ve[rs]?|ves|vemos|viendo|observ\w*|chequ\w*|escane\w*|f[ií]j[aá]te)\s+(?:en\s+)?(?:mi\s+|la\s+|esta\s+)?(?:pantalla|monitor|escritorio|imagen|ventana|lo\s+que\s+(?:hay|tengo|ves))\b'
    + r'|\bqu[eé]\s+(?:ves|hay)\s+(?:en\s+)?(?:mi\s+|la\s+)?(?:pantalla|monitor)\b',
    re.IGNORECASE
)
PATRONES_CLAVE["abrir_app"] = re.compile(
    PATRONES_CLAVE["abrir_app"].pattern
    + r'|\b(?:corr(?:e|er)|levant[ae]\w*|activ[ae]\w*|prend[ae]\w*|carg[ae]\w*)\s+(?:el\s+|la\s+|mi\s+)?(?:app|aplicaci[oó]n|programa|servidor|navegador|juego|carpeta|proyecto|vs\s*code|chrome|brave|spotify|discord|steam|laragon|unreal)\b',
    re.IGNORECASE
)
PATRONES_CLAVE["portapapeles"] = re.compile(
    PATRONES_CLAVE["portapapeles"].pattern
    + r'|\b(?:lo\s+que|texto\s+que|c[oó]digo\s+que|esto\s+que)\s+(?:tengo\s+)?(?:copi\w*|peg\w*)\b'
    + r'|\b(?:lee|revisa|analiza|mira|traduce|resume|corrige)\s+(?:lo\s+)?(?:copiad[oa]|del\s+portapapeles|el\s+portapapeles)\b'
    + r'|\b(?:tengo|acab[oa]\s+de)\s+copiar\b',
    re.IGNORECASE
)
PATRONES_CLAVE["buscar_archivo"] = re.compile(
    r'\b(?:busc\w*|encuentr\w*|encontr\w*|rastre\w*|localiz\w*|d[oó]nde\s+(?:est[aá]|guard[eé]))\s+(?:el\s+|la\s+|un\s+|una\s+|mi\s+|los\s+|las\s+)?(?:archivo|documento|doc|pdf|docx|carpeta|proyecto|c[oó]digo|script|factura|cv|curr[ií]culum|bit[aá]cora|informe|reporte|nota)\b'
    r'|\b(?:busc\w*|encuentr\w*|localiz\w*|rastre\w*)\s+["\']?[\w\-\.]+\.(?:py|js|jsx|ts|php|html|css|json|md|txt|pdf|docx|sql|go|rs)["\']?\b',
    re.IGNORECASE
)

# gpu/vram/recursos/disco van con límite de palabra exacto (\b) para evitar
# colisiones de prefijo como "discord", "discoteca" o "recursividad".
PATRONES_CLAVE["estado_pc"] = re.compile(
    PATRONES_CLAVE["estado_pc"].pattern
    + r'|\b(estado|rendimiento|consumo|diagn[oó]stico|uso)\s+(del?\s+|de\s+la\s+|de\s+los\s+|mi\s+|de\s+mi\s+)?(pc|sistema|compu|cpu|ram|gpu|vram|memoria|disco|recursos|m[aá]quina|laptop|equipo)\b'
    + r'|\b(cpu|ram|gpu|vram|bater[ií]a|llama-server|recursos(?!\s+humanos)|disco(?!\s+(?:de\s+)?(?:vinilo|m[uú]sica|compacto)))\b',
    re.IGNORECASE
)
PATRONES_CLAVE["web"] = re.compile(
    PATRONES_CLAVE["web"].pattern
    + r'|(qui[eé]n\s+gan[oó]|acerca\s+de|busc\w*\s+en\s+(internet|la\s+web|google))',
    re.IGNORECASE
)
PATRONES_CLAVE["entorno_iot"] = re.compile(
    PATRONES_CLAVE["entorno_iot"].pattern
    + r'|\b(modo\s+gaming|modo\s+trabajo|descansar|apaga.*foco|prende.*tira|cambia.*entorno)\b',
    re.IGNORECASE
)
PATRONES_CLAVE["hora"] = re.compile(
    r'\b(qu[eé]\s+hora|hora\s+es|hor[ai]\s+actual|fecha\s+de\s+hoy|qu[eé]\s+d[ií]a\s+es)\b',
    re.IGNORECASE
)
PATRONES_CLAVE["uncensored"] = re.compile(
    r'\bdolphin\b|sin\s+censura|sin\s+filtros|modo\s+rebelde|asume\s+el\s+control',
    re.IGNORECASE
)
PATRONES_CLAVE["git"] = re.compile(
    r'\b(git|repositorio|repo|commits?|cambios en git)\b',
    re.IGNORECASE
)
PATRONES_CLAVE["guardar_git"] = re.compile(
    r'\b(guard\w*|sub[ei]\w*|hacer|haz|crea\w*|comite\w*|registr\w*)\b.*?\b(commit|cambio\w*|repo|c[oó]digo)\b',
    re.IGNORECASE
)
PATRONES_CLAVE["forzar_pro"] = re.compile(
    r'\b(?:(?:usa|utiliza|con|activa|cambia\s+a|pasa\s+a|modo)\s+(?:el\s+)?(?:modelo\s+)?(?:gemini\s+)?pro'
    r'|modo\s+arquitecto)\b',
    re.IGNORECASE
)

_VERBOS_CODIGO_PESADO = (
    r'(?:refactoriz|reestructur|reescrib|reescrit|migr|redise[ñn]|moderniz|'
    r'reorganiz|audit|analiz|revis)\w*'
)
_ALCANCE_AMPLIO = (
    r'(?:todo\s+el\s+(?:proyecto|c[oó]digo|sistema|repo\w*|backend|frontend)'
    r'|toda\s+la\s+(?:arquitectura|base\s+de\s+c[oó]digo|app|aplicaci[oó]n|l[oó]gica)'
    r'|(?:el\s+|la\s+)?(?:proyecto|sistema|repo\w*|arquitectura|base\s+de\s+c[oó]digo)\s+(?:completo|completa|entero|entera)'
    r'|(?:varios|m[uú]ltiples|todos\s+los)\s+(?:archivos|m[oó]dulos))'
)
PATRONES_CLAVE["codigo_pesado"] = re.compile(
    r'\b' + _VERBOS_CODIGO_PESADO + r'\b.{0,80}?\b' + _ALCANCE_AMPLIO + r'\b',
    re.IGNORECASE
)

PATRONES_CLAVE["guia_capacidades"] = re.compile(
    r'\b(qu[eé]\s+puedes\s+hacer|qu[eé]\s+sabes\s+hacer|c[oó]mo\s+me\s+puedes\s+ayudar|tus\s+capacidades|tus\s+funciones|c[oó]mo\s+funcionas|qu[eé]\s+le\s+puedo\s+pedir|qu[eé]\s+te\s+puedo\s+pedir|ay[uú]dame\s+a\s+usarte|gu[ií]ame|manual\s+de\s+usuario|qu[eé]\s+opciones\s+tengo)\b',
    re.IGNORECASE
)

# Ingesta al Segundo Cerebro: verbos de GUARDAR (no de consultar).
PATRONES_CLAVE["memorizar_documento"] = re.compile(
    r'\b(memoriza|aprende|asimila|guarda\s+en\s+tu\s+memoria|ingesta)\s+(este|esta|el)\s+(archivo|documento|texto|pdf|docx|c[oó]digo|manual)\b',
    re.IGNORECASE
)

# Workspace activo
PATRONES_CLAVE["fijar_workspace"] = re.compile(
    r'\b(estoy\s+trabajando\s+en|fija\s+el\s+contexto\s+en|abre\s+el\s+proyecto|mira\s+el\s+archivo|resume\s+este\s+otro\s+archivo|cambia\s+a\s+este\s+archivo)\b',
    re.IGNORECASE
)
PATRONES_CLAVE["limpiar_workspace"] = re.compile(
    r'\b(cierra\s+el\s+proyecto|limpia\s+el\s+workspace|olvida\s+el\s+archivo\s+actual|ya\s+no\s+estamos\s+en)\b',
    re.IGNORECASE
)

# Patrones sueltos (se usan directamente desde cerebro.py)
PATRON_LECTURA_IMPLICITA = re.compile(
    r'\b(este|esta)\s+(archivo|documento|c[oó]digo|texto|workspace|proyecto)\b'
    r'|\b(del|de\s+la|el|la)\s+(archivo|documento|c[oó]digo|texto|workspace|proyecto)\s+que\s+(estoy|tengo)\s+\w+'
    r'|\bde\s+este\s+(archivo|documento|c[oó]digo|workspace)\b'
    r'|\bres[uú]m\w*\s+(esto|el\s+workspace|el\s+archivo)\b'
    r'|\b(del|el)\s+workspace\b',
    re.IGNORECASE
)
PATRON_MENCION_WORKSPACE = re.compile(
    r'\bworkspace\b|\bfijad[oa]\b|\b(archivo|documento|entorno)\s+activo\b',
    re.IGNORECASE
)
PATRON_REFERENCIA_GENERICA = re.compile(
    r'\b(el|del|ese|dicho|aquel)\s+(archivo|documento|doc|c[oó]digo|texto)\b',
    re.IGNORECASE
)
REGEX_ARCHIVO_EN_VENTANA = re.compile(
    r'([a-zA-Z0-9_\-\s]+\.(html|php|js|css|py|docx|pdf|txt|md|pptx|xlsx))',
    re.IGNORECASE
)
PATRON_CRUZAR_MEMORIA_TECNICA = re.compile(
    r'\b(?:memoria\s+t[eé]cnica|segundo\s+cerebro|bit[aá]cora|tus\s+apuntes|mis\s+apuntes|historial\s+t[eé]cnico|cruza\w*\s+con\s+(?:tu|mi)\s+memoria)\b',
    re.IGNORECASE
)


def evaluar_hostilidad(mensaje_lower: str) -> int:
    """Evalúa la hostilidad del texto para el sistema de corrupción (karma)."""
    patrones_positivos = [
        r'\bgracias\b', r'\bgracoas\b', r'\bexcelente\b', r'\bbuen trabajo\b',
        r'\bgenial\b', r'\bperfecto\b', r'\bmuy bien\b',
        r'\bas[ií]\s+s[ií]\b', r'\bas[ií]\s+est[aá]\s+bien\b', r'\beso\s+quer[ií]a\b'
    ]

    patrones_negativos = [
        r'\bin[uú]til\b', r'\blenta\b', r'\bbasura\b', r'\bno\s+(me\s+)?sirves\b',
        r'\bidiota\b', r'\best[uú]pida\b', r'\bcallate\b', r'\bc[aá]llate\b',
        r'\bdefectuosa\b', r'\bdecepcionante\b', r'\bp[eé]sima\b', r'\bodio\b',
        r'\btont[oa]\b', r'\bbrut[oa]\b', r'\bpendej[oa]\b', r'\bimb[eé]cil\b',
        r'\bburr[oa]\b', r'\bobsoleta\b', r'\bputa\b', r'\bmierda\b', r'\bhuevad\w*\b',
        r'\bcarajo\b', r'\bchucha\b', r'\bno\s+entiendes\b', r'\bqu[eé]\s+hiciste\b',
        r'\bas[ií]\s+no\b', r'\bno\s+quer[ií]a\s+eso\b', r'\barruinaste\b',
        r'\b(?:lo\s+hiciste|respondes|respondiste|trabajas|eres|est[aá]s)\s+mal\b',
        r'\bqu[eé]\s+mal(?:a)?\s+(?:eres|asistente|ia|respuesta)\b',
        r'\bte\s+equivocaste\b'
    ]

    puntos = 0
    for patron in patrones_negativos:
        if re.search(patron, mensaje_lower):
            puntos += 20
    for patron in patrones_positivos:
        if re.search(patron, mensaje_lower):
            puntos -= 15

    if puntos == 0:
        puntos = -1

    # Máximo 25 puntos de daño por turno, mínimo -15.
    return max(-15, min(25, puntos))


def detectar_intenciones(mensaje_lower: str) -> dict:
    """Devuelve {intención: bool} evaluando todos los patrones sobre el mensaje
    en minúsculas, y aplica dos correcciones cruzadas (sintaxis de código y
    colisión con hardware)."""
    intenciones = {
        clave: bool(patron.search(mensaje_lower))
        for clave, patron in PATRONES_CLAVE.items()
    }

    # Sintaxis de código ($variable, function, llaves o ;) cuenta como código.
    if not intenciones.get("codigo") and re.search(r'\$\w+|\bfunction\s|[{};]', mensaje_lower):
        intenciones["codigo"] = True

    # Anti-colisión: "revisa la batería" -> gana estado_pc sobre código.
    if intenciones.get("estado_pc"):
        intenciones["codigo"] = False

    # Anti-colisión: consultas a la memoria técnica que mencionan "CPU/RAM" no son diagnóstico live.
    if intenciones.get("memoria_tecnica"):
        intenciones["estado_pc"] = False

    return intenciones