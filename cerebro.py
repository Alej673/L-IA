import os
from dotenv import load_dotenv
from google import genai

# 1. Cargar variables de entorno
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("¡Error! No se encontró la variable GEMINI_API_KEY en el archivo .env")

# 2. Inicializar el cliente con la nueva librería
print("Inicializando el cerebro de la IA con la nueva SDK...")
client = genai.Client(api_key=api_key)

# 3. Realizar la consulta
try:
    print("Enviando mensaje de prueba a Gemini...")
    
    # Usamos gemini-2.5-flash garantizando compatibilidad con la nueva API
    response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents='Hola Gemini, estoy programando un asistente de escritorio en Python desde cero. ¿Puedes escucharme?'
    )
    
    print("\n=== RESPUESTA DEL ASISTENTE ===")
    print(response.text)
    print("================================\n")

except Exception as e:
    print(f"\nOcurrió un error en la conexión: {e}")