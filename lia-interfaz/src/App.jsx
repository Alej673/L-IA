import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Mic, Paperclip, Terminal, Cpu, Database, Upload, AlertTriangle } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import './App.css'

function App() {
  const [estadoLIA, setEstadoLIA] = useState('reposo') 
  const [input, setInput] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const [escuchando, setEscuchando] = useState(false)
  const [mensajes, setMensajes] = useState([
    { rol: 'ia', texto: 'L-IA v3.2.0 inicializada. Esperando directivas...' }
  ])

  const finalDelChatRef = useRef(null)
  const archivoInputRef = useRef(null)

  // NUEVO ESTADO DEL SEMÁFORO
  const [semaforo, setSemaforo] = useState({ activa: false, herramienta: '', argumentos: '' })

  useEffect(() => {
    finalDelChatRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [mensajes])

  const colorNucleo = estadoLIA === 'reposo' ? '#00ffff' : estadoLIA === 'procesando' ? '#ffaa00' : estadoLIA === 'procesando_rag' ? '#ff00ff' : '#ff3300'

  // NUEVO: Vigía del Semáforo
  useEffect(() => {
    let intervalo;
    // Solo vigila si L-IA está pensando (procesando)
    if (estadoLIA === 'procesando') {
      intervalo = setInterval(async () => {
        try {
          const res = await fetch("http://127.0.0.1:8000/semaforo")
          const data = await res.json()
          if (data.activa && !semaforo.activa) {
            setSemaforo(data)
          }
        } catch (e) { console.error("Error de semáforo", e) }
      }, 1000) // Pregunta cada 1 segundo
    }
    return () => clearInterval(intervalo)
  }, [estadoLIA, semaforo.activa])

  // NUEVA: Función para responder al semáforo
  const responderSemaforo = async (autorizado) => {
    try {
      await fetch("http://127.0.0.1:8000/semaforo/responder", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ autorizado })
      })
      setSemaforo({ activa: false, herramienta: '', argumentos: '' })
    } catch (e) {
      console.error("Fallo al enviar decisión al núcleo")
    }
  }

  const manejarEnvio = async (e) => {
    // Si viene de un evento (ej. presionar Enter), prevenimos que recargue la página
    if (e) e.preventDefault();

    // Bloquea si ya está generando o el texto está vacío
    if (!input.trim() || cargando) return; 

    const textoUsuario = input;
    
    setCargando(true);
    abortControllerRef.current = new AbortController();
    
    // Inyectamos el mensaje del usuario y creamos una burbuja VACÍA para L-IA
    setMensajes(prev => [
      ...prev, 
      { rol: 'usuario', texto: textoUsuario },
      { rol: 'ia', texto: '', origen: '', documento: null } 
    ]);
    
    setInput('');
    setEstadoLIA('procesando');

    try {
      const respuesta = await fetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texto: textoUsuario }),
        signal: abortControllerRef.current.signal
      });

      // --- INICIO DE TU BUCLE DE LECTURA EXACTAMENTE COMO LO TIENES ---
      const reader = respuesta.body.getReader()
      const decoder = new TextDecoder("utf-8")
      let buffer = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        
        buffer += decoder.decode(value, { stream: true })
        const partes = buffer.split("\n\n")
        buffer = partes.pop() 

        for (const parte of partes) {
          if (parte.startsWith("data: ")) {
            const dataStr = parte.replace("data: ", "")
            try {
              const data = JSON.parse(dataStr)
              
              if (data.tipo === "chunk") {
                if (data.texto.length > 50) {
                  setMensajes(prev => {
                    const nuevos = [...prev]
                    nuevos[nuevos.length - 1].texto += data.texto
                    return nuevos
                  });
                } else {
                  const letras = data.texto.split("");
                  for (let i = 0; i < letras.length; i++) {
                    setMensajes(prev => {
                      const nuevos = [...prev]
                      const ultimo = nuevos[nuevos.length - 1]
                      ultimo.texto += letras[i]
                      return nuevos
                    });
                    await new Promise(resolve => setTimeout(resolve, 15));
                  }
                }
              } else if (data.tipo === "fin") {
                setMensajes(prev => {
                  const nuevos = [...prev]
                  const ultimo = nuevos[nuevos.length - 1]
                  ultimo.origen = data.origen
                  if (data.documento) ultimo.documento = data.documento
                  return nuevos
                })
              } else if (data.tipo === "error") {
                setMensajes(prev => {
                  const nuevos = [...prev]
                  nuevos[nuevos.length - 1].texto += `\n[ERROR]: ${data.texto}`
                  return nuevos
                })
              }
            } catch(err) {
              console.error("Error parseando el chunk:", err)
            }
          }
        }
      }
      // --- FIN DE TU BUCLE DE LECTURA ---

    } catch (error) {
      if (error.name === 'AbortError') {
        setMensajes(prev => {
          const nuevos = [...prev];
          nuevos[nuevos.length - 1].texto += '\n\n*(Respuesta abortada)*';
          nuevos[nuevos.length - 1].cancelado = true; // <-- NUEVO ESTADO
          return nuevos;
        });
      } else {
        setMensajes(prev => {
          const nuevos = [...prev];
          nuevos[nuevos.length - 1].texto += '\n\n[ERROR] Caída del enlace con el núcleo.';
          return nuevos;
        });
      }
    } finally {
      // Liberamos los seguros de la interfaz SIEMPRE, pase lo que pase
      setEstadoLIA('reposo');
      setCargando(false);
    }
  }

  const procesarArchivoRAG = async (archivo) => {
    setEstadoLIA('procesando_rag')
    setMensajes(prev => [...prev, { rol: 'sistema', texto: `[SISTEMA] Ingestando ${archivo.name}...` }])
    const formData = new FormData()
    formData.append("archivo", archivo)
    try {
      const respuesta = await fetch("http://127.0.0.1:8000/ingestar", { method: "POST", body: formData })
      const data = await respuesta.json()
      setMensajes(prev => [...prev, { rol: 'ia', texto: data.mensaje }])
    } catch (error) {
      setMensajes(prev => [...prev, { rol: 'sistema', texto: '[ERROR] Fallo en RAG.' }])
    } finally {
      setEstadoLIA('reposo')
    }
  }

  const manejarDragOver = (e) => { e.preventDefault(); if (!isDragging) setIsDragging(true) }
  const manejarDragLeave = (e) => { e.preventDefault(); setIsDragging(false) }
  const manejarDrop = (e) => { e.preventDefault(); setIsDragging(false); if (e.dataTransfer.files.length > 0) procesarArchivoRAG(e.dataTransfer.files[0]) }
  const manejarClickArchivo = () => archivoInputRef.current?.click()
  const manejarSeleccionArchivo = (e) => { if (e.target.files.length > 0) procesarArchivoRAG(e.target.files[0]); e.target.value = null }

  // MICRÓFONO SILENCIOSO: Solo cambia estado visual y (a futuro) llama a la API, no ensucia el chat
  const manejarMicrofono = () => {
    setEscuchando(!escuchando)
    // fetch("http://127.0.0.1:8000/microfono", { method: "POST", body: JSON.stringify({ estado: !escuchando }) })
  }

  const [cargando, setCargando] = useState(false);
  const abortControllerRef = useRef(null);

  const detenerGeneracion = async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort(); 
    }
    setCargando(false);
    
    try {
      // Cambiado a 127.0.0.1 para mantener tu estándar
      await fetch("http://127.0.0.1:8000/cancelar", { method: "POST" });
    } catch (error) {
      console.error("Error al abortar en el backend:", error);
    }
  };

  return (
    <div className="hud-container" onDragOver={manejarDragOver} onDragLeave={manejarDragLeave} onDrop={manejarDrop}>
      
      {/* EL NUEVO MODAL DEL SEMÁFORO */}
      <AnimatePresence>
        {semaforo.activa && (
          <motion.div 
            className="modal-overlay"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          >
            <motion.div 
              className="modal-semaforo"
              initial={{ scale: 0.8, y: 50 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.8, opacity: 0 }}
              transition={{ type: "spring", bounce: 0.5 }}
            >
              <AlertTriangle color="#ff0055" size={50} style={{ marginBottom: '10px' }} />
              <h3 style={{ color: '#ff0055', margin: '0 0 15px 0', letterSpacing: '2px' }}>ALERTA NIVEL 2</h3>
              <p style={{ color: '#fff', fontSize: '14px', marginBottom: '10px' }}>L-IA requiere autorización crítica para ejecutar:</p>
              
              <div className="codigo-alerta">{semaforo.herramienta}</div>
              <p style={{ color: '#fff', fontSize: '14px', margin: '15px 0 10px 0' }}>Argumentos detectados:</p>
              <div className="codigo-alerta">{semaforo.argumentos}</div>

              <div className="botones-alerta">
                <button className="btn-denegar" onClick={() => responderSemaforo(false)}>ABORTAR</button>
                <button className="btn-autorizar" onClick={() => responderSemaforo(true)}>AUTORIZAR</button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="panel central">
        {/* NÚCLEO ESTÁTICO (NO HACE SCROLL) */}
        <div className="nucleo-wrapper">
          <motion.div className="anillo-exterior" style={{ borderColor: colorNucleo }} animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: estadoLIA === 'reposo' ? 10 : 1.5, ease: "linear" }} />
          <motion.div className="anillo-interior" style={{ borderColor: colorNucleo }} animate={{ scale: [1, 1.1, 1] }} transition={{ repeat: Infinity, duration: estadoLIA === 'reposo' ? 2 : 0.5 }} />
          <div className="centro-nucleo" style={{ background: colorNucleo, boxShadow: `0 0 20px ${colorNucleo}` }} />
        </div>

        {/* ZONA EXCLUSIVA DE SCROLL */}
        <div className="chat-terminal">
          {mensajes.map((msg, idx) => (
            <div key={idx} className={`burbuja-mensaje ${msg.rol} ${msg.cancelado ? 'mensaje-abortado' : ''}`}>

              {/* --- NUEVA CABECERA CON ETIQUETAS --- */}
              <div className="remitente" style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <span>{msg.rol === 'ia' ? '> L-IA:' : msg.rol === 'sistema' ? '> SYS:' : '> TÚ:'}</span>

                {/* ETIQUETA DE MODELO (Local, Nube, Dolphin) */}
                {msg.rol === 'ia' && msg.origen && (
                  <span className={`badge-origen ${msg.origen.toLowerCase()}`}>
                    {msg.origen.toUpperCase()}
                  </span>
                )}

                {/* ETIQUETA DE DOCUMENTO ACTIVO */}
                {msg.rol === 'ia' && msg.documento && (
                  <span className="badge-doc">
                    📄 {msg.documento}
                  </span>
                )}
              </div>
              {/* ---------------------------------- */}

              <div className="contenido-markdown">
                {msg.rol === 'ia' ? (
                  <ReactMarkdown>{msg.texto}</ReactMarkdown>
                ) : (
                  msg.texto
                )}
              </div>
            </div>
          ))}
          <div ref={finalDelChatRef} />
        </div>

        {/* CONTROLES ESTÁTICOS (NO HACEN SCROLL) */}
        <form onSubmit={manejarEnvio} className="controles-input">
          <input type="file" ref={archivoInputRef} style={{ display: 'none' }} onChange={manejarSeleccionArchivo} />
          <button type="button" className="hud-btn" onClick={manejarClickArchivo}><Paperclip size={18} /></button>
          <button type="button" className="hud-btn" onClick={manejarMicrofono} style={{ color: escuchando ? '#ff0055' : '#00ffff', boxShadow: escuchando ? 'inset 0 0 10px rgba(255,0,85,0.5)' : '' }}>
            <Mic size={18} />
          </button>
          
          <textarea 
            className="hud-input custom-scrollbar" 
            placeholder="Ingresa texto..." 
            value={input} 
            onChange={(e) => {
              setInput(e.target.value);
              // Resetea a la altura base para recalcular
              e.target.style.height = '42px'; 
              // Crece suavemente hasta un máximo de 100px
              e.target.style.height = `${Math.min(e.target.scrollHeight, 100)}px`;
            }}
            disabled={cargando}
            rows={1}
            style={{ 
              resize: 'none', 
              overflowY: 'auto', 
              height: '42px', /* Altura fija inicial como el input viejo */
              padding: '10px 15px', 
              lineHeight: '20px',
              fontFamily: 'inherit',
              boxSizing: 'border-box'
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                manejarEnvio();
                // Lo devolvemos a su estado delgado al enviar
                e.target.style.height = '42px'; 
              }
            }}
          />

          {cargando ? (
            <button 
              type="button" 
              className="hud-btn" 
              onClick={detenerGeneracion} 
              style={{ color: '#ff0055', borderColor: '#ff0055', boxShadow: '0 0 10px rgba(255,0,85,0.5)' }}
              title="Abortar Generación"
            >
              🛑
            </button>
          ) : (
            <button type="submit" className="hud-btn animado" disabled={!input.trim() || cargando}>
              <Terminal size={18} />
            </button>
          )}
        </form>
      </div>
    </div>
  )
}

export default App