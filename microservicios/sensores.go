package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"sort"
	"time"

	"github.com/shirou/gopsutil/v3/cpu"
	"github.com/shirou/gopsutil/v3/mem"
	"github.com/shirou/gopsutil/v3/process"
)

type SystemStatus struct {
	CPU     string `json:"cpu"`
	RAM     string `json:"ram"`
	TopApps string `json:"top_apps"`
}

func getSystemStatus(w http.ResponseWriter, r *http.Request) {
	cpuPercent, _ := cpu.Percent(time.Second, false)
	cpuStr := "Error"
	if len(cpuPercent) > 0 {
		cpuStr = fmt.Sprintf("%.1f%%", cpuPercent[0])
	}

	vMem, _ := mem.VirtualMemory()
	ramStr := fmt.Sprintf("%.2fGB de %.2fGB (%.1f%%)",
		float64(vMem.Used)/(1024*1024*1024),
		float64(vMem.Total)/(1024*1024*1024),
		vMem.UsedPercent)

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