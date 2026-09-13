import pygetwindow as gw

print("\n--- VENTANAS DETECTADAS EN PANTALLA ---")
for v in gw.getAllWindows():
    if v.title.strip() and v.visible and not v.isMinimized:
        print(f"[{v.title.strip()}]")