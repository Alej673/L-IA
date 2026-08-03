"""
apis.py
--------
Integraciones externas de L-IA: hora, clima y calendario.

Diseño intencional: estas funciones NO usan function-calling del modelo.
En vez de eso, se resuelven de forma determinista en Python y su resultado
se inyecta como texto en el contexto de la conversación (mismo patrón que
_procesar_portapapeles / _procesar_archivo en cerebro.py). Esto es más
rápido, más confiable, y no le exige nada al modelo local: para cuando
Gemma 2 "ve" el mensaje, el dato ya está resuelto y solo tiene que
redactarlo con su personalidad.
"""

import os
from datetime import datetime, timedelta

import requests

# ==========================================
# 1. HORA
# ==========================================
DIAS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
            "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def obtener_hora_actual() -> str:
    """
    Devuelve la fecha y hora actuales del sistema, en español, sin depender
    de la configuración regional (locale) del sistema operativo -- por eso
    los nombres de día/mes están mapeados a mano arriba.
    """
    ahora = datetime.now()
    dia_semana = DIAS_ES[ahora.weekday()]
    mes = MESES_ES[ahora.month - 1]
    return (
        f"Son las {ahora.strftime('%H:%M')} del {dia_semana} {ahora.day} de {mes} de {ahora.year}."
    )


# ==========================================
# 2. CLIMA (Open-Meteo: gratis, sin API key)
# ==========================================
# Ciudad que se usa si el usuario no especifica ninguna en el mensaje.
# Cámbiala por tu ciudad, o defínela como variable de entorno CIUDAD_DEFECTO.
CIUDAD_DEFECTO = os.getenv("CIUDAD_DEFECTO", "Quito")

# Mapeo simplificado de los "weather codes" WMO que usa Open-Meteo
# (https://open-meteo.com/en/docs -> WMO Weather interpretation codes)
CODIGOS_CLIMA = {
    0: "cielo despejado", 1: "mayormente despejado", 2: "parcialmente nublado",
    3: "nublado", 45: "neblina", 48: "neblina con escarcha",
    51: "llovizna ligera", 53: "llovizna moderada", 55: "llovizna intensa",
    61: "lluvia ligera", 63: "lluvia moderada", 65: "lluvia intensa",
    71: "nevada ligera", 73: "nevada moderada", 75: "nevada intensa",
    80: "chubascos ligeros", 81: "chubascos moderados", 82: "chubascos violentos",
    95: "tormenta eléctrica", 96: "tormenta con granizo", 99: "tormenta con granizo intenso",
}


def obtener_clima(ciudad: str = None) -> str:
    """
    Consulta el clima actual de una ciudad usando Open-Meteo (sin API key).

    Proceso en 2 pasos, porque Open-Meteo separa geocodificación y clima:
      1. Geocoding API: convierte el nombre de la ciudad en lat/lon.
      2. Forecast API: pide el clima actual para esas coordenadas.
    """
    ciudad = (ciudad or CIUDAD_DEFECTO).strip()

    try:
        # 1. Geocodificación: nombre de ciudad -> coordenadas
        geo_resp = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": ciudad, "count": 1, "language": "es"},
            timeout=6,
        )
        geo_resp.raise_for_status()
        resultados = geo_resp.json().get("results")

        if not resultados:
            return f"No pude encontrar la ciudad '{ciudad}' para consultar el clima."

        lugar = resultados[0]
        lat, lon = lugar["latitude"], lugar["longitude"]
        nombre_encontrado = lugar.get("name", ciudad)
        pais = lugar.get("country", "")

        # 2. Clima actual para esas coordenadas
        clima_resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                "timezone": "auto",
            },
            timeout=6,
        )
        clima_resp.raise_for_status()
        actual = clima_resp.json().get("current", {})

        temperatura = actual.get("temperature_2m")
        humedad = actual.get("relative_humidity_2m")
        viento = actual.get("wind_speed_10m")
        codigo = actual.get("weather_code")
        descripcion = CODIGOS_CLIMA.get(codigo, "condición desconocida")

        return (
            f"Clima actual en {nombre_encontrado}, {pais}: {temperatura}°C, {descripcion}. "
            f"Humedad {humedad}%, viento {viento} km/h."
        )

    except requests.exceptions.RequestException as e:
        return f"Error de conexión al consultar el clima: {e}"
    except Exception as e:
        return f"Error inesperado al consultar el clima: {e}"


# ==========================================
# 3. CALENDARIO (Google Calendar API - gratis)
# ==========================================
# Requiere las librerías:
#   pip install google-auth-oauthlib google-api-python-client
#
# Requiere un archivo 'credentials.json' en la carpeta del proyecto
# (instrucciones de cómo obtenerlo, fuera de este archivo).
#
# La primera vez que se llama a obtener_eventos_calendario(), se abrirá
# el navegador para autorizar el acceso; después de eso, queda guardado
# un 'token.json' local y ya no se vuelve a pedir.
SCOPES_CALENDARIO = ["https://www.googleapis.com/auth/calendar.readonly"]
ARCHIVO_CREDENCIALES = "credentials.json"
ARCHIVO_TOKEN = "token.json"


def _obtener_credenciales_calendario():
    """Maneja el flujo OAuth de Google: reutiliza el token guardado o pide
    autorización por navegador si no existe o venció."""
    # Imports diferidos: así el resto de apis.py (hora, clima) funciona
    # aunque estas librerías todavía no estén instaladas.
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if os.path.exists(ARCHIVO_TOKEN):
        creds = Credentials.from_authorized_user_file(ARCHIVO_TOKEN, SCOPES_CALENDARIO)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(ARCHIVO_CREDENCIALES):
                raise FileNotFoundError(
                    f"Falta '{ARCHIVO_CREDENCIALES}'. Sigue los pasos de configuración "
                    f"de Google Calendar antes de usar esta función."
                )
            flow = InstalledAppFlow.from_client_secrets_file(ARCHIVO_CREDENCIALES, SCOPES_CALENDARIO)
            creds = flow.run_local_server(port=0)

        # Guardamos el token para no tener que re-autorizar cada vez
        with open(ARCHIVO_TOKEN, "w") as token_file:
            token_file.write(creds.to_json())

    return creds


def obtener_eventos_calendario(dias: int = 1) -> str:
    """
    Devuelve los próximos eventos del calendario principal de Google
    dentro de los próximos `dias` días (por defecto: hoy).
    """
    try:
        from googleapiclient.discovery import build

        creds = _obtener_credenciales_calendario()
        servicio = build("calendar", "v3", credentials=creds)

        ahora = datetime.utcnow().isoformat() + "Z"
        limite = (datetime.utcnow() + timedelta(days=dias)).isoformat() + "Z"

        resultado = servicio.events().list(
            calendarId="primary",
            timeMin=ahora,
            timeMax=limite,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        eventos = resultado.get("items", [])
        if not eventos:
            return f"No hay eventos programados en las próximas {dias * 24} horas."

        lineas = []
        for evento in eventos:
            inicio = evento["start"].get("dateTime", evento["start"].get("date"))
            titulo = evento.get("summary", "(Sin título)")
            lineas.append(f"- {titulo} · {inicio}")

        return "Próximos eventos:\n" + "\n".join(lineas)

    except ImportError:
        return (
            "Error: faltan librerías de Google Calendar. Ejecuta en la terminal: "
            "pip install google-auth-oauthlib google-api-python-client"
        )
    except FileNotFoundError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error al consultar el calendario: {e}"