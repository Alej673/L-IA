import keyboard
import tkinter as tk
import threading
import re
import pystray
from PIL import Image, ImageDraw
import sys
import cerebro
import database
import contexto  # Tu módulo de visión de ventanas


class InterfazLIA:
    def __init__(self):
        # 1. Configuración de la Ventana
        self.root = tk.Tk()
        self.root.title("L-IA Asistente")
        self.root.geometry("650x450")
        self.root.configure(bg="#11111b")

        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.centrar_ventana()

        self.frame = tk.Frame(self.root, bg="#11111b", padx=20, pady=20)
        self.frame.pack(fill=tk.BOTH, expand=True)

        # 2. ORDEN CORRECTO: Primero anclamos el input al fondo de la ventana
        self.input_field = tk.Entry(
            self.frame, bg="#313244", fg="#a6e3a1", font=("Consolas", 12, "bold"),
            insertbackground="white", bd=5, relief=tk.FLAT
        )
        self.input_field.pack(side=tk.BOTTOM, fill=tk.X, ipady=10)
        self.input_field.bind("<Return>", self.enviar_mensaje)

        # 3. Línea separadora (también anclada abajo, justo sobre el input)
        tk.Frame(self.frame, bg="#45475a", height=2).pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 10))

        # 4. El área de chat toma el resto del espacio hacia arriba
        self.chat_area = tk.Text(
            self.frame, bg="#1e1e2e", fg="#cdd6f4", font=("Consolas", 11),
            wrap=tk.WORD, bd=0, highlightthickness=0
        )
        self.chat_area.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.chat_area.insert(tk.END, "🤖 L-IA en línea. Presiona ESC para ocultarme.\n\n")
        self.chat_area.config(state=tk.DISABLED)

        # Eventos globales
        self.root.bind("<Escape>", self.ocultar_ventana)
        self.root.attributes('-alpha', 0.0)
        self.visible = False

    def centrar_ventana(self):
        """Calcula la posición para que la ventana aparezca centrada horizontalmente
        y en el tercio superior de la pantalla."""
        self.root.update_idletasks()
        ancho = 650
        alto = 450
        x = (self.root.winfo_screenwidth() // 2) - (ancho // 2)
        y = (self.root.winfo_screenheight() // 3) - (alto // 2)
        self.root.geometry(f'{ancho}x{alto}+{x}+{y}')

    def toggle_ventana(self):
        """Alterna la visibilidad de la ventana (usado por el atajo global ctrl+alt+j)."""
        if self.visible:
            self.ocultar_ventana()
        else:
            self.mostrar_ventana()

    def mostrar_ventana(self, event=None):
        self.root.attributes('-alpha', 0.95)
        self.visible = True

        # ESTO ARREGLA EL BUG DEL TECLADO: Le roba el foco a Windows a la fuerza
        self.root.focus_force()
        self.input_field.focus_set()

    def ocultar_ventana(self, event=None):
        self.root.attributes('-alpha', 0.0)
        self.visible = False

    def agregar_texto(self, texto, color="#cdd6f4"):
        """Agrega una línea al área de chat (de solo lectura fuera de este método)."""
        self.chat_area.config(state=tk.NORMAL)
        self.chat_area.insert(tk.END, texto + "\n\n")
        self.chat_area.see(tk.END)
        self.chat_area.config(state=tk.DISABLED)

    def enviar_mensaje(self, event):
        """Se dispara al presionar Enter en el input. Procesa en un hilo aparte
        para no congelar la interfaz mientras L-IA piensa."""
        mensaje = self.input_field.get().strip()
        if not mensaje:
            return

        self.input_field.delete(0, tk.END)
        self.agregar_texto(f"TÚ: {mensaje}", color="#89b4fa")

        threading.Thread(target=self.procesar_en_fondo, args=(mensaje,), daemon=True).start()

    def procesar_en_fondo(self, mensaje):
        """
        Envía el mensaje al cerebro (cerebro.charlar_con_lia) y muestra la respuesta.

        Caso especial: si el buscador de archivos de tools.py encontró varias
        coincidencias, en vez de mostrar la lista como texto plano, se abre un
        popup con un botón por cada archivo encontrado (ver lanzar_popup_archivos).
        """
        self.input_field.config(state=tk.DISABLED)
        self.agregar_texto("🤖 L-IA está pensando...")

        try:
            # MAGIA AQUÍ: Le inyectamos el contexto de la ventana y el texto resaltado
            mensaje_con_contexto = contexto.inyectar_contexto_implicito(mensaje)

            # El cerebro recibe el mensaje enriquecido
            respuesta, origen = cerebro.charlar_con_lia(mensaje_con_contexto)

            # --- INTERCEPTOR DE MÚLTIPLES ARCHIVOS ---
            # OJO: antes esto dependía de que la respuesta contuviera literalmente
            # la frase "Encontré múltiples coincidencias para". Eso rompía en
            # cuanto L-IA reescribía la frase con su propia personalidad
            # sarcástica (Fase Cálida) — el if daba False y el popup nunca se
            # abría, aunque la lista de rutas sí estuviera en el texto.
            #
            # Fix: no confiamos en las PALABRAS de la IA, confiamos en el
            # FORMATO. Buscamos el patrón numérico de rutas de Windows
            # (ej. "1. C:\...") en cualquier parte de la respuesta, sin
            # importar con qué sarcasmo lo haya envuelto.
            rutas_encontradas = re.findall(r'\d+\.\s+([a-zA-Z]:\\[^\n]+)', respuesta)

            if rutas_encontradas:
                # Borramos el mensaje aburrido de "L-IA está pensando..."
                self.chat_area.config(state=tk.NORMAL)
                self.chat_area.delete("end-3l", "end-1l")
                self.chat_area.config(state=tk.DISABLED)

                self.agregar_texto(f"🤖 L-IA ({origen}):\n[Abriendo interfaz de selección de archivos...]")
                # Le pasamos también el mensaje original: así, cuando el usuario
                # elija un archivo, no perdemos de vista qué quería hacer con él.
                self.lanzar_popup_archivos(rutas_encontradas, mensaje)
            else:
                # Si no hay rutas numeradas, es una respuesta normal
                self.agregar_texto(f"🤖 L-IA ({origen}):\n{respuesta}")

        except Exception as e:
            self.agregar_texto(f"❌ Error en el sistema: {e}")

        self.input_field.config(state=tk.NORMAL)
        self.input_field.focus_set()

    # ==========================================
    # MÉTODOS PARA VENTANA EMERGENTE DE SELECCIÓN
    # ==========================================
    # Flujo completo:
    #   1. procesar_en_fondo detecta varias coincidencias de archivo.
    #   2. lanzar_popup_archivos agenda el dibujo del popup en el hilo de Tk.
    #   3. _dibujar_ventana_opciones crea un botón por cada ruta encontrada.
    #   4. Al hacer clic, _ejecutar_seleccion cierra el popup y relanza la
    #      conversación combinando la ruta elegida con lo que el usuario
    #      quería hacer originalmente (mensaje_original).

    def lanzar_popup_archivos(self, rutas, mensaje_original):
        """Agenda la creación del popup en el hilo principal de Tkinter
        (los widgets de Tk no son thread-safe, por eso se usa root.after)."""
        self.root.after(0, self._dibujar_ventana_opciones, rutas, mensaje_original)

    def _dibujar_ventana_opciones(self, rutas, mensaje_original):
        """Dibuja la ventana emergente con un botón por cada archivo candidato."""
        popup = tk.Toplevel(self.root)
        popup.title("L-IA: Archivos Duplicados")
        popup.geometry("550x300")
        popup.configure(bg="#11111b")
        popup.attributes('-topmost', True)  # Siempre por encima

        # Centrar sobre la ventana principal
        x = self.root.winfo_x() + 50
        y = self.root.winfo_y() + 50
        popup.geometry(f"+{x}+{y}")

        tk.Label(popup, text="🕵️‍♀️ Encontré varios archivos. Haz clic en el correcto:",
                 bg="#11111b", fg="#a6e3a1", font=("Consolas", 11, "bold")).pack(pady=15)

        # Crear un botón por cada ruta encontrada.
        # Los valores por defecto (r=ruta) evitan el clásico bug de closures
        # en bucles, donde todos los botones terminarían apuntando a la
        # última ruta de la lista.
        for ruta in rutas:
            btn = tk.Button(
                popup, text=ruta, bg="#313244", fg="#cdd6f4", font=("Consolas", 9),
                activebackground="#89b4fa", activeforeground="#11111b", bd=0, cursor="hand2",
                command=lambda r=ruta: self._ejecutar_seleccion(r, popup, mensaje_original)
            )
            btn.pack(fill=tk.X, padx=20, pady=5, ipady=5)

    def _ejecutar_seleccion(self, ruta, popup, mensaje_original):
        """
        Se ejecuta cuando el usuario elige un archivo del popup.

        En vez de mandar una orden genérica ("lee este archivo"), combinamos
        la ruta elegida con la intención original del usuario, para que L-IA
        haga exactamente lo que se le pidió al principio (resumir, analizar,
        buscar un bug, etc.) sobre el archivo correcto.
        """
        popup.destroy()
        self.agregar_texto(f"TÚ: [Selección Automática]\n{ruta}", color="#89b4fa")

        orden_invisible = f'Tengo este archivo: "{ruta}". Sobre este archivo, haz lo siguiente: {mensaje_original}'

        threading.Thread(target=self.procesar_en_fondo, args=(orden_invisible,), daemon=True).start()


def crear_icono_imagen():
    """Crea un ícono de estado simple (un cuadrado verde) para la bandeja del sistema"""
    image = Image.new('RGB', (64, 64), color=(17, 17, 27))
    d = ImageDraw.Draw(image)
    d.rectangle([(16, 16), (48, 48)], fill=(166, 227, 161))  # Verde L-IA
    return image


def iniciar_tray_icon(app):
    """Configura el menú del clic derecho en el ícono de Windows"""
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

    # Registramos el atajo global
    keyboard.add_hotkey('ctrl+alt+j', app.toggle_ventana)

    print("=========================================")
    print(" 🚀 L-IA HÍBRIDA: MODO INMORTAL ACTIVADO")
    print("=========================================")

    # Lanzamos el ícono en la bandeja del sistema en un hilo separado
    hilo_tray = threading.Thread(target=iniciar_tray_icon, args=(app,), daemon=True)
    hilo_tray.start()

    # Iniciamos el bucle principal de la interfaz gráfica
    app.root.mainloop()


if __name__ == "__main__":
    main()