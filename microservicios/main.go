package main

import (
	"fmt"
	"net/http"
)

func main() {
	// Las funciones ya existen en el mismo paquete gracias a sensores.go y git.go
	http.HandleFunc("/sistema", getSystemStatus)
	http.HandleFunc("/git/estado", getGitStatus)
	http.HandleFunc("/git/cambios", getGitCambios)

	fmt.Println("✅ Motor Go activo en puerto 10510 (Sensores y Git)...")
	http.ListenAndServe(":10510", nil)
}
