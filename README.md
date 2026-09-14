# L-IA: Asistente Híbrido de Inteligencia Artificial (Local/Nube)

Asistente personal interactivo con arquitectura híbrida que combina modelos de lenguaje locales y en la nube. Optimiza el uso de hardware local y cuotas de API mediante un enrutador inteligente, operando principalmente con procesamiento local y delegando tareas masivas de forma dinámica.

[![Estado](https://img.shields.io/badge/estado-funcional-4ade80)](https://github.com/Alej673/L-IA)
[![Versión](https://img.shields.io/badge/versi%C3%B3n-3.2.0-00f2fe)](https://github.com/Alej673/L-IA)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)

---

## Contexto y reto de desarrollo

El objetivo fue desarrollar un asistente avanzado capaz de operar dentro de las restricciones de hardware de una GPU RTX 4050 con 6 GB de VRAM. Se requería una herramienta que pudiera interactuar con el sistema operativo, analizar código fuente, leer el estado del repositorio y automatizar tareas, manteniendo la seguridad de la máquina y evitando latencias excesivas en las respuestas.

**Solución:** una arquitectura donde el LLM decide la intención de la tarea, pero un motor interno en Python controla los permisos y la ejecución. El sistema conmuta entre modelos ligeros y pesados evaluando el peso del contexto, logrando respuestas fluidas sin saturar la memoria de video.

---

## Stack tecnológico

- **Modelos de lenguaje (LLM):** Gemma 2 9B y Dolphin-Mistral 7B (ejecución local vía Ollama), Gemini Pro y Gemini Flash (nube).
- **Memoria vectorial (RAG):** ChromaDB con modelo de embeddings `all-MiniLM-L6-v2`, ejecutado 100% en CPU para preservar la VRAM.
- **Procesamiento de voz:** Edge-TTS (síntesis fluida), Vosk (centinela *wake word*), faster-whisper (transcripción STT).
- **Base de datos y memoria:** SQLite (perfil, historial, herramientas activas, workspace).
- **Interfaz gráfica:** Tkinter con `queue.Queue` (thread-safe) para streaming de tokens sin bloqueos.
- **Automatización de entorno:** pygetwindow (ventanas activas), difflib (búsqueda difusa), pygame (feedback acústico asíncrono).

---

## Decisiones arquitectónicas clave

### Semáforo v3 (enrutamiento inteligente)
Motor de decisión dinámico que cruza conteo de tokens estimados, detección de intenciones mediante expresiones regulares (con *fuzzy matching* vía rapidfuzz) y contexto de la tarea. Tareas de código ligeras se resuelven en local; cargas masivas (superiores al umbral de 30,000 tokens) se derivan automáticamente a Gemini.

### Tool Manager (cortafuegos de seguridad)
Capa de permisos jerárquica con niveles (0, 1, 2) que intercepta toda ejecución de funciones solicitadas por los LLMs. Las acciones destructivas (Nivel 2, como purgas de archivos o `git commit` / `push`) se suspenden hasta que el usuario aprueba la ejecución mediante un popup asíncrono en la interfaz gráfica.

### Workspace Activo (caché contextual)
Sistema que resuelve la "amnesia post-lectura" mediante la detección de la ventana activa en Windows. El asistente lee el archivo en foco, genera en segundo plano un micro-resumen y lo inyecta en el *prompt* del sistema, permitiendo preguntas de seguimiento de bajísimo consumo (30-50 tokens).

### Segundo Cerebro (RAG local)
Implementación de memoria a largo plazo con aislamiento de recursos: la vectorización de la documentación técnica se ejecuta 100% en CPU para preservar la VRAM exclusivamente para el LLM, permitiendo consultas históricas exactas y sin alucinaciones.

### Hot-Swap de modelos y control de VRAM
Capacidad de descargar un modelo y montar otro bajo demanda usando `keep_alive=0` en Ollama. Intercambio de VRAM en ~12 segundos, habilitando la alternancia dinámica entre modelos especializados según la tarea.

---

## Módulos principales

| Módulo | Responsabilidad |
|--------|-----------------|
| **Segundo Cerebro (RAG)** | Indexa y recupera fragmentos de documentación técnica de forma semántica, inyectándolos con un "bozal de consulta" estricto para evitar alucinaciones. |
| **Control de versiones** | Ejecuta flujos completos de Git (`add`, `commit`, `push`) evaluando el diferencial de código y delegando la redacción técnica del commit al LLM. |
| **Escucha híbrida y TTS** | Canal de entrada/salida acústico continuo con detección pasiva y transcripción, usando streaming asíncrono de voz para reducir la latencia percibida. |
| **Conciencia de entorno** | Detección de la ventana de código o documento activo en Windows, extrayendo silenciosamente el contexto para asistir sin la fricción de copiar y pegar. |

---

## Capturas

| Interfaz principal | Streaming y respuesta |
|:---:|:---:|
| ![Interfaz principal de L-IA](Interfaz_LIA.png) | ![Streaming de respuesta](Streaming_LIA.png) |

| Configuración de modelos | Workspace activo |
|:---:|:---:|
| ![Configuración de modelos](Modelos_LIA.png) | ![Workspace activo](Workspace_LIA.png) |

---

## Estado del proyecto

- **Versión actual:** v3.2.0
- **Estado:** Funcional (rama principal estable y cerrada para exhibición técnica).
- **Fases completadas:**
  - Fase 3: Autoconciencia y base de datos (SQLite)
  - Fase 4: Enrutador inteligente (Semáforo v3) y Tool Manager
  - Fase 5: Módulo híbrido de voz (STT/TTS)
  - Fase 6: Memoria vectorial y RAG en CPU (ChromaDB)
  - Fase 7: Conciencia de entorno (Workspace activo)
- **Documentación:** bitácora técnica completa y caso de estudio web disponible.

---

## Instalación local

```bash
# 1. Clonar el repositorio
git clone https://github.com/Alej673/L-IA.git
cd L-IA

# 2. Configurar entorno virtual y dependencias
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Configurar variables de entorno (API Keys para servicios en la nube)
cp .env.example .env
# editar .env con las claves de Gemini u otros servicios

# 4. Iniciar la interfaz gráfica
python launcher.py
```

---

## Enlaces y recursos

- 💻 **Repositorio de código:** [github.com/Alej673/L-IA](https://github.com/Alej673/L-IA)
- 🎥 **Video demostración:** [Ver en YouTube](https://youtu.be/z0cT4v-rG7E)
- 📝 **Caso de estudio (portafolio):** [Análisis técnico y arquitectura](https://alej673.github.io/proyecto-LIA.html)

---

**Autor:** Alejandro Larco
[GitHub](https://github.com/Alej673) · [LinkedIn](https://www.linkedin.com/in/alejandro-larco-03297b42a/) · [Portafolio](https://alej673.github.io/proyecto-LIA.html)

*Proyecto de desarrollo personal — Arquitectura de asistentes híbridos.*
