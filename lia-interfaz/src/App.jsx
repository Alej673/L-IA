import React, { useState, useEffect, useRef, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import './App.css'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { Mic, Paperclip, Terminal, Cpu, Database, Upload, AlertTriangle, Activity, ShieldAlert, MessageSquare, Plus, Folder, Pencil, Trash2, Check, X, Menu, Volume2, VolumeX } from 'lucide-react'
import { motion, AnimatePresence, useDragControls, useMotionValue, useTransform } from 'framer-motion'
import ColapsoSistema from './ColapsoSistema'
import { invoke } from '@tauri-apps/api/core';

const API = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

// Extensiones que el backend sabe leer (ajústalas a tu /ingestar)
const EXTENSIONES_VALIDAS = ['txt', 'md', 'py', 'js', 'php', 'html', 'css', 'json', 'docx', 'pdf', 'pptx', 'xlsx']

const MENSAJE_INICIAL = 'L-IA v3.2.1 inicializada. Esperando directivas...'

const nuevoId = () =>
  (typeof crypto !== 'undefined' && crypto.randomUUID)
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`

const mensajeInicial = () => ({ id: nuevoId(), rol: 'ia', texto: MENSAJE_INICIAL })

// =========================================
// CONFIGURACIÓN VISUAL POR ESTADO DEL NÚCLEO
// =========================================
const CONFIG_ESTADOS = {
  reposo: { tonos: ['#00ffff', '#33e0ff', '#00d4ff', '#33e0ff'], label: 'EN ESPERA', icon: Mic, giro: 14, pulso: 3 },
  // NUEVO ESTADO: Reflejo visual al abrir el micrófono
  escuchando: { tonos: ['#ff0055', '#ff3366', '#ff0033', '#cc0022'], label: 'CAPTURANDO AUDIO...', icon: Mic, giro: 6, pulso: 1.2 },
  procesando_pregunta: { tonos: ['#ffaa00', '#ffcc33', '#ffdd55', '#ffaa00'], label: 'ANALIZANDO DUDA...', icon: Cpu, giro: 2.2, pulso: 0.9 },
  procesando_doc: { tonos: ['#00ffaa', '#33ffcc', '#00e699', '#00ffaa'], label: 'LEYENDO DOCUMENTO...', icon: Database, giro: 1.5, pulso: 0.8 },
  procesando_sistema: { tonos: ['#0055ff', '#3388ff', '#0066ff', '#0033ee'], label: 'AUDITANDO SISTEMA...', icon: Terminal, giro: 0.8, pulso: 0.4 },
  procesando_git: { tonos: ['#ff3366', '#ff6688', '#ee1144', '#ff3366'], label: 'ENRUTANDO REPOSITORIO...', icon: Activity, giro: 1.2, pulso: 0.6 },
  procesando_rag: { tonos: ['#ff00ff', '#cc00ff', '#ff55ff', '#e000e6'], label: 'ANALIZANDO VECTOR...', icon: Database, giro: 1.6, pulso: 0.7 },
  escribiendo: { tonos: ['#39ff88', '#00ffc3', '#7bffb0', '#22ffaa'], label: 'ESCRIBIENDO...', icon: Activity, giro: 1.4, pulso: 0.5 },
  error: { tonos: ['#ff0033', '#ff5500', '#ff0055', '#ff2200'], label: 'ERROR CRÍTICO', icon: ShieldAlert, giro: 0.6, pulso: 0.25 },
}

// Frases rotativas mientras L-IA "piensa"
const FRASES_PENSAMIENTO = {
  procesando_pregunta: ['ANALIZANDO DUDA...', 'CRUZANDO DATOS...', 'VALIDANDO...', 'CASI LISTO...', 'UN MOMENTO MÁS...'],
  procesando_sistema: ['AUDITANDO SISTEMA...', 'LEYENDO SENSORES...', 'VERIFICANDO HARDWARE...', 'CONSULTANDO NÚCLEO...', 'CASI...'],
  procesando_git: ['ENRUTANDO REPOSITORIO...', 'REVISANDO COMMITS...', 'LEYENDO DIFF...', 'COMPARANDO RAMAS...', 'CASI...'],
  procesando_doc: ['LEYENDO DOCUMENTO...', 'EXTRAYENDO CONTENIDO...', 'INDEXANDO...', 'PROCESANDO TEXTO...', 'CASI...'],
}

// =========================================
// HOOKS Y UTILIDADES
// =========================================
function useCicloDeTono(tonos, intervaloMs = 1800) {
  const [indice, setIndice] = useState(0)
  useEffect(() => {
    setIndice(0)
    const id = setInterval(() => setIndice(i => (i + 1) % tonos.length), intervaloMs)
    return () => clearInterval(id)
  }, [tonos, intervaloMs])
  return tonos[indice]
}

const GESTOS_PENSAMIENTO = ['duda', 'mirada_arriba', 'ceja_alzada', 'concentracion', 'casi']

function useGestoPensamiento(activo, intervaloMs = 1400) {
  const [ronda, setRonda] = useState(0)
  useEffect(() => {
    if (!activo) { setRonda(0); return }
    const id = setInterval(() => setRonda(r => r + 1), intervaloMs)
    return () => clearInterval(id)
  }, [activo, intervaloMs])
  return [GESTOS_PENSAMIENTO[ronda % GESTOS_PENSAMIENTO.length], ronda]
}

// Mide el volumen del micrófono (0..1) sin provocar re-renders por frame
function useNivelMicrofono(activo) {
  const nivel = useMotionValue(0)
  const [hayVoz, setHayVoz] = useState(false)

  useEffect(() => {
    if (!activo) { nivel.set(0); setHayVoz(false); return }

    let cancelado = false
    let stream, ctx, raf
    let suavizado = 0
    let vozActual = false

    ;(async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: { echoCancellation: true, noiseSuppression: true }
        })
        if (cancelado) { stream.getTracks().forEach(t => t.stop()); return }

        ctx = new (window.AudioContext || window.webkitAudioContext)()
        const analyser = ctx.createAnalyser()
        analyser.fftSize = 256
        ctx.createMediaStreamSource(stream).connect(analyser)
        const datos = new Uint8Array(analyser.fftSize)

        const loop = () => {
          analyser.getByteTimeDomainData(datos)
          let suma = 0
          for (let i = 0; i < datos.length; i++) {
            const v = (datos[i] - 128) / 128
            suma += v * v
          }
          const rms = Math.sqrt(suma / datos.length)
          const objetivo = Math.min(1, rms * 6)
          // sube rápido, baja lento: se siente orgánico
          suavizado += (objetivo - suavizado) * (objetivo > suavizado ? 0.5 : 0.12)
          nivel.set(suavizado)

          const voz = suavizado > 0.12
          if (voz !== vozActual) { vozActual = voz; setHayVoz(voz) }
          raf = requestAnimationFrame(loop)
        }
        loop()
      } catch (e) {
        console.warn('Sin acceso al micrófono para la aureola:', e)
      }
    })()

    return () => {
      cancelado = true
      cancelAnimationFrame(raf)
      stream?.getTracks().forEach(t => t.stop())
      ctx?.close().catch(() => {})
      nivel.set(0)
      setHayVoz(false)
    }
  }, [activo, nivel])

  return { nivel, hayVoz }
}

// Gestos de "intento escuchar" mientras no hay voz
const GESTOS_ESCUCHA = ['atento', 'ladeaIzq', 'atento', 'ladeaDer']
function useGestoEscucha(activo, intervaloMs = 1100) {
  const [i, setI] = useState(0)
  useEffect(() => {
    if (!activo) { setI(0); return }
    const id = setInterval(() => setI(n => n + 1), intervaloMs)
    return () => clearInterval(id)
  }, [activo, intervaloMs])
  return GESTOS_ESCUCHA[i % GESTOS_ESCUCHA.length]
}

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
      // Ideal: un endpoint propio (/lector/detener) para no tocar el chat
      await fetch(`${API}/cancelar`, { method: 'POST' })
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

// =========================================
// NÚCLEO L-IA: Expresividad, Micro-Estados y Tareas
// =========================================
function NucleoLIA({ estado, mensajeEspera, modoColapso }) {
  const estadoReal = estado === 'procesando' ? 'procesando_pregunta' : estado

  const pensando = estadoReal.startsWith('procesando')
  const [gesto, rondaGesto] = useGestoPensamiento(pensando)

  const cfg = CONFIG_ESTADOS[estadoReal] || CONFIG_ESTADOS.reposo
  const { label, giro, pulso, tonos } = cfg
  const color = useCicloDeTono(tonos, estadoReal === 'error' ? 600 : 1800)
  const colorRostro = '#021017'

  const escuchandoAhora = estadoReal === 'escuchando'
  const { nivel, hayVoz } = useNivelMicrofono(escuchandoAhora)
  const gestoEscucha = useGestoEscucha(escuchandoAhora && !hayVoz)

  const escalaAureola = useTransform(nivel, [0, 1], [1.05, 1.6])
  const opacidadAureola = useTransform(nivel, [0, 1], [0.35, 1])

  const [parpadeo, setParpadeo] = useState(false)
  const [mouseOffset, setMouseOffset] = useState({ x: 0, y: 0 })
  const [miradaVagante, setMiradaVagante] = useState({ x: 0, y: 0 })
  const [tiempoInactiva, setTiempoInactiva] = useState(0)
  const [subEstado, setSubEstado] = useState('normal')

  // 1. Detección de movimiento
  useEffect(() => {
    const handleMouseMove = (e) => {
      setTiempoInactiva(0)
      setSubEstado('normal')
      const offsetX = (e.clientX - window.innerWidth / 2) / 45
      const offsetY = (e.clientY - window.innerHeight / 2) / 60
      const limit = (val, max) => Math.min(Math.max(val, -max), max)
      setMouseOffset({ x: limit(offsetX, 10), y: limit(offsetY, 7) })
    }
    window.addEventListener('mousemove', handleMouseMove)
    return () => window.removeEventListener('mousemove', handleMouseMove)
  }, [])

  // 2. Progresión de aburrimiento
  useEffect(() => {
    if (estadoReal !== 'reposo') {
      setSubEstado('normal')
      setTiempoInactiva(0) // si no, al volver a reposo se dormiría de inmediato
      return
    }
    const timer = setInterval(() => {
      setTiempoInactiva(prev => {
        const t = prev + 1
        if (t > 40) setSubEstado('durmiendo')
        else if (t > 34) setSubEstado('bostezo')
        else if (t > 24) setSubEstado('molesta')
        else if (t > 15) setSubEstado('impaciente')
        else if (t > 7) setSubEstado('alegre')
        else setSubEstado('normal')
        return t
      })
    }, 1000)
    return () => clearInterval(timer)
  }, [estadoReal])

  // 3. Mirada errante natural
  useEffect(() => {
    if (estadoReal !== 'reposo' || subEstado === 'durmiendo') {
      setMiradaVagante({ x: 0, y: 0 })
      return
    }
    const intervaloMirada = setInterval(() => {
      if (tiempoInactiva > 3) {
        const angulo = Math.random() * Math.PI * 2
        const radio = 4 + Math.random() * 5
        setMiradaVagante({ x: Math.cos(angulo) * radio, y: Math.sin(angulo) * (radio * 0.6) })
      } else {
        setMiradaVagante({ x: 0, y: 0 })
      }
    }, 2800)
    return () => clearInterval(intervaloMirada)
  }, [estadoReal, subEstado, tiempoInactiva])

  // 4. Parpadeo
  useEffect(() => {
    if (subEstado === 'durmiendo') return
    let timeoutId
    const ciclo = setInterval(() => {
      setParpadeo(true)
      timeoutId = setTimeout(() => setParpadeo(false), 140)
    }, Math.random() * 3500 + 2500)
    return () => {
      clearInterval(ciclo)
      clearTimeout(timeoutId)
    }
  }, [subEstado])

  // --- GEOMETRÍA FACIAL ---
  const getOjos = () => {
    if (parpadeo || subEstado === 'durmiendo') return { height: '2px', width: '10px', y: 3, rotate: 0, borderRadius: '2px', scaleY: 1 }
    if (subEstado === 'bostezo') return { height: '3px', width: '9px', y: -2, rotate: -15, borderRadius: '2px', scaleY: 1 }
    if (subEstado === 'alegre') return { height: '6px', width: '10px', y: -1, rotate: 0, borderRadius: '50% 50% 0 0', scaleY: 1 }
    if (subEstado === 'impaciente') return { height: '8px', width: '10px', y: 0, rotate: -8, borderRadius: '30%', scaleY: 1 }
    if (subEstado === 'molesta' || estadoReal === 'error') return { height: '7px', width: '10px', y: 1, rotate: 18, borderRadius: '4px', scaleY: 1 }

    if (pensando && gesto === 'mirada_arriba') return { height: '7px', width: '9px', y: -6, rotate: 0, borderRadius: '50%', scaleY: 1 }
    if (pensando && gesto === 'ceja_alzada') return { height: '10px', width: '8px', y: -3, rotate: 10, borderRadius: '40%', scaleY: 1 }
    if (pensando && gesto === 'concentracion') return { height: '6px', width: '10px', y: 0, rotate: 0, borderRadius: '30%', scaleY: 0.8 }
    if (pensando && gesto === 'casi') return { height: '9px', width: '9px', y: -2, rotate: 0, borderRadius: '50%', scaleY: 1.15 }

    if (estadoReal === 'procesando_pregunta') return { height: '9px', width: '9px', y: -3, rotate: 0, borderRadius: '50%', scaleY: 1 }
    if (estadoReal === 'procesando_sistema') return { height: '2px', width: '18px', y: -2, rotate: 0, borderRadius: '1px', scaleX: 1.2, scaleY: 1 }
    if (estadoReal === 'procesando_doc') return { height: '4px', width: '4px', y: -2, rotate: 0, borderRadius: '50%', scaleY: 1 }

    if (estadoReal === 'procesando_rag' || estadoReal === 'procesando_git') return { height: '10px', width: '10px', y: -2, rotate: 0, borderRadius: '50%', scaleY: 1 }
    if (estadoReal === 'escribiendo') return { height: '8px', width: '9px', y: -2, rotate: -5, borderRadius: '4px 4px 50% 50%', scaleY: 1 }
    // Expresión de atención máxima cuando escucha
    if (estadoReal === 'escuchando') {
      if (hayVoz) return { height: '14px', width: '14px', y: -2, rotate: 0, borderRadius: '50%', scaleY: 1 }
      if (gestoEscucha === 'ladeaIzq') return { height: '11px', width: '11px', y: -2, rotate: -10, borderRadius: '50%', scaleY: 1.1 }
      if (gestoEscucha === 'ladeaDer') return { height: '11px', width: '11px', y: -2, rotate: 10, borderRadius: '50%', scaleY: 1.1 }
      return { height: '12px', width: '12px', y: -3, rotate: 0, borderRadius: '50%', scaleY: 1.2 }
    }

    return { height: '9px', width: '9px', y: 0, rotate: 0, borderRadius: '50%', scaleY: 1 }
  }

  const getBoca = () => {
    if (subEstado === 'durmiendo') return { width: '6px', height: '2px', borderRadius: '1px', scaleY: 1, rotate: 0, y: 3 }
    if (subEstado === 'bostezo') return { width: '10px', height: '14px', borderRadius: '40%', scaleY: 1.2, rotate: 0, y: 1 }
    if (subEstado === 'alegre') return { width: '13px', height: '6px', borderRadius: '0 0 10px 10px', scaleY: 1, rotate: 0, y: 2 }
    if (subEstado === 'impaciente') return { width: '9px', height: '3px', borderRadius: '2px', scaleY: 1, rotate: 6, y: 1 }
    if (subEstado === 'molesta' || estadoReal === 'error') return { width: '12px', height: '3px', borderRadius: '2px', scaleY: 1, rotate: -8, y: 1 }

    if (pensando && gesto === 'mirada_arriba') return { width: '5px', height: '5px', borderRadius: '50%', scaleY: 1, rotate: 0, y: 0 }
    if (pensando && gesto === 'ceja_alzada') return { width: '7px', height: '3px', borderRadius: '2px', scaleY: 1, rotate: 4, y: 1 }
    if (pensando && gesto === 'concentracion') return { width: '9px', height: '2px', borderRadius: '1px', scaleY: 1, rotate: 0, y: 2 }
    if (pensando && gesto === 'casi') return { width: '6px', height: '6px', borderRadius: '50%', scaleY: 1, rotate: 0, y: 1 }

    if (estadoReal === 'procesando_pregunta') return { width: '4px', height: '4px', borderRadius: '50%', scaleY: 1, rotate: 0, y: 1 }

    if (estadoReal === 'escribiendo') return { width: '15px', height: '6px', borderRadius: '3px 3px 10px 10px', scaleY: [1, 1.4, 0.8, 1.2], rotate: 0, y: 0 }
    if (['procesando_rag', 'procesando_git', 'procesando_sistema', 'procesando_doc'].includes(estadoReal)) return { width: '5px', height: '5px', borderRadius: '50%', scaleY: 1, rotate: 0, y: 0 }
    // Boca en forma de "O" vibrando al ritmo de la voz
    if (estadoReal === 'escuchando') {
      return hayVoz
        ? { width: '8px', height: '8px', borderRadius: '50%', scaleY: [1, 1.4, 0.9, 1.2], rotate: 0, y: 2 }
        : { width: '5px', height: '5px', borderRadius: '50%', scaleY: 1, rotate: 0, y: 2 }
    }

    return { width: '10px', height: '3px', borderRadius: '1px 1px 6px 6px', scaleY: 1, rotate: 0, y: 1 }
  }

  const ojosCfg = getOjos()
  const bocaCfg = getBoca()

  const faceOffset = estadoReal === 'escuchando'
    ? { x: hayVoz ? 0 : ({ ladeaIzq: -6, ladeaDer: 6 }[gestoEscucha] ?? 0), y: hayVoz ? -2 : 0 }
    : estadoReal === 'reposo' && subEstado !== 'durmiendo'
      ? {
          x: tiempoInactiva > 3 ? miradaVagante.x : mouseOffset.x,
          y: tiempoInactiva > 3 ? miradaVagante.y : mouseOffset.y,
        }
      : { x: 0, y: subEstado === 'durmiendo' ? 4 : 0 }

  const textoEtiqueta =
    escuchandoAhora ? (hayVoz ? 'ESCUCHANDO...' : 'ESPERANDO VOZ...') :
    subEstado === 'durmiendo' ? 'SUSPENDIDA (REPOSO)' :
    subEstado === 'bostezo' ? 'MODO REPOSO...' :
    subEstado === 'molesta' ? 'ESPERANDO ÓRDENES...' :
    subEstado === 'impaciente' ? 'EN ESPERA' :
    pensando && mensajeEspera ? mensajeEspera.toUpperCase() :
    pensando && FRASES_PENSAMIENTO[estadoReal]
      ? FRASES_PENSAMIENTO[estadoReal][rondaGesto % FRASES_PENSAMIENTO[estadoReal].length]
      : label
  // 2. Levantar el componente por encima del telón
    // Levantar el componente por encima del telón
  const zIndexOverride = modoColapso ? { zIndex: 10001, position: 'relative' } : {};
  const c = modoColapso ? '#ff0033' : color; // color efectivo (rojo en colapso)

  return (
    <div className={`nucleo-wrapper ${modoColapso ? 'glitch-rgb' : ''}`} style={zIndexOverride}>
      <div className="nucleo-halo" style={{ background: `radial-gradient(circle, ${c}33, transparent 70%)` }} />

      {/* NODO DE GIT BRANCHING */}
      <AnimatePresence>
        {estadoReal === 'procesando_git' && (
          <motion.div
            className="nodo-git"
            style={{ background: c, color: c, top: '50%', left: '50%', marginTop: '-7px', marginLeft: '-7px' }}
            initial={{ x: 0, y: 0, opacity: 0 }}
            animate={{ x: 50, y: -30, opacity: 1 }}
            exit={{ x: 0, y: 0, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 50, damping: 10 }}
          >
            <motion.div style={{ position: 'absolute', top: '50%', right: '100%', height: '2px', width: '50px', background: c, transformOrigin: 'right', rotate: '30deg' }} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* AUREOLA DE ESCUCHA (se apaga en colapso) */}
      <AnimatePresence>
        {escuchandoAhora && !modoColapso && (
          <motion.div
            key="aureola"
            className="aureola-escucha"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
          >
            <motion.div
              className="aureola-voz"
              style={{
                scale: escalaAureola,
                opacity: opacidadAureola,
                borderColor: color,
                background: `radial-gradient(circle, transparent 50%, ${color}44 72%, transparent 100%)`,
                boxShadow: `0 0 30px ${color}, inset 0 0 30px ${color}66`,
              }}
            />
            {[0, 1, 2].map(i => (
              <motion.span
                key={i}
                className="onda-escucha"
                style={{ borderColor: color }}
                animate={{ scale: [1.9, 1], opacity: [0, 0.8, 0] }}
                transition={{ repeat: Infinity, duration: 1.8, delay: i * 0.6, ease: 'easeIn' }}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      <motion.div
        key={`onda-${estadoReal}`}
        className="aureola-voz"
        style={{ borderColor: c }}
        initial={{ scale: 0.7, opacity: 0.8 }}
        animate={{ scale: 1.7, opacity: 0 }}
        transition={{ duration: 0.8, ease: 'easeOut' }}
      />

      {/* PARTÍCULAS */}
      <motion.div
        className="anillo-particulas"
        animate={{ rotate: modoColapso ? [0, -360] : 360 }}
        transition={{ repeat: Infinity, duration: modoColapso ? 0.6 : giro * 2.2, ease: 'linear' }}
      >
        {[...Array(6)].map((_, i) => (
          <span key={i} className="particula" style={{ background: c, boxShadow: `0 0 8px ${c}`, transform: `rotate(${i * 60}deg) translateX(88px)` }} />
        ))}
      </motion.div>

      {/* ANILLOS (corruptos en colapso) */}
      <motion.div
        className="anillo-exterior"
        style={{ borderColor: c }}
        animate={{ rotate: modoColapso ? [0, 360, -180, 720] : 360 }}
        transition={{ repeat: Infinity, duration: modoColapso ? 0.3 : giro, ease: modoColapso ? 'backInOut' : 'linear' }}
      />
      <motion.div
        className="anillo-medio"
        style={{ borderTopColor: modoColapso ? '#00ffff' : color, borderBottomColor: c }}
        animate={{ rotate: -360 }}
        transition={{ repeat: Infinity, duration: modoColapso ? 0.15 : giro * 1.5, ease: 'linear' }}
      />
      <motion.div
        className="anillo-interior"
        style={{ borderColor: modoColapso ? '#00ffff' : color }}
        animate={{ scale: modoColapso ? [1, 0.8, 1.3, 1] : [1, 1.15, 1], opacity: [0.55, 1, 0.55] }}
        transition={{ repeat: Infinity, duration: modoColapso ? 0.2 : pulso }}
      />

      {/* NÚCLEO */}
      <motion.div
        className="centro-nucleo"
        style={{
          background: modoColapso
            ? `radial-gradient(circle at 45% 35%, #ffffff 0%, #ffaaaa 20%, #cc00ff 50%, #ff0033 90%)`
            : `radial-gradient(circle at 45% 35%, #ffffff 0%, #a6ffff 30%, ${color} 80%)`,
          boxShadow: modoColapso
            ? `0 0 40px #ff0033, 0 0 80px rgba(255,0,0,0.8)`
            : `0 0 25px ${color}, 0 0 55px ${color}66`,
          overflow: 'visible',
        }}
        animate={
          modoColapso
            ? { scale: [1, 1.05, 0.9, 1.1], rotate: [-5, 5, -2, 4], opacity: 1 }
            : {
                scale: estadoReal === 'escribiendo' ? [1, 1.2, 0.95, 1.1, 1] :
                       escuchandoAhora ? (hayVoz ? 1.08 : [1, 1.03, 1]) :
                       subEstado === 'bostezo' ? [1, 1.15, 0.95, 1] :
                       [1, 1.06, 1],
                opacity: subEstado === 'durmiendo' ? 0.7 : 1,
                rotate: escuchandoAhora && !hayVoz
                  ? ({ ladeaIzq: -10, ladeaDer: 10 }[gestoEscucha] ?? 0)
                  : pensando
                    ? ({ duda: 15, mirada_arriba: -8, ceja_alzada: 10, concentracion: -4, casi: 0 }[gesto] ?? 0)
                    : 0,
              }
        }
        transition={{
          repeat: Infinity,
          duration: modoColapso ? 0.2 : (subEstado === 'bostezo' ? 2.5 : pulso),
          ease: 'easeInOut',
        }}
      >
        {/* ICONOS FLOTANTES DE EMOCIÓN (ocultos en colapso) */}
        <AnimatePresence>
          {!modoColapso && subEstado === 'durmiendo' && (
            <div style={{ position: 'absolute', top: '-15px', right: '-15px', zIndex: 10, pointerEvents: 'none' }}>
              {[0, 1, 2].map((i) => (
                <motion.span
                  key={`zzz-${i}`}
                  style={{ color, position: 'absolute', fontWeight: 'bold', fontSize: '13px', textShadow: `0 0 6px ${color}` }}
                  initial={{ opacity: 0, y: 0, x: 0, scale: 0.5 }}
                  animate={{ opacity: [0, 1, 0], y: -24 - (i * 12), x: 12 + (i * 8), scale: [0.5, 1.1, 0.8] }}
                  transition={{ repeat: Infinity, duration: 2.4, delay: i * 0.7, ease: 'easeOut' }}
                >
                  Z
                </motion.span>
              ))}
            </div>
          )}
          {!modoColapso && subEstado === 'impaciente' && (
            <motion.div
              initial={{ opacity: 0, y: -5, scale: 0.8 }}
              animate={{ opacity: [0.4, 1, 0.4], y: -18 }}
              exit={{ opacity: 0 }}
              transition={{ repeat: Infinity, duration: 1.4 }}
              style={{ position: 'absolute', top: 0, right: '0px', color, fontSize: '11px', fontWeight: 'bold', letterSpacing: '2px', textShadow: `0 0 6px ${color}` }}
            >
              ...
            </motion.div>
          )}
          {!modoColapso && subEstado === 'molesta' && (
            <motion.div
              initial={{ opacity: 0, scale: 0.6, rotate: -15 }}
              animate={{ opacity: [0.7, 1, 0.7], scale: [1, 1.15, 1] }}
              exit={{ opacity: 0 }}
              transition={{ repeat: Infinity, duration: 0.8 }}
              style={{ position: 'absolute', top: '-10px', right: '-5px', color: '#ff0055', fontSize: '14px', textShadow: '0 0 8px #ff0055' }}
            >
              💢
            </motion.div>
          )}
          {!modoColapso && subEstado === 'alegre' && (
            <motion.div
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{ opacity: [0.3, 0.9, 0.3], y: [-10, -16, -10], scale: [0.8, 1.1, 0.8] }}
              exit={{ opacity: 0 }}
              transition={{ repeat: Infinity, duration: 1.8 }}
              style={{ position: 'absolute', top: '-5px', right: '-8px', color: '#00ffff', fontSize: '12px', textShadow: '0 0 8px #00ffff' }}
            >
              ✦
            </motion.div>
          )}
        </AnimatePresence>

        {/* LENTES DE LECTURA */}
        <AnimatePresence>
          {!modoColapso && estadoReal === 'procesando_doc' && (
            <motion.div
              className="lentes-lectura"
              style={{ color }}
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: -2 }}
              exit={{ opacity: 0, y: 10 }}
            >
              <div className="lente" style={{ borderColor: color, background: `${color}33` }} />
              <div className="puente-lentes" style={{ background: color }} />
              <div className="lente" style={{ borderColor: color, background: `${color}33` }} />
            </motion.div>
          )}
        </AnimatePresence>

        {/* ESCÁNER RAG */}
        {!modoColapso && estadoReal === 'procesando_rag' && (
          <div className="escaner-rag">
            <motion.div className="escaner-rag-barra" animate={{ top: ['-10%', '110%'] }} transition={{ repeat: Infinity, duration: 1.3, ease: 'linear' }} />
          </div>
        )}

        {/* ROSTRO */}
        <motion.div
          className="rostro-holografico"
          animate={modoColapso ? { x: [-2, 2, -1, 3], y: [1, -2, 2, -1] } : { x: faceOffset.x, y: faceOffset.y }}
          transition={
            modoColapso
              ? { repeat: Infinity, duration: 0.1 }
              : { type: 'spring', stiffness: 100, damping: 18 }
          }
        >
          <div className="fila-ojos">
            <motion.div
              className="ojo"
              style={{ background: colorRostro }}
              animate={{ ...ojosCfg, scale: 1.2 }}
              transition={{ duration: 0.15 }}
            />
            <motion.div
              className="ojo"
              style={{ background: colorRostro }}
              animate={{ ...ojosCfg, scale: 1.2, rotate: -ojosCfg.rotate }}
              transition={{ duration: 0.15 }}
            />
          </div>

          {/* Boca */}
          <motion.div
            className="boca"
            style={{ background: modoColapso ? '#021017' : colorRostro }}
            animate={
              modoColapso
                ? { width: ['35px', '15px', '40px'], rotate: [20, -15, 25], height: ['2px', '6px', '1px'] }
                : bocaCfg
            }
            transition={
              modoColapso
                ? { duration: 0.2, repeat: Infinity }
                : { duration: estadoReal === 'escribiendo' ? 0.4 : 0.2, repeat: estadoReal === 'escribiendo' ? Infinity : 0, ease: 'easeInOut' }
            }
          />
        </motion.div>
      </motion.div>

      {/* BARRAS DE VOZ */}
      {estadoReal === 'escribiendo' && (
        <div className="barras-voz">
          {[0, 1, 2, 3, 4].map((i) => (
            <motion.span
              key={i}
              style={{ background: c, boxShadow: `0 0 6px ${c}` }}
              animate={{ height: ['20%', '85%', '35%', '65%', '20%'] }}
              transition={{ repeat: Infinity, duration: modoColapso ? 0.3 : 0.9, delay: i * 0.09, ease: 'easeInOut' }}
            />
          ))}
        </div>
      )}

      {estadoReal === 'error' && (
        <motion.div className="destello-error" style={{ borderColor: c }} animate={{ opacity: [0, 0.5, 0], scale: [1, 1.08, 1] }} transition={{ repeat: Infinity, duration: 0.5 }} />
      )}

      {/* ETIQUETA */}
      <AnimatePresence mode="wait">
        <motion.div
          key={`${estadoReal}-${subEstado}-${pensando ? rondaGesto : 0}-${modoColapso}`}
          className="etiqueta-estado"
          style={{ color: c, textShadow: `0 0 8px ${c}99` }}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.25 }}
        >
          {textoEtiqueta}
        </motion.div>
      </AnimatePresence>
    </div>
  )
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
      <code
        style={{
          background: 'rgba(0, 255, 255, 0.12)',
          color: '#39ff88',
          padding: '2px 6px',
          borderRadius: '4px',
          fontSize: '13px',
          fontFamily: 'monospace',
          border: '1px solid rgba(0, 255, 255, 0.25)'
        }}
        {...props}
      >
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
    <div style={{ position: 'relative', marginTop: '12px', marginBottom: '12px', borderRadius: '6px', overflow: 'hidden', border: '1px solid rgba(0,255,255,0.2)' }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        background: '#041c26',
        padding: '6px 12px',
        borderBottom: '1px solid rgba(0,255,255,0.1)'
      }}>
        <span style={{ color: '#00ffff', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '1px', opacity: 0.8 }}>
          {lenguaje}
        </span>
        <button
          type="button"
          onClick={manejarCopia}
          style={{
            background: 'none',
            border: 'none',
            color: copiado ? '#39ff88' : '#00ffff',
            cursor: 'pointer',
            fontSize: '11px',
            letterSpacing: '1px',
            transition: 'all 0.2s'
          }}
        >
          {copiado ? '✓ COPIADO' : 'COPIAR'}
        </button>
      </div>

      {/* Sin {...props}: son props de <code> y no le corresponden al highlighter */}
      <SyntaxHighlighter
        style={vscDarkPlus}
        language={lenguaje}
        PreTag="div"
        customStyle={{
          margin: 0,
          padding: '14px',
          background: '#010a0f',
          fontSize: '13px',
          lineHeight: '1.4'
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
  // BOTÓN DEBUG: LLAMAR AL GUION DE PYTHON--eliminar despues
  // ==========================================
  const simularColapsoVisual = async () => {
    // 1. Oscurecemos la pantalla real al instante
    setModoColapso(true);
    await invoke('activar_modo_invasivo').catch(console.error);

    // 2. Le damos a Windows medio segundo para estirar la ventana
    await new Promise(r => setTimeout(r, 600));

    // 3. ¡Lanzamos el detonante a Python!
    // Usamos un comando secreto que tu backend reconocerá
    enviarOrden('/run_fase_1'); 
  };
  // Multi-sesión
  const [sesiones, setSesiones] = useState([])
  const [sesionActual, setSesionActual] = useState('default')
  const [sidebarAbierto, setSidebarAbierto] = useState(false)
  const [editandoSesion, setEditandoSesion] = useState(null)
  const [tituloTemp, setTituloTemp] = useState('')

  const [semaforo, setSemaforo] = useState({ activa: false, herramienta: '', argumentos: '' })
  const [cargando, setCargando] = useState(false)

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

  const responderSemaforo = async (autorizado) => {
    try {
      const res = await fetch(`${API}/semaforo/responder`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ autorizado })
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setSemaforo({ activa: false, herramienta: '', argumentos: '' })
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

    let estadoTemporal = 'procesando_pregunta'
    const textoMinusculas = textoAEnviar.toLowerCase()
    if (/\b(git|commit|commits|ramas)\b/.test(textoMinusculas)) estadoTemporal = 'procesando_git'
    else if (/\b(sistema|hardware|ram)\b/.test(textoMinusculas)) estadoTemporal = 'procesando_sistema'
    else if (/(archivo|documento|workspace|\blee\b|\brevisa)/.test(textoMinusculas)) estadoTemporal = 'procesando_doc'

    setEstadoLIA(estadoTemporal)
    setMensajeEspera(null)
    let huboError = false

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
              setModoColapso(true);
            }
            if (!yaEscribiendo) setMensajeEspera(data.mensaje_espera || null)
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
            
            actualizarUltimoMensaje(m => ({ ...m, origen: data.origen, documento: data.documento || m.documento }))
            if (data.workspace !== undefined) setWorkspaceActivo(data.workspace)
            cargarSesiones()
            // El título automático se genera en un hilo aparte y puede tardar
            setTimeout(cargarSesiones, 3000)
          } else if (data.tipo === 'error') {
            huboError = true
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

  // Micrófono manual (Conectado a Whisper local)
  const manejarMicrofono = async () => {
    if (escuchando || cargando) return
    setEscuchando(true)
    setEstadoLIA('escuchando') // Cambiamos la cara de L-IA a rojo al instante
    setVozGlobal(true)
    
    try {
      // Ordenamos a Python que abra el canal de audio
      const res = await fetch(`${API}/escuchar`, { method: 'POST' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      
      const data = await res.json()
      
      // Si capturó palabras, las mandamos automáticamente
      if (data.texto && data.texto.trim() !== '') {
        enviarOrden(data.texto, true)
      } else {
        // Si fue silencio o ruido nulo, regresamos a la normalidad
        setEstadoLIA('reposo')
      }
    } catch (error) {
      console.error('Error con el micrófono local:', error)
      agregarSistema('[ERROR] Fallo en el canal de audio (Whisper no respondió).')
      setEstadoLIA('error')
      setTimeout(() => setEstadoLIA('reposo'), 1600)
    } finally {
      setEscuchando(false)
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
        style={{
          position: 'fixed',
          top: 0,
          left: 'calc(50% - 90px)',
          width: '180px',
          height: '30px',
          zIndex: 50,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center'
        }}
      >
        <div className="franja-grip" data-tauri-drag-region />
      </div>

      {/* CAPA DE DRAG & DROP */}
      {isDragging && (
        <div className="capa-drag" style={{ pointerEvents: 'none' }}>
          <Upload size={40} />
          <p>Suelta el archivo para ingestarlo</p>
        </div>
      )}

      {/* BOTÓN TEMPORAL DE PRUEBA DE COLAPSO */}
        <button 
          type="button" 
          className="hud-btn" 
          onClick={simularColapsoVisual} 
          style={{ 
            position: 'absolute',
            top: '15px',
            right: '65px', /* Al lado del botón de voz */
            zIndex: 10,
            color: '#ff0000', 
            borderColor: '#ff0000',
            boxShadow: 'inset 0 0 10px rgba(255, 0, 0, 0.5)',
            padding: '8px'
          }}
          title="SIMULAR COLAPSO"
        >
          <ShieldAlert size={20} />
        </button>

      {/* --- SIDEBAR MULTI-SESIÓN --- */}
      {sidebarAbierto && <div className="sidebar-backdrop" onClick={() => setSidebarAbierto(false)} />}
      <div className={`panel lateral-izquierdo ${sidebarAbierto ? 'abierto' : ''}`} style={{ padding: '15px' }}>
        <h2 className="hud-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          HISTORIAL DE CONVERSACIÓN
          <button
            type="button"
            onClick={crearNuevaSesion}
            disabled={cargando}
            className="hud-btn"
            style={{ padding: '6px 10px', display: 'flex', alignItems: 'center', gap: '5px', fontSize: '10px' }}
          >
            <Plus size={12} /> NUEVA
          </button>
        </h2>

        <div className="lista-sesiones custom-scrollbar" style={{ display: 'flex', flexDirection: 'column', gap: '8px', overflowY: 'auto', flex: 1 }}>
          {sesiones.map(s => {
            const isActiva = s.id === sesionActual
            const nombreArchivo = nombreDeRuta(s.workspace_activo)
            const puedeCambiar = !isActiva && !editandoSesion && !cargando
            return (
              <div
                key={s.id}
                onClick={() => puedeCambiar && cargarContextoSesion(s.id)}
                className="item-sesion"
                style={{
                  background: isActiva ? 'rgba(0, 255, 255, 0.15)' : 'rgba(0, 0, 0, 0.4)',
                  border: `1px solid ${isActiva ? '#00ffff' : 'rgba(0,255,255,0.1)'}`,
                  padding: '10px',
                  borderRadius: '6px',
                  cursor: puedeCambiar ? 'pointer' : 'default',
                  transition: 'all 0.2s ease',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '5px'
                }}
              >
                {editandoSesion === s.id ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '5px', width: '100%' }}>
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
                      style={{ flex: 1, minWidth: 0, background: '#021017', color: '#00ffff', border: '1px solid #00ffff', borderRadius: '4px', padding: '4px', fontSize: '11px', outline: 'none' }}
                      onClick={e => e.stopPropagation()}
                    />
                    <button type="button" onClick={(e) => guardarNuevoTitulo(s.id, e)} className="hud-btn" style={{ padding: '4px', border: 'none', flexShrink: 0 }}><Check size={14} color="#39ff88" /></button>
                    <button type="button" onClick={(e) => { e.stopPropagation(); setEditandoSesion(null) }} className="hud-btn" style={{ padding: '4px', border: 'none', flexShrink: 0 }}><X size={14} color="#ff0055" /></button>
                  </div>
                ) : (
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', gap: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, minWidth: 0, color: isActiva ? '#fff' : '#88ccff', fontSize: '12px' }}>
                      <MessageSquare size={14} style={{ flexShrink: 0 }} />
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: isActiva ? 'bold' : 'normal' }}>
                        {s.titulo || 'Conversación'}
                      </span>
                    </div>
                    {s.id !== 'default' && (
                      <div className="acciones-sesion" style={{ display: 'flex', gap: '6px', flexShrink: 0 }}>
                        <button type="button" onClick={(e) => { e.stopPropagation(); setEditandoSesion(s.id); setTituloTemp(s.titulo || '') }} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }} title="Editar Título"><Pencil size={13} color="#00ffff" /></button>
                        <button type="button" onClick={(e) => eliminarSesion(s.id, e)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }} title="Borrar Historial"><Trash2 size={13} color="#ff0055" /></button>
                      </div>
                    )}
                  </div>
                )}

                {nombreArchivo && !editandoSesion && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '5px', color: '#39ff88', fontSize: '10px', paddingLeft: '22px' }}>
                    <Folder size={12} style={{ flexShrink: 0 }} />
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{nombreArchivo}</span>
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
              style={{ width: '85%', maxWidth: '400px' }}
            >
              <motion.div
                className="modal-semaforo"
                style={{ width: '100%', maxWidth: 'none', boxSizing: 'border-box' }}
                initial={{ scale: 0.8, y: 50 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.8, opacity: 0 }}
                transition={{ type: 'spring', bounce: 0.5 }}
              >
                {/* CABECERA = MANIJA DE ARRASTRE */}
                <div
                  onPointerDown={(e) => dragControls.start(e)}
                  style={{
                    cursor: 'grab',
                    touchAction: 'none',
                    userSelect: 'none',
                    width: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center'
                  }}
                  title="Arrastra para mover"
                >
                  <AlertTriangle color="#ff0055" size={50} style={{ marginBottom: '10px' }} />
                  <h3 style={{ color: '#ff0055', margin: '0 0 15px 0', letterSpacing: '2px' }}>ALERTA NIVEL 2</h3>
                </div>

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

      {/* --- PANEL CENTRAL --- */}
      <div className="panel central" style={{ position: 'relative' }}>
        
        {/* MENÚ LATERAL (Izquierda) */}
        <button type="button" className="hud-btn btn-menu-sidebar" onClick={() => setSidebarAbierto(true)} title="Sesiones">
          <Menu size={18} />
        </button>

        {/* INTERRUPTOR GLOBAL DE VOZ (Derecha) */}
        <button 
          type="button" 
          className="hud-btn" 
          onClick={() => setVozGlobal(!vozGlobal)} 
          style={{ 
            position: 'absolute',
            top: '15px',
            right: '15px',
            zIndex: 10,
            color: vozGlobal ? '#39ff88' : '#00ffff', 
            opacity: vozGlobal ? 1 : 0.5,
            borderColor: vozGlobal ? '#39ff88' : 'transparent',
            boxShadow: vozGlobal ? 'inset 0 0 10px rgba(57, 255, 136, 0.2)' : 'none',
            transition: 'all 0.2s ease',
            padding: '8px'
          }}
          title={vozGlobal ? "Respuestas por voz ACTIVADAS" : "Respuestas por voz DESACTIVADAS"}
        >
          {vozGlobal ? <Volume2 size={20} /> : <VolumeX size={20} />}
        </button>

        <NucleoLIA estado={estadoLIA} mensajeEspera={mensajeEspera} />
        {/* INDICADOR DE WORKSPACE ACTIVO */}
        <AnimatePresence>
          {workspaceActivo && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                margin: '0 0 8px 0',
                padding: '6px 12px',
                background: 'rgba(57, 255, 136, 0.08)',
                border: '1px solid rgba(57, 255, 136, 0.35)',
                borderRadius: '6px',
                color: '#39ff88',
                fontSize: '12px',
                letterSpacing: '1px'
              }}
            >
              <motion.span
                style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  background: '#39ff88',
                  boxShadow: '0 0 8px #39ff88',
                  flexShrink: 0
                }}
                animate={{ opacity: [0.5, 1, 0.5] }}
                transition={{ repeat: Infinity, duration: 1.6, ease: 'easeInOut' }}
              />
              <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                TRABAJANDO EN: {workspaceActivo}
              </span>
              <button
                type="button"
                onClick={limpiarWorkspace}
                title="Liberar workspace"
                style={{ background: 'none', border: 'none', color: '#ff0055', cursor: 'pointer', fontSize: '14px' }}
              >
                ✕
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

            return (
              <div key={msg.id} className={`burbuja-mensaje ${msg.rol} ${msg.cancelado ? 'mensaje-abortado' : ''}`}>
                <div className="remitente" style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                  <span>{msg.rol === 'ia' ? '> L-IA:' : msg.rol === 'sistema' ? '> SYS:' : '> TÚ:'}</span>

                  {msg.rol === 'ia' && msg.documento && (
                    <span className="badge-doc">📄 {nombreDeRuta(msg.documento)}</span>
                  )}
                  {msg.rol === 'ia' && msg.origen && (
                    <span className={`badge-origen ${msg.origen}`}>{msg.origen.toUpperCase()}</span>
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
          <button type="button" className="hud-btn" onClick={manejarClickArchivo}><Paperclip size={18} /></button>
          <button type="button" className="hud-btn" onClick={manejarMicrofono} style={{ color: escuchando ? '#ff0055' : '#00ffff', boxShadow: escuchando ? 'inset 0 0 10px rgba(255,0,85,0.5)' : '' }}>
            <Mic size={18} />
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
                e.preventDefault()
                manejarEnvio()
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
            <button type="submit" className="hud-btn animado" disabled={!input.trim()}>
              <Terminal size={18} />
            </button>
          )}
        </form>
      </div>

      {/* PANEL DERECHO */}
      <div className="panel lateral-derecho">
        <h2 className="hud-title">SISTEMA L-IA</h2>
        <div style={{ color: '#00ffff', opacity: 0.7, fontSize: '11px', marginTop: '10px' }}>
          Módulos en línea.<br />
          Esperando telemetría...
        </div>
      </div>
    </div>
  )
}

