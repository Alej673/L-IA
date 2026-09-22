import React, { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Mic, Paperclip, Terminal, Cpu, Database, Upload, AlertTriangle, Activity, ShieldAlert } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import './App.css'

// =========================================
// CONFIGURACIÓN VISUAL POR ESTADO DEL NÚCLEO
// (Se mantiene intacta tu configuración)
// =========================================
const CONFIG_ESTADOS = {
  reposo: { tonos: ['#00ffff', '#33e0ff', '#00d4ff', '#33e0ff'], label: 'EN ESPERA', icon: Mic, giro: 14, pulso: 3 },
  procesando: { tonos: ['#ffaa00', '#ff8800', '#ffcc33', '#ff9500'], label: 'PENSANDO...', icon: Cpu, giro: 2.2, pulso: 0.9 },
  escribiendo: { tonos: ['#39ff88', '#00ffc3', '#7bffb0', '#22ffaa'], label: 'ESCRIBIENDO...', icon: Activity, giro: 1.4, pulso: 0.5 },
  procesando_rag: { tonos: ['#ff00ff', '#cc00ff', '#ff55ff', '#e000e6'], label: 'ANALIZANDO DOCUMENTO...', icon: Database, giro: 1.6, pulso: 0.7 },
  error: { tonos: ['#ff0033', '#ff5500', '#ff0055', '#ff2200'], label: 'ERROR CRÍTICO', icon: ShieldAlert, giro: 0.6, pulso: 0.25 },
}

function useCicloDeTono(tonos, intervaloMs = 1800) {
  const [indice, setIndice] = useState(0)
  useEffect(() => {
    setIndice(0)
    const id = setInterval(() => setIndice(i => (i + 1) % tonos.length), intervaloMs)
    return () => clearInterval(id)
  }, [tonos, intervaloMs])
  return tonos[indice]
}

// =========================================
// NÚCLEO LIA: Animación central fusionada
// =========================================
function NucleoLIA({ estado }) {
  const cfg = CONFIG_ESTADOS[estado] || CONFIG_ESTADOS.reposo;
  const { label, giro, pulso, tonos } = cfg;
  const color = useCicloDeTono(tonos, estado === 'error' ? 600 : 1800);
  const colorRostro = '#021017'; // Un poco más oscuro para mejor contraste

  // --- ESTADOS BASE Y TRACKING (Los tuyos) ---
  const [parpadeo, setParpadeo] = useState(false);
  const [mouseOffset, setMouseOffset] = useState({ x: 0, y: 0 });
  const [miradaAleatoria, setMiradaAleatoria] = useState({ x: 0, y: 0 });
  const [tiempoInactiva, setTiempoInactiva] = useState(0);

  // --- NUEVO: Evolución del aburrimiento ---
  // Reemplazamos el booleano 'aburrida' por niveles: 'normal', 'bostezo', 'durmiendo'
  const [subEstado, setSubEstado] = useState('normal'); 

  // 1. Manejador Global de Movimiento del Ratón (Tu código)
  useEffect(() => {
    const handleMouseMove = (e) => {
      setSubEstado('normal'); // Despierta al mover el ratón
      setTiempoInactiva(0);
      setMiradaAleatoria({ x: 0, y: 0 });

      const windowCenterX = window.innerWidth / 2;
      const windowCenterY = window.innerHeight / 2;
      const offsetX = (e.clientX - windowCenterX) / 50; 
      const offsetY = (e.clientY - windowCenterY) / 70;
      const limit = (val, max) => Math.min(Math.max(val, -max), max);
      
      setMouseOffset({ x: limit(offsetX, 12), y: limit(offsetY, 8) });
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  // 2. Temporizador Fusionado (Miradas + Bostezo + Dormir)
  useEffect(() => {
    let intervaloTiempo = null;
    let intervaloAccion = null;

    if (estado === 'reposo') {
      // Contador general
      intervaloTiempo = setInterval(() => {
        setTiempoInactiva(prev => {
          const nuevoTiempo = prev + 1;
          // Evolución del aburrimiento
          if (nuevoTiempo > 30) setSubEstado('durmiendo'); // A los 30s se duerme
          else if (nuevoTiempo === 20) setSubEstado('bostezo'); // A los 20s da un bostezo largo
          else if (nuevoTiempo > 23 && nuevoTiempo < 30) setSubEstado('normal'); // Termina de bostezar
          return nuevoTiempo;
        });
      }, 1000);

      // Miradas aleatorias solo si NO está durmiendo
      intervaloAccion = setInterval(() => {
        if (subEstado !== 'durmiendo' && tiempoInactiva > 2 && tiempoInactiva < 20) {
          setMiradaAleatoria({
             x: (Math.random() - 0.5) * 8, 
             y: (Math.random() - 0.5) * 4  
          });
          setTimeout(() => setMiradaAleatoria({ x: 0, y: 0 }), Math.random() * 2000 + 1000);
        }
      }, 4000);
    }

    return () => {
      clearInterval(intervaloTiempo);
      clearInterval(intervaloAccion);
    };
  }, [estado, subEstado, tiempoInactiva]);

  // 3. Parpadeo Orgánico (Se detiene si está dormida)
  useEffect(() => {
    const intervaloParpadeo = setInterval(() => {
      if (subEstado !== 'durmiendo') {
        setParpadeo(true);
        setTimeout(() => setParpadeo(false), 150);
      }
    }, Math.random() * 4000 + 2000);
    return () => clearInterval(intervaloParpadeo);
  }, [subEstado]);

  // --- EXPRESIONES FACIALES FUSIONADAS ---
  const getOjos = () => {
    if (parpadeo || subEstado === 'durmiendo') return { height: '2px', width: '10px', y: 4, rotate: 0, borderRadius: '2px', scaleY: 1 };
    if (subEstado === 'bostezo') return { height: '3px', width: '9px', y: -1, rotate: -12, borderRadius: '2px', scaleY: 1 };

    if (estado === 'error') return { height: '7px', width: '10px', y: 0, rotate: 18, borderRadius: '4px', scaleY: 1 };
    if (estado === 'procesando' || estado === 'procesando_rag') return { height: '10px', width: '10px', y: -2, rotate: 0, borderRadius: '50%', scaleY: 1 };
    if (estado === 'escribiendo') return { height: '8px', width: '9px', y: -2, rotate: -6, borderRadius: '4px 4px 50% 50%', scaleY: 1 };

    // Reposo / Normal: Ojos circulares/ligeramente ovalados
    return { height: '9px', width: '9px', y: 0, rotate: 0, borderRadius: '50%', scaleY: 1 };
  }

  const getBoca = () => {
    if (subEstado === 'durmiendo') return { width: '6px', height: '2px', borderRadius: '1px', scaleY: 1, rotate: 0, y: 3 };
    if (subEstado === 'bostezo') return { width: '10px', height: '14px', borderRadius: '40%', scaleY: 1.2, rotate: 0, y: 0 };

    if (estado === 'error') return { width: '12px', height: '3px', borderRadius: '2px', scaleY: 1, rotate: -10, y: 0 };
    if (estado === 'escribiendo') return { width: '16px', height: '6px', borderRadius: '3px 3px 10px 10px', scaleY: [1, 1.5, 0.8, 1.3], rotate: 0, y: 0 };
    if (estado === 'procesando' || estado === 'procesando_rag') return { width: '5px', height: '5px', borderRadius: '50%', scaleY: 1, rotate: 0, y: 0 };

    // Reposo / Normal: leve sonrisa (esquinas inferiores más curvas que las superiores)
    return { width: '11px', height: '4px', borderRadius: '1px 1px 8px 8px', scaleY: 1, rotate: 0, y: 1 };
  }

  const ojosCfg = getOjos();
  const bocaCfg = getBoca();

  // El desplazamiento final de la cara respeta tu lógica de Parallax
  const faceOffset = estado === 'reposo' && subEstado !== 'durmiendo'
        ? { x: mouseOffset.x + miradaAleatoria.x, y: mouseOffset.y + miradaAleatoria.y } 
        : { x: 0, y: subEstado === 'durmiendo' ? 4 : 0 }; // Si duerme, la cara cae un poco al centro-abajo

  return (
    <div className="nucleo-wrapper">
      <div className="nucleo-halo" style={{ background: `radial-gradient(circle, ${color}33, transparent 70%)` }} />

      {/* Anillos Orbitales */}
      <motion.div className="anillo-particulas" animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: giro * 2.2, ease: 'linear' }}>
        {[...Array(6)].map((_, i) => (
          <span key={i} className="particula" style={{ background: color, boxShadow: `0 0 8px ${color}`, transform: `rotate(${i * 60}deg) translateX(88px)` }} />
        ))}
      </motion.div>

      <motion.div className="anillo-exterior" style={{ borderColor: color }} animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: giro, ease: 'linear' }} />
      <motion.div className="anillo-medio" style={{ borderTopColor: color, borderBottomColor: color }} animate={{ rotate: -360 }} transition={{ repeat: Infinity, duration: giro * 1.5, ease: 'linear' }} />
      <motion.div className="anillo-interior" style={{ borderColor: color }} animate={{ scale: [1, 1.15, 1], opacity: [0.55, 1, 0.55] }} transition={{ repeat: Infinity, duration: pulso }} />

      {/* Núcleo Central */}
      <motion.div
        className="centro-nucleo"
        style={{
          background: `radial-gradient(circle at 45% 35%, #ffffff 0%, #a6ffff 30%, ${color} 80%)`,
          boxShadow: `0 0 25px ${color}, 0 0 55px ${color}66`,
          overflow: 'visible' // CRÍTICO: Inyectado aquí para que las Zzz puedan salir de la esfera
        }}
        animate={{
          scale: estado === 'escribiendo' ? [1, 1.22, 0.94, 1.12, 1] : 
                 subEstado === 'bostezo' ? [1, 1.14, 0.96, 1] : 
                 [1, 1.08, 1],
          opacity: subEstado === 'durmiendo' ? 0.75 : 1
        }}
        transition={{ repeat: Infinity, duration: subEstado === 'bostezo' ? 2.5 : pulso, ease: 'easeInOut' }}
      >
        
        {/* Generador de Partículas Zzz */}
        {subEstado === 'durmiendo' && (
          <div style={{ position: 'absolute', top: '-10px', right: '-10px', zIndex: 10 }}>
            {[0, 1, 2].map((i) => (
              <motion.span
                key={i}
                className="particula-zzz"
                style={{ color, position: 'absolute', textShadow: `0 0 8px ${color}` }}
                initial={{ opacity: 0, y: 0, x: 0, scale: 0.6 }}
                animate={{ opacity: [0, 1, 0], y: -20 - (i * 12), x: 10 + (i * 8), scale: [0.6, 1.2, 0.8] }}
                transition={{ repeat: Infinity, duration: 2.6, delay: i * 0.8, ease: 'easeOut' }}
              >
                Z
              </motion.span>
            ))}
          </div>
        )}

        {/* Escáner RAG */}
        {estado === 'procesando_rag' && (
          <div className="escaner-rag">
            <motion.div className="escaner-rag-barra" animate={{ top: ['-10%', '110%'] }} transition={{ repeat: Infinity, duration: 1.3, ease: 'linear' }} />
          </div>
        )}

        {/* Rostro con Parallax */}
        <motion.div 
          className="rostro-holografico"
          animate={{ x: faceOffset.x, y: faceOffset.y }}
          transition={{ type: "spring", stiffness: 120, damping: 20 }}
        >
          <div className="fila-ojos">
            {/* Ojo Izquierdo: Pasamos el objeto directamente para evitar redundancias */}
            <motion.div className="ojo" style={{ background: colorRostro }} animate={ojosCfg} transition={{ duration: 0.15 }} />
            {/* Ojo Derecho: Invertimos la rotación para simetría */}
            <motion.div className="ojo" style={{ background: colorRostro }} animate={{ ...ojosCfg, rotate: -ojosCfg.rotate }} transition={{ duration: 0.15 }} />
          </div>
          <motion.div className="boca" style={{ background: colorRostro }} animate={bocaCfg} transition={{ duration: estado === 'escribiendo' ? 0.45 : 0.2, repeat: estado === 'escribiendo' ? Infinity : 0, ease: 'easeInOut' }} />
        </motion.div>
      </motion.div>

      {/* Barras Ecualizador */}
      {estado === 'escribiendo' && (
        <div className="barras-voz">
          {[0, 1, 2, 3, 4].map((i) => (
            <motion.span key={i} style={{ background: color, boxShadow: `0 0 6px ${color}` }} animate={{ height: ['20%', '85%', '35%', '65%', '20%'] }} transition={{ repeat: Infinity, duration: 0.9, delay: i * 0.09, ease: 'easeInOut' }} />
          ))}
        </div>
      )}

      {/* Destello Error */}
      {estado === 'error' && (
        <motion.div className="destello-error" style={{ borderColor: color }} animate={{ opacity: [0, 0.5, 0], scale: [1, 1.08, 1] }} transition={{ repeat: Infinity, duration: 0.5 }} />
      )}

      {/* Etiqueta Inferior */}
      <AnimatePresence mode="wait">
        <motion.div key={estado} className="etiqueta-estado" style={{ color, textShadow: `0 0 8px ${color}99` }} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.25 }}>
          {subEstado === 'durmiendo' ? 'MODO REPOSO' : label}
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
        // fase de error: el núcleo destella un momento antes de calmarse
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