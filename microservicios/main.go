package main

import (
	"fmt"
	"log"
	"net/http"
	"time"
)

func main() {
	http.HandleFunc("/sistema", getSystemStatus)
	http.HandleFunc("/git/estado", getGitStatus)
	http.HandleFunc("/git/cambios", getGitCambios)

	// Nueva ruta para el escáner concurrente de archivos
	http.HandleFunc("/archivos/buscar", buscarArchivosHandler)

	srv := &http.Server{
		Addr:              "127.0.0.1:10510",
		ReadHeaderTimeout: 5 * time.Second,
	}

	fmt.Println("✅ Motor Go activo en 127.0.0.1:10510 (Sensores, Git y Buscador)...")
	log.Fatal(srv.ListenAndServe())
}
