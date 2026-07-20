import keyboard
import tkinter as tk
import threading
import cerebro
import database

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
        self.root.update_idletasks()
        ancho = 650
        alto = 450
        x = (self.root.winfo_screenwidth() // 2) - (ancho // 2)
        y = (self.root.winfo_screenheight() // 3) - (alto // 2)
        self.root.geometry(f'{ancho}x{alto}+{x}+{y}')

    def toggle_ventana(self):
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
        self.chat_area.config(state=tk.NORMAL)
        self.chat_area.insert(tk.END, texto + "\n\n")
        self.chat_area.see(tk.END)
        self.chat_area.config(state=tk.DISABLED)

    def enviar_mensaje(self, event):
        mensaje = self.input_field.get().strip()
        if not mensaje: return
        
        self.input_field.delete(0, tk.END)
        self.agregar_texto(f"TÚ: {mensaje}", color="#89b4fa")
        
        threading.Thread(target=self.procesar_en_fondo, args=(mensaje,), daemon=True).start()

    def procesar_en_fondo(self, mensaje):
        self.input_field.config(state=tk.DISABLED)
        self.agregar_texto("🤖 L-IA está pensando...")
        
        try:
            respuesta, origen = cerebro.charlar_con_lia(mensaje)
            self.agregar_texto(f"🤖 L-IA ({origen}):\n{respuesta}")
        except Exception as e:
            self.agregar_texto(f"❌ Error en el sistema: {e}")
            
        self.input_field.config(state=tk.NORMAL)
        self.input_field.focus_set()

def main():
    database.inicializar_base_datos()
    app = InterfazLIA()
    
    keyboard.add_hotkey('ctrl+alt+j', app.toggle_ventana)
    
    print("=========================================")
    print(" 🚀 L-IA HÍBRIDA: INTERFAZ ACTIVADA")
    print("=========================================")
    print("Atajo: ctrl + alt + j (Muestra/Oculta la interfaz)")
    print("Para apagar a L-IA, cierra esta consola base.")
    
    app.root.mainloop()

if __name__ == "__main__":
    main()