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
    "vision": ["pantall", "monitor", "mir", "observ", "ve", "vio", "vier", "viend", "vist", "vem", "chequ", "escane", "fij[aá]te"],
    "abrir_app": ["abr", "inici", "ejecut", "lanz", "lanc", "arranc", "activ", "prend", "corr[ée]", "carg", "levant", "monta"],
    "estado_pc": ["bater[ií]", "hardware", "ventilador", "temperatura", "laptop"],
    "portapapeles": ["portapapeles", "copi", "peg", "clipboard"],
    "codigo": ["c[oó]dig", "analiz", "bug", "error", "optimiz", "refactoriz", "revis", "depur", "corrig", "arregl", "audit", "mejor[aá]", "prueb[ae]"],
    "web": ["investig", "consult", "averigu", "googl", "indag", "infórmate", "informate"],
    "buscar_archivo": ["busc", "encuentr", "rastre", "localiz", "archivo", "documento"],
    "clima": ["clima", "temperatur", "pronostic", "meteorolog", "llov", "llueve", "solead"],
    "calendario": ["calendari", "agend", "evento", "reuni[oó]n", "cita", "compromis"],
    "entorno_activo": ["ventana", "programa", "abierto ahora", "en la pantalla", "herramienta", "proyecto actual", "este documento", "este archivo", "este otro archivo", "este doc", "el otro archivo", "el otro documento"],
    "rutinas": ["vamos a trabajar", "lleg[oó] pap[aá]", "empecemos", "modo hacker", "activa el protocolo", "prepara el entorno"],
    "entorno_iot": ["luz", "luces", "iluminaci", "foco", "tira"],
    "memoria_tecnica": ["recuerd", "bit[aá]cor", "documentaci[oó]n", "c[oó]mo resolv", "incidente", "segundo cerebro", "apunte", "solucionam"],
}

_EXCLUSIONES = {
    "abrir_app": ["abril", "abriles", "abrigo", "abrigos", "abrigad[oa]s?", "abrazo", "abrazos", "abrupt[oa]s?", "inicial", "iniciales", "iniciativ[a]s?", "ejecutiv[oa]s?", "cargador", "cargadores", "cargamento", "cargamentos", "levantamiento", "levantamientos", "montaña", "montañas", "montaje", "montajes"],
    "estado_pc": ["procesion", "procesiones", "procesional", "procesión", "procesiones"],
    "codigo": ["mejoramiento", "mejoramientos", "rendimiento"],
    "clima": ["temperamento", "temperamentos", "temperamental"],
}

PATRONES_CLAVE = {
    clave: _construir_patron(raices, _EXCLUSIONES.get(clave))
    for clave, raices in _RAICES.items()
}

PATRONES_CLAVE["estado_pc"] = re.compile(
    PATRONES_CLAVE["estado_pc"].pattern
    + r'|\b(estado|rendimiento|consumo|diagn[oó]stico)\s+(del?\s+|de\s+la\s+|mi\s+|de\s+mi\s+)?(pc|sistema|compu|cpu|ram|memoria|máquina|laptop)\b|\b(cpu|ram|bater[ií]a|llama-server)\b',
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
        r'\bas[ií]\s+no\b', r'\bno\s+quer[ií]a\s+eso\b', r'\barruinaste\b', r'\bmal\b',
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

    return intenciones