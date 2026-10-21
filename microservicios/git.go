package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"os/exec"
)

type GitRequest struct {
	Ruta string `json:"ruta"`
}

type GitResponse struct {
	Resultado string `json:"resultado"`
	Error     string `json:"error"`
}

func getGitStatus(w http.ResponseWriter, r *http.Request) {
	var req GitRequest
	json.NewDecoder(r.Body).Decode(&req)
	w.Header().Set("Content-Type", "application/json")

	gitPath := req.Ruta + "/.git"
	if _, err := os.Stat(gitPath); os.IsNotExist(err) {
		json.NewEncoder(w).Encode(GitResponse{Error: "La carpeta no está inicializada como repositorio Git."})
		return
	}

	cmdStatus := exec.Command("git", "status", "--short")
	cmdStatus.Dir = req.Ruta
	outStatus, err := cmdStatus.CombinedOutput()
	if err != nil {
		json.NewEncoder(w).Encode(GitResponse{Error: fmt.Sprintf("Error ejecutando git status: %s", err.Error())})
		return
	}

	cmdLog := exec.Command("git", "log", "-3", "--oneline")
	cmdLog.Dir = req.Ruta
	outLog, _ := cmdLog.CombinedOutput()

	resultadoFinal := fmt.Sprintf("=== ESTADO DEL REPOSITORIO (%s) ===\n%s\n=== ÚLTIMOS COMMITS (Historial reciente) ===\n%s",
		req.Ruta, string(outStatus), string(outLog))

	json.NewEncoder(w).Encode(GitResponse{Resultado: resultadoFinal})
}

func getGitCambios(w http.ResponseWriter, r *http.Request) {
	var req GitRequest
	json.NewDecoder(r.Body).Decode(&req)
	w.Header().Set("Content-Type", "application/json")

	gitPath := req.Ruta + "/.git"
	if _, err := os.Stat(gitPath); os.IsNotExist(err) {
		json.NewEncoder(w).Encode(GitResponse{Error: "La ruta no es un repositorio Git."})
		return
	}

	cmdStatus := exec.Command("git", "status", "--porcelain")
	cmdStatus.Dir = req.Ruta
	outStatus, _ := cmdStatus.CombinedOutput()

	if len(outStatus) == 0 {
		json.NewEncoder(w).Encode(GitResponse{Resultado: "No hay cambios pendientes en este repositorio."})
		return
	}

	cmdDiff := exec.Command("git", "diff")
	cmdDiff.Dir = req.Ruta
	outDiff, _ := cmdDiff.CombinedOutput()

	cmdDiffCached := exec.Command("git", "diff", "--cached")
	cmdDiffCached.Dir = req.Ruta
	outDiffCached, _ := cmdDiffCached.CombinedOutput()

	resultadoFinal := fmt.Sprintf("=== ARCHIVOS MODIFICADOS ===\n%s\n=== CÓDIGO ALTERADO ===\n%s\n%s",
		string(outStatus), string(outDiff), string(outDiffCached))

	json.NewEncoder(w).Encode(GitResponse{Resultado: resultadoFinal})
}
