import React, { useState, useEffect, useRef, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import './App.css'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { Mic, Paperclip, Terminal, Upload, AlertTriangle, ShieldAlert, MessageSquare, Plus, Folder, Pencil, Trash2, Check, X, Menu, Volume2, VolumeX, Copy, Square } from 'lucide-react'
import { motion, AnimatePresence, useDragControls } from 'framer-motion'
import NucleoLIA from './NucleoLIA'
import ColapsoSistema from './ColapsoSistema'
import { invoke } from '@tauri-apps/api/core';

const API = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:10500'

// Extensiones que el backend sabe leer (ajústalas a tu /ingestar)
const EXTENSIONES_VALIDAS = ['txt', 'md', 'py', 'js', 'php', 'html', 'css', 'json', 'docx', 'pdf']

// Estados visuales permitidos que el backend (SSOT) puede sincronizar vía SSE
const ESTADOS_VISUALES_BACKEND = new Set([
  'procesando_pregunta',
  'procesando_sistema',
  'procesando_git',
  'procesando_doc',
  'procesando_rag',
])

const MENSAJE_INICIAL = 'L-IA v3.2.1 inicializada. Esperando directivas...'

const nuevoId = () =>
  (typeof crypto !== 'undefined' && crypto.randomUUID)
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`

const mensajeInicial = () => ({ id: nuevoId(), rol: 'ia', texto: MENSAJE_INICIAL })

// Polling sin solapamiento: espera a que termine la petición anterior
// antes de programar la siguiente (a diferencia de setInterval + fetch).
function usePolling(callback, intervaloMs, activo = true) {
  const cbRef = useRef(callback)
  useEffect(() => { cbRef.current = callback })

  useEffect(() => {
    if (!activo) return
    let cancelado = false
    let timer
    const tick = async () => {
      try { await cbRef.current() } catch (e) { /* backend caído: reintenta en el siguiente ciclo */ }
      if (!cancelado) timer = setTimeout(tick, intervaloMs)
    }
    timer = setTimeout(tick, intervaloMs)
    return () => { cancelado = true; clearTimeout(timer) }
  }, [intervaloMs, activo])
}

// Quita markdown para que el TTS no lea símbolos ni código
const limpiarMarkdownParaVoz = (md = '') =>
  md
    .replace(/```[\s\S]*?```/g, ' (bloque de código omitido). ')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/!\[[^\]]*\]\([^)]*\)/g, '')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/https?:\/\/\S+/g, '')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/(\*\*|__|\*)/g, '')
    .replace(/^\s*[-+*]\s+/gm, '')
    .replace(/^\s*>\s?/gm, '')
    .replace(/\n{2,}/g, '\n')
    .trim()

// Lector de voz: un solo mensaje a la vez, con "token" para ignorar respuestas viejas
function useLectorVoz() {
  const [idLeyendo, setIdLeyendo] = useState(null)
  const timerRef = useRef(null)
  const tokenRef = useRef(0)

  const detener = useCallback(async () => {
    clearTimeout(timerRef.current)
    tokenRef.current += 1
    setIdLeyendo(null)
    try {
      // Silencia solo la salida de voz sin abortar el chat
      await fetch(`${API}/voz/silenciar`, { method: 'POST' })
    } catch (e) {
      console.error('Error al detener lectura:', e)
    }
  }, [])

  const alternar = useCallback(async (texto, id) => {
    if (idLeyendo === id) return detener()          // mismo mensaje: apagar
    if (idLeyendo !== null) await detener()          // otro sonando: cortarlo

    const limpio = limpiarMarkdownParaVoz(texto)
    if (!limpio) return

    const miToken = ++tokenRef.current
    setIdLeyendo(id) // feedback visual inmediato

    try {
      const res = await fetch(`${API}/lector`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ texto: limpio })
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      if (miToken !== tokenRef.current) return // se canceló mientras esperábamos

      // Estimación: el backend aún no informa cuándo termina el audio
      const ms = limpio.split(/\s+/).length * 350 + 2000
      timerRef.current = setTimeout(() => {
        if (miToken === tokenRef.current) setIdLeyendo(null)
      }, ms)
    } catch (e) {
      console.error('Error al invocar el lector:', e)
      if (miToken === tokenRef.current) setIdLeyendo(null)
    }
  }, [idLeyendo, detener])

  useEffect(() => () => clearTimeout(timerRef.current), [])

  return { idLeyendo, alternar, detener }
}

// Bloques de código vs código en línea
function BloqueDeCodigo({ node, className, children, ...props }) {
  const [copiado, setCopiado] = useState(false)

  const match = /language-(\w+)/.exec(className || '')
  const lenguaje = match ? match[1] : 'text'
  const codigoString = String(children).replace(/\n$/, '')

  // Un bloque con fence ocupa varias líneas en el markdown original,
  // aunque su contenido sea de una sola línea.
  const ocupaVariasLineas = node?.position && node.position.start.line !== node.position.end.line
  const esBloque = Boolean(match) || codigoString.includes('\n') || Boolean(ocupaVariasLineas)

  if (!esBloque) {
    return (
      <code className="codigo-inline" {...props}>
        {children}
      </code>
    )
  }

  const manejarCopia = async () => {
    try {
      await navigator.clipboard.writeText(codigoString)
      setCopiado(true)
      setTimeout(() => setCopiado(false), 2000)
    } catch (err) {
      console.error('Error al copiar', err)
    }
  }

  return (
    <div className="bloque-codigo">
      <div className="bloque-codigo-header">
        <span className="bloque-codigo-lang">
          {lenguaje}
        </span>
        <button
          type="button"
          onClick={manejarCopia}
          className={`bloque-codigo-copiar ${copiado ? 'copiado' : ''}`}
        >
          {copiado ? <><Check size={12} /> COPIADO</> : <><Copy size={12} /> COPIAR</>}
        </button>
      </div>

      {/* Sin {...props}: son props de <code> y no le corresponden al highlighter */}
      <SyntaxHighlighter
        style={vscDarkPlus}
        language={lenguaje}
        PreTag="div"
        customStyle={{
          margin: 0,
          padding: '12px 14px',
          background: 'transparent',
          fontSize: '12.5px',
          lineHeight: '1.5'
        }}
      >
        {codigoString}
      </SyntaxHighlighter>
    </div>
  )
}

// =========================================
// APP: INTERFAZ PRINCIPAL
// =========================================
export default function App() {
  const [estadoLIA, setEstadoLIA] = useState('reposo')
  const [input, setInput] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const [escuchando, setEscuchando] = useState(false)
  const [mensajes, setMensajes] = useState(() => [mensajeInicial()])
  const [mensajeEspera, setMensajeEspera] = useState(null)
  const [workspaceActivo, setWorkspaceActivo] = useState(null)
  const [vozGlobal, setVozGlobal] = useState(false)
  const [modoColapso, setModoColapso] = useState(false);
  const [comandoColapso, setComandoColapso] = useState(null);

  // ==========================================
  // BOTÓN DEBUG: LLAMAR AL GUION DE FORMA SILENCIOSA-ELIMINAR DESPUES DE PRUEBAS
  // ==========================================
  const simularColapsoVisual = async () => {
    // EL BOTÓN SOLO HACE LA PETICIÓN. CERO CAMBIOS VISUALES AQUÍ.
    try {
      const respuesta = await fetch(`${API}/debug/forzar_fase_1`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!respuesta.ok || !respuesta.body) throw new Error(`HTTP ${respuesta.status}`);

      const reader = respuesta.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const partes = buffer.split('\n\n');
        buffer = partes.pop();

        for (const parte of partes) {
          if (!parte.startsWith('data: ')) continue;
          
          if (parte.endsWith('|||')) {
            try {
              const jsonStr = parte.slice(6, -3); 
              const trigger = JSON.parse(jsonStr);
              setComandoColapso(trigger);

              // 👉 AQUÍ OCURRE LA MAGIA DIRIGIDA POR PYTHON
              if (trigger.comando === 'INICIAR_COLAPSO') {
                setModoColapso(true); // 1. Muestra el componente rojo
                invoke('activar_modo_invasivo').catch(console.error); // 2. Secuestra el monitor
              }
              else if (trigger.comando === 'RESTAURAR_SISTEMA') {
                invoke('restaurar_ventana').catch(console.error);
                setModoColapso(false);
              }
            } catch (e) {
              console.error("Error parseando trigger anómalo", e);
            }
          } else {
            // Atrapamos el fin de la película para soltar la pantalla
            try {
              const data = JSON.parse(parte.slice(6));
              if (data.tipo === 'fin' || data.tipo === 'error') {
                invoke('restaurar_ventana').catch(console.error);
                setModoColapso(false);
                setComandoColapso({ comando: 'RESET' });
              }
            } catch (e) {}
          }
        }
      }
    } catch (error) {
      console.error("Error en el canal silencioso:", error);
    }
  };

  // Multi-sesión
  const [sesiones, setSesiones] = useState([])
  const [sesionActual, setSesionActual] = useState('default')
  const [sidebarAbierto, setSidebarAbierto] = useState(false)
  const [editandoSesion, setEditandoSesion] = useState(null)
  const [tituloTemp, setTituloTemp] = useState('')

  const [semaforo, setSemaforo] = useState({ activa: false, herramienta: '', argumentos: '' })
  const [cargando, setCargando] = useState(false)
  const [semaforoArchivos, setSemaforoArchivos] = useState({ activa: false, opciones: [] }) // NUEVO
  const [feedbackDecision, setFeedbackDecision] = useState(null)
  const feedbackTimerRef = useRef(null)

  const finalDelChatRef = useRef(null)
  const archivoInputRef = useRef(null)
  const textareaRef = useRef(null)
  const dragContador = useRef(0)
  const abortControllerRef = useRef(null)
  const overlayRef = useRef(null)
  const dragControls = useDragControls()

  // Refs para que los pollings usen siempre el valor más reciente
  const cargandoRef = useRef(false)
  cargandoRef.current = cargando
  const enviarOrdenRef = useRef(null)
  const vozGlobalRef = useRef(vozGlobal)
  vozGlobalRef.current = vozGlobal
  const escuchaTokenRef = useRef(0)
  const escucharAbortRef = useRef(null)
  const ultimoEventoTactilRef = useRef({})

  // Lector de voz
  const { idLeyendo, alternar: alternarLectura, detener: detenerLectura } = useLectorVoz()

  // Al cambiar de sesión, corta la lectura
  useEffect(() => {
    if (idLeyendo !== null) detenerLectura()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sesionActual])

  // ---------- Helpers de estado inmutable ----------
  const actualizarUltimoMensaje = (fn) => {
    setMensajes(prev => {
      if (prev.length === 0) return prev
      const copia = [...prev]
      copia[copia.length - 1] = fn(copia[copia.length - 1])
      return copia
    })
  }

  const agregarSistema = (texto) =>
    setMensajes(prev => [...prev, { id: nuevoId(), rol: 'sistema', texto }])

  const nombreDeRuta = (ruta) => (ruta ? String(ruta).split(/[\\/]/).pop() : null)

  useEffect(() => {
    finalDelChatRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [mensajes])

  // Freno de emergencia al cerrar la ventana
  useEffect(() => {
    const matarAudioAlCerrar = () => {
      fetch(`${API}/cancelar`, { method: 'POST', keepalive: true }).catch(() => {})
    }
    window.addEventListener('beforeunload', matarAudioAlCerrar)
    return () => window.removeEventListener('beforeunload', matarAudioAlCerrar)
  }, [])

  // =========================================
  // MULTI-SESIÓN
  // =========================================
  const cargarSesiones = async () => {
    try {
      const res = await fetch(`${API}/sesiones`)
      if (res.ok) setSesiones(await res.json())
    } catch (e) {
      console.error('Fallo al cargar lista de sesiones', e)
    }
  }

  const cargarContextoSesion = async (idSesion) => {
    try {
      const res = await fetch(`${API}/sesiones/${idSesion}/contexto`)
      if (!res.ok) return
      const data = await res.json()
      const mapeados = (data.historial || []).map(m => ({
        id: nuevoId(),
        rol: m.rol === 'model' ? 'ia' : 'usuario',
        texto: m.mensaje
      }))
      if (mapeados.length === 0) mapeados.push(mensajeInicial())
      // Solo cambiamos de sesión cuando el contexto llegó bien
      setSesionActual(idSesion)
      setMensajes(mapeados)
      setWorkspaceActivo(nombreDeRuta(data.workspace_activo))
    } catch (e) {
      console.error('Fallo al cargar contexto de sesión', e)
    }
  }

  const crearNuevaSesion = async () => {
    if (cargando) return
    try {
      const res = await fetch(`${API}/sesiones/nueva`, { method: 'POST' })
      if (res.ok) {
        const data = await res.json()
        await cargarSesiones()
        cargarContextoSesion(data.sesion_id)
      }
    } catch (e) {
      console.error('Fallo al crear sesión', e)
    }
  }

  const guardarNuevoTitulo = async (id, e) => {
    if (e) e.stopPropagation()
    if (!tituloTemp.trim()) { setEditandoSesion(null); return }
    try {
      const res = await fetch(`${API}/sesiones/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ titulo: tituloTemp })
      })
      if (!res.ok) {
        console.error('Error renombrando. Status:', res.status)
        return
      }
      setEditandoSesion(null)
      cargarSesiones()
    } catch (err) {
      console.error('Error renombrando', err)
    }
  }

  const eliminarSesion = async (id, e) => {
    e.stopPropagation()
    if (cargando) return
    try {
      const res = await fetch(`${API}/sesiones/${id}`, { method: 'DELETE' })
      // El backend responde 200 incluso al fallar: hay que mirar data.status
      const data = await res.json().catch(() => ({}))
      if (!res.ok || data.status === 'error') {
        console.error('No se pudo borrar la sesión:', data.detalle || res.status)
        agregarSistema('[ERROR] No se pudo borrar la conversación.')
        return
      }
      if (sesionActual === id) await cargarContextoSesion('default')
      cargarSesiones()
    } catch (err) {
      console.error('Fallo de red al borrar sesión', err)
      agregarSistema('[ERROR] Fallo de red al borrar la conversación.')
    }
  }

  // Al montar: lista de pestañas + historial de "default"
  useEffect(() => {
    cargarSesiones()
    cargarContextoSesion('default')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Evita que el webview abra el archivo si se suelta fuera de la zona de drop
  useEffect(() => {
    const bloquear = (e) => {
      if (Array.from(e.dataTransfer?.types || []).includes('Files')) e.preventDefault()
    }
    window.addEventListener('dragover', bloquear)
    window.addEventListener('drop', bloquear)
    return () => {
      window.removeEventListener('dragover', bloquear)
      window.removeEventListener('drop', bloquear)
    }
  }, [])

  // =========================================
  // POLLING: Semáforo y Radar de voz
  // =========================================
  const piensaOEscribe = estadoLIA === 'escribiendo' || estadoLIA.startsWith('procesando')

  usePolling(async () => {
    const res = await fetch(`${API}/semaforo`)
    if (!res.ok) return
    const data = await res.json()
    if (data.activa) setSemaforo(data)
  }, 1000, piensaOEscribe && !semaforo.activa)

  // Polling ultra rápido (300ms) para que la reacción al "Oye Lía" se sienta instantánea
  usePolling(async () => {
    if (cargandoRef.current) return
    const res = await fetch(`${API}/radar/leer`)
    if (!res.ok) return
    const data = await res.json()
    
    if (data.hay_mensaje && data.datos) {
      if (data.datos.accion === 'despertar') {
        // Vosk detectó el nombre: activamos el HUD instantáneamente
        setEstadoLIA('escuchando')
        setEscuchando(true)
        setVozGlobal(true)
      } 
      else if (data.datos.accion === 'ejecutar') {
        // Whisper terminó de transcribir: enviamos el texto
        enviarOrdenRef.current?.(data.datos.texto, true)
        setEscuchando(false)
      } 
      else if (data.datos.accion === 'cancelar') {
        // Fue un falso positivo, volvemos a la normalidad
        setEstadoLIA('reposo')
        setEscuchando(false)
      }
    }
  }, 300, !cargando)

  usePolling(async () => {
    const res = await fetch(`${API}/semaforo/archivos`)
    if (!res.ok) return
    const data = await res.json()
    if (data.activa) setSemaforoArchivos(data)
  }, 1000, piensaOEscribe && !semaforoArchivos.activa)

  useEffect(() => () => clearTimeout(feedbackTimerRef.current), [])

  const dispararFeedbackDecision = useCallback((tipo, origen) => {
    clearTimeout(feedbackTimerRef.current)
    setFeedbackDecision({ tipo, origen, id: Date.now() })
    feedbackTimerRef.current = setTimeout(() => {
      setFeedbackDecision(null)
    }, 1100)
  }, [])

  // 'caricia' reduce corrupción; 'poke_advertencia' y 'escudo_paciencia' se registran aparte con cooldown
  const manejarInteraccionNucleo = useCallback((evento) => {
    const tipo = evento?.tipo
    if (tipo === 'caricia') {
      fetch(`${API}/interaccion/caricia`, { method: 'POST' }).catch((e) => {
        console.warn('No se pudo registrar caricia en el núcleo:', e)
      })
      return
    }

    if (tipo !== 'poke_advertencia' && tipo !== 'escudo_paciencia') return

    const cooldownMs = tipo === 'escudo_paciencia' ? 8000 : 5000
    const ahora = performance.now()
    if (ahora - (ultimoEventoTactilRef.current[tipo] || 0) < cooldownMs) return
    ultimoEventoTactilRef.current[tipo] = ahora

    fetch(`${API}/interaccion/nucleo`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tipo, clics: evento.clics ?? 0 }),
    })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data?.aplicado && data?.mensaje) agregarSistema(data.mensaje)
      })
      .catch((e) => {
        console.warn(`No se pudo registrar interacción '${tipo}':`, e)
      })
  }, [])

  const responderSemaforoArchivos = async (rutaSeleccionada) => {
    try {
      const res = await fetch(`${API}/semaforo/archivos/responder`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ruta: rutaSeleccionada })
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setSemaforoArchivos({ activa: false, opciones: [] })
      dispararFeedbackDecision(rutaSeleccionada ? 'autorizado' : 'denegado', 'archivos')
    } catch (e) {
      console.error('Fallo al enviar decisión de archivo al núcleo', e)
    }
  }

  const responderSemaforo = async (autorizado) => {
    try {
      const res = await fetch(`${API}/semaforo/responder`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ autorizado })
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setSemaforo({ activa: false, herramienta: '', argumentos: '' })
      dispararFeedbackDecision(autorizado ? 'autorizado' : 'denegado', 'seguridad')
    } catch (e) {
      // Si falla, el modal queda abierto para poder reintentar
      console.error('Fallo al enviar decisión al núcleo', e)
    }
  }

  // =========================================
  // CHAT (texto o voz)
  // =========================================
  const enviarOrden = async (textoAEnviar, activarVoz = false) => {
    if (!textoAEnviar.trim() || cargandoRef.current) return

    setCargando(true)
    cargandoRef.current = true
    const controller = new AbortController()
    abortControllerRef.current = controller

    setMensajes(prev => [
      ...prev,
      { id: nuevoId(), rol: 'usuario', texto: textoAEnviar },
      { id: nuevoId(), rol: 'ia', texto: '', origen: '', documento: null }
    ])

    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = '42px'

    // Estado neutro inicial; el backend (SSOT) sincroniza el estado visual real vía SSE
    setEstadoLIA('procesando_pregunta')
    setMensajeEspera(null)
    let huboError = false
    let colapsoEnTurno = false

    try {
      const respuesta = await fetch(`${API}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ texto: textoAEnviar, sesion_id: sesionActual, usar_voz: activarVoz }),
        signal: controller.signal
      })

      if (!respuesta.ok || !respuesta.body) throw new Error(`HTTP ${respuesta.status}`)

      const reader = respuesta.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''
      let yaEscribiendo = false

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const partes = buffer.split('\n\n')
        buffer = partes.pop()

        for (const parte of partes) {
          if (!parte.startsWith('data: ')) continue

          // ==========================================
          // INTERCEPTOR DE EVENTOS ANÓMALOS (GUION REAL)
          // ==========================================
          if (parte.endsWith('|||')) {
            try {
              const jsonStr = parte.slice(6, -3); 
              const trigger = JSON.parse(jsonStr);
              
              colapsoEnTurno = true;
              setModoColapso(true);
              setComandoColapso(trigger);

              // Si Python manda la orden de inicio, secuestramos la pantalla real
              if (trigger.comando === 'INICIAR_COLAPSO') {
                invoke('activar_modo_invasivo').catch(console.error);
              }
              // Si Python manda la orden de fin, soltamos la pantalla
              else if (trigger.comando === 'RESTAURAR_SISTEMA') {
                invoke('restaurar_ventana').catch(console.error);
                setModoColapso(false);
                colapsoEnTurno = false;
              }

            } catch (e) {
              console.error("Error parseando trigger anómalo", e);
            }
            continue; 
          }

          // Solo el parseo va en try/catch: los errores reales ya no se tragan
          let data
          try { data = JSON.parse(parte.slice(6)) } catch { continue }

          if (data.tipo === 'estado') {
            // Si el backend avisa de un error crítico ANTES de hablar, preparamos el telón
            if (data.perfil === 'error_critico') {
              colapsoEnTurno = true;
              setModoColapso(true);
            }
            if (!yaEscribiendo) {
              if (data.estado_visual && ESTADOS_VISUALES_BACKEND.has(data.estado_visual)) {
                setEstadoLIA(data.estado_visual)
              }
              if (data.mensaje_espera !== undefined) {
                setMensajeEspera(data.mensaje_espera || null)
              }
            }
          } else if (data.tipo === 'chunk') {
            if (!yaEscribiendo) {
              yaEscribiendo = true
              setMensajeEspera(null)
              setEstadoLIA('escribiendo')
            }
            if (data.texto.length > 50) {
              actualizarUltimoMensaje(m => ({ ...m, texto: m.texto + data.texto }))
            } else {
              // Efecto typewriter, interrumpible si se aborta
              for (const letra of data.texto) {
                if (controller.signal.aborted) break
                actualizarUltimoMensaje(m => ({ ...m, texto: m.texto + letra }))
                await new Promise(resolve => setTimeout(resolve, 15))
              }
            }
          } else if (data.tipo === 'fin') {
            // Quitamos el modo colapso para devolver la app a la normalidad
            setModoColapso(false);
            setComandoColapso(null);
            if (colapsoEnTurno) {
              invoke('restaurar_ventana').catch(console.error);
              colapsoEnTurno = false;
            }
            
            actualizarUltimoMensaje(m => ({ ...m, origen: data.origen, documento: data.documento || m.documento }))
            if (data.workspace !== undefined) setWorkspaceActivo(data.workspace)
            cargarSesiones()
            // El título automático se genera en un hilo aparte y puede tardar
            setTimeout(cargarSesiones, 3000)
          } else if (data.tipo === 'error') {
            huboError = true
            if (colapsoEnTurno) {
              setModoColapso(false);
              setComandoColapso({ comando: 'RESET' });
              invoke('restaurar_ventana').catch(console.error);
              colapsoEnTurno = false;
            }
            actualizarUltimoMensaje(m => ({ ...m, texto: m.texto + `\n[ERROR]: ${data.texto}` }))
          }
        }
      }
    } catch (error) {
      if (error.name === 'AbortError') {
        actualizarUltimoMensaje(m => ({ ...m, texto: m.texto + '\n\n*(Respuesta abortada)*', cancelado: true }))
      } else {
        huboError = true
        actualizarUltimoMensaje(m => ({ ...m, texto: m.texto + '\n\n[ERROR] Caída del enlace con el núcleo.' }))
      }
    } finally {
      if (colapsoEnTurno) {
        setModoColapso(false)
        setComandoColapso({ comando: 'RESET' })
        invoke('restaurar_ventana').catch(console.error)
        colapsoEnTurno = false
      }
      setCargando(false)
      cargandoRef.current = false
      setMensajeEspera(null)
      if (huboError) {
        setEstadoLIA('error')
        setTimeout(() => setEstadoLIA('reposo'), 1600)
      } else {
        setEstadoLIA('reposo')
      }
    }
  }
  enviarOrdenRef.current = enviarOrden

  const manejarEnvio = (e) => {
    if (e) e.preventDefault()
    enviarOrden(input, vozGlobal) // <--- Ahora respeta el botón global
  }

  const detenerGeneracion = async () => {
    abortControllerRef.current?.abort()
    try {
      await fetch(`${API}/cancelar`, { method: 'POST' })
    } catch (error) {
      console.error('Error al abortar en el backend:', error)
    }
  }

  const alternarVozGlobal = async () => {
    const nuevoEstado = !vozGlobal
    setVozGlobal(nuevoEstado)
    vozGlobalRef.current = nuevoEstado

    if (!nuevoEstado) {
      try {
        await fetch(`${API}/voz/silenciar`, { method: 'POST' })
      } catch (error) {
        console.error('Error al silenciar la voz:', error)
      }
    }
  }

  // Micrófono manual (Conectado a Whisper local)
  const manejarMicrofono = async () => {
    if (escuchando) {
      escuchaTokenRef.current += 1
      escucharAbortRef.current?.abort()
      escucharAbortRef.current = null
      setEscuchando(false)
      setEstadoLIA('reposo')
      try {
        await fetch(`${API}/escuchar/cancelar`, { method: 'POST' })
      } catch (error) {
        console.error('Error al cancelar la escucha:', error)
      }
      return
    }

    if (cargando) return

    const miToken = ++escuchaTokenRef.current
    const controller = new AbortController()
    escucharAbortRef.current = controller

    setEscuchando(true)
    setEstadoLIA('escuchando') // Cambiamos la cara de L-IA a rojo al instante
    if (!vozGlobal) {
      setVozGlobal(true)
      vozGlobalRef.current = true
    }
    
    try {
      // Ordenamos a Python que abra el canal de audio
      const res = await fetch(`${API}/escuchar`, {
        method: 'POST',
        signal: controller.signal
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      
      const data = await res.json()
      if (miToken !== escuchaTokenRef.current) return
      
      // Si capturó palabras, las mandamos automáticamente
      if (data.texto && data.texto.trim() !== '') {
        enviarOrden(data.texto, vozGlobalRef.current)
      } else {
        // Si fue silencio o ruido nulo, regresamos a la normalidad
        setEstadoLIA('reposo')
      }
    } catch (error) {
      if (error.name === 'AbortError' || miToken !== escuchaTokenRef.current) return
      console.error('Error con el micrófono local:', error)
      agregarSistema('[ERROR] Fallo en el canal de audio (Whisper no respondió).')
      setEstadoLIA('error')
      setTimeout(() => setEstadoLIA('reposo'), 1600)
    } finally {
      if (miToken === escuchaTokenRef.current) {
        escucharAbortRef.current = null
        setEscuchando(false)
      }
    }
  }

  // =========================================
  // INGESTA DE ARCHIVOS (RAG)
  // =========================================
  const procesarArchivoRAG = async (archivo) => {
    setEstadoLIA('procesando_rag')
    agregarSistema(`[SISTEMA] Ingestando ${archivo.name}...`)
    const formData = new FormData()
    formData.append('archivo', archivo)
    formData.append('sesion_id', sesionActual)
    try {
      const respuesta = await fetch(`${API}/ingestar`, { method: 'POST', body: formData })
      const data = await respuesta.json().catch(() => ({}))
      setMensajes(prev => [...prev, {
        id: nuevoId(),
        rol: 'ia',
        texto: data.mensaje || (respuesta.ok ? 'Archivo procesado.' : `[ERROR] El núcleo rechazó el archivo (HTTP ${respuesta.status}).`)
      }])

      if (respuesta.ok && data.status === 'completado') {
        setWorkspaceActivo(archivo.name)
        cargarSesiones()
      }
      setEstadoLIA('reposo')
    } catch (error) {
      agregarSistema('[ERROR] Fallo en RAG.')
      setEstadoLIA('error')
      setTimeout(() => setEstadoLIA('reposo'), 1600)
    }
  }

  // Validación común para drop y selector de archivos
  const validarEIngestar = (archivos) => {
    if (archivos.length === 0) return

    if (cargando || estadoLIA === 'procesando_rag') {
      agregarSistema('[SISTEMA] Estoy ocupada. Suelta el archivo cuando termine.')
      return
    }

    const archivo = archivos[0]
    const ext = archivo.name.includes('.') ? archivo.name.split('.').pop().toLowerCase() : ''

    if (!EXTENSIONES_VALIDAS.includes(ext)) {
      agregarSistema(`[SISTEMA] Formato .${ext || '(sin extensión)'} no soportado. Acepto: ${EXTENSIONES_VALIDAS.join(', ')}.`)
      return
    }

    if (archivos.length > 1) {
      agregarSistema(`[SISTEMA] Recibí ${archivos.length} archivos; ingesto solo el primero (${archivo.name}).`)
    }

    procesarArchivoRAG(archivo)
  }

  const limpiarWorkspace = async () => {
    try {
      const respuesta = await fetch(`${API}/workspace/limpiar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sesion_id: sesionActual })
      })
      const data = await respuesta.json()
      if (data.status === 'completado' || data.status === 'ok') {
        setWorkspaceActivo(null)
        agregarSistema('[SISTEMA] Workspace liberado.')
        cargarSesiones()
      } else {
        agregarSistema('[ERROR] No se pudo liberar el workspace.')
      }
    } catch (error) {
      console.error('Error al limpiar workspace', error)
      agregarSistema('[ERROR] Sin enlace con el núcleo al liberar el workspace.')
    }
  }

  // =========================================
  // DRAG & DROP
  // =========================================
  const tieneArchivos = (e) => Array.from(e.dataTransfer?.types || []).includes('Files')

  const manejarDragEnter = (e) => {
    if (!tieneArchivos(e)) return
    e.preventDefault()
    dragContador.current += 1
    setIsDragging(true)
  }

  const manejarDragOver = (e) => {
    if (!tieneArchivos(e)) return
    e.preventDefault()
    e.dataTransfer.dropEffect = 'copy'
  }

  const manejarDragLeave = (e) => {
    if (!tieneArchivos(e)) return
    e.preventDefault()
    dragContador.current = Math.max(0, dragContador.current - 1)
    if (dragContador.current === 0) setIsDragging(false)
  }

  const manejarDrop = (e) => {
    if (!tieneArchivos(e)) return
    e.preventDefault()
    dragContador.current = 0
    setIsDragging(false)
    validarEIngestar(Array.from(e.dataTransfer.files || []))
  }

  const manejarClickArchivo = () => archivoInputRef.current?.click()
  const manejarSeleccionArchivo = (e) => {
    validarEIngestar(Array.from(e.target.files || []))
    e.target.value = null
  }

  // =========================================
  // RENDER
  // =========================================
  return (
    <div
      className="hud-container"
      onDragEnter={manejarDragEnter}
      onDragOver={manejarDragOver}
      onDragLeave={manejarDragLeave}
      onDrop={manejarDrop}
    >

      <ColapsoSistema activo={modoColapso} comandoActual={comandoColapso} />
      
      {/* FRANJA DE ARRASTRE */}
      <div
        data-tauri-drag-region
        className="franja-arrastre"
      >
        <div className="franja-grip" data-tauri-drag-region />
      </div>

      {/* CAPA DE DRAG & DROP */}
      {isDragging && (
        <div className="capa-drag">
          <Upload size={40} />
          <p>Suelta el archivo para ingestarlo</p>
        </div>
      )}

      {/* BOTÓN TEMPORAL DE PRUEBA DE COLAPSO */}
        <button
          type="button"
          className="hud-btn btn-debug-colapso"
          onClick={simularColapsoVisual}
          title="SIMULAR COLAPSO"
        >
          <ShieldAlert size={16} />
        </button>

      {/* --- SIDEBAR MULTI-SESIÓN --- */}
      {sidebarAbierto && <div className="sidebar-backdrop" onClick={() => setSidebarAbierto(false)} />}
      <div className={`panel lateral-izquierdo ${sidebarAbierto ? 'abierto' : ''}`}>
        <h2 className="hud-title sidebar-header">
          HISTORIAL DE CONVERSACIÓN
          <button
            type="button"
            onClick={crearNuevaSesion}
            disabled={cargando}
            className="hud-btn btn-nueva-sesion"
          >
            <Plus size={12} /> NUEVA
          </button>
        </h2>

        <div className="lista-sesiones custom-scrollbar">
          {sesiones.map(s => {
            const isActiva = s.id === sesionActual
            const nombreArchivo = nombreDeRuta(s.workspace_activo)
            const puedeCambiar = !isActiva && !editandoSesion && !cargando
            return (
              <div
                key={s.id}
                onClick={() => puedeCambiar && cargarContextoSesion(s.id)}
                className={`item-sesion ${isActiva ? 'activa' : ''} ${puedeCambiar ? 'clickeable' : ''}`}
              >
                {editandoSesion === s.id ? (
                  <div className="sesion-editar-wrap">
                    <input
                      autoFocus
                      value={tituloTemp}
                      onChange={e => setTituloTemp(e.target.value)}
                      onKeyDown={e => {
                        if (e.key === 'Enter') {
                          e.preventDefault()
                          guardarNuevoTitulo(s.id, e)
                        }
                        if (e.key === 'Escape') setEditandoSesion(null)
                      }}
                      className="sesion-editar-input"
                      onClick={e => e.stopPropagation()}
                    />
                    <button type="button" onClick={(e) => guardarNuevoTitulo(s.id, e)} className="hud-btn btn-sesion-confirmar"><Check size={14} /></button>
                    <button type="button" onClick={(e) => { e.stopPropagation(); setEditandoSesion(null) }} className="hud-btn btn-sesion-cancelar"><X size={14} /></button>
                  </div>
                ) : (
                  <div className="sesion-fila">
                    <div className="sesion-titulo-wrap">
                      <MessageSquare size={13} />
                      <span>
                        {s.titulo || 'Conversación'}
                      </span>
                    </div>
                    {s.id !== 'default' && (
                      <div className="acciones-sesion">
                        <button type="button" className="btn-sesion-accion editar" onClick={(e) => { e.stopPropagation(); setEditandoSesion(s.id); setTituloTemp(s.titulo || '') }} title="Editar Título"><Pencil size={13} /></button>
                        <button type="button" className="btn-sesion-accion eliminar" onClick={(e) => eliminarSesion(s.id, e)} title="Borrar Historial"><Trash2 size={13} /></button>
                      </div>
                    )}
                  </div>
                )}

                {nombreArchivo && !editandoSesion && (
                  <div className="sesion-workspace">
                    <Folder size={11} />
                    <span>{nombreArchivo}</span>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* MODAL DEL SEMÁFORO */}
      <AnimatePresence>
        {semaforo.activa && (
          <motion.div
            ref={overlayRef}
            className="modal-overlay"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          >
            <motion.div
              drag
              dragControls={dragControls}
              dragListener={false}
              dragMomentum={false}
              dragElastic={0}
              dragConstraints={overlayRef}
              className="modal-drag-wrap"
            >
              <motion.div
                className="modal-semaforo"
                initial={{ scale: 0.8, y: 50 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.8, opacity: 0 }}
                transition={{ type: 'spring', bounce: 0.5 }}
              >
                {/* CABECERA = MANIJA DE ARRASTRE */}
                <div
                  onPointerDown={(e) => dragControls.start(e)}
                  className="modal-cabecera-arrastre"
                  title="Arrastra para mover"
                >
                  <div className="modal-icono-alerta">
                    <AlertTriangle size={22} />
                  </div>
                  <h3 className="modal-titulo-alerta">ALERTA NIVEL 2</h3>
                </div>

                <p className="modal-texto">L-IA requiere autorización crítica para ejecutar:</p>

                <div className="codigo-alerta">{semaforo.herramienta}</div>
                <p className="modal-texto">Argumentos detectados:</p>

                <pre className="codigo-alerta codigo-alerta-pre custom-scrollbar">
                  {(() => {
                    if (!semaforo.argumentos) return 'Ninguno'
                    try {
                      const obj = typeof semaforo.argumentos === 'string'
                        ? JSON.parse(semaforo.argumentos)
                        : semaforo.argumentos
                      return JSON.stringify(obj, null, 2)
                    } catch (e) {
                      return semaforo.argumentos
                    }
                  })()}
                </pre>

                <div className="botones-alerta">
                  <button type="button" className="btn-denegar" onClick={() => responderSemaforo(false)}>ABORTAR</button>
                  <button type="button" className="btn-autorizar" onClick={() => responderSemaforo(true)}>AUTORIZAR</button>
                </div>
              </motion.div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* MODAL DE DESAMBIGUACIÓN DE ARCHIVOS */}
      <AnimatePresence>
        {semaforoArchivos.activa && (
          <motion.div
            className="modal-overlay modal-overlay-archivos"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          >
            <motion.div
              className="modal-semaforo modal-archivos"
              initial={{ scale: 0.8, y: 50 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.8, opacity: 0 }}
              transition={{ type: 'spring', bounce: 0.5 }}
            >
              <div className="modal-cabecera-archivos">
                <div className="modal-icono-archivos">
                  <Folder size={22} />
                </div>
                <h3 className="modal-titulo-archivos">
                  MÚLTIPLES ARCHIVOS ENCONTRADOS
                </h3>
              </div>

              <p className="modal-texto">
                Se encontraron {semaforoArchivos.opciones.length} coincidencias. Selecciona el archivo exacto que deseas leer:
              </p>

              <div className="lista-archivos-opciones custom-scrollbar">
                {semaforoArchivos.opciones.map((archivo, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => responderSemaforoArchivos(archivo.ruta)}
                    className="opcion-archivo-btn"
                  >
                    <span className="opcion-archivo-nombre">
                      {archivo.ruta.split(/[\\/]/).pop()}
                    </span>
                    <span className="opcion-archivo-ruta">
                      Ruta: {archivo.ruta}
                    </span>
                    <div className="opcion-archivo-meta">
                      <span>🗓️ {archivo.fecha}</span>
                      <span>⚖️ {archivo.tamano_kb.toFixed(2)} KB</span>
                    </div>
                  </button>
                ))}
              </div>

              <div className="botones-alerta">
                <button type="button" className="btn-denegar" onClick={() => responderSemaforoArchivos(null)}>
                  CANCELAR BÚSQUEDA
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* --- PANEL CENTRAL --- */}
      <div className="panel central">
        
        {/* MENÚ LATERAL (Izquierda) */}
        <button type="button" className="hud-btn btn-menu-sidebar" onClick={() => setSidebarAbierto(true)} title="Sesiones">
          <Menu size={16} />
        </button>

        {/* INTERRUPTOR GLOBAL DE VOZ (Derecha) */}
        <button
          type="button"
          className={`hud-btn btn-voz-global ${vozGlobal ? 'activo' : ''}`}
          onClick={alternarVozGlobal}
          title={vozGlobal ? "Respuestas por voz ACTIVADAS" : "Respuestas por voz DESACTIVADAS"}
        >
          {vozGlobal ? <Volume2 size={16} /> : <VolumeX size={16} />}
        </button>

        <NucleoLIA
          estado={estadoLIA}
          mensajeEspera={mensajeEspera}
          modoColapso={modoColapso}
          onInteraccion={manejarInteraccionNucleo}
          semaforoVisual={semaforo.activa ? 'seguridad' : semaforoArchivos.activa ? 'archivos' : null}
          feedbackDecision={feedbackDecision}
        />
        {/* INDICADOR DE WORKSPACE ACTIVO */}
        <AnimatePresence>
          {workspaceActivo && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              className="workspace-chip"
            >
              <motion.span
                className="workspace-chip-dot"
                animate={{ opacity: [0.5, 1, 0.5] }}
                transition={{ repeat: Infinity, duration: 1.6, ease: 'easeInOut' }}
              />
              <span className="workspace-chip-texto">
                TRABAJANDO EN: {workspaceActivo}
              </span>
              <button
                type="button"
                onClick={limpiarWorkspace}
                title="Liberar workspace"
                className="workspace-chip-cerrar"
              >
                <X size={13} />
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ZONA DE SCROLL */}
        <div className="chat-terminal custom-scrollbar">
          {mensajes.map((msg, idx) => {
            const esUltimo = idx === mensajes.length - 1
            const leyendo = idLeyendo === msg.id
            const puedeLeerse = msg.rol === 'ia' && !msg.cancelado && msg.texto && !(cargando && esUltimo)
            const origenClase = msg.origen ? msg.origen.toLowerCase() : ''

            return (
              <div key={msg.id} className={`burbuja-mensaje ${msg.rol}${origenClase ? ` origen-${origenClase}` : ''}${msg.cancelado ? ' mensaje-abortado' : ''}`}>
                <div className="remitente">
                  <span className="remitente-nombre">{msg.rol === 'ia' ? '> L-IA:' : msg.rol === 'sistema' ? '> SYS:' : '> TÚ:'}</span>

                  {msg.rol === 'ia' && msg.documento && (
                    <span className="badge-doc">📄 {nombreDeRuta(msg.documento)}</span>
                  )}
                  {msg.rol === 'ia' && msg.origen && (
                    <span className={`badge-origen ${origenClase}`}>{msg.origen.toUpperCase()}</span>
                  )}

                  {puedeLeerse && (
                    <button
                      type="button"
                      onClick={() => alternarLectura(msg.texto, msg.id)}
                      className={`hud-btn btn-leer ${leyendo ? 'leyendo' : ''}`}
                      title={leyendo ? 'Detener lectura' : 'Leer en voz alta'}
                      aria-pressed={leyendo}
                    >
                      {leyendo ? <X size={12} /> : <Volume2 size={12} />}
                      {leyendo ? 'DETENER' : 'LEER'}
                    </button>
                  )}
                </div>

                <div className="contenido-markdown">
                  {msg.rol === 'ia' ? (
                    <ReactMarkdown components={{ code: BloqueDeCodigo }}>
                      {msg.texto}
                    </ReactMarkdown>
                  ) : (
                    msg.texto
                  )}
                </div>
              </div>
            )
          })}
          <div ref={finalDelChatRef} />
        </div>

        {/* CONTROLES */}
        <form onSubmit={manejarEnvio} className="controles-input">
          <input
            type="file"
            ref={archivoInputRef}
            style={{ display: 'none' }}
            accept={EXTENSIONES_VALIDAS.map(e => `.${e}`).join(',')}
            onChange={manejarSeleccionArchivo}
          />
          <button type="button" className="hud-btn btn-composer" onClick={manejarClickArchivo} title="Adjuntar archivo"><Paperclip size={17} /></button>
          <button type="button" className={`hud-btn btn-composer btn-composer-mic ${escuchando ? 'escuchando' : ''}`} onClick={manejarMicrofono} title={escuchando ? "Cancelar escucha" : "Activar micrófono"}>
            <Mic size={17} />
          </button>
          
          <textarea
            ref={textareaRef}
            className="hud-input custom-scrollbar"
            placeholder="Ingresa texto..."
            value={input}
            onChange={(e) => {
              setInput(e.target.value)
              e.target.style.height = '42px'
              e.target.style.height = `${Math.min(e.target.scrollHeight, 100)}px`
            }}
            readOnly={cargando} // readOnly (no disabled): un textarea disabled no recibe eventos de arrastre
            rows={1}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                manejarEnvio()
              }
            }}
          />

          {cargando ? (
            <button
              type="button"
              className="hud-btn btn-composer btn-composer-detener"
              onClick={detenerGeneracion}
              title="Abortar Generación"
            >
              <Square size={15} />
            </button>
          ) : (
            <button type="submit" className="hud-btn btn-composer btn-composer-enviar animado" disabled={!input.trim()} title="Enviar">
              <Terminal size={17} />
            </button>
          )}
        </form>
      </div>

      {/* PANEL DERECHO */}
      <div className="panel lateral-derecho">
        <h2 className="hud-title">SISTEMA L-IA</h2>
        <div className="telemetria-placeholder">
          Módulos en línea.<br />
          Esperando telemetría...
        </div>
      </div>
    </div>
  )
}

