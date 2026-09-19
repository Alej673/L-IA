Set WshShell = CreateObject("WScript.Shell")

' 1. Arrancar el backend usando python.exe normal, pero el "0" lo hace 100% invisible
WshShell.CurrentDirectory = "C:\Users\ACER\Desktop\Documentos\Proyecto de IA\L-IA"
WshShell.Run chr(34) & "C:\Users\ACER\Desktop\Documentos\Proyecto de IA\L-IA\venv\Scripts\python.exe" & Chr(34) & " -m uvicorn api:app --port 8000", 0

' 2. Arrancar la interfaz gráfica de Tauri (también oculta con "0")
WshShell.CurrentDirectory = "C:\Users\ACER\Desktop\Documentos\Proyecto de IA\L-IA\lia-interfaz\src-tauri\target\release"
WshShell.Run chr(34) & "C:\Users\ACER\Desktop\Documentos\Proyecto de IA\L-IA\lia-interfaz\src-tauri\target\release\app.exe" & Chr(34), 0

Set WshShell = Nothing