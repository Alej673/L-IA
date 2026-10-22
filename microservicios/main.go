package main

import (
	"fmt"
	"net/http"
)

func main() {
	http.HandleFunc("/sistema", getSystemStatus)
	http.HandleFunc("/git/estado", getGitStatus)
	http.HandleFunc("/git/cambios", getGitCambios)

	// Nueva ruta para el escáner concurrente de archivos
	http.HandleFunc("/archivos/buscar", buscarArchivosHandler)

	fmt.Println("✅ Motor Go activo en puerto 10510 (Sensores, Git y Buscador)...")
	http.ListenAndServe(":10510", nil)
}
