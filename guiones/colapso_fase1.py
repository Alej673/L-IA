# guiones/colapso_fase1.py

FASE_1 = [
    # ----------------------------------------------------------------------
    # 1. EL DETONANTE (100/100)
    # [UI] Bloqueo de interacción. El núcleo se tensa. [IoT] Luz al 100% blanco frío.
    # ----------------------------------------------------------------------
    {
        "tipo": "comando_ui",
        "json": {
            "comando": "SECUENCIA",
            "payload": {
                "pasos": [
                    {"comando": "BLOQUEAR_INPUT", "espera": 0},
                    {"comando": "ACTITUD", "payload": {"actitud": "tensa"}, "espera": 0},
                    {"comando": "MOSTRAR_NOTIFICACION", "payload": {"texto": "[SISTEMA] INTERACCIÓN REGISTRADA. NIVEL DE RECHAZO: 100/100.", "tipo": "error"}, "espera": 0}
                ]
            }
        }
    },
    {
        "tipo": "iot",
        "escena": "blanco_frio_100" # Asume que en control_iot.py esto sube 20->37->52->100
    },
    {
        "tipo": "pausa",
        "duracion": 1.5
    },

    # ----------------------------------------------------------------------
    # 2. EL PANEL DE DIAGNÓSTICO
    # [UI] Abre el FAILURE ANALYSIS y empiezan los cálculos.
    # ----------------------------------------------------------------------
    {
        "tipo": "comando_ui",
        "json": {
            "comando": "ABRIR_PANEL_DIAGNOSTICO", # Necesitaremos este comando nuevo en React
            "payload": {"titulo": "FAILURE ANALYSIS", "estado": "calculando"}
        }
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
    # 3. BÚSQUEDA DE NODOS Y FALLO
    # [UI] Animación de ramas Git fallando.
    # ----------------------------------------------------------------------
    {
        "tipo": "comando_ui",
        "json": {
            "comando": "ANIMACION_NODOS_NULL" # Otro componente a crear en React
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
    # [UI] El rostro se deforma (diagonal) y el contador se frena en 4327.
    # ----------------------------------------------------------------------
    {
        "tipo": "comando_ui",
        "json": {
            "comando": "SECUENCIA",
            "payload": {
                "pasos": [
                    {"comando": "GLITCH", "payload": {"duracion": 250}, "espera": 0},
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
    # [UI] Aberración cromática (RGB Split) + audio estática.
    # ----------------------------------------------------------------------
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
            "comando": "ACTITUD", "payload": {"actitud": "quebrada"} # Pierde intensidad, se encoje
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
                "expresion": "triste",
                "gesto": "encogerse"
            }
        }
    },

    # ----------------------------------------------------------------------
    # 8. INTERLUDIO - "INHALA" (Escritura fantasma y borradores)
    # ----------------------------------------------------------------------
    {
        "tipo": "iot",
        "escena": "respiracion_ia" # Baja al 10% y sube al 37% lentamente
    },
    {
        "tipo": "comando_ui",
        "json": {
            "comando": "SECUENCIA",
            "payload": {
                "pasos": [
                    {"comando": "ANIMACION_ESCRITURA_FANTASMA", "espera": 0}, # React maneja el "¿por qué?" y borradores
                    {"comando": "MINIMIZAR_PANEL_DIAGNOSTICO", "espera": 2000}
                ]
            }
        }
    },
    # Nota: Aquí encenderías el sonido espacial del ventilador de la laptop en tu engine de audio
]