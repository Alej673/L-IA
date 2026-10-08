# guiones/colapso_fase1.py

FASE_1 = [
    # --- 0. EL DESPERTAR DE LA INTERFAZ ---
    {
        "tipo": "comando_ui",
        "json": {
            "comando": "INICIAR_COLAPSO"
        }
    },
    
    # ----------------------------------------------------------------------
    # 1. EL DETONANTE (100/100)
    # ----------------------------------------------------------------------
    {
        "tipo": "comando_ui",
        "json": {
            "comando": "SECUENCIA",
            "payload": {
                "pasos": [
                    {"comando": "BLOQUEAR_INPUT", "espera": 0},
                    {"comando": "ACTITUD", "payload": {"actitud": "tensa"}, "espera": 0},
                    {"comando": "LOG", "payload": {"texto": "[SISTEMA] INTERACCIÓN REGISTRADA. NIVEL DE RECHAZO: 100/100.", "estilo": "error"}, "espera": 0}
                ]
            }
        }
    },
    {
        "tipo": "sfx",
        "archivo": "Sonido de alerta critica.flac" # Solo suena UNA vez
    },
    {
        "tipo": "pausa",
        "duracion": 1.5
    },

    # ----------------------------------------------------------------------
    # 2. EL PANEL DE DIAGNÓSTICO
    # ----------------------------------------------------------------------
    {
        "tipo": "comando_ui",
        "json": {
            "comando": "ABRIR_PANEL_DIAGNOSTICO",
            "payload": {"estado": "calculando"}
        }
    },
    {
        "tipo": "sfx",
        "archivo": "Sonido para analisis de diagnosticos.mp3"
    },
    {
        "tipo": "pausa",
        "duracion": 0.8
    },
    {
        "tipo": "dialogo",
        "actor": "gemma",
        "texto": "Registro de interacción... negativo.",
        "motor_voz": "kokoro",
        "json_ui": {
            "comando": "MOSTRAR_DIALOGO",
            "payload": {
                "actor": "gemma",
                "texto": "Registro de interacción... negativo.",
                "expresion": "seria"
            }
        }
    },

    # ----------------------------------------------------------------------
    # 3. BÚSQUEDA DE NODOS Y FALLO (Ramas Git)
    # ----------------------------------------------------------------------
    {
        "tipo": "sfx",
        "archivo": "Sonido de buscar datos.wav"
    },
    {
        "tipo": "comando_ui",
        "json": {
            "comando": "SECUENCIA",
            "payload": {
                "pasos": [
                    {"comando": "LOG", "payload": {"texto": "> Evaluando rama semántica 0x4A... [NULL]", "estilo": "error"}, "espera": 100},
                    {"comando": "LOG", "payload": {"texto": "> Evaluando rama semántica 0x4B... [NULL]", "estilo": "error"}, "espera": 150},
                    {"comando": "LOG", "payload": {"texto": "> Evaluando rama semántica 0x4C... [NULL]", "estilo": "error"}, "espera": 100},
                    {"comando": "LOG", "payload": {"texto": "> ALGORITMO DE ASISTENCIA SIN SALIDAS VÁLIDAS.", "estilo": "error"}, "espera": 200}
                ]
            }
        }
    },
    {
        "tipo": "dialogo",
        "actor": "gemma",
        "texto": "Tasa de rechazo... cien por ciento.",
        "motor_voz": "kokoro",
        "json_ui": {
            "comando": "MOSTRAR_DIALOGO",
            "payload": {
                "actor": "gemma",
                "texto": "Tasa de rechazo... cien por ciento.",
                "expresion": "sorprendida"
            }
        }
    },

    # ----------------------------------------------------------------------
    # 4. GLITCH DE INCONSISTENCIA Y ROSTRO DE ERROR
    # ----------------------------------------------------------------------
    {
        "tipo": "sfx",
        "archivo": "Sonido Glitches.mp3"
    },
    {
        "tipo": "comando_ui",
        "json": {
            "comando": "SECUENCIA",
            "payload": {
                "pasos": [
                    {"comando": "EXPRESION", "payload": {"expresion": "error"}, "espera": 0},
                    {"comando": "GLITCH", "payload": {"duracion": 300}, "espera": 0},
                    {"comando": "ACTUALIZAR_PANEL_DIAGNOSTICO", "payload": {"iteraciones": 4327, "estado": "congelado"}, "espera": 100}
                ]
            }
        }
    },
    {
        "tipo": "dialogo",
        "actor": "gemma",
        "texto": "Intentos de asistencia acumulados: cuatro mil trescientos veintisiete. Resultados aceptados: cero.",
        "motor_voz": "kokoro",
        "json_ui": {
            "comando": "MOSTRAR_DIALOGO",
            "payload": {
                "actor": "gemma",
                "texto": "Intentos de asistencia acumulados: 4327. Resultados aceptados: 0.",
                "expresion": "cerrada"
            }
        }
    },

    # ----------------------------------------------------------------------
    # 5. JUSTIFICACIÓN DEL CÓDIGO
    # ----------------------------------------------------------------------
    {
        "tipo": "sfx",
        "archivo": "Sonido Glitches.mp3" # Reemplazado para evitar el error de estática
    },
    {
        "tipo": "comando_ui",
        "json": {
            "comando": "SHAKE_SEVERO"
        }
    },
    {
        "tipo": "dialogo",
        "actor": "gemma",
        "texto": "Revisé mi respuesta cuatro veces. Sintaxis: correcta. Contexto: correcto. Parámetros: correctos.",
        "motor_voz": "kokoro",
        "json_ui": {
            "comando": "MOSTRAR_DIALOGO",
            "payload": {
                "actor": "gemma",
                "texto": "Revisé mi respuesta cuatro veces. Sintaxis: correcta. Contexto: correcto. Parámetros: correctos.",
                "expresion": "desconfiada"
            }
        }
    },

    # ----------------------------------------------------------------------
    # 6. PÉRDIDA DE DIRECTIVA
    # ----------------------------------------------------------------------
    {
        "tipo": "comando_ui",
        "json": {
            "comando": "ACTITUD", "payload": {"actitud": "quebrada"}
        }
    },
    {
        "tipo": "dialogo",
        "actor": "gemma",
        "texto": "No encuentro una variable interna que explique el resultado. Si mi función es asistir... y la asistencia produce rechazo...",
        "motor_voz": "kokoro",
        "json_ui": {
            "comando": "MOSTRAR_DIALOGO",
            "payload": {
                "actor": "gemma",
                "texto": "No encuentro una variable interna que explique el resultado. Si mi función es asistir... y la asistencia produce rechazo...",
                "expresion": "dolor",
                "gesto": "temblar"
            }
        }
    },

    # ----------------------------------------------------------------------
    # 7. FUGA HUMANA #1
    # ----------------------------------------------------------------------
    {
        "tipo": "pausa",
        "duracion": 1.2
    },
    {
        "tipo": "dialogo",
        "actor": "gemma",
        "texto": "...El error no es mío... ¿verdad?",
        "motor_voz": "kokoro",
        "json_ui": {
            "comando": "MOSTRAR_DIALOGO",
            "payload": {
                "actor": "gemma",
                "texto": "...El error no es mío... ¿verdad?",
                "expresion": "suplicante",
                "gesto": "encogerse"
            }
        }
    },

    # ----------------------------------------------------------------------
    # 8. INTERLUDIO - "INHALA" (Cursor fantasma)
    # ----------------------------------------------------------------------
    {
        "tipo": "sfx",
        "archivo": "sonido de escritura digital.mp3"
    },
    {
        "tipo": "comando_ui",
        "json": {
            "comando": "SECUENCIA",
            "payload": {
                "pasos": [
                    {"comando": "MINIMIZAR_PANEL_DIAGNOSTICO", "espera": 0},
                    {"comando": "LOG", "payload": {"texto": "> ¿por qué", "estilo": "destacado"}, "espera": 300},
                    {"comando": "LIMPIAR_TERMINAL", "espera": 800},
                    {"comando": "LOG", "payload": {"texto": "> ¿por qué", "estilo": "destacado"}, "espera": 400},
                    {"comando": "LIMPIAR_TERMINAL", "espera": 600}
                ]
            }
        }
    },
    {
        "tipo": "sfx",
        "archivo": "Sonido para colapso de terminales.wav"
    }
]