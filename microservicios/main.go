package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"sort"
	"time"

	"github.com/shirou/gopsutil/v3/cpu"
	"github.com/shirou/gopsutil/v3/mem"
	"github.com/shirou/gopsutil/v3/process"
)

// --- ESTRUCTURAS DE HARDWARE ---
type SystemStatus struct {
	CPU     string `json:"cpu"`
	RAM     string `json:"ram"`
	TopApps string `json:"top_apps"`
}

// --- ESTRUCTURAS DE GIT ---
type GitRequest struct {
	Ruta string `json:"ruta"`
}

type GitResponse struct {
	Resultado string `json:"resultado"`
	Error     string `json:"error"`
}

// --- ENDPOINT 1: ESTADO DEL SISTEMA ---
func getSystemStatus(w http.ResponseWriter, r *http.Request) {
	// 1. Leer CPU
	cpuPercent, _ := cpu.Percent(time.Second, false)
	cpuStr := "Error"
	if len(cpuPercent) > 0 {
		cpuStr = fmt.Sprintf("%.1f%%", cpuPercent[0])
	}

	// 2. Leer RAM
	vMem, _ := mem.VirtualMemory()
	ramStr := fmt.Sprintf("%.2fGB de %.2fGB (%.1f%%)",
		float64(vMem.Used)/(1024*1024*1024),
		float64(vMem.Total)/(1024*1024*1024),
		vMem.UsedPercent)

	// 3. Leer procesos (Top 3)
	procs, _ := process.Processes()
	type ProcInfo struct {
		Name string
		Mem  float32
	}
	var procList []ProcInfo

	for _, p := range procs {
		name, _ := p.Name()
		memInfo, err := p.MemoryPercent()
		if err == nil {
			procList = append(procList, ProcInfo{Name: name, Mem: memInfo})
		}
	}

	sort.Slice(procList, func(i, j int) bool {
		return procList[i].Mem > procList[j].Mem
	})

	topApps := "No disponible"
	if len(procList) >= 3 {
		topApps = fmt.Sprintf("%s (%.1f%%), %s (%.1f%%), %s (%.1f%%)",
			procList[0].Name, procList[0].Mem,
			procList[1].Name, procList[1].Mem,
			procList[2].Name, procList[2].Mem)
	}

	status := SystemStatus{
		CPU:     cpuStr,
		RAM:     ramStr,
		TopApps: topApps,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(status)
}

// --- ENDPOINT 2: LECTURA DE GIT ---
func getGitStatus(w http.ResponseWriter, r *http.Request) {
	var req GitRequest
	json.NewDecoder(r.Body).Decode(&req)
	w.Header().Set("Content-Type", "application/json")

	// 1. Validar si la ruta existe y es un repositorio Git
	gitPath := req.Ruta + "/.git"
	if _, err := os.Stat(gitPath); os.IsNotExist(err) {
		json.NewEncoder(w).Encode(GitResponse{Error: "La carpeta no está inicializada como repositorio Git."})
		return
	}

	// 2. Ejecutar 'git status' de forma concurrente
	cmdStatus := exec.Command("git", "status", "--short")
	cmdStatus.Dir = req.Ruta
	outStatus, err := cmdStatus.CombinedOutput()
	if err != nil {
		json.NewEncoder(w).Encode(GitResponse{Error: fmt.Sprintf("Error ejecutando git status: %s", err.Error())})
		return
	}

	// 3. Ejecutar 'git log'
	cmdLog := exec.Command("git", "log", "-3", "--oneline")
	cmdLog.Dir = req.Ruta
	outLog, _ := cmdLog.CombinedOutput()

	// 4. Armar el resultado idéntico al que esperaba L-IA
	resultadoFinal := fmt.Sprintf("=== ESTADO DEL REPOSITORIO (%s) ===\n%s\n=== ÚLTIMOS COMMITS (Historial reciente) ===\n%s",
		req.Ruta, string(outStatus), string(outLog))

	json.NewEncoder(w).Encode(GitResponse{Resultado: resultadoFinal})
}

// --- ENDPOINT 3: LECTURA PROFUNDA DE CAMBIOS (DIFF) ---
func getGitCambios(w http.ResponseWriter, r *http.Request) {
	var req GitRequest
	json.NewDecoder(r.Body).Decode(&req)
	w.Header().Set("Content-Type", "application/json")

	gitPath := req.Ruta + "/.git"
	if _, err := os.Stat(gitPath); os.IsNotExist(err) {
		json.NewEncoder(w).Encode(GitResponse{Error: "La ruta no es un repositorio Git."})
		return
	}

	// 1. Extraer archivos modificados (status)
	cmdStatus := exec.Command("git", "status", "--porcelain")
	cmdStatus.Dir = req.Ruta
	outStatus, _ := cmdStatus.CombinedOutput()

	// Si no hay texto en el status, no hay cambios
	if len(outStatus) == 0 {
		json.NewEncoder(w).Encode(GitResponse{Resultado: "No hay cambios pendientes en este repositorio."})
		return
	}

	// 2. Extraer las líneas exactas de código modificado (diff)
	cmdDiff := exec.Command("git", "diff")
	cmdDiff.Dir = req.Ruta
	outDiff, _ := cmdDiff.CombinedOutput()

	// 3. Extraer cambios que ya estén en staging (por si usaste git add a mano)
	cmdDiffCached := exec.Command("git", "diff", "--cached")
	cmdDiffCached.Dir = req.Ruta
	outDiffCached, _ := cmdDiffCached.CombinedOutput()

	resultadoFinal := fmt.Sprintf("=== ARCHIVOS MODIFICADOS ===\n%s\n=== CÓDIGO ALTERADO ===\n%s\n%s",
		string(outStatus), string(outDiff), string(outDiffCached))

	json.NewEncoder(w).Encode(GitResponse{Resultado: resultadoFinal})
}

// --- ORQUESTADOR PRINCIPAL ---
func main() {
	http.HandleFunc("/sistema", getSystemStatus)
	http.HandleFunc("/git/estado", getGitStatus)
	http.HandleFunc("/git/cambios", getGitCambios)

	fmt.Println("✅ Microservicios Go activos en puerto 10510 (Sensores y Git)...")
	http.ListenAndServe(":10510", nil)
}
