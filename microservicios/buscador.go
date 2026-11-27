package main

import (
	"encoding/json"
	"io/fs"
	"net/http"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"sync/atomic"
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
	"node_modules": true, "vendor": true, ".git": true, ".venv": true,
	"venv": true, "__pycache__": true, "target": true,
	"dist": true, "build": true, "lia_chroma_db": true,
	"AppData": true, "Saved": true, "Intermediate": true,
}

const maxResultadosBusqueda = 20

// filtrarCarpetasRaiz elimina rutas duplicadas y subcarpetas cuya carpeta padre
// ya está incluida en la lista (evita escaneos paralelos repetidos del mismo subárbol).
func filtrarCarpetasRaiz(carpetas []string) []string {
	limpias := make([]string, 0, len(carpetas))
	for _, c := range carpetas {
		c = strings.TrimSpace(c)
		if c == "" {
			continue
		}
		limpias = append(limpias, filepath.Clean(c))
	}

	sort.Slice(limpias, func(i, j int) bool {
		return len(limpias[i]) < len(limpias[j])
	})

	sep := string(filepath.Separator)
	raices := make([]string, 0, len(limpias))
	for _, cand := range limpias {
		candLower := strings.ToLower(cand)
		esHija := false
		for _, raiz := range raices {
			raizLower := strings.ToLower(raiz)
			prefijo := raizLower
			if !strings.HasSuffix(prefijo, sep) {
				prefijo += sep
			}
			if candLower == raizLower || strings.HasPrefix(candLower, prefijo) {
				esHija = true
				break
			}
		}
		if !esHija {
			raices = append(raices, cand)
		}
	}
	return raices
}

func buscarArchivosHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	var req BuscarRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		json.NewEncoder(w).Encode(BuscarResponse{Error: "Petición mal formada"})
		return
	}

	palabra := strings.ToLower(strings.TrimSpace(req.PalabraClave))
	if palabra == "" {
		json.NewEncoder(w).Encode(BuscarResponse{Resultados: []ArchivoEncontrado{}})
		return
	}

	carpetasRaiz := filtrarCarpetasRaiz(req.Carpetas)

	resultados := make([]ArchivoEncontrado, 0, maxResultadosBusqueda)
	vistos := make(map[string]struct{}, maxResultadosBusqueda)
	var mu sync.Mutex
	var wg sync.WaitGroup
	var limiteAlcanzado atomic.Bool

	// Lanzar una goroutine por cada "Zona Segura" para buscar en paralelo
	for _, carpeta := range carpetasRaiz {
		wg.Add(1)
		go func(rutaBase string) {
			defer wg.Done()

			filepath.WalkDir(rutaBase, func(path string, d fs.DirEntry, err error) error {
				if limiteAlcanzado.Load() {
					return fs.SkipAll
				}
				if err != nil {
					return nil // Ignorar archivos bloqueados por Windows o sin permisos
				}

				if d.IsDir() {
					if path != rutaBase && (carpetasExcluidas[d.Name()] || strings.HasPrefix(d.Name(), ".")) {
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
						clave := filepath.Clean(strings.ToLower(path))
						mu.Lock()
						if len(resultados) >= maxResultadosBusqueda {
							limiteAlcanzado.Store(true)
							mu.Unlock()
							return fs.SkipAll
						}
						if _, duplicado := vistos[clave]; duplicado {
							mu.Unlock()
							return nil
						}
						vistos[clave] = struct{}{}
						resultados = append(resultados, ArchivoEncontrado{
							Ruta:       path,
							FechaModif: info.ModTime().Format("2006-01-02 15:04"),
							TamanoKB:   float64(info.Size()) / 1024.0,
						})
						alcanzado := len(resultados) >= maxResultadosBusqueda
						if alcanzado {
							limiteAlcanzado.Store(true)
						}
						mu.Unlock()
						if alcanzado {
							return fs.SkipAll
						}
					}
				}
				return nil
			})
		}(carpeta)
	}

	wg.Wait() // Esperar a que todos los hilos de búsqueda terminen
	json.NewEncoder(w).Encode(BuscarResponse{Resultados: resultados})
}
