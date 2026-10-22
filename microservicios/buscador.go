package main

import (
	"encoding/json"
	"io/fs"
	"net/http"
	"path/filepath"
	"strings"
	"sync"
)

type BuscarRequest struct {
	PalabraClave string   `json:"palabra_clave"`
	Carpetas     []string `json:"carpetas"` // Las zonas seguras enviadas desde Python
}

type ArchivoEncontrado struct {
	Ruta       string  `json:"ruta"`
	FechaModif string  `json:"fecha"`
	TamanoKB   float64 `json:"tamano_kb"`
}

type BuscarResponse struct {
	Resultados []ArchivoEncontrado `json:"resultados"`
	Error      string              `json:"error,omitempty"`
}

// Replicamos tu lista de exclusión para no saturar la búsqueda
var carpetasExcluidas = map[string]bool{
	"node_modules": true, "vendor": true, ".git": true,
	"AppData": true, "Saved": true, "Intermediate": true,
}

func buscarArchivosHandler(w http.ResponseWriter, r *http.Request) {
	var req BuscarRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		json.NewEncoder(w).Encode(BuscarResponse{Error: "Petición mal formada"})
		return
	}
	w.Header().Set("Content-Type", "application/json")

	palabra := strings.ToLower(req.PalabraClave)
	var resultados []ArchivoEncontrado
	var mu sync.Mutex
	var wg sync.WaitGroup

	// Lanzar una goroutine por cada "Zona Segura" para buscar en paralelo
	for _, carpeta := range req.Carpetas {
		wg.Add(1)
		go func(rutaBase string) {
			defer wg.Done()

			filepath.WalkDir(rutaBase, func(path string, d fs.DirEntry, err error) error {
				if err != nil {
					return nil // Ignorar archivos bloqueados por Windows o sin permisos
				}

				if d.IsDir() {
					if carpetasExcluidas[d.Name()] || strings.HasPrefix(d.Name(), ".") {
						return filepath.SkipDir
					}
					return nil
				}

				// Ignorar temporales de Word/Excel y ocultos
				if strings.HasPrefix(d.Name(), "~$") || strings.HasPrefix(d.Name(), ".") {
					return nil
				}

				// Coincidencia de nombre
				if strings.Contains(strings.ToLower(d.Name()), palabra) {
					info, err := d.Info()
					if err == nil {
						mu.Lock()
						// Limitamos a 20 resultados máximos para no saturar la interfaz de React
						if len(resultados) < 20 {
							resultados = append(resultados, ArchivoEncontrado{
								Ruta:       path,
								FechaModif: info.ModTime().Format("2006-01-02 15:04"),
								TamanoKB:   float64(info.Size()) / 1024.0,
							})
						}
						mu.Unlock()
					}
				}
				return nil
			})
		}(carpeta)
	}

	wg.Wait() // Esperar a que todos los hilos de búsqueda terminen
	json.NewEncoder(w).Encode(BuscarResponse{Resultados: resultados})
}
