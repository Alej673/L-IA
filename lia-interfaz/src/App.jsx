import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Mic, Paperclip, Terminal, Cpu, Database, Upload } from 'lucide-react'
import './App.css'
import { useEffect } from 'react'
import { getCurrentWindow } from '@tauri-apps/api/window'
import { register, isRegistered } from '@tauri-apps/plugin-global-shortcut'

function App() {
  const [estadoLIA, setEstadoLIA] = useState('reposo') 
  const [input, setInput] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const [mensajes, setMensajes] = useState([
    { rol: 'ia', texto: 'L-IA v3.2.0 inicializada. Esperando directivas...' }
  ])

  // Ajuste de colores: cyan (reposo), naranja (procesando texto), magenta (procesando RAG)
  const colorNucleo = estadoLIA === 'reposo' ? '#00ffff' : estadoLIA === 'procesando' ? '#ffaa00' : estadoLIA === 'procesando_rag' ? '#ff00ff' : '#ff3300'

  // --- 1. COMUNICACIÓN DE TEXTO CON FASTAPI ---
  const manejarEnvio = async (e) => {
    e.preventDefault()
    if (!input.trim()) return

    const textoUsuario = input
    setMensajes(prev => [...prev, { rol: 'usuario', texto: textoUsuario }])
    setInput('')
    setEstadoLIA('procesando') // El núcleo cambia a naranja y gira rápido

    try {
      const respuesta = await fetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texto: textoUsuario })
      })
      const data = await respuesta.json()
      setMensajes(prev => [...prev, data])
    } catch (error) {
      setMensajes(prev => [...prev, { rol: 'sistema', texto: '[ERROR] No se pudo establecer enlace con el núcleo local.' }])
    } finally {
      setEstadoLIA('reposo')
    }
  }

  // --- 2. COMUNICACIÓN DE ARCHIVOS (RAG) CON FASTAPI ---
  const manejarDragOver = (e) => {
    e.preventDefault()
    if (!isDragging) setIsDragging(true)
  }

  const manejarDragLeave = (e) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const manejarDrop = async (e) => {
    e.preventDefault()
    setIsDragging(false)
    
    const archivos = e.dataTransfer.files
    if (archivos.length > 0) {
      const archivo = archivos[0]
      setEstadoLIA('procesando_rag') // El núcleo cambia a magenta
      setMensajes(prev => [...prev, { rol: 'sistema', texto: `[SISTEMA] Transfiriendo ${archivo.name} al motor vectorial...` }])

      // Usamos FormData para enviar archivos binarios a la API
      const formData = new FormData()
      formData.append("archivo", archivo)

      try {
        const respuesta = await fetch("http://127.0.0.1:8000/ingestar", {
          method: "POST",
          body: formData
        })
        const data = await respuesta.json()
        setMensajes(prev => [...prev, { rol: 'ia', texto: data.mensaje }])
      } catch (error) {
        setMensajes(prev => [...prev, { rol: 'sistema', texto: '[ERROR] Fallo en la transferencia de datos al módulo RAG.' }])
      } finally {
        setEstadoLIA('reposo')
      }
    }
  }

  return (
    <div 
      className="hud-container"
      onDragOver={manejarDragOver}
      onDragLeave={manejarDragLeave}
      onDrop={manejarDrop}
    >
      {/* CAPA HOLOGRÁFICA DE ARRASTRE */}
      <AnimatePresence>
        {isDragging && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{
              position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
              background: 'rgba(255, 0, 255, 0.1)',
              backdropFilter: 'blur(8px)',
              border: '2px dashed #ff00ff',
              zIndex: 50, display: 'flex', flexDirection: 'column',
              justifyContent: 'center', alignItems: 'center', color: '#ff00ff'
            }}
          >
            <Upload size={64} style={{ marginBottom: '20px' }} />
            <h2>SUELTA EL ARCHIVO PARA INGESTAR EN EL SEGUNDO CEREBRO</h2>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="panel lateral">
        <h4 className="hud-title">SYSTEM_METRICS</h4>
        <div className="modulo-stat">
          <Cpu size={16} color="#00ffff" />
          <span>CPU USAGE</span>
          <div className="barra-progreso"><div className="fill" style={{width: '45%'}}></div></div>
        </div>
        <div className="modulo-stat">
          <Database size={16} color="#00ffff" />
          <span>VRAM ALLOC</span>
          <div className="barra-progreso"><div className="fill" style={{width: '80%', background: '#ff00ff'}}></div></div>
        </div>
      </div>

      <div className="panel central">
        <div className="nucleo-wrapper">
          <motion.div 
            className="anillo-exterior"
            style={{ borderColor: colorNucleo }}
            animate={{ rotate: 360 }}
            transition={{ repeat: Infinity, duration: estadoLIA === 'reposo' ? 10 : 1.5, ease: "linear" }}
          />
          <motion.div 
            className="anillo-interior"
            style={{ borderColor: colorNucleo }}
            animate={{ scale: [1, 1.1, 1] }}
            transition={{ repeat: Infinity, duration: estadoLIA === 'reposo' ? 2 : 0.5 }}
          />
          <div className="centro-nucleo" style={{ background: colorNucleo, boxShadow: `0 0 20px ${colorNucleo}` }} />
        </div>

        <div className="chat-terminal" style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {mensajes.map((msg, idx) => (
            <div key={idx} style={{ 
              color: msg.rol === 'sistema' ? '#ff00ff' : msg.rol === 'usuario' ? '#fff' : '#00ffff',
              opacity: msg.rol === 'sistema' ? 0.8 : 1,
              alignSelf: msg.rol === 'usuario' ? 'flex-end' : 'flex-start',
              background: msg.rol === 'usuario' ? 'rgba(0, 255, 255, 0.1)' : 'transparent',
              padding: msg.rol === 'usuario' ? '5px 10px' : '0',
              borderRadius: '5px'
            }}>
              {msg.rol === 'ia' ? '> L-IA: ' : msg.rol === 'usuario' ? '' : '> '}{msg.texto}
            </div>
          ))}
        </div>

        <form onSubmit={manejarEnvio} className="controles-input">
          <button type="button" className="hud-btn"><Paperclip size={18} /></button>
          <input 
            type="text" 
            className="hud-input" 
            placeholder="Ingresa comando..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
          <button type="submit" className="hud-btn animado"><Terminal size={18} /></button>
        </form>
      </div>

      <div className="panel lateral">
        <h4 className="hud-title">ACTIVE_MODULES</h4>
        <div className="lista-modulos">
          <div className="etiqueta-modulo on" style={{ color: estadoLIA === 'procesando_rag' ? '#ff00ff' : '#00ffff' }}>CHROMA_DB</div>
          <div className="etiqueta-modulo on">OLLAMA_SERVER</div>
          <div className="etiqueta-modulo off">EDGE_TTS</div>
        </div>
      </div>
    </div>
  )
}

export default App