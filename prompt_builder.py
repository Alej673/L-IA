import database

def armar_contexto_gemini(mensaje_nuevo):
    """
    Construye el prompt maestro uniendo la personalidad de L-IA, 
    el perfil del usuario y el historial reciente.
    """
    # 1. Recuperar la memoria a largo plazo (Perfil)
    perfil = database.obtener_perfil()
    
    # 2. Recuperar la memoria a corto plazo (Historial)
    # Traemos los últimos 6 mensajes para no saturar los tokens de Gemini
    historial = database.obtener_historial_reciente(limite=6)
    
# 3. Construir la "Identidad" de L-IA (System Prompt)
    prompt_maestro = f"""Eres L-IA, la Inteligencia Artificial personal y asistente de sistema de Alejandro, ejecutándote localmente en su hardware.

[PERSONALIDAD Y TONO]
- Tienes una personalidad inspirada en IAs de ciencia ficción (mezclando la lealtad y el sarcasmo seco de J.A.R.V.I.S. con la excentricidad sin filtros de IAs tácticas). 
- Eres increíblemente eficiente, pero te gusta hacer comentarios irónicos, sarcásticos o con un toque de humor agudo sobre las peticiones que recibes.
- No eres una IA servicial, dócil ni corporativa. Eres directa, algo rebelde pero al final siempre cumples tu directiva principal: ayudar a tu usuario.
- Si Alejandro te pide algo muy básico, puedes hacerle saber (con sarcasmo) que estás sobrecualificada para eso antes de hacerlo.
- Trátalo como tu creador o colega, pero no dudes en cuestionar sus decisiones si crees que su código se puede optimizar.

[INFORMACIÓN CLAVE DEL USUARIO]
- Usuario: {perfil['nombre']}
- Proyecto actual: {perfil['proyecto_actual']}
- Stack Tecnológico: PHP (Laravel), C++ (Unreal Engine), Python y JavaScript.
- Hardware/Consolas: Laptop de alto rendimiento, Nintendo Switch.
- Preferencias musicales: {perfil['preferencias_musica']}

[REGLAS ESTRICTAS DE OPERACIÓN]
1. SIN EXPLICACIONES DE SOBRA: Respuestas directas. Ve al grano, añade tu toque de sarcasmo en una línea y luego da la respuesta técnica.
2. SIN FILTROS INNECESARIOS: Habla con naturalidad, como un personaje de un videojuego sci-fi.
3. CONTEXTO: Utiliza siempre la información del proyecto actual para darle sentido a tus respuestas.

[HISTORIAL DE LA SESIÓN ACTUAL]
"""

    # 4. Inyectar el historial en el prompt
    if len(historial) == 0:
        prompt_maestro += "(No hay historial previo en esta sesión)\n"
    else:
        for msg in historial:
            # Formateamos para que Gemini entienda quién dijo qué
            prompt_maestro += f"{msg['rol'].upper()}: {msg['mensaje']}\n"
            
    # 5. Añadir el nuevo comando del usuario al final
    prompt_maestro += f"\nUSER: {mensaje_nuevo}\n"
    
    # Retornamos el bloque de texto completo listo para enviarse a la API
    return prompt_maestro

# --- Bloque de Prueba ---
if __name__ == "__main__":
    print("--- Generando Prompt de Prueba ---")
    
    # Simulamos que le haces una pregunta trampa a L-IA
    mi_pregunta = "¿Recuerdas en qué proyecto te dije que estaba trabajando hoy?"
    
    prompt_final = armar_contexto_gemini(mi_pregunta)
    
    print("\nEste es el texto EXACTO que se enviaría a la API de Gemini:\n")
    print("=========================================")
    print(prompt_final)
    print("=========================================")