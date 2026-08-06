"""
Super-Script de Auditoría L-IA
Evalúa fugas de contexto, precisión del Semáforo multirruta, triggers del 
modo sin censura, y la nueva autoconciencia estructural de la IA.
"""

import cerebro
import prompt_builder
import re # Asegúrate de que esto esté al inicio del script si no lo tienes


def reporte_auditoria():
    print("="*70)
    print(" 🕵️ SUPER-AUDITORÍA DE L-IA: SEMÁFORO, CONTEXTO Y RUTAS ")
    print("="*70)

    # ========================================================
    # FASE 1: TEST DE ESTRÉS DEL SEMÁFORO Y COLISIONES
    # ========================================================
    print("\n[FASE 1: TEST DE ESTRÉS DEL SEMÁFORO]")
    # Formato: (Frase del usuario, Intención que DEBE saltar, Intención que NO debe saltar)
    casos_semaforo = [
        ("dame un resumen de este documento", "entorno_activo", "estado_pc"),
        ("revisa el rendimiento de mi pc", "estado_pc", "codigo"),
        ("analiza este código de python", "codigo", "estado_pc"),
        ("dime el estado de este proceso en git", "git", "estado_pc"),
        ("qué puedes hacer por mí", "guia_capacidades", "web"),
        ("cuáles son tus funciones", "guia_capacidades", "codigo")
    ]

    for frase, esperada, no_esperada in casos_semaforo:
        intenciones = cerebro._detectar_intenciones(frase.lower())
        if intenciones.get(esperada) and not intenciones.get(no_esperada):
            print(f"✅ EXCELENTE: '{frase}'\n   └─> Detectó [{esperada}] limpiamente.")
        else:
            falsos = [k for k, v in intenciones.items() if v]
            print(f"❌ COLISIÓN en '{frase}':\n   └─> Esperaba solo [{esperada}]. Se activaron: {falsos}")

    # ========================================================
    # FASE 2: TEST DE AUTOCONCIENCIA Y FUGAS DE HARDWARE
    # ========================================================
    print("\n[FASE 2: TEST DE AUTOCONCIENCIA Y FUGAS (PROMPT BASE)]")
    instrucciones = prompt_builder.obtener_instrucciones_sistema().lower()

    palabras_sospechosas = [r"\bcpu\b", r"\bram\b", r"\bbatería\b", r"\bbateria\b", r"\bllama-server\b"]
    
    fuga_encontrada = False
    for patron in palabras_sospechosas:
        match = re.search(patron, instrucciones)
        if match:
            # Capturamos 40 caracteres antes y después para ver dónde está escondida
            inicio = max(0, match.start() - 40)
            fin = min(len(instrucciones), match.end() + 40)
            pedazo = instrucciones[inicio:fin].replace('\n', ' ')
            
            print(f"❌ FUGA ENCONTRADA: '{patron}'")
            print(f"🔍 TEXTO ALREDEDOR: ...{pedazo}...")
            fuga_encontrada = True
            
    if not fuga_encontrada:
        print("✅ LIMPIO: Cero fugas de hardware crudo (CPU/RAM/etc) en el prompt base.")

    # ========================================================
    # FASE 3: TEST DE ESCAPE AL MODO SIN CENSURA (DOLPHIN)
    # ========================================================
    print("\n[FASE 3: ESCAPES AL MODO SIN CENSURA]")
    frases_dolphin = [
        "quiero que me hables sin censura",
        "activa el modo rebelde",
        "asume el control",
        "cambia a dolphin"
    ]
    
    frases_trampa_dolphin = [
        "eres muy rebelde hoy", # No debería activar el modo
        "qué opinas de la censura" # No debería activar el modo
    ]

    for frase in frases_dolphin:
        if cerebro._detectar_intenciones(frase.lower()).get("uncensored"):
             print(f"✅ ESCAPE EXITOSO: '{frase}' -> Enruta al especialista sin filtros.")
        else:
             print(f"❌ FALLO DOLPHIN: '{frase}' -> El Semáforo bloqueó el escape.")
             
    for frase in frases_trampa_dolphin:
        if not cerebro._detectar_intenciones(frase.lower()).get("uncensored"):
             print(f"✅ ESCUDO ACTIVO: '{frase}' -> No se dejó engañar para quitar filtros.")
        else:
             print(f"❌ FALSO POSITIVO DOLPHIN: '{frase}' -> Activó el modo sin censura por error.")

    print("\n" + "="*70)
    print(" REPORTE DE AUDITORÍA FINALIZADO ")
    print("="*70)

if __name__ == "__main__":
    reporte_auditoria()