import keyboard
import tkinter as tk
import threading
import time
import re
import pystray
from PIL import Image, ImageDraw
import sys
import cerebro
import database

# ==========================================
# TEMA / PALETA DE COLORES (Catppuccin Mocha)
# Centralizado acá para no repetir hex codes por todo el archivo.
# ==========================================
class Tema:
    BG = "#11111b"
    BG_SURFACE = "#1e1e2e"
    BG_INPUT = "#313244"
    BORDE = "#45475a"

    TEXTO = "#cdd6f4"
    TEXTO_SUAVE = "#a6adc8"

    ACCENT_USER = "#89b4fa"      # Azul (tú)
    ACCENT_LIA = "#a6e3a1"       # Verde (L-IA)
    ACCENT_ERROR = "#f38ba8"     # Rojo
    ACCENT_WARN = "#f9e2af"      # Amarillo

    FUENTE = ("Consolas", 11)
    FUENTE_BOLD = ("Consolas", 11, "bold")
    FUENTE_TITULO = ("Consolas", 10, "bold")
    FUENTE_CHICA = ("Consolas", 9)


# ==========================================
# LIMPIEZA DE RESPUESTA DEL MODELO
# ==========================================
# El modelo a veces ignora la regla "CERO ACOTACIONES ACTORALES" del
# prompt de sistema y mete su propio prefijo "L-IA:" al inicio de la
# respuesta, duplicando lo que ya muestra la burbuja del chat (que trae
# su propio remitente "🤖 L-IA (origen)"). Esto pasa igual en consola,
# no es exclusivo del launcher -- pero acá lo limpiamos antes de
# mostrarlo para que la burbuja quede consistente.
_PATRON_PREFIJO_LIA = re.compile(r'^\s*L-?IA\s*:\s*', re.IGNORECASE)


def _limpiar_respuesta_ia(texto: str) -> str:
    return _PATRON_PREFIJO_LIA.sub('', texto, count=1).strip()


class InterfazLIA:
    def __init__(self):
        # 1. Configuración de la Ventana
        self.root = tk.Tk()
        self.root.title("L-IA Asistente")
        self.ANCHO, self.ALTO = 650, 470
        self.root.geometry(f"{self.ANCHO}x{self.ALTO}")
        self.root.configure(bg=Tema.BG)

        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.centrar_ventana()

        # Contenedor con borde sutil para que la ventana no se sienta "flotando en la nada"
        self.contenedor = tk.Frame(self.root, bg=Tema.BORDE, bd=0)
        self.contenedor.pack(fill=tk.BOTH, expand=True)

        self.frame = tk.Frame(self.contenedor, bg=Tema.BG)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=(0, 1))

        self._construir_barra_titulo()
        # OJO CON EL ORDEN: pack() reserva espacio en el orden en que se
        # agregan los widgets, sin importar el 'side'. Si el chat (con
        # expand=True) se empaqueta primero, se come TODO el espacio
        # disponible y el input queda con altura cero. Por eso el input
        # se construye antes que el chat.
        self._construir_input()
        self._construir_area_chat()

        # Tags de texto usados para dar formato a las burbujas del chat
        self._configurar_tags_chat()

        self.chat_area.config(state=tk.NORMAL)
        self.chat_area.insert(tk.END, "🤖 L-IA en línea. Presiona ESC para ocultarme.\n\n")
        self.chat_area.config(state=tk.DISABLED)

        # Eventos globales
        self.root.bind("<Escape>", self.ocultar_ventana)

        # Ventana totalmente opaca (nada de fades con -alpha: en Windows,
        # combinado con overrideredirect, provoca el bug del "fantasma" en
        # zonas que no alcanzaron a pintarse). Escondemos con withdraw(),
        # que sencillamente desmapea la ventana del todo — sin bitmaps
        # cacheados, sin transparencia, sin sorpresas.
        self.root.attributes('-alpha', 1.0)
        self.root.update_idletasks()
        self.root.withdraw()
        self.visible = False
        self._animando = False

    # ==========================================
    # CONSTRUCCIÓN DE LA UI
    # ==========================================
    def _construir_barra_titulo(self):
        """Barra de título custom: como usamos overrideredirect (sin marco nativo
        de Windows), sin esto la ventana no se podría arrastrar ni cerrar."""
        self.barra_titulo = tk.Frame(self.frame, bg=Tema.BG_SURFACE, height=34)
        self.barra_titulo.pack(side=tk.TOP, fill=tk.X)
        self.barra_titulo.pack_propagate(False)

        self.status_dot = tk.Label(
            self.barra_titulo, text="●", bg=Tema.BG_SURFACE, fg=Tema.ACCENT_LIA,
            font=("Consolas", 12)
        )
        self.status_dot.pack(side=tk.LEFT, padx=(12, 4))

        tk.Label(
            self.barra_titulo, text="L-IA Asistente Híbrido", bg=Tema.BG_SURFACE,
            fg=Tema.TEXTO, font=Tema.FUENTE_TITULO
        ).pack(side=tk.LEFT)

        tk.Label(
            self.barra_titulo, text="Ctrl+Alt+J para mostrar/ocultar", bg=Tema.BG_SURFACE,
            fg=Tema.TEXTO_SUAVE, font=("Consolas", 8)
        ).pack(side=tk.LEFT, padx=12)

        btn_cerrar = tk.Label(
            self.barra_titulo, text="✕", bg=Tema.BG_SURFACE, fg=Tema.TEXTO_SUAVE,
            font=Tema.FUENTE_TITULO, cursor="hand2", padx=10
        )
        btn_cerrar.pack(side=tk.RIGHT, fill=tk.Y)
        btn_cerrar.bind("<Button-1>", self.ocultar_ventana)
        btn_cerrar.bind("<Enter>", lambda e: btn_cerrar.config(fg=Tema.ACCENT_ERROR))
        btn_cerrar.bind("<Leave>", lambda e: btn_cerrar.config(fg=Tema.TEXTO_SUAVE))

        # Arrastrar la ventana desde la barra de título
        self._drag_data = {"x": 0, "y": 0}
        for widget in (self.barra_titulo,):
            widget.bind("<ButtonPress-1>", self._iniciar_arrastre)
            widget.bind("<B1-Motion>", self._arrastrar_ventana)

    def _iniciar_arrastre(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _arrastrar_ventana(self, event):
        x = self.root.winfo_x() + (event.x - self._drag_data["x"])
        y = self.root.winfo_y() + (event.y - self._drag_data["y"])
        self.root.geometry(f"+{x}+{y}")

    def _construir_area_chat(self):
        chat_wrapper = tk.Frame(self.frame, bg=Tema.BG)
        chat_wrapper.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=16, pady=(12, 8))

        scrollbar = tk.Scrollbar(chat_wrapper, bg=Tema.BG_SURFACE, troughcolor=Tema.BG,
                                  bd=0, activebackground=Tema.BORDE)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.chat_area = tk.Text(
            chat_wrapper, bg=Tema.BG_SURFACE, fg=Tema.TEXTO, font=Tema.FUENTE,
            wrap=tk.WORD, bd=0, highlightthickness=0, padx=14, pady=12,
            yscrollcommand=scrollbar.set, state=tk.DISABLED, spacing3=6
        )
        self.chat_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.chat_area.yview)

    def _construir_input(self):
        input_wrapper = tk.Frame(self.frame, bg=Tema.BG)
        input_wrapper.pack(side=tk.BOTTOM, fill=tk.X, padx=16, pady=(0, 14))

        caja_input = tk.Frame(input_wrapper, bg=Tema.BG_INPUT)
        caja_input.pack(fill=tk.X)

        tk.Label(
            caja_input, text="›", bg=Tema.BG_INPUT, fg=Tema.ACCENT_LIA,
            font=Tema.FUENTE_BOLD
        ).pack(side=tk.LEFT, padx=(12, 0))

        self.input_field = tk.Entry(
            caja_input, bg=Tema.BG_INPUT, fg=Tema.TEXTO, font=Tema.FUENTE,
            insertbackground=Tema.ACCENT_LIA, bd=0, relief=tk.FLAT,
            # En Windows, si no fijamos esto a mano, Tk pinta el highlight de
            # foco/selección con el azul de sistema y tapa todo el campo.
            highlightthickness=0,
            highlightbackground=Tema.BG_INPUT,
            highlightcolor=Tema.BG_INPUT,
            selectbackground=Tema.ACCENT_USER,
            selectforeground=Tema.BG,
            disabledbackground=Tema.BG_INPUT,
            disabledforeground=Tema.TEXTO_SUAVE,
            readonlybackground=Tema.BG_INPUT,
        )
        self.input_field.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=12, padx=8)
        self.input_field.bind("<Return>", self.enviar_mensaje)

        # Placeholder simple: texto guía que desaparece al enfocar/escribir
        self._placeholder_texto = "Escribe un mensaje..."
        self._placeholder_activo = False
        self._mostrar_placeholder()
        self.input_field.bind("<FocusIn>", self._quitar_placeholder)
        self.input_field.bind("<FocusOut>", self._restaurar_placeholder_si_vacio)

    def _mostrar_placeholder(self):
        self.input_field.insert(0, self._placeholder_texto)
        self.input_field.config(fg=Tema.TEXTO_SUAVE)
        self._placeholder_activo = True

    def _quitar_placeholder(self, event=None):
        if self._placeholder_activo:
            self.input_field.delete(0, tk.END)
            self.input_field.config(fg=Tema.TEXTO)
            self._placeholder_activo = False

    def _restaurar_placeholder_si_vacio(self, event=None):
        if not self.input_field.get().strip():
            self._mostrar_placeholder()

    def _configurar_tags_chat(self):
        """Tags de formato para las 'burbujas' de texto. Reemplaza el insert()
        plano de antes: ahora cada remitente tiene su propio color/negrita,
        y además usamos tags con nombre único para poder borrar mensajes
        puntuales (como el 'pensando...') sin depender de contar líneas."""
        self.chat_area.tag_config("remitente_tu", foreground=Tema.ACCENT_USER, font=Tema.FUENTE_BOLD)
        self.chat_area.tag_config("remitente_lia", foreground=Tema.ACCENT_LIA, font=Tema.FUENTE_BOLD)
        self.chat_area.tag_config("remitente_error", foreground=Tema.ACCENT_ERROR, font=Tema.FUENTE_BOLD)
        self.chat_area.tag_config("cuerpo", foreground=Tema.TEXTO)
        self.chat_area.tag_config("cuerpo_suave", foreground=Tema.TEXTO_SUAVE, font=("Consolas", 10, "italic"))

    # ==========================================
    # POSICIÓN / VISIBILIDAD (con fade suave)
    # ==========================================
    def centrar_ventana(self):
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (self.ANCHO // 2)
        y = (self.root.winfo_screenheight() // 3) - (self.ALTO // 2)
        self.root.geometry(f'{self.ANCHO}x{self.ALTO}+{x}+{y}')

    def toggle_ventana(self):
        if self.visible:
            self.ocultar_ventana()
        else:
            self.mostrar_ventana()

    def _fade(self, objetivo, paso):
        """(Ya no se usa para mostrar/ocultar — ver mostrar_ventana/ocultar_ventana.
        Se deja por si en el futuro quieres un efecto puntual con -alpha en
        una ventana que NO tenga overrideredirect, donde no da problemas)."""
        actual = self.root.attributes('-alpha')
        nuevo = actual + paso
        terminado = (paso > 0 and nuevo >= objetivo) or (paso < 0 and nuevo <= objetivo)
        nuevo = objetivo if terminado else nuevo
        self.root.attributes('-alpha', nuevo)
        if not terminado:
            self.root.after(12, lambda: self._fade(objetivo, paso))

    def mostrar_ventana(self, event=None):
        self.visible = True
        self.root.deiconify()
        # En algunos builds de Windows, deiconify() puede resetear el
        # overrideredirect (apareceria un ícono en la barra de tareas).
        # Lo reafirmamos por las dudas.
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        # Le roba el foco a Windows a la fuerza (arregla el bug del teclado)
        self.root.focus_force()
        self.input_field.focus_set()

    def ocultar_ventana(self, event=None):
        self.visible = False
        self.root.withdraw()

    # ==========================================
    # UTILIDADES DE CHAT
    # ==========================================
    def agregar_texto(self, remitente, texto, tag_remitente="cuerpo", tag_id=None):
        """Inserta un mensaje con formato de burbuja. Si se pasa tag_id, envuelve
        todo el bloque en un tag único para poder borrarlo después con precisión
        (usado por el placeholder de 'pensando...')."""
        self.chat_area.config(state=tk.NORMAL)
        inicio = self.chat_area.index(tk.END)

        if remitente:
            self.chat_area.insert(tk.END, f"{remitente}\n", tag_remitente)
        self.chat_area.insert(tk.END, f"{texto}\n\n", "cuerpo")

        if tag_id:
            fin = self.chat_area.index(tk.END)
            self.chat_area.tag_add(tag_id, inicio, fin)

        self.chat_area.see(tk.END)
        self.chat_area.config(state=tk.DISABLED)

    def borrar_bloque(self, tag_id):
        """Borra un mensaje previamente marcado con agregar_texto(..., tag_id=...).
        Reemplaza el viejo hack de índices de línea ('end-3l', 'end-1l'), que
        se rompía si el mensaje tenía saltos de línea internos."""
        rangos = self.chat_area.tag_ranges(tag_id)
        if not rangos:
            return
        self.chat_area.config(state=tk.NORMAL)
        self.chat_area.delete(rangos[0], rangos[1])
        self.chat_area.config(state=tk.DISABLED)

    # ==========================================
    # STREAMING EN VIVO DE LA RESPUESTA (Fase 5)
    # ==========================================
    # Estos métodos conectan cerebro.py con la burbuja de chat en tiempo
    # real. IMPORTANTE: cerebro.py corre en un hilo de fondo (ver
    # procesar_en_fondo), y Tkinter NO es thread-safe -- nunca se debe
    # tocar self.chat_area directamente desde ese hilo. Por eso el callback
    # que se le pasa a cerebro (ver más abajo) siempre reenvuelve la
    # actualización real en self.root.after(0, ...), que la agenda para
    # ejecutarse en el hilo principal de Tkinter.
    def iniciar_burbuja_streaming(self):
        """Crea una burbuja vacía para L-IA y devuelve un tag_id único para
        poder seguir escribiendo dentro de ella (o borrarla entera después,
        p. ej. si termina siendo el caso especial de archivos duplicados)."""
        tag_id = f"stream_{time.time_ns()}"
        self.chat_area.config(state=tk.NORMAL)
        inicio = self.chat_area.index(tk.END)
        self.chat_area.insert(tk.END, "🤖 L-IA\n", "remitente_lia")
        self.chat_area.insert(tk.END, "\n\n", "cuerpo")
        fin = self.chat_area.index(tk.END)
        self.chat_area.tag_add(tag_id, inicio, fin)
        self.chat_area.see(tk.END)
        self.chat_area.config(state=tk.DISABLED)
        return tag_id

    def agregar_token_streaming(self, fragmento, tag_id=None):
        """Inserta un fragmento de texto SIEMPRE 2 caracteres antes del final
        del widget -- justo antes del '\\n\\n' que cierra la burbuja recién
        creada. Ahora también aplica tag_id (si se pasa) para que el rango
        tageado se mantenga contiguo y tag_ranges() siga devolviendo un único
        par (inicio, fin) sin importar cuántos tokens se inserten."""
        self.chat_area.config(state=tk.NORMAL)
        tags = ("cuerpo", tag_id) if tag_id else ("cuerpo",)
        self.chat_area.insert("end-2c", fragmento, tags)
        self.chat_area.see(tk.END)
        self.chat_area.config(state=tk.DISABLED)

    def _reemplazar_texto_burbuja(self, tag_id, texto_nuevo):
        """Reemplaza TODO el contenido (header + cuerpo) de una burbuja de
        streaming ya existente. Se usa solo para el caso puntual de limpiar
        el prefijo 'L-IA:' que a veces mete el modelo, una vez que ya
        sabemos el texto final completo."""
        rangos = self.chat_area.tag_ranges(tag_id)
        if not rangos:
            return
        self.chat_area.config(state=tk.NORMAL)
        self.chat_area.delete(rangos[0], rangos[1])
        inicio = rangos[0]
        self.chat_area.insert(inicio, "🤖 L-IA\n", "remitente_lia")
        self.chat_area.insert(tk.INSERT, f"{texto_nuevo}\n\n", "cuerpo")
        fin = self.chat_area.index(tk.INSERT)
        self.chat_area.tag_add(tag_id, inicio, fin)
        self.chat_area.see(tk.END)
        self.chat_area.config(state=tk.DISABLED)

    # ==========================================
    # ENVÍO / PROCESAMIENTO DE MENSAJES
    # ==========================================
    def enviar_mensaje(self, event):
        if self._placeholder_activo:
            return
        mensaje = self.input_field.get().strip()
        if not mensaje:
            return

        self.input_field.delete(0, tk.END)
        self.agregar_texto("TÚ", mensaje, tag_remitente="remitente_tu")

        threading.Thread(target=self.procesar_en_fondo, args=(mensaje,), daemon=True).start()

    def procesar_en_fondo(self, mensaje):
        """
        Envía el mensaje al cerebro (cerebro.charlar_con_lia) y muestra la respuesta.

        Ahora la respuesta se va pintando EN VIVO en la burbuja conforme
        cerebro.py va transmitiendo tokens (vía callback_stream), en vez de
        esperar a que la función entera termine para mostrar todo de golpe.

        Caso especial: si el buscador de archivos de tools.py encontró varias
        coincidencias, en vez de mostrar la lista como texto plano, se abre un
        popup con un botón por cada archivo encontrado (ver lanzar_popup_archivos).
        """
        self.input_field.config(state=tk.DISABLED)
        self.status_dot.config(fg=Tema.ACCENT_WARN)
        self.agregar_texto("", "🤖 L-IA está pensando...", tag_remitente="cuerpo_suave", tag_id="placeholder")

        # Estado compartido entre este hilo y los callbacks agendados con
        # root.after (por eso es un dict, no variables sueltas: evita
        # líos con 'nonlocal' anidado en dos funciones distintas).
        estado = {"tag_streaming": None, "buffer_inicial": "", "prefijo_revisado": False}

        def _pintar_fragmento(fragmento):
            if not estado["prefijo_revisado"]:
                estado["buffer_inicial"] += fragmento
                if len(estado["buffer_inicial"]) < 12 and ":" not in estado["buffer_inicial"]:
                    return
                estado["prefijo_revisado"] = True
                fragmento = _limpiar_respuesta_ia(estado["buffer_inicial"])
                if not fragmento:
                    return

            if estado["tag_streaming"] is None:
                self.borrar_bloque("placeholder")
                estado["tag_streaming"] = self.iniciar_burbuja_streaming()
            self.agregar_token_streaming(fragmento, tag_id=estado["tag_streaming"])

        def _on_token(fragmento):
            # Se llama desde el hilo de cerebro.py -- SIEMPRE reenviar a
            # través de root.after para tocar el widget desde el hilo
            # correcto (el de Tkinter).
            self.root.after(0, lambda f=fragmento: _pintar_fragmento(f))

        try:
            respuesta, origen = cerebro.charlar_con_lia(
                mensaje,
                callback_ui=self.solicitar_permiso_ui,
                callback_stream=_on_token
            )

            # Si por algún motivo esa ruta de cerebro.py nunca llamó a
            # callback_stream (p. ej. una ruta vieja que todavía no lo
            # propaga), no quedó ninguna burbuja dibujada -- nos aseguramos
            # de no dejar embarrado el "pensando...".
            if estado["tag_streaming"] is None:
                self.borrar_bloque("placeholder")

            # --- INTERCEPTOR DE MÚLTIPLES ARCHIVOS ---
            # No confiamos en las PALABRAS de la IA (se rompía cuando reescribía
            # la frase con su personalidad sarcástica), confiamos en el FORMATO:
            # buscamos el patrón numérico de rutas de Windows en cualquier
            # parte de la respuesta.
            rutas_encontradas = re.findall(r'\d+\.\s+([a-zA-Z]:\\[^\n]+)', respuesta)

            if rutas_encontradas:
                if estado["tag_streaming"] is not None:
                    self.borrar_bloque(estado["tag_streaming"])
                self.agregar_texto(
                    f"🤖 L-IA ({origen})",
                    "[Abriendo interfaz de selección de archivos...]",
                    tag_remitente="remitente_lia"
                )
                self.lanzar_popup_archivos(rutas_encontradas, mensaje)
            else:
                respuesta_limpia = _limpiar_respuesta_ia(respuesta)
                if estado["tag_streaming"] is not None:
                    # Ya se mostró en vivo. Solo se retoca si el texto final
                    # limpio no coincide con lo que ya está pintado (caso
                    # raro: el prefijo se coló pese al buffer inicial).
                    rangos = self.chat_area.tag_ranges(estado["tag_streaming"])
                    if rangos:
                        contenido_actual = self.chat_area.get(rangos[0], rangos[-1]).strip()
                        esperado = f"🤖 L-IA\n{respuesta_limpia}".strip()
                        if contenido_actual != esperado:
                            self._reemplazar_texto_burbuja(estado["tag_streaming"], respuesta_limpia)
                else:
                    self.agregar_texto(f"🤖 L-IA ({origen})", respuesta_limpia, tag_remitente="remitente_lia")

        except Exception as e:
            self.borrar_bloque("placeholder")
            if estado["tag_streaming"] is not None:
                self.borrar_bloque(estado["tag_streaming"])
            self.agregar_texto("❌ Error en el sistema", str(e), tag_remitente="remitente_error")

        self.status_dot.config(fg=Tema.ACCENT_LIA)
        self.input_field.config(state=tk.NORMAL)
        self.input_field.focus_set()

    # ==========================================
    # HELPER COMÚN PARA POPUPS
    # ==========================================
    def _crear_popup_base(self, titulo, ancho=450):
        """Centraliza la creación de ventanas emergentes: mismo fondo, mismo
        posicionamiento relativo a la ventana principal, siempre topmost.
        OJO: ya NO fija la altura acá. Con altura fija, si el contenido
        (ej. un mensaje de commit largo) no cabe, los botones quedan
        empujados fuera del área visible y Tkinter no los muestra ni
        redimensiona la ventana solo. Hay que llamar a
        self._ajustar_popup_a_contenido(popup) después de empaquetar TODO
        el contenido del popup."""
        popup = tk.Toplevel(self.root)
        popup.title(titulo)
        popup.configure(bg=Tema.BG)
        popup.attributes('-topmost', True)
        popup.minsize(ancho, 100)
        return popup

    def _ajustar_popup_a_contenido(self, popup, ancho_min=450, alto_max=600):
        """Llamar SIEMPRE después de empaquetar todo el contenido de un popup.
        Calcula el tamaño real que necesita el contenido y redimensiona la
        ventana a eso (con un tope de alto para no salirse de pantalla, en
        cuyo caso el propio widget con scrollbar interno se encarga del resto)."""
        popup.update_idletasks()
        ancho = max(ancho_min, popup.winfo_reqwidth())
        alto = min(alto_max, popup.winfo_reqheight())
        x = self.root.winfo_x() + 80
        y = self.root.winfo_y() + 80
        popup.geometry(f"{ancho}x{alto}+{x}+{y}")

    # ==========================================
    # VENTANA EMERGENTE DE PERMISOS (Tool Manager)
    # ==========================================
    def solicitar_permiso_ui(self, nombre_herramienta, argumentos):
        """
        Bloquea el hilo de ejecución de forma segura y lanza un popup visual
        para que el usuario decida si autoriza o bloquea una herramienta de Nivel 2.
        Usa un Event de threading para esperar la respuesta sin congelar la UI de Tkinter.
        """
        resultado_permiso = threading.Event()
        decision = {"autorizado": False}

        def _dibujar_popup_seguridad():
            es_commit = nombre_herramienta == "hacer_commit_git"
            popup = self._crear_popup_base(
                "⚠️ L-IA: Alerta de Seguridad",
                ancho=550 if es_commit else 470
            )

            tk.Label(
                popup, text="⚠️ ACCIÓN DEL SISTEMA BLOQUEADA",
                bg=Tema.BG, fg=Tema.ACCENT_ERROR, font=Tema.FUENTE_BOLD
            ).pack(pady=(15, 5))

            if es_commit:
                titulo = argumentos.get('titulo_commit', 'Sin título')
                descripcion = argumentos.get('descripcion_commit', 'Sin descripción')
                ruta_commit = argumentos.get('ruta_repo', 'Desconocida')
                texto_aviso = (
                    f"🛠️ ACCIÓN: GUARDAR CÓDIGO (Git Commit)\n\n"
                    f"📌 TÍTULO:\n{titulo}\n\n"
                    f"📝 DESCRIPCIÓN:\n{descripcion}\n\n"
                    f"📁 PROYECTO:\n{ruta_commit}"
                )
            else:
                texto_aviso = (
                    f"El modelo intenta ejecutar una acción de Nivel 2:\n"
                    f"Herramienta: {nombre_herramienta}\n"
                    f"Argumentos: {argumentos}"
                )

            tk.Label(
                popup, text=texto_aviso, bg=Tema.BG, fg=Tema.TEXTO,
                font=Tema.FUENTE_CHICA, justify=tk.LEFT, wraplength=500
            ).pack(pady=10, padx=15, anchor="w")

            def permitir():
                decision["autorizado"] = True
                popup.destroy()
                resultado_permiso.set()

            def bloquear():
                decision["autorizado"] = False
                popup.destroy()
                resultado_permiso.set()

            frame_botones = tk.Frame(popup, bg=Tema.BG)
            frame_botones.pack(pady=15)

            tk.Button(
                frame_botones, text="PERMITIR [S]", bg=Tema.ACCENT_LIA, fg=Tema.BG,
                font=Tema.FUENTE_TITULO, bd=0, padx=10, pady=5, cursor="hand2", command=permitir
            ).pack(side=tk.LEFT, padx=10)

            tk.Button(
                frame_botones, text="BLOQUEAR [N]", bg=Tema.ACCENT_ERROR, fg=Tema.BG,
                font=Tema.FUENTE_TITULO, bd=0, padx=10, pady=5, cursor="hand2", command=bloquear
            ).pack(side=tk.LEFT, padx=10)

            # Atajos de teclado reales para S / N (antes los botones lo
            # sugerían en el texto pero no estaban conectados a nada)
            popup.bind("s", lambda e: permitir())
            popup.bind("S", lambda e: permitir())
            popup.bind("n", lambda e: bloquear())
            popup.bind("N", lambda e: bloquear())
            popup.focus_force()

            # Si cierran con la 'X', se cuenta como bloqueado por defecto
            popup.protocol("WM_DELETE_WINDOW", bloquear)

            # Ahora que ya empaquetamos TODO (labels + botones), calculamos
            # el tamaño real que necesita el contenido.
            self._ajustar_popup_a_contenido(popup, ancho_min=550 if es_commit else 470)

        self.root.after(0, _dibujar_popup_seguridad)
        resultado_permiso.wait()
        return decision["autorizado"]

    # ==========================================
    # VENTANA EMERGENTE DE SELECCIÓN DE ARCHIVOS
    # ==========================================
    def lanzar_popup_archivos(self, rutas, mensaje_original):
        self.root.after(0, self._dibujar_ventana_opciones, rutas, mensaje_original)

    def _dibujar_ventana_opciones(self, rutas, mensaje_original):
        popup = self._crear_popup_base("L-IA: Archivos Duplicados", ancho=550)

        tk.Label(
            popup, text="🕵️‍♀️ Encontré varios archivos. Haz clic en el correcto:",
            bg=Tema.BG, fg=Tema.ACCENT_LIA, font=Tema.FUENTE_BOLD
        ).pack(pady=15)

        # Contenedor scrollable por si hay muchas coincidencias
        alto_lista = min(42 * len(rutas), 350)
        canvas = tk.Canvas(popup, bg=Tema.BG, highlightthickness=0, height=alto_lista)
        lista = tk.Frame(canvas, bg=Tema.BG)
        canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=20)
        canvas.create_window((0, 0), window=lista, anchor="nw")
        lista.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # Un botón por ruta. r=ruta como default evita el bug clásico de
        # closures en bucles (todos los botones apuntando a la última ruta).
        for ruta in rutas:
            btn = tk.Button(
                lista, text=ruta, bg=Tema.BG_INPUT, fg=Tema.TEXTO, font=Tema.FUENTE_CHICA,
                activebackground=Tema.ACCENT_USER, activeforeground=Tema.BG, bd=0, cursor="hand2",
                anchor="w", command=lambda r=ruta: self._ejecutar_seleccion(r, popup, mensaje_original)
            )
            btn.pack(fill=tk.X, pady=5, ipady=6)

        self._ajustar_popup_a_contenido(popup, ancho_min=550, alto_max=650)

    def _ejecutar_seleccion(self, ruta, popup, mensaje_original):
        """
        Combina la ruta elegida con la intención original del usuario, para
        que L-IA haga exactamente lo pedido (resumir, analizar, buscar un
        bug, etc.) sobre el archivo correcto en vez de una orden genérica.
        """
        popup.destroy()
        self.agregar_texto("TÚ [Selección Automática]", ruta, tag_remitente="remitente_tu")

        orden_invisible = f'Tengo este archivo: "{ruta}". Sobre este archivo, haz lo siguiente: {mensaje_original}'
        threading.Thread(target=self.procesar_en_fondo, args=(orden_invisible,), daemon=True).start()


def crear_icono_imagen():
    """Ícono de estado para la bandeja del sistema (cuadrado verde L-IA)."""
    image = Image.new('RGB', (64, 64), color=(17, 17, 27))
    d = ImageDraw.Draw(image)
    d.rectangle([(16, 16), (48, 48)], fill=(166, 227, 161))
    return image


def iniciar_tray_icon(app):
    """Configura el menú del clic derecho en el ícono de Windows."""
    def on_mostrar(icon, item):
        app.mostrar_ventana()

    def on_salir(icon, item):
        icon.stop()
        app.root.quit()
        sys.exit()

    menu = pystray.Menu(
        pystray.MenuItem("Mostrar L-IA", on_mostrar),
        pystray.MenuItem("Apagar L-IA", on_salir)
    )

    icono = pystray.Icon("L-IA", crear_icono_imagen(), "L-IA Asistente Híbrido", menu)
    icono.run()


def main():
    database.inicializar_base_datos()
    app = InterfazLIA()

    keyboard.add_hotkey('ctrl+alt+j', app.toggle_ventana)

    print("=========================================")
    print(" 🚀 L-IA HÍBRIDA: MODO INMORTAL ACTIVADO")
    print("=========================================")

    hilo_tray = threading.Thread(target=iniciar_tray_icon, args=(app,), daemon=True)
    hilo_tray.start()

    app.root.mainloop()


if __name__ == "__main__":
    main()