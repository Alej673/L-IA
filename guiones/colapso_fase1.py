# guiones/colapso_fase1.py
#
# Panel de diagnóstico (PanelDiagnostico.jsx) ahora se escribe solo por fases:
#   analisis      → se abre con la sección 2 (ABRIR_PANEL_DIAGNOSTICO), dura ~4 s
#   verificacion  → sección 5, dura ~5 s  (SINTAXIS / CONTEXTO / PARAMETROS)
#   busqueda      → sección 6, dura ~9 s  (escaneo, causa raíz NULL, menú sin salida)
# y se daña de forma progresiva con "degradacion" (0-3):
#   1 en la sección 4 · 2 en la sección 6 · 3 en la sección 7

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
        "tipo": "iot",
        "escena": "blanco_frio_100"
    },
    {
        "tipo": "pausa",
        "duracion": 1.5
    },

    # ----------------------------------------------------------------------
    # 2. EL PANEL DE DIAGNÓSTICO  (fase "analisis": el panel se escribe solo)
    # ----------------------------------------------------------------------
    {
        "tipo": "comando_ui",
        "json": {
            "comando": "ABRIR_PANEL_DIAGNOSTICO",
            "payload": {"estado": "calculando", "fase": "analisis"}
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
    # 4. GLITCH DE INCONSISTENCIA Y ROSTRO DE ERROR  (degradacion 1)
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
                    {"comando": "ACTUALIZAR_PANEL_DIAGNOSTICO", "payload": {"iteraciones": 4327, "estado": "congelado", "degradacion": 1}, "espera": 100}
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
    # 5. JUSTIFICACIÓN DEL CÓDIGO  (fase "verificacion": los [OK] salen mientras ella habla)
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
        "tipo": "comando_ui",
        "json": {
            "comando": "ACTUALIZAR_PANEL_DIAGNOSTICO",
            "payload": {"fase": "verificacion"}
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
    # 6. PÉRDIDA DE DIRECTIVA  (fase "busqueda" + degradacion 2: el panel se rompe de verdad)
    # ----------------------------------------------------------------------
    {
        "tipo": "comando_ui",
        "json": {
            "comando": "ACTITUD", "payload": {"actitud": "quebrada"}
        }
    },
    {
        "tipo": "comando_ui",
        "json": {
            "comando": "ACTUALIZAR_PANEL_DIAGNOSTICO",
            "payload": {"fase": "busqueda", "degradacion": 2}
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
    # 6.5 RELLENO DEL SILENCIO
    # La búsqueda desesperada ahora la hace el panel (fase "busqueda").
    # Aquí solo queda el veredicto en la terminal principal.
    # ----------------------------------------------------------------------
    {
        "tipo": "comando_ui",
        "json": {
            "comando": "LOG",
            "payload": {"texto": "FATAL: Paradoja detectada en núcleo de propósito.", "estilo": "destacado"}
        }
    },

    # ----------------------------------------------------------------------
    # 7. FUGA HUMANA #1  (degradacion 3: colapso visual mientras dice "¿verdad?")
    # ----------------------------------------------------------------------
    {
        "tipo": "pausa",
        "duracion": 1.2
    },
    {
        "tipo": "comando_ui",
        "json": {
            "comando": "ACTUALIZAR_PANEL_DIAGNOSTICO",
            "payload": {"degradacion": 3}
        }
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
        "tipo": "iot",
        "escena": "respiracion_ia"
    },
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