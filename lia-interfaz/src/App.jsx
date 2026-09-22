import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Mic, Paperclip, Terminal, Cpu, Database, Upload, AlertTriangle } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import './App.css'

// =========================================
// CONFIGURACIÓN VISUAL POR ESTADO DEL NÚCLEO
// =========================================
const CONFIG_ESTADOS = {
  reposo: {
    color: '#00ffff',
    label: 'EN ESPERA',
    giro: 14,
    pulso: 3,
  },
  procesando: {
    color: '#ffaa00',
    label: 'PENSANDO...',
    giro: 2.2,
    pulso: 0.9,
  },
  escribiendo: {
    color: '#39ff88',
    label: 'ESCRIBIENDO...',
    giro: 1.4,
    pulso: 0.5,
  },
  procesando_rag: {
    color: '#ff00ff',
    label: 'ANALIZANDO DOCUMENTO...',
    giro: 1.6,
    pulso: 0.7,
  },
  error: {
    color: '#ff0033',
    label: 'ERROR CRÍTICO',
    giro: 0.6,
    pulso: 0.25,
  },
}

// =========================================
// COMPONENTE: NÚCLEO L-IA (bolita central)
// =========================================
function NucleoLIA({ estado }) {
  const cfg = CONFIG_ESTADOS[estado] || CONFIG_ESTADOS.reposo
  const { color, label, giro, pulso } = cfg

  return (
    <div className="nucleo-wrapper">
      {/* Halo ambiental de fondo, cambia de color suavemente */}
      <motion.div
        className="nucleo-halo"
        animate={{ background: `radial-gradient(circle, ${color}33, transparent 70%)` }}
        transition={{ duration: 0.6 }}
      />

      {/* Anillo de partículas orbitales */}
      <motion.div
        className="anillo-particulas"
        animate={{ rotate: 360 }}
        transition={{ repeat: Infinity, duration: giro * 2.2, ease: 'linear' }}
      >
        {[...Array(6)].map((_, i) => (
          <span
            key={i}
            className="particula"
            style={{
              background: color,
              boxShadow: `0 0 8px ${color}`,
              transform: `rotate(${i * 60}deg) translateX(88px)`,
            }}
          />
        ))}
      </motion.div>

      {/* Anillo exterior punteado */}
      <motion.div
        className="anillo-exterior"
        style={{ borderColor: color }}
        animate={{ rotate: 360 }}
        transition={{ repeat: Infinity, duration: giro, ease: 'linear' }}
      />

      {/* Anillo medio, gira al revés para efecto giroscopio */}
      <motion.div
        className="anillo-medio"
        style={{ borderTopColor: color, borderBottomColor: color }}
        animate={{ rotate: -360 }}
        transition={{ repeat: Infinity, duration: giro * 1.5, ease: 'linear' }}
      />

      {/* Anillo interior, pulsa */}
      <motion.div
        className="anillo-interior"
        style={{ borderColor: color }}
        animate={{ scale: [1, 1.15, 1], opacity: [0.55, 1, 0.55] }}
        transition={{ repeat: Infinity, duration: pulso }}
      />

      {/* Núcleo central con gradiente "vivo" */}
      <motion.div
        className="centro-nucleo"
        style={{
          background: `radial-gradient(circle at 35% 30%, #ffffff, ${color} 65%)`,
          boxShadow: `0 0 25px ${color}, 0 0 55px ${color}66`,
        }}
        animate={{
          scale: estado === 'escribiendo' ? [1, 1.22, 0.94, 1.12, 1] : [1, 1.08, 1],
        }}
        transition={{
          repeat: Infinity,
          duration: estado === 'escribiendo' ? 0.6 : pulso,
          ease: 'easeInOut',
        }}
      />

      {/* Barras estilo ecualizador — solo mientras L-IA escribe */}
      {estado === 'escribiendo' && (
        <div className="barras-voz">
          {[0, 1, 2, 3, 4].map((i) => (
            <motion.span
              key={i}
              style={{ background: color, boxShadow: `0 0 6px ${color}` }}
              animate={{ height: ['20%', '85%', '35%', '65%', '20%'] }}
              transition={{ repeat: Infinity, duration: 0.9, delay: i * 0.09, ease: 'easeInOut' }}
            />
          ))}
        </div>
      )}

      {/* Destello de alerta — solo en error */}
      {estado === 'error' && (
        <motion.div
          className="destello-error"
          animate={{ opacity: [0, 0.5, 0] }}
          transition={{ repeat: Infinity, duration: 0.5 }}
        />
      )}

      {/* Etiqueta de estado, con transición al cambiar */}
      <AnimatePresence mode="wait">
        <motion.div
          key={estado}
          className="etiqueta-estado"
          style={{ color, textShadow: `0 0 8px ${color}99` }}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.25 }}
        >
          {label}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}

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

  // ESTADO DEL SEMÁFORO
  const [semaforo, setSemaforo] = useState({ activa: false, herramienta: '', argumentos: '' })

  useEffect(() => {
    finalDelChatRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [mensajes])

  // Vigía del Semáforo
  useEffect(() => {
    let intervalo;
    // Solo vigila si L-IA está pensando o escribiendo
    if (estadoLIA === 'procesando' || estadoLIA === 'escribiendo') {
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

  // Función para responder al semáforo
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

  const [cargando, setCargando] = useState(false);
  const abortControllerRef = useRef(null);

  const manejarEnvio = async (e) => {
    if (e) e.preventDefault();
    if (!input.trim() || cargando) return;

    const textoUsuario = input;

    setCargando(true);
    abortControllerRef.current = new AbortController();

    setMensajes(prev => [
      ...prev,
      { rol: 'usuario', texto: textoUsuario },
      { rol: 'ia', texto: '', origen: '', documento: null }
    ]);

    setInput('');
    setEstadoLIA('procesando'); // fase 1: esperando que el núcleo "piense"

    let huboError = false;

    try {
      const respuesta = await fetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texto: textoUsuario }),
        signal: abortControllerRef.current.signal
      });

      const reader = respuesta.body.getReader()
      const decoder = new TextDecoder("utf-8")
      let buffer = ""
      let yaEscribiendo = false

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
                // fase 2: en cuanto llega el primer chunk, pasamos a "escribiendo"
                if (!yaEscribiendo) {
                  yaEscribiendo = true
                  setEstadoLIA('escribiendo')
                }

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
                huboError = true
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

    } catch (error) {
      if (error.name === 'AbortError') {
        setMensajes(prev => {
          const nuevos = [...prev];
          nuevos[nuevos.length - 1].texto += '\n\n*(Respuesta abortada)*';
          nuevos[nuevos.length - 1].cancelado = true;
          return nuevos;
        });
      } else {
        huboError = true;
        setMensajes(prev => {
          const nuevos = [...prev];
          nuevos[nuevos.length - 1].texto += '\n\n[ERROR] Caída del enlace con el núcleo.';
          return nuevos;
        });
      }
    } finally {
      setCargando(false);
      if (huboError) {
        // fase de error: el núcleo destella en rojo un momento antes de calmarse
        setEstadoLIA('error');
        setTimeout(() => setEstadoLIA('reposo'), 1600);
      } else {
        setEstadoLIA('reposo');
      }
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
      setEstadoLIA('reposo')
    } catch (error) {
      setMensajes(prev => [...prev, { rol: 'sistema', texto: '[ERROR] Fallo en RAG.' }])
      setEstadoLIA('error')
      setTimeout(() => setEstadoLIA('reposo'), 1600)
    }
  }

  const manejarDragOver = (e) => { e.preventDefault(); if (!isDragging) setIsDragging(true) }
  const manejarDragLeave = (e) => { e.preventDefault(); setIsDragging(false) }
  const manejarDrop = (e) => { e.preventDefault(); setIsDragging(false); if (e.dataTransfer.files.length > 0) procesarArchivoRAG(e.dataTransfer.files[0]) }
  const manejarClickArchivo = () => archivoInputRef.current?.click()
  const manejarSeleccionArchivo = (e) => { if (e.target.files.length > 0) procesarArchivoRAG(e.target.files[0]); e.target.value = null }

  const manejarMicrofono = () => {
    setEscuchando(!escuchando)
  }

  const detenerGeneracion = async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setCargando(false);

    try {
      await fetch("http://127.0.0.1:8000/cancelar", { method: "POST" });
    } catch (error) {
      console.error("Error al abortar en el backend:", error);
    }
  };

  return (
    <div className="hud-container" onDragOver={manejarDragOver} onDragLeave={manejarDragLeave} onDrop={manejarDrop}>

      {/* CAPA DE DRAG & DROP */}
      {isDragging && (
        <div className="capa-drag">
          <Upload size={40} />
          <p>Suelta el archivo para ingestarlo</p>
        </div>
      )}

      {/* MODAL DEL SEMÁFORO */}
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

              <pre className="codigo-alerta custom-scrollbar" style={{
                whiteSpace: 'pre-wrap',
                wordWrap: 'break-word',
                textAlign: 'left',
                maxHeight: '180px',
                overflowY: 'auto',
                fontSize: '13px',
                lineHeight: '1.5',
                margin: '0 0 20px 0'
              }}>
                {(() => {
                  if (!semaforo.argumentos) return "Ninguno";
                  try {
                    const obj = typeof semaforo.argumentos === 'string'
                      ? JSON.parse(semaforo.argumentos)
                      : semaforo.argumentos;
                    return JSON.stringify(obj, null, 2);
                  } catch (e) {
                    return semaforo.argumentos;
                  }
                })()}
              </pre>

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
        <NucleoLIA estado={estadoLIA} />

        {/* ZONA EXCLUSIVA DE SCROLL */}
        <div className="chat-terminal">
          {mensajes.map((msg, idx) => (
            <div key={idx} className={`burbuja-mensaje ${msg.rol} ${msg.cancelado ? 'mensaje-abortado' : ''}`}>

              <div className="remitente" style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <span>{msg.rol === 'ia' ? '> L-IA:' : msg.rol === 'sistema' ? '> SYS:' : '> TÚ:'}</span>

                {msg.rol === 'ia' && msg.origen && (
                  <span className={`badge-origen ${msg.origen.toLowerCase()}`}>
                    {msg.origen.toUpperCase()}
                  </span>
                )}

                {msg.rol === 'ia' && msg.documento && (
                  <span className="badge-doc">
                    📄 {msg.documento}
                  </span>
                )}
              </div>

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
              e.target.style.height = '42px';
              e.target.style.height = `${Math.min(e.target.scrollHeight, 100)}px`;
            }}
            disabled={cargando}
            rows={1}
            style={{
              resize: 'none',
              overflowY: 'auto',
              height: '42px',
              padding: '10px 15px',
              lineHeight: '20px',
              fontFamily: 'inherit',
              boxSizing: 'border-box'
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                manejarEnvio();
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