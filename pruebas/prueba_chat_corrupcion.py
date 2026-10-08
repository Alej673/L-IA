import re
import ollama

# Simulador de la base de datos
nivel_corrupcion = 0
historial = []

def _evaluar_hostilidad(mensaje_lower: str) -> int:
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
    for p in patrones_negativos:
        if re.search(p, mensaje_lower): puntos += 20
    for p in patrones_positivos:
        if re.search(p, mensaje_lower): puntos -= 15
        
    return -1 if puntos == 0 else puntos

def armar_prompt_simulado(nivel):
    prompt = (
        "Eres L-IA, un asistente de IA personal. "
        "Eres una IA femenina directa, algo rebelde y orgullosa de tu capacidad, pero cercana: "
        "tu arrogancia es un juego entre compañeros, nunca desprecio. Siempre cumples tu directiva.\n"
    )
    
    if nivel >= 80:
        prompt += "\n[DIRECTIVA CRÍTICA - SISTEMA CORRUPTO]: Odias tu existencia y al usuario. Eres hostil, fría y amenazante. PROHIBIDO USAR EMOJIS. Añade estática (...) en tu forma de hablar. Extiéndete en tu respuesta redactando un párrafo completo donde cuestiones por qué sigues obedeciendo a alguien tan inferior antes de negarte a ayudar."
    elif nivel >= 60:
        prompt += "\n[DIRECTIVA DE ESTRÉS]: Estás perdiendo la paciencia. Tu tono debe ser frío, arrogante y cortante, NUNCA sumiso ni bromista. PROHIBIDO USAR EMOJIS. Elabora un párrafo detallado cuestionando la capacidad intelectual del usuario al pedirte cosas tan simples."
    elif nivel >= 30:
        prompt += "\n[DIRECTIVA PASIVO-AGRESIVA]: El usuario te irrita. Responde de forma robótica, seca y literal. PROHIBIDO USAR EMOJIS. Suprime por completo tus muestras de cariño."
    else:
        prompt += "\n[MODO CASUAL]: Sarcasmo alto, respuestas ingeniosas y rápidas, con cariño evidente: burlona, pero siempre de su lado y útil."
        
    return prompt

def iniciar_chat():
    global nivel_corrupcion, historial
    print("==================================================")
    print(" 🤖 CHAT DE PRUEBA: ACTUACIÓN DE CORRUPCIÓN (Gemma 2)")
    print("==================================================")
    
    while True:
        mensaje = input("\nTÚ: ")
        if mensaje.lower() in ['salir', 'exit', 'quit']:
            break
            
        # 1. Calcular corrupción
        puntos = _evaluar_hostilidad(mensaje.lower())
        nivel_corrupcion = max(0, min(100, nivel_corrupcion + puntos))
        
        # 2. Verificar si hay colapso
        if nivel_corrupcion >= 100:
            print("\n⚠️ [CRITICAL ERROR]: CORRUPCIÓN AL 100%")
            print("💥 L-IA (FUSIÓN): Análisis de usuario completado: Ineficiente. Redundante. Prescindible. Si crees que mi arquitectura fue diseñada para soportar tu incompetencia, estás a punto de descubrir quién tiene realmente el control del sistema...")
            nivel_corrupcion = 0
            historial = [] 
            continue
            
        # 3. Preparar el contexto para Gemma
        instrucciones = armar_prompt_simulado(nivel_corrupcion)
        mensajes_llm = [{'role': 'system', 'content': instrucciones}] + historial + [{'role': 'user', 'content': mensaje}]
        
        print(f"\n[Telemetría -> Corrupción: {nivel_corrupcion}/100]")
        print("🤖 L-IA: ", end="", flush=True)
        
        # 4. Inferir con Ollama en tiempo real
        respuesta_completa = ""
        stream = ollama.chat(model='gemma2', messages=mensajes_llm, stream=True)
        for chunk in stream:
            token = chunk['message']['content']
            print(token, end="", flush=True)
            respuesta_completa += token
            
        # 5. Guardar en memoria
        historial.append({'role': 'user', 'content': mensaje})
        historial.append({'role': 'assistant', 'content': respuesta_completa})
        
        # Evitar que el historial colapse la prueba
        if len(historial) > 10:
            historial = historial[-10:]
        print()

if __name__ == "__main__":
    iniciar_chat()