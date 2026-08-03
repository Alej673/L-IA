Set WshShell = CreateObject("WScript.Shell")

' 1. Le decimos a Windows dónde vivo realmente
WshShell.CurrentDirectory = "C:\Users\ACER\Desktop\Documentos\Proyecto de IA\L-IA"

' 2. Me ejecuto de forma invisible
WshShell.Run chr(34) & "C:\Users\ACER\Desktop\Documentos\Proyecto de IA\L-IA\venv\Scripts\pythonw.exe" & Chr(34) & " " & Chr(34) & "C:\Users\ACER\Desktop\Documentos\Proyecto de IA\L-IA\launcher.py" & Chr(34), 0

Set WshShell = Nothing