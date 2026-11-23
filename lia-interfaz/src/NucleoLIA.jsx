import React, { useState, useEffect, useRef, useCallback } from 'react'
import './NucleoColapso.css'
import './NucleoLIA.css'
import {
  motion,
  AnimatePresence,
  useMotionValue,
  useTransform,
  useSpring,
  useAnimationFrame,
  useAnimation,
} from 'framer-motion'
import { Mic, Cpu, Database, Terminal, Activity, ShieldAlert } from 'lucide-react'

// =========================================
// CONFIGURACIÓN VISUAL POR ESTADO DEL NÚCLEO (Paleta Raycast Lote 5)
// =========================================
const CONFIG_ESTADOS = {
  reposo: { tonos: ['#22d3ee', '#38bdf8', '#06b6d4', '#67e8f9'], label: 'EN ESPERA', icon: Mic, velAngular: 26, pulso: 3.2 },
  escuchando: { tonos: ['#f43f5e', '#fb7185', '#e11d48', '#fda4af'], label: 'CAPTURANDO AUDIO...', icon: Mic, velAngular: 62, pulso: 1.2 },
  procesando_pregunta: { tonos: ['#fbbf24', '#fcd34d', '#f59e0b', '#fde68a'], label: 'ANALIZANDO DUDA...', icon: Cpu, velAngular: 155, pulso: 0.95 },
  procesando_doc: { tonos: ['#34d399', '#6ee7b7', '#10b981', '#5eead4'], label: 'LEYENDO DOCUMENTO...', icon: Database, velAngular: 195, pulso: 0.85 },
  procesando_sistema: { tonos: ['#38bdf8', '#60a5fa', '#2563eb', '#38bdf8'], label: 'AUDITANDO SISTEMA...', icon: Terminal, velAngular: 360, pulso: 0.45 },
  procesando_git: { tonos: ['#fb7185', '#f43f5e', '#f97316', '#fb7185'], label: 'ENRUTANDO REPOSITORIO...', icon: Activity, velAngular: 250, pulso: 0.65 },
  procesando_rag: { tonos: ['#a78bfa', '#c084fc', '#8b5cf6', '#c4b5fd'], label: 'ANALIZANDO VECTOR...', icon: Database, velAngular: 215, pulso: 0.75 },
  escribiendo: { tonos: ['#34d399', '#2dd4bf', '#6ee7b7', '#34d399'], label: 'ESCRIBIENDO...', icon: Activity, velAngular: 225, pulso: 0.6 },
  error: { tonos: ['#f43f5e', '#ef4444', '#fb7185', '#dc2626'], label: 'ERROR CRÍTICO', icon: ShieldAlert, velAngular: 480, pulso: 0.28 },
}

const FRASES_PENSAMIENTO = {
  procesando_pregunta: ['ANALIZANDO DUDA...', 'CRUZANDO DATOS...', 'VALIDANDO...', 'CASI LISTO...', 'UN MOMENTO MÁS...'],
  procesando_sistema: ['AUDITANDO SISTEMA...', 'LEYENDO SENSORES...', 'VERIFICANDO HARDWARE...', 'CONSULTANDO NÚCLEO...', 'CASI...'],
  procesando_git: ['ENRUTANDO REPOSITORIO...', 'REVISANDO COMMITS...', 'LEYENDO DIFF...', 'COMPARANDO RAMAS...', 'CASI...'],
  procesando_doc: ['LEYENDO DOCUMENTO...', 'EXTRAYENDO CONTENIDO...', 'INDEXANDO...', 'PROCESANDO TEXTO...', 'CASI...'],
  procesando_rag: ['ANALIZANDO VECTOR...', 'SEGMENTANDO TEXTO...', 'INDEXANDO MEMORIA...', 'ENLAZANDO SEMÁNTICA...', 'CASI LISTO...'],
}

const BARRAS_VOZ_CFG = [
  { escalas: [0.22, 0.88, 0.34, 0.70, 0.22], dur: 0.78, delay: 0.00 },
  { escalas: [0.35, 0.62, 0.98, 0.40, 0.35], dur: 0.92, delay: 0.08 },
  { escalas: [0.26, 0.95, 0.48, 0.84, 0.26], dur: 0.68, delay: 0.04 },
  { escalas: [0.30, 0.72, 0.92, 0.36, 0.30], dur: 0.86, delay: 0.12 },
  { escalas: [0.20, 0.78, 0.30, 0.64, 0.20], dur: 0.74, delay: 0.06 },
]

// Paletas constantes fuera del componente para no reiniciar useCicloDeTono en cada render
const TONOS_SEMAFORO_SEGURIDAD = ['#f59e0b', '#f43f5e', '#fbbf24', '#fb7185']
const TONOS_SEMAFORO_ARCHIVOS = ['#22d3ee', '#38bdf8', '#67e8f9', '#34d399']
const TONOS_FEEDBACK_OK = ['#34d399', '#6ee7b7']
const TONOS_FEEDBACK_NO = ['#f43f5e', '#fb7185']

// Actividades autónomas en reposo con ritmo pausado e intervalos naturales en 'normal'
const ACTIVIDADES_REPOSO = ['jugar_orbe', 'explorar_formas', 'leer_libre', 'accesorio_audio']
const TIEMPOS_REPOSO_MS = {
  normalInicial: [14000, 18000],
  actividad: [22000, 34000],
  pausaEntreActividades: [10000, 16000],
  pausaPreSueno: [10000, 14000],
  bostezo: 4800,
  somnolienta: 4200,
}

function aleatorioEntre(min, max) {
  return min + Math.random() * (max - min)
}

function crearCicloReposoInicial(ahora) {
  return {
    fase: 'normal_inicial',
    finFaseTs: ahora + aleatorioEntre(...TIEMPOS_REPOSO_MS.normalInicial),
    actividadesHechas: 0,
    ultimaActividad: null,
  }
}

function elegirActividadAleatoria(excluir = null) {
  const pool = ACTIVIDADES_REPOSO.filter(a => a !== excluir)
  return pool[Math.floor(Math.random() * pool.length)]
}

// =========================================
// HOOKS EXCLUSIVOS DEL AVATAR
// =========================================
function useCicloDeTono(tonos, intervaloMs = 2400) {
  const [indice, setIndice] = useState(0)
  useEffect(() => {
    const id = setInterval(() => setIndice(i => i + 1), intervaloMs)
    return () => clearInterval(id)
  }, [tonos, intervaloMs])
  return tonos[indice % tonos.length]
}

const GESTOS_PENSAMIENTO = ['duda', 'mirada_arriba', 'ceja_alzada', 'concentracion', 'casi']

function useGestoPensamiento(activo, intervaloMs = 1500) {
  const [ronda, setRonda] = useState(0)
  useEffect(() => {
    if (!activo) return
    const id = setInterval(() => setRonda(r => r + 1), intervaloMs)
    return () => clearInterval(id)
  }, [activo, intervaloMs])
  if (!activo) return ['duda', 0]
  return [GESTOS_PENSAMIENTO[ronda % GESTOS_PENSAMIENTO.length], ronda]
}

const GESTOS_HABLA = ['neutro', 'asentir', 'ladeo_izq', 'ladeo_der', 'enfasis_ceja', 'calido', 'enfocado']

function useGestoHabla(activo) {
  const [gesto, setGesto] = useState({ tipo: 'neutro', pulso: 0 })
  useEffect(() => {
    if (!activo) return
    let timerId
    let ultimo = 'neutro'
    const programar = () => {
      const espera = 950 + Math.random() * 1150
      timerId = setTimeout(() => {
        const candidatos = GESTOS_HABLA.filter(g => g !== ultimo)
        const siguiente = candidatos[Math.floor(Math.random() * candidatos.length)]
        ultimo = siguiente
        setGesto(prev => ({ tipo: siguiente, pulso: prev.pulso + 1 }))
        programar()
      }, espera)
    }
    programar()
    return () => clearTimeout(timerId)
  }, [activo])
  return activo ? gesto : { tipo: 'neutro', pulso: 0 }
}

// Mide el volumen del micrófono (0..1) sin provocar re-renders por frame
function useNivelMicrofono(activo) {
  const nivel = useMotionValue(0)
  const [hayVozInterno, setHayVozInterno] = useState(false)

  useEffect(() => {
    if (!activo) {
      nivel.set(0)
      return
    }

    let cancelado = false
    let stream, ctx, raf
    let suavizado = 0
    let vozActual = null

    ;(async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: { echoCancellation: true, noiseSuppression: true },
        })
        if (cancelado) {
          stream.getTracks().forEach(t => t.stop())
          return
        }

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
          suavizado += (objetivo - suavizado) * (objetivo > suavizado ? 0.5 : 0.12)
          nivel.set(suavizado)

          const voz = suavizado > 0.12
          if (voz !== vozActual) {
            vozActual = voz
            setHayVozInterno(voz)
          }
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
    }
  }, [activo, nivel])

  return { nivel, hayVoz: activo && hayVozInterno }
}

const GESTOS_ESCUCHA = ['atento', 'ladeaIzq', 'atento', 'ladeaDer']

function useGestoEscucha(activo, intervaloMs = 1200) {
  const [i, setI] = useState(0)
  useEffect(() => {
    if (!activo) return
    const id = setInterval(() => setI(n => n + 1), intervaloMs)
    return () => clearInterval(id)
  }, [activo, intervaloMs])
  return activo ? GESTOS_ESCUCHA[i % GESTOS_ESCUCHA.length] : 'atento'
}

// =========================================
// MINI-ESCENAS HOLOGRÁFICAS (0 MB VRAM · 100% GPU)
// =========================================
function crearPathEngranaje(dientes, rExt, rInt, cx = 18, cy = 18) {
  const pts = []
  const paso = (Math.PI * 2) / dientes
  for (let i = 0; i < dientes; i++) {
    const a0 = i * paso
    const a1 = a0 + paso * 0.18
    const a2 = a0 + paso * 0.34
    const a3 = a0 + paso * 0.62
    const a4 = a0 + paso * 0.78
    pts.push(
      `${i === 0 ? 'M' : 'L'} ${(cx + rInt * Math.cos(a0)).toFixed(2)} ${(cy + rInt * Math.sin(a0)).toFixed(2)}`,
      `L ${(cx + rInt * Math.cos(a1)).toFixed(2)} ${(cy + rInt * Math.sin(a1)).toFixed(2)}`,
      `L ${(cx + rExt * Math.cos(a2)).toFixed(2)} ${(cy + rExt * Math.sin(a2)).toFixed(2)}`,
      `L ${(cx + rExt * Math.cos(a3)).toFixed(2)} ${(cy + rExt * Math.sin(a3)).toFixed(2)}`,
      `L ${(cx + rInt * Math.cos(a4)).toFixed(2)} ${(cy + rInt * Math.sin(a4)).toFixed(2)}`,
    )
  }
  return `${pts.join(' ')} Z`
}

const PATH_ENGRANAJE_10 = crearPathEngranaje(10, 16.5, 12.2)
const PATH_ENGRANAJE_7 = crearPathEngranaje(7, 16.2, 11.4)
const PATH_ENGRANAJE_8 = crearPathEngranaje(8, 16.2, 11.8)

function EngranajeSVG({ pathD }) {
  return (
    <svg width="100%" height="100%" viewBox="0 0 36 36" fill="none" aria-hidden="true">
      <path d={pathD} fill="currentColor" fillOpacity="0.12" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <circle cx="18" cy="18" r="6.2" stroke="currentColor" strokeWidth="1.4" />
      <circle cx="18" cy="18" r="2.2" fill="currentColor" />
    </svg>
  )
}

function EscenaSistema({ color }) {
  return (
    <motion.div
      key="escena-sistema"
      className="escena-sistema"
      style={{ color }}
      initial={{ opacity: 0, scale: 0.84 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.84 }}
      transition={{ duration: 0.28 }}
    >
      <motion.div
        className="engranaje-hud engranaje-1"
        animate={{ rotate: 360 }}
        transition={{ repeat: Infinity, duration: 7.0, ease: 'linear' }}
      >
        <EngranajeSVG pathD={PATH_ENGRANAJE_10} />
      </motion.div>

      <motion.div
        className="engranaje-hud engranaje-2"
        animate={{ rotate: -360 }}
        transition={{ repeat: Infinity, duration: 4.9, ease: 'linear' }}
      >
        <EngranajeSVG pathD={PATH_ENGRANAJE_7} />
      </motion.div>

      <motion.div
        className="engranaje-hud engranaje-3"
        animate={{ rotate: 360 }}
        transition={{ repeat: Infinity, duration: 5.6, ease: 'linear' }}
      >
        <EngranajeSVG pathD={PATH_ENGRANAJE_8} />
      </motion.div>

      {[
        { mx: -64, my: -38, delay: 0 },
        { mx: 62, my: 32, delay: 0.45 },
      ].map((p, idx) => (
        <motion.span
          key={idx}
          className="pulso-hud-dot"
          style={{ marginLeft: p.mx, marginTop: p.my, background: color }}
          animate={{ opacity: [0.2, 1, 0.2], scale: [0.8, 1.45, 0.8] }}
          transition={{ repeat: Infinity, duration: 1.1, delay: p.delay, ease: 'easeInOut' }}
        />
      ))}
    </motion.div>
  )
}

const NODOS_GIT = [
  { x: 18, y: 76, delay: 0.0 },
  { x: 18, y: 52, delay: 0.55 },
  { x: 46, y: 40, delay: 1.1 },
]

function EscenaGit({ color }) {
  return (
    <motion.div
      key="escena-git"
      className="escena-git"
      style={{ color }}
      initial={{ opacity: 0, x: -12, scale: 0.85 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: -8, scale: 0.85 }}
      transition={{ type: 'spring', stiffness: 160, damping: 18 }}
    >
      <svg className="git-svg" viewBox="0 0 78 92" fill="none" aria-hidden="true">
        <path
          d="M 18 82 L 18 28 Q 20 18 34 16"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeOpacity="0.85"
        />
        <path
          d="M 18 66 C 18 52, 46 54, 46 38 L 46 27"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeDasharray="3 2.5"
          strokeOpacity="0.8"
        />
        <path
          d="M 41 24 H 61 C 64.5 24 67 21.5 67 18.2 C 67 15.2 64.8 12.8 62 12.5 C 61 8.6 57.5 6 53.3 6 C 48.6 6 44.8 9.6 44.5 14.2 C 41.4 14.5 39 17 39 20 C 39 22.3 39.8 24 41 24 Z"
          fill="currentColor"
          fillOpacity="0.14"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
        <path
          d="M 53 20 V 12 M 49.8 15 L 53 11.8 L 56.2 15"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>

      {NODOS_GIT.map((n, idx) => (
        <motion.span
          key={idx}
          className="git-commit-dot"
          style={{ left: n.x, top: n.y, background: color }}
          animate={{ scale: [0.85, 1.35, 0.85], opacity: [0.45, 1, 0.45] }}
          transition={{ repeat: Infinity, duration: 1.8, delay: n.delay, ease: 'easeInOut' }}
        />
      ))}

      {[
        { x: [18, 18, 22, 39], y: [76, 46, 22, 16], delay: 0.0 },
        { x: [18, 36, 46, 51], y: [64, 52, 34, 22], delay: 0.75 },
        { x: [18, 18, 26, 42], y: [72, 38, 20, 16], delay: 1.45 },
      ].map((pkt, idx) => (
        <motion.span
          key={`pkt-${idx}`}
          className="git-paquete"
          style={{ left: 0, top: 0 }}
          animate={{ x: pkt.x, y: pkt.y, opacity: [0, 1, 1, 0], scale: [0.6, 1.15, 0.85, 0.4] }}
          transition={{ repeat: Infinity, duration: 1.9, delay: pkt.delay, ease: 'easeInOut' }}
        />
      ))}
    </motion.div>
  )
}

const CHUNKS_RAG = [
  { y0: -12, delay: 0.0 },
  { y0: -4, delay: 0.42 },
  { y0: 4, delay: 0.84 },
  { y0: 12, delay: 1.26 },
]

function EscenaRAG({ color }) {
  return (
    <motion.div
      key="escena-rag"
      className="escena-rag"
      style={{ color }}
      initial={{ opacity: 0, x: 12, scale: 0.86 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 10, scale: 0.86 }}
      transition={{ type: 'spring', stiffness: 160, damping: 18 }}
    >
      <motion.div
        className="rag-doc-origen"
        style={{ borderColor: `${color}88` }}
        animate={{ scale: [1, 0.95, 1], opacity: [0.8, 1, 0.8] }}
        transition={{ repeat: Infinity, duration: 1.8, ease: 'easeInOut' }}
      >
        <span style={{ width: '90%' }} />
        <span style={{ width: '70%' }} />
        <span style={{ width: '100%' }} />
        <span style={{ width: '60%' }} />
      </motion.div>

      {CHUNKS_RAG.map((chunk, idx) => (
        <motion.div
          key={idx}
          className="rag-chunk"
          style={{ background: color }}
          animate={{
            x: [0, 38, 78],
            y: [chunk.y0, chunk.y0 * 0.45, 0],
            scale: [0.95, 1.05, 0.3],
            opacity: [0, 1, 0.9, 0],
          }}
          transition={{ repeat: Infinity, duration: 1.68, delay: chunk.delay, ease: 'easeIn' }}
        />
      ))}
    </motion.div>
  )
}

const LINEAS_DOC = ['82%', '95%', '66%', '88%', '54%']

function EscenaDoc({ color }) {
  return (
    <motion.div
      key="escena-doc"
      className="escena-doc"
      initial={{ opacity: 0, x: -12, scale: 0.86 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: -10, scale: 0.86 }}
      transition={{ type: 'spring', stiffness: 170, damping: 18 }}
    >
      <motion.div
        className="doc-tarjeta"
        style={{ borderColor: `${color}77` }}
        animate={{ y: [2, -2, 2] }}
        transition={{ repeat: Infinity, duration: 2.8, ease: 'easeInOut' }}
      >
        <motion.div
          className="doc-cursor-lectura"
          animate={{ y: [0, 44, 0] }}
          transition={{ repeat: Infinity, duration: 2.4, ease: 'easeInOut' }}
        />
        {LINEAS_DOC.map((ancho, idx) => (
          <motion.span
            key={idx}
            className="doc-linea"
            style={{ width: ancho, background: color }}
            animate={{ opacity: [0.22, 1, 0.35, 0.22], scaleX: [0.92, 1, 0.96, 0.92] }}
            transition={{
              repeat: Infinity,
              duration: 2.4,
              delay: idx * 0.26,
              ease: 'easeInOut',
            }}
          />
        ))}
      </motion.div>
    </motion.div>
  )
}

function ArcosAcusticos({ color, hayVoz }) {
  const dur = hayVoz ? 0.95 : 2.1
  const opMax = hayVoz ? 0.95 : 0.45
  return (
    <motion.div
      key="arcos-acusticos"
      className="arcos-acusticos"
      style={{ color }}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.22 }}
    >
      {[0, 1, 2].map(i => (
        <React.Fragment key={i}>
          <motion.span
            className="arco-lado izq"
            animate={{ x: [-15, 5], scale: [1.08, 0.84], opacity: [0, opMax, 0] }}
            transition={{ repeat: Infinity, duration: dur, delay: i * (dur / 3), ease: 'easeIn' }}
          >
            <svg width="20" height="44" viewBox="0 0 20 44" fill="none" aria-hidden="true">
              <path d="M 14 6 C 5 14, 5 30, 14 38" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </motion.span>
          <motion.span
            className="arco-lado der"
            animate={{ x: [15, -5], scale: [1.08, 0.84], opacity: [0, opMax, 0] }}
            transition={{ repeat: Infinity, duration: dur, delay: i * (dur / 3), ease: 'easeIn' }}
          >
            <svg width="20" height="44" viewBox="0 0 20 44" fill="none" aria-hidden="true">
              <path d="M 6 6 C 15 14, 15 30, 6 38" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </motion.span>
        </React.Fragment>
      ))}
    </motion.div>
  )
}

const CHISPAS_CFG = [
  { x0: 36, y0: -26, x1: 66, y1: -50, dur: 1.25, delay: 0.0 },
  { x0: -38, y0: -24, x1: -70, y1: -46, dur: 1.4, delay: 0.25 },
  { x0: 44, y0: 4, x1: 78, y1: 10, dur: 1.15, delay: 0.45 },
  { x0: -44, y0: 8, x1: -76, y1: 18, dur: 1.5, delay: 0.15 },
  { x0: 30, y0: 32, x1: 58, y1: 56, dur: 1.35, delay: 0.65 },
  { x0: -32, y0: 30, x1: -58, y1: 54, dur: 1.2, delay: 0.85 },
  { x0: 12, y0: -44, x1: 22, y1: -72, dur: 1.45, delay: 0.35 },
  { x0: -14, y0: -44, x1: -24, y1: -70, dur: 1.3, delay: 0.95 },
]

function ChispasEscritura({ color }) {
  return (
    <motion.div
      key="chispas-escritura"
      className="chispas-escritura"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
    >
      {CHISPAS_CFG.map((ch, idx) => (
        <motion.span
          key={idx}
          className="chispa-dato"
          style={{ background: color }}
          animate={{
            x: [ch.x0, ch.x1],
            y: [ch.y0, ch.y1],
            rotate: [45, 135],
            scale: [0.4, 1.1, 0.2],
            opacity: [0, 0.9, 0],
          }}
          transition={{ repeat: Infinity, duration: ch.dur, delay: ch.delay, ease: 'easeOut' }}
        />
      ))}
    </motion.div>
  )
}

function EscudoHexagonal({ pulsoRebote }) {
  return (
    <motion.div
      key="escudo-hex"
      className="escudo-hexagonal"
      initial={{ opacity: 0, scale: 0.65, rotate: -18 }}
      animate={{ opacity: 1, scale: 1, rotate: 0 }}
      exit={{ opacity: 0, scale: 0.72, rotate: 18 }}
      transition={{ type: 'spring', stiffness: 220, damping: 18 }}
    >
      <motion.svg
        width="108"
        height="108"
        viewBox="0 0 108 108"
        fill="none"
        aria-hidden="true"
        animate={{ rotate: 360 }}
        transition={{ repeat: Infinity, duration: 18, ease: 'linear' }}
      >
        <polygon
          points="54,6 96,30 96,78 54,102 12,78 12,30"
          fill="rgba(34, 211, 238, 0.08)"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
        <polygon
          points="54,15 88,34.5 88,73.5 54,93 20,73.5 20,34.5"
          stroke="#67e8f9"
          strokeWidth="1"
          strokeDasharray="4 4"
          strokeOpacity="0.7"
          strokeLinejoin="round"
        />
        {[
          [54, 6],
          [96, 30],
          [96, 78],
          [54, 102],
          [12, 78],
          [12, 30],
        ].map(([cx, cy], idx) => (
          <circle key={idx} cx={cx} cy={cy} r="2.6" fill="#67e8f9" />
        ))}
      </motion.svg>

      {pulsoRebote > 0 && (
        <motion.div
          key={pulsoRebote}
          className="escudo-destello"
          initial={{ scale: 0.86, opacity: 0.95 }}
          animate={{ scale: 1.32, opacity: 0 }}
          transition={{ duration: 0.36, ease: 'easeOut' }}
        />
      )}
    </motion.div>
  )
}

function DestellosCaricia() {
  const estrellas = [
    { top: '4px', left: '4px', delay: 0 },
    { top: '-6px', right: '6px', delay: 0.35 },
    { bottom: '6px', right: '-4px', delay: 0.65 },
  ]
  return (
    <motion.div
      key="caricia-destellos"
      className="caricia-destellos"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
    >
      {estrellas.map((pos, idx) => (
        <motion.span
          key={idx}
          className="caricia-estrella"
          style={pos}
          animate={{ opacity: [0.25, 1, 0.25], y: [0, -7, 0], scale: [0.8, 1.2, 0.8] }}
          transition={{ repeat: Infinity, duration: 1.4, delay: pos.delay, ease: 'easeInOut' }}
        >
          ✦
        </motion.span>
      ))}
    </motion.div>
  )
}

// --- Actividades autónomas en reposo ---
function ActividadOrbe({ color }) {
  return (
    <motion.div
      key="act-orbe"
      className="actividad-orbe"
      initial={{ opacity: 0, scale: 0.7 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.7 }}
      transition={{ duration: 0.28 }}
    >
      <motion.div
        className="orbe-pelota"
        style={{ background: `radial-gradient(circle at 35% 35%, #ffffff 0%, ${color} 80%)` }}
        animate={{
          y: [-46, 0, -46],
          scaleX: [0.95, 1.24, 0.95],
          scaleY: [1.05, 0.76, 1.05],
        }}
        transition={{
          repeat: Infinity,
          duration: 1.25,
          times: [0, 0.5, 1],
          ease: ['easeIn', 'easeOut'],
        }}
      />
      <motion.span
        className="orbe-base"
        style={{ background: color }}
        animate={{ scaleX: [0.65, 1.15, 0.65], opacity: [0.2, 0.65, 0.2] }}
        transition={{ repeat: Infinity, duration: 1.25, ease: 'easeInOut' }}
      />
    </motion.div>
  )
}

function ActividadFormas({ color }) {
  return (
    <motion.div
      key="act-formas"
      className="actividad-formas"
      style={{ color }}
      initial={{ opacity: 0, x: -10, scale: 0.8 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: -10, scale: 0.8 }}
      transition={{ duration: 0.28 }}
    >
      {/* Triángulo */}
      <motion.div
        className="forma-geo"
        style={{ top: '4px', left: '10px', width: '18px', height: '18px' }}
        animate={{ y: [-3, 3, -3], rotate: [0, 360] }}
        transition={{
          y: { repeat: Infinity, duration: 2.6, ease: 'easeInOut' },
          rotate: { repeat: Infinity, duration: 8, ease: 'linear' },
        }}
      >
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
          <polygon points="9,2 16,15 2,15" fill="currentColor" fillOpacity="0.16" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
        </svg>
      </motion.div>

      {/* Rombo */}
      <motion.div
        className="forma-geo"
        style={{ top: '28px', left: '34px', width: '16px', height: '16px' }}
        animate={{ y: [3, -4, 3], rotate: [0, -180, -360] }}
        transition={{
          y: { repeat: Infinity, duration: 2.2, ease: 'easeInOut' },
          rotate: { repeat: Infinity, duration: 6.5, ease: 'linear' },
        }}
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <rect x="3" y="3" width="10" height="10" rx="2" fill="currentColor" fillOpacity="0.16" stroke="currentColor" strokeWidth="1.5" />
        </svg>
      </motion.div>

      {/* Anillo */}
      <motion.div
        className="forma-geo"
        style={{ top: '52px', left: '14px', width: '15px', height: '15px' }}
        animate={{ y: [-2, 4, -2], scale: [0.9, 1.12, 0.9] }}
        transition={{ repeat: Infinity, duration: 2.4, ease: 'easeInOut' }}
      >
        <svg width="15" height="15" viewBox="0 0 15 15" fill="none" aria-hidden="true">
          <circle cx="7.5" cy="7.5" r="5" stroke="currentColor" strokeWidth="1.6" />
        </svg>
      </motion.div>
    </motion.div>
  )
}

function AccesorioAuriculares({ color }) {
  return (
    <motion.div
      key="act-auriculares"
      className="accesorio-auriculares"
      style={{ color }}
      initial={{ opacity: 0, y: -12, scale: 0.85 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -10, scale: 0.85 }}
      transition={{ type: 'spring', stiffness: 220, damping: 18 }}
    >
      <svg width="82" height="54" viewBox="0 0 82 54" fill="none" aria-hidden="true">
        {/* Diadema superior */}
        <path
          d="M 10 38 C 10 10, 72 10, 72 38"
          stroke="currentColor"
          strokeWidth="2.6"
          strokeLinecap="round"
        />
        <path
          d="M 24 14 C 34 9, 48 9, 58 14"
          stroke="#ffffff"
          strokeOpacity="0.7"
          strokeWidth="1.6"
          strokeLinecap="round"
        />
        {/* Copa izquierda */}
        <rect x="4" y="31" width="9" height="17" rx="4.5" fill="currentColor" fillOpacity="0.28" stroke="currentColor" strokeWidth="1.6" />
        {/* Copa derecha */}
        <rect x="69" y="31" width="9" height="17" rx="4.5" fill="currentColor" fillOpacity="0.28" stroke="currentColor" strokeWidth="1.6" />
      </svg>
    </motion.div>
  )
}

// --- Escenas holográficas para Semáforos y Feedback de Decisión ---
function EscenaAlertaSeguridad({ color }) {
  return (
    <motion.div
      key="escena-alerta-seguridad"
      className="escena-alerta-seguridad"
      style={{ color }}
      initial={{ opacity: 0, scale: 0.85 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.85 }}
      transition={{ duration: 0.25 }}
    >
      <motion.span
        className="alerta-anillo-pulso"
        animate={{ scale: [0.96, 1.24, 0.96], opacity: [0.22, 0.82, 0.22] }}
        transition={{ repeat: Infinity, duration: 1.35, ease: 'easeInOut' }}
      />
      <motion.div
        className="alerta-escudo-badge"
        animate={{ y: [-3, 3, -3] }}
        transition={{ repeat: Infinity, duration: 2.1, ease: 'easeInOut' }}
      >
        <svg width="36" height="40" viewBox="0 0 36 40" fill="none" aria-hidden="true">
          <path
            d="M18 3L31 8.5V19C31 27.6 25.4 34.4 18 37C10.6 34.4 5 27.6 5 19V8.5L18 3Z"
            fill="currentColor"
            fillOpacity="0.16"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinejoin="round"
          />
          <path d="M18 12.5V21.5" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
          <circle cx="18" cy="26.5" r="1.6" fill="currentColor" />
        </svg>
      </motion.div>
    </motion.div>
  )
}

const TARJETAS_ARCHIVO_CFG = [
  { ancho: '72%', delay: 0.0 },
  { ancho: '88%', delay: 0.35 },
  { ancho: '62%', delay: 0.7 },
]

function EscenaOpcionesArchivos({ color }) {
  return (
    <motion.div
      key="escena-opciones-archivos"
      className="escena-opciones-archivos"
      style={{ color }}
      initial={{ opacity: 0, x: -10, scale: 0.88 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: -8, scale: 0.88 }}
      transition={{ type: 'spring', stiffness: 180, damping: 18 }}
    >
      {TARJETAS_ARCHIVO_CFG.map((card, idx) => (
        <motion.div
          key={idx}
          className="opcion-holo-card"
          style={{ borderColor: `${color}88` }}
          animate={{ x: [0, 3.5, 0], opacity: [0.5, 1, 0.5] }}
          transition={{ repeat: Infinity, duration: 2.0, delay: card.delay, ease: 'easeInOut' }}
        >
          <span className="opcion-holo-dot" style={{ background: color }} />
          <span className="opcion-holo-bar" style={{ width: card.ancho, background: color }} />
        </motion.div>
      ))}
    </motion.div>
  )
}

function EscenaFeedbackDecision({ tipo }) {
  const esOk = tipo === 'autorizado'
  const c = esOk ? '#34d399' : '#f43f5e'
  return (
    <motion.div
      key={`escena-feedback-${tipo}`}
      className="escena-feedback-decision"
      style={{ color: c }}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.18 }}
    >
      <motion.span
        className="feedback-onda"
        initial={{ scale: 0.72, opacity: 0.92 }}
        animate={{ scale: 1.48, opacity: 0 }}
        transition={{ duration: 0.68, ease: 'easeOut' }}
      />
      <motion.div
        className="feedback-badge"
        initial={{ scale: 0.4, opacity: 0, rotate: esOk ? -18 : 18 }}
        animate={{ scale: [0.4, 1.15, 1], opacity: 1, rotate: 0 }}
        exit={{ scale: 0.75, opacity: 0 }}
        transition={{ duration: 0.34, ease: 'easeOut' }}
      >
        {esOk ? (
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
            <motion.path
              d="M3.5 9.5L7.4 13.2L14.5 5.2"
              stroke="currentColor"
              strokeWidth="2.4"
              strokeLinecap="round"
              strokeLinejoin="round"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 0.28, delay: 0.06 }}
            />
          </svg>
        ) : (
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
            <motion.path
              d="M5 5L13 13M13 5L5 13"
              stroke="currentColor"
              strokeWidth="2.4"
              strokeLinecap="round"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 0.24, delay: 0.04 }}
            />
          </svg>
        )}
      </motion.div>
    </motion.div>
  )
}

// =========================================
// NÚCLEO L-IA: Expresividad, GPU 60 FPS e Interacciones Táctiles
// =========================================
export default function NucleoLIA({
  estado,
  mensajeEspera,
  modoColapso = false,
  onInteraccion,
  semaforoVisual = null,
  feedbackDecision = null,
}) {
  const estadoReal = estado === 'procesando' ? 'procesando_pregunta' : estado
  const pensando = estadoReal.startsWith('procesando')
  const escribiendoAhora = estadoReal === 'escribiendo'
  const escuchandoAhora = estadoReal === 'escuchando'

  // Exclusión mutua visual: el semáforo activo o su feedback (~1s) prevalecen sobre las mini-escenas
  // técnicas sin mutar `estadoLIA`, evitando colisiones visuales y preservando SSE y polling.
  const feedbackActivo = !modoColapso ? feedbackDecision : null
  const semaforoActivo = !modoColapso && !feedbackActivo ? semaforoVisual : null
  const mostrarEscenaBase = !modoColapso && !semaforoActivo && !feedbackActivo

  const cfg = CONFIG_ESTADOS[estadoReal] || CONFIG_ESTADOS.reposo
  const { label, velAngular, pulso, tonos } = cfg
  const tonosActivos =
    feedbackActivo ? (feedbackActivo.tipo === 'autorizado' ? TONOS_FEEDBACK_OK : TONOS_FEEDBACK_NO) :
    semaforoActivo === 'seguridad' ? TONOS_SEMAFORO_SEGURIDAD :
    semaforoActivo === 'archivos' ? TONOS_SEMAFORO_ARCHIVOS :
    tonos
  const intervaloTono =
    semaforoActivo === 'seguridad' ? 900 : estadoReal === 'error' ? 600 : 2400
  const color = useCicloDeTono(tonosActivos, intervaloTono)
  const colorRostro = '#021017'

  const [gesto, rondaGesto] = useGestoPensamiento(estadoReal === 'procesando_pregunta')
  const gestoHabla = useGestoHabla(escribiendoAhora && mostrarEscenaBase)
  const { nivel, hayVoz } = useNivelMicrofono(escuchandoAhora)
  const gestoEscucha = useGestoEscucha(escuchandoAhora && !hayVoz)

  // Escala reactiva de aureola y boca en GPU
  const escalaAureola = useTransform(nivel, [0, 1], [1.05, 1.58])
  const opacidadAureola = useTransform(nivel, [0, 1], [0.35, 0.95])
  const escalaBocaVoz = useTransform(nivel, [0, 1], [0.85, 1.85])
  const escalaBocaAnchoVoz = useTransform(nivel, [0, 1], [1.0, 1.18])

  // Sub-estados de inactividad + actividades autónomas aleatorias
  const [estadoAnterior, setEstadoAnterior] = useState(estadoReal)
  const [subEstadoReposo, setSubEstadoReposo] = useState('normal')

  // Estado táctil ("poke", "caricia", "escudo") solo en reposo
  const [interaccion, setInteraccion] = useState(null)
  const [etiquetaTactil, setEtiquetaTactil] = useState(null)
  const [glitchPoke, setGlitchPoke] = useState(false)
  const [escudoRebote, setEscudoRebote] = useState(0)

  if (estadoReal !== estadoAnterior) {
    setEstadoAnterior(estadoReal)
    setSubEstadoReposo('normal')
    setInteraccion(null)
    setEtiquetaTactil(null)
    setGlitchPoke(false)
  }

  const subEstado = estadoReal === 'reposo' ? subEstadoReposo : 'normal'
  const interaccionActiva = (estadoReal === 'reposo' && !modoColapso) ? interaccion : null
  const actividadActual =
    estadoReal === 'reposo' && mostrarEscenaBase && !interaccionActiva && ACTIVIDADES_REPOSO.includes(subEstado)
      ? subEstado
      : null

  // Referencias (0 re-renders en loops)
  const wrapperRef = useRef(null)
  const ultimaActividadRef = useRef(0)
  const cicloReposoRef = useRef(null)
  const bloqueoReposoRef = useRef(false)
  const estadoPrevioRef = useRef(estadoReal)
  const pokesRef = useRef(0)
  const interaccionRef = useRef(null)
  const decayTimerRef = useRef(null)
  const interaccionTimerRef = useRef(null)
  const glitchTimerRef = useRef(null)
  const cariciaRef = useRef({ lastX: null, lastY: null, lastTs: 0, acumMs: 0, lastDecayAt: 0 })
  const ultimaEmisionCariciaRef = useRef(0)

  // MotionValues para tracking ocular 2.5D + lectura + actividades
  const miradaTargetX = useMotionValue(0)
  const miradaTargetY = useMotionValue(0)
  const miradaX = useSpring(miradaTargetX, { stiffness: 150, damping: 20, mass: 0.6 })
  const miradaY = useSpring(miradaTargetY, { stiffness: 150, damping: 20, mass: 0.6 })
  const esferaX = useTransform(miradaX, v => v * 0.22)
  const esferaY = useTransform(miradaY, v => v * 0.22)

  // MotionValues para parpadeo/guiño en GPU (scaleY)
  const parpadeoIzqRaw = useMotionValue(1)
  const parpadeoDerRaw = useMotionValue(1)
  const parpadeoIzq = useSpring(parpadeoIzqRaw, { stiffness: 650, damping: 30, mass: 0.35 })
  const parpadeoDer = useSpring(parpadeoDerRaw, { stiffness: 650, damping: 30, mass: 0.35 })

  // Inercia angular continua de anillos y partículas
  const rotExt = useMotionValue(0)
  const rotMed = useMotionValue(0)
  const rotPart = useMotionValue(0)
  const velActualRef = useRef(cfg.velAngular)

  // Impulsos puntuales
  const controlesGesto = useAnimation()

  const reiniciarCicloReposo = useCallback((ahora = performance.now()) => {
    ultimaActividadRef.current = ahora
    cicloReposoRef.current = crearCicloReposoInicial(ahora)
  }, [])

  useEffect(() => {
    bloqueoReposoRef.current = Boolean(interaccion || semaforoActivo || feedbackActivo)
  }, [interaccion, semaforoActivo, feedbackActivo])

  const limpiarTimersTactiles = useCallback(() => {
    clearTimeout(decayTimerRef.current)
    clearTimeout(interaccionTimerRef.current)
    clearTimeout(glitchTimerRef.current)
  }, [])

  useEffect(() => limpiarTimersTactiles, [limpiarTimersTactiles])

  useEffect(() => {
    if (estadoReal !== 'reposo') {
      limpiarTimersTactiles()
      pokesRef.current = 0
      interaccionRef.current = null
      cicloReposoRef.current = null
      cariciaRef.current = { lastX: null, lastY: null, lastTs: 0, acumMs: 0, lastDecayAt: 0 }
    }
  }, [estadoReal, limpiarTimersTactiles])

  const fijarInteraccion = useCallback((tipo, texto) => {
    interaccionRef.current = tipo
    setInteraccion(tipo)
    setEtiquetaTactil(texto)
  }, [])

  const activarEscudo = useCallback((totalClics) => {
    limpiarTimersTactiles()
    pokesRef.current = totalClics
    setGlitchPoke(false)
    fijarInteraccion('escudo', 'ESCUDO ACTIVO // REINICIANDO PACIENCIA...')
    onInteraccion?.({ tipo: 'escudo_paciencia', clics: totalClics })
    controlesGesto.start({
      scale: [0.92, 1.08, 1],
      transition: { duration: 0.38, ease: 'easeOut' },
    })
    interaccionTimerRef.current = setTimeout(() => {
      pokesRef.current = 0
      fijarInteraccion(null, null)
      reiniciarCicloReposo()
    }, 5000)
  }, [limpiarTimersTactiles, fijarInteraccion, onInteraccion, controlesGesto, reiniciarCicloReposo])

  const programarDecayPokes = useCallback(() => {
    clearTimeout(decayTimerRef.current)
    decayTimerRef.current = setTimeout(() => {
      if (interaccionRef.current === 'escudo') return
      pokesRef.current = 0
      if (['sorpresa', 'fastidio', 'advertencia'].includes(interaccionRef.current)) {
        fijarInteraccion(null, null)
        reiniciarCicloReposo()
      }
    }, 6000)
  }, [fijarInteraccion, reiniciarCicloReposo])

  const manejarClickNucleo = useCallback((e) => {
    e.stopPropagation()
    if (estadoReal !== 'reposo' || modoColapso) {
      controlesGesto.start({
        scale: [1, 1.055, 0.975, 1],
        transition: { duration: 0.24, ease: 'easeOut' },
      })
      return
    }

    reiniciarCicloReposo()
    setSubEstadoReposo('normal')
    cariciaRef.current.acumMs = 0

    if (interaccionRef.current === 'escudo') {
      setEscudoRebote(n => n + 1)
      controlesGesto.start({
        x: [0, -3, 2, 0],
        scale: [1, 0.96, 1.02, 1],
        transition: { duration: 0.25 },
      })
      return
    }

    const nuevo = pokesRef.current + 1
    pokesRef.current = nuevo

    if (nuevo >= 9) {
      activarEscudo(nuevo)
      return
    }

    programarDecayPokes()
    clearTimeout(interaccionTimerRef.current)

    if (nuevo <= 2) {
      fijarInteraccion('sorpresa', nuevo === 1 ? '¿QUÉ PASA?' : 'HEY...')
      controlesGesto.start({
        scaleX: [1, 1.16, 0.92, 1.04, 1],
        scaleY: [1, 0.84, 1.08, 0.97, 1],
        transition: { duration: 0.38, ease: 'easeOut' },
      })
      interaccionTimerRef.current = setTimeout(() => {
        if (interaccionRef.current === 'sorpresa') {
          fijarInteraccion(null, null)
          reiniciarCicloReposo()
        }
      }, 1800)
    } else if (nuevo <= 5) {
      const textos = ['OYE, ESO MOLESTA', 'NO TOQUES EL NÚCLEO', 'EN SERIO, PARA...']
      fijarInteraccion('fastidio', textos[nuevo - 3])
      controlesGesto.start({
        scale: [1, 0.91, 1.02, 1],
        y: [0, 3, 0],
        transition: { duration: 0.34, ease: 'easeOut' },
      })
      interaccionTimerRef.current = setTimeout(() => {
        if (interaccionRef.current === 'fastidio') {
          fijarInteraccion(null, null)
          reiniciarCicloReposo()
        }
      }, 2200)
    } else {
      fijarInteraccion('advertencia', 'ÚLTIMA ADVERTENCIA...')
      if (nuevo === 6) {
        onInteraccion?.({ tipo: 'poke_advertencia', clics: nuevo })
      }
      setGlitchPoke(true)
      clearTimeout(glitchTimerRef.current)
      glitchTimerRef.current = setTimeout(() => setGlitchPoke(false), 220)
      controlesGesto.start({
        x: [0, -6, 6, -4, 3, 0],
        scale: [1, 1.08, 0.96, 1],
        transition: { duration: 0.32 },
      })
      interaccionTimerRef.current = setTimeout(() => {
        if (interaccionRef.current === 'advertencia') {
          fijarInteraccion(null, null)
          reiniciarCicloReposo()
        }
      }, 2200)
    }
  }, [estadoReal, modoColapso, controlesGesto, activarEscudo, programarDecayPokes, fijarInteraccion, onInteraccion, reiniciarCicloReposo])

  // Interacción 100% positiva al acariciar suavemente la esfera
  const manejarPointerMoveEsfera = useCallback((e) => {
    if (estadoReal !== 'reposo' || modoColapso || interaccionRef.current === 'escudo') return

    const ahora = performance.now()
    const cRef = cariciaRef.current
    if (cRef.lastX !== null) {
      const dt = Math.min(ahora - cRef.lastTs, 120)
      const dist = Math.hypot(e.clientX - cRef.lastX, e.clientY - cRef.lastY)
      if (dist >= 0.6) {
        cRef.acumMs += dt
        if (cRef.acumMs >= 1200) {
          const recienActivada = interaccionRef.current !== 'caricia'
          if (recienActivada) {
            setSubEstadoReposo('normal')
            fijarInteraccion('caricia', 'ESO SE SIENTE BIEN')
            if (ahora - ultimaEmisionCariciaRef.current >= 5000) {
              ultimaEmisionCariciaRef.current = ahora
              onInteraccion?.({ tipo: 'caricia' })
            }
            if (pokesRef.current > 0) {
              const reducido = Math.max(0, pokesRef.current - 3)
              pokesRef.current = reducido
              cRef.lastDecayAt = ahora
              if (reducido === 0) clearTimeout(decayTimerRef.current)
            }
          } else if (pokesRef.current > 0 && ahora - cRef.lastDecayAt > 420) {
            const reducido = Math.max(0, pokesRef.current - 1)
            pokesRef.current = reducido
            cRef.lastDecayAt = ahora
            if (reducido === 0) clearTimeout(decayTimerRef.current)
          }

          clearTimeout(interaccionTimerRef.current)
          interaccionTimerRef.current = setTimeout(() => {
            if (interaccionRef.current === 'caricia') {
              fijarInteraccion(null, null)
              reiniciarCicloReposo()
            }
            cariciaRef.current.acumMs = 0
          }, 1300)
        }
      }
    }
    cRef.lastX = e.clientX
    cRef.lastY = e.clientY
    cRef.lastTs = ahora
  }, [estadoReal, modoColapso, fijarInteraccion, onInteraccion, reiniciarCicloReposo])

  const manejarPointerLeaveEsfera = useCallback(() => {
    cariciaRef.current.lastX = null
    cariciaRef.current.lastY = null
    cariciaRef.current.acumMs = 0
  }, [])

  // Inercia angular continua (60 FPS)
  useAnimationFrame((_, deltaMs) => {
    const dt = Math.min(deltaMs, 50) / 1000
    let velObjetivo = velAngular
    if (modoColapso) velObjetivo = 540
    else if (feedbackActivo) velObjetivo = feedbackActivo.tipo === 'autorizado' ? 110 : 185
    else if (semaforoActivo === 'seguridad') velObjetivo = 135
    else if (semaforoActivo === 'archivos') velObjetivo = 75
    else if (estadoReal === 'reposo' && subEstado === 'bostezo') velObjetivo = 15
    else if (estadoReal === 'reposo' && subEstado === 'somnolienta') velObjetivo = 10
    else if (estadoReal === 'reposo' && subEstado === 'durmiendo') velObjetivo = 7
    else if (escuchandoAhora) velObjetivo = velAngular + nivel.get() * 115

    velActualRef.current += (velObjetivo - velActualRef.current) * Math.min(1, dt * 3.5)
    const v = velActualRef.current
    rotExt.set(rotExt.get() + v * dt)
    rotMed.set(rotMed.get() - v * 0.68 * dt)
    rotPart.set(rotPart.get() + v * 0.45 * dt)
  })

  // 1. Seguimiento ocular 2.5D relativo al centro real de la ventana/núcleo
  useEffect(() => {
    const onMouseMove = (e) => {
      reiniciarCicloReposo()
      if (estadoReal === 'reposo') {
        setSubEstadoReposo(prev => (prev === 'normal' ? prev : 'normal'))
      }
      if (estadoReal !== 'reposo' || subEstado === 'durmiendo' || modoColapso || semaforoActivo || feedbackActivo) return
      if (interaccionRef.current === 'escudo') return

      const rect = wrapperRef.current?.getBoundingClientRect()
      const cx = rect ? rect.left + rect.width / 2 : window.innerWidth / 2
      const cy = rect ? rect.top + rect.height / 2 : 95
      const dx = (e.clientX - cx) / 140
      const dy = (e.clientY - cy) / 140
      miradaTargetX.set(Math.tanh(dx) * 8.2)
      miradaTargetY.set(Math.tanh(dy) * 5.6)
    }
    window.addEventListener('mousemove', onMouseMove, { passive: true })
    return () => window.removeEventListener('mousemove', onMouseMove)
  }, [estadoReal, subEstado, modoColapso, semaforoActivo, feedbackActivo, miradaTargetX, miradaTargetY, reiniciarCicloReposo])

  // 2. Reloj de inactividad con máquina de fases: actividades pausadas (22-34s),
  //    pausas en 'normal' y transición conjunta bostezo -> somnolienta -> durmiendo.
  useEffect(() => {
    if (estadoReal !== 'reposo' || modoColapso) return
    reiniciarCicloReposo()
    const id = setInterval(() => {
      // Pausar progresión durante interacciones táctiles o modales activos para no interrumpir al usuario
      if (bloqueoReposoRef.current || interaccionRef.current) {
        reiniciarCicloReposo(performance.now())
        return
      }
      // Avance por timestamps: 0 re-renders por segundo mientras permanece dentro de una fase
      const ahora = performance.now()
      const ciclo = cicloReposoRef.current || crearCicloReposoInicial(ahora)
      if (ciclo.fase === 'durmiendo' || ahora < ciclo.finFaseTs) return

      if (ciclo.fase === 'normal_inicial' || ciclo.fase === 'pausa') {
        const act = elegirActividadAleatoria(ciclo.ultimaActividad)
        cicloReposoRef.current = {
          fase: 'actividad',
          finFaseTs: ahora + aleatorioEntre(...TIEMPOS_REPOSO_MS.actividad),
          actividadesHechas: ciclo.actividadesHechas + 1,
          ultimaActividad: act,
        }
        setSubEstadoReposo(act)
        return
      }

      if (ciclo.fase === 'actividad') {
        const siguienteFase = ciclo.actividadesHechas < 2 ? 'pausa' : 'pausa_sueno'
        const [minPausa, maxPausa] =
          siguienteFase === 'pausa'
            ? TIEMPOS_REPOSO_MS.pausaEntreActividades
            : TIEMPOS_REPOSO_MS.pausaPreSueno
        cicloReposoRef.current = {
          ...ciclo,
          fase: siguienteFase,
          finFaseTs: ahora + aleatorioEntre(minPausa, maxPausa),
        }
        setSubEstadoReposo('normal')
        return
      }

      if (ciclo.fase === 'pausa_sueno') {
        cicloReposoRef.current = { ...ciclo, fase: 'bostezo', finFaseTs: ahora + TIEMPOS_REPOSO_MS.bostezo }
        setSubEstadoReposo('bostezo')
        return
      }

      if (ciclo.fase === 'bostezo') {
        cicloReposoRef.current = { ...ciclo, fase: 'somnolienta', finFaseTs: ahora + TIEMPOS_REPOSO_MS.somnolienta }
        setSubEstadoReposo('somnolienta')
        return
      }

      if (ciclo.fase === 'somnolienta') {
        cicloReposoRef.current = { ...ciclo, fase: 'durmiendo', finFaseTs: Infinity }
        setSubEstadoReposo('durmiendo')
      }
    }, 1000)
    return () => clearInterval(id)
  }, [estadoReal, modoColapso, reiniciarCicloReposo])

  // 3. Dirección de mirada según semáforos, estado, actividades autónomas e interacción táctil
  useEffect(() => {
    if (feedbackActivo) {
      miradaTargetX.set(0)
      miradaTargetY.set(feedbackActivo.tipo === 'autorizado' ? -0.6 : 0)
      return
    }

    if (semaforoActivo === 'seguridad') {
      miradaTargetX.set(0)
      miradaTargetY.set(3.0)
      return
    }

    if (semaforoActivo === 'archivos') {
      let miraOpciones = true
      miradaTargetX.set(3.4)
      miradaTargetY.set(-0.4)
      const id = setInterval(() => {
        miraOpciones = !miraOpciones
        miradaTargetX.set(miraOpciones ? 3.4 : 0)
        miradaTargetY.set(miraOpciones ? -0.4 : 2.8)
      }, 1400)
      return () => clearInterval(id)
    }

    if (estadoReal === 'procesando_doc' || actividadActual === 'leer_libre') {
      let paso = 0
      const puntos = [
        { x: -2.2, y: -2.0 },
        { x: 2.0, y: -2.0 },
        { x: 5.8, y: -2.0 },
        { x: -1.8, y: 0.0 },
        { x: 2.2, y: 0.0 },
        { x: 5.8, y: 0.0 },
        { x: -1.5, y: 2.0 },
        { x: 2.4, y: 2.0 },
        { x: 5.4, y: 2.0 },
      ]
      miradaTargetX.set(puntos[0].x)
      miradaTargetY.set(puntos[0].y)
      const id = setInterval(() => {
        paso = (paso + 1) % puntos.length
        miradaTargetX.set(puntos[paso].x)
        miradaTargetY.set(puntos[paso].y)
      }, 420)
      return () => clearInterval(id)
    }

    if (estadoReal === 'procesando_sistema') {
      let idx = 0
      const focos = [
        { x: 2.8, y: -1.6 },
        { x: 0.0, y: 0.0 },
        { x: -2.6, y: 1.2 },
      ]
      miradaTargetX.set(focos[0].x)
      miradaTargetY.set(focos[0].y)
      const id = setInterval(() => {
        idx = (idx + 1) % focos.length
        miradaTargetX.set(focos[idx].x)
        miradaTargetY.set(focos[idx].y)
      }, 1050)
      return () => clearInterval(id)
    }

    if (estadoReal === 'procesando_git') {
      miradaTargetX.set(3.4)
      miradaTargetY.set(-1.2)
      return
    }

    if (estadoReal === 'procesando_rag') {
      let arriba = true
      miradaTargetX.set(-2.2)
      miradaTargetY.set(-2.4)
      const id = setInterval(() => {
        arriba = !arriba
        miradaTargetY.set(arriba ? -2.6 : 2.6)
      }, 620)
      return () => clearInterval(id)
    }

    if (estadoReal === 'procesando_pregunta') {
      const mapa = {
        duda: { x: -2.2, y: -2.4 },
        mirada_arriba: { x: 2.0, y: -4.2 },
        ceja_alzada: { x: -1.2, y: -1.6 },
        concentracion: { x: 0, y: 0.6 },
        casi: { x: 0, y: -1.2 },
      }
      const m = mapa[gesto] ?? { x: 0, y: 0 }
      miradaTargetX.set(m.x)
      miradaTargetY.set(m.y)
      return
    }

    if (escribiendoAhora) {
      const mapa = {
        neutro: { x: 0, y: 0 },
        asentir: { x: 0, y: 1.4 },
        ladeo_izq: { x: -2.6, y: -0.6 },
        ladeo_der: { x: 2.6, y: -0.6 },
        enfasis_ceja: { x: 1.4, y: -1.6 },
        calido: { x: 0, y: -0.6 },
        enfocado: { x: 0, y: 0.5 },
      }
      const m = mapa[gestoHabla.tipo] ?? { x: 0, y: 0 }
      miradaTargetX.set(m.x)
      miradaTargetY.set(m.y)
      return
    }

    if (escuchandoAhora) {
      miradaTargetX.set(hayVoz ? 0 : ({ ladeaIzq: -4.2, ladeaDer: 4.2 }[gestoEscucha] ?? 0))
      miradaTargetY.set(hayVoz ? -1.4 : 0)
      return
    }

    if (estadoReal !== 'reposo') {
      miradaTargetX.set(0)
      miradaTargetY.set(0)
      return
    }

    if (interaccionActiva === 'escudo') {
      miradaTargetX.set(6.8)
      miradaTargetY.set(-0.6)
      return
    }

    if (interaccionActiva) {
      miradaTargetX.set(0)
      miradaTargetY.set(interaccionActiva === 'sorpresa' ? -1.4 : 0)
      return
    }

    if (subEstado === 'bostezo') {
      miradaTargetX.set(0)
      miradaTargetY.set(-0.8)
      return
    }

    if (subEstado === 'somnolienta') {
      miradaTargetX.set(0)
      miradaTargetY.set(2.2)
      return
    }

    if (subEstado === 'durmiendo') {
      miradaTargetX.set(0)
      miradaTargetY.set(3.5)
      return
    }

    if (actividadActual === 'jugar_orbe') {
      let abajo = false
      miradaTargetX.set(4.5)
      miradaTargetY.set(-3.0)
      const id = setInterval(() => {
        abajo = !abajo
        miradaTargetY.set(abajo ? 2.4 : -3.0)
      }, 625)
      return () => clearInterval(id)
    }

    if (actividadActual === 'explorar_formas') {
      let idx = 0
      const puntos = [
        { x: 4.2, y: -2.2 },
        { x: 4.8, y: 0.4 },
        { x: 3.6, y: 2.2 },
      ]
      miradaTargetX.set(puntos[0].x)
      miradaTargetY.set(puntos[0].y)
      const id = setInterval(() => {
        idx = (idx + 1) % puntos.length
        miradaTargetX.set(puntos[idx].x)
        miradaTargetY.set(puntos[idx].y)
      }, 1150)
      return () => clearInterval(id)
    }

    if (actividadActual === 'accesorio_audio') {
      miradaTargetX.set(0)
      miradaTargetY.set(-0.8)
      return
    }

    // Mirada errante natural tras >3s sin mover el cursor
    let timerId
    const cicloMirada = () => {
      const espera = 2200 + Math.random() * 2000
      timerId = setTimeout(() => {
        const inactivoSeg = (performance.now() - ultimaActividadRef.current) / 1000
        if (inactivoSeg > 3) {
          const ang = Math.random() * Math.PI * 2
          const rad = 2.8 + Math.random() * 4.2
          miradaTargetX.set(Math.cos(ang) * rad)
          miradaTargetY.set(Math.sin(ang) * (rad * 0.55))
        }
        cicloMirada()
      }, espera)
    }
    cicloMirada()
    return () => clearTimeout(timerId)
  }, [
    estadoReal,
    subEstado,
    actividadActual,
    interaccionActiva,
    semaforoActivo,
    feedbackActivo,
    gesto,
    escribiendoAhora,
    gestoHabla,
    escuchandoAhora,
    hayVoz,
    gestoEscucha,
    miradaTargetX,
    miradaTargetY,
  ])

  // 4. Parpadeo orgánico GPU (cadencia variable, doble parpadeo ocasional y guiño en caricia/orbe)
  useEffect(() => {
    if (
      subEstado === 'durmiendo' ||
      subEstado === 'bostezo' ||
      subEstado === 'somnolienta' ||
      modoColapso ||
      Boolean(feedbackActivo)
    ) {
      parpadeoIzqRaw.set(1)
      parpadeoDerRaw.set(1)
      return
    }

    let activo = true
    const timers = new Set()
    const esperar = (ms, fn) => {
      const id = setTimeout(() => {
        timers.delete(id)
        if (activo) fn()
      }, ms)
      timers.add(id)
    }

    const ejecutarParpadeo = () => {
      const guinoAlegre =
        estadoReal === 'reposo' &&
        (interaccionActiva === 'caricia' || actividadActual === 'jugar_orbe') &&
        Math.random() < 0.25

      parpadeoDerRaw.set(0.08)
      if (!guinoAlegre) parpadeoIzqRaw.set(0.08)

      esperar(105, () => {
        parpadeoIzqRaw.set(1)
        parpadeoDerRaw.set(1)

        if (!guinoAlegre && Math.random() < 0.2) {
          esperar(130, () => {
            parpadeoIzqRaw.set(0.08)
            parpadeoDerRaw.set(0.08)
            esperar(95, () => {
              parpadeoIzqRaw.set(1)
              parpadeoDerRaw.set(1)
            })
          })
        }
      })
    }

    const programarCiclo = () => {
      const intervalo = 2400 + Math.random() * 3400
      esperar(intervalo, () => {
        ejecutarParpadeo()
        programarCiclo()
      })
    }
    programarCiclo()

    return () => {
      activo = false
      timers.forEach(clearTimeout)
      timers.clear()
      parpadeoIzqRaw.set(1)
      parpadeoDerRaw.set(1)
    }
  }, [estadoReal, subEstado, actividadActual, interaccionActiva, modoColapso, feedbackActivo, parpadeoIzqRaw, parpadeoDerRaw])

  // 5. Micro-gestos puntuales de transición (`escribiendo -> reposo`, `-> error`, semáforos, énfasis)
  const feedbackId = feedbackActivo?.id ?? null
  const feedbackTipo = feedbackActivo?.tipo ?? null
  useEffect(() => {
    if (!feedbackId || !feedbackTipo) return
    if (feedbackTipo === 'autorizado') {
      controlesGesto.start({
        y: [0, 6, -1.5, 3, 0],
        scale: [1, 1.07, 0.99, 1.02, 1],
        transition: { duration: 0.56, ease: 'easeInOut' },
      })
    } else {
      controlesGesto.start({
        x: [0, -6.5, 6.5, -4, 3, 0],
        scale: [1, 0.95, 1.02, 1],
        transition: { duration: 0.44, ease: 'easeOut' },
      })
    }
  }, [feedbackId, feedbackTipo, controlesGesto])

  useEffect(() => {
    const previo = estadoPrevioRef.current
    estadoPrevioRef.current = estadoReal

    if (previo === 'escribiendo' && estadoReal === 'reposo') {
      controlesGesto.start({
        y: [0, 5.5, -1, 2.5, 0],
        scale: [1, 1.03, 1, 1.015, 1],
        transition: { duration: 0.52, ease: 'easeInOut' },
      })
    } else if (previo !== 'error' && estadoReal === 'error') {
      controlesGesto.start({
        x: [0, -7, 7, -5, 4, -2, 0],
        scale: [1, 1.12, 0.96, 1.04, 1],
        transition: { duration: 0.46, ease: 'easeOut' },
      })
    }
  }, [estadoReal, controlesGesto])

  useEffect(() => {
    if (!escribiendoAhora || gestoHabla.tipo !== 'asentir') return
    controlesGesto.start({
      y: [0, 3.8, 0],
      transition: { duration: 0.36, ease: 'easeInOut' },
    })
  }, [escribiendoAhora, gestoHabla, controlesGesto])

  // --- GEOMETRÍA FACIAL ASIMÉTRICA ---
  const getOjos = () => {
    const base = (cfgOjo) => ({ scaleX: 1, scaleY: 1, ...cfgOjo })

    if (feedbackActivo) {
      if (feedbackActivo.tipo === 'autorizado') {
        const g = base({ height: '5.5px', width: '11px', y: -1, rotate: 0, borderRadius: '50% 50% 0 0' })
        return { izq: g, der: g }
      }
      return {
        izq: base({ height: '5.5px', width: '10.5px', y: 1, rotate: 14, borderRadius: '3px' }),
        der: base({ height: '5.5px', width: '10.5px', y: 1, rotate: -14, borderRadius: '3px' }),
      }
    }

    if (semaforoActivo === 'seguridad') {
      return {
        izq: base({ height: '7.5px', width: '10px', y: 0, rotate: 8, borderRadius: '40%' }),
        der: base({ height: '7.5px', width: '10px', y: 0, rotate: -8, borderRadius: '40%' }),
      }
    }

    if (semaforoActivo === 'archivos') {
      const g = base({ height: '10.5px', width: '10px', y: -1, rotate: 0, borderRadius: '50%' })
      return { izq: g, der: g }
    }

    if (estadoReal === 'reposo') {
      if (interaccionActiva === 'escudo') {
        return {
          izq: base({ height: '3.5px', width: '10px', y: 0, rotate: 6, borderRadius: '3px' }),
          der: base({ height: '3.5px', width: '10px', y: 0, rotate: -6, borderRadius: '3px' }),
        }
      }
      if (interaccionActiva === 'caricia') {
        const g = base({ height: '5.5px', width: '11px', y: -1, rotate: 0, borderRadius: '50% 50% 0 0' })
        return { izq: g, der: g }
      }
      if (interaccionActiva === 'sorpresa') {
        const g = base({ height: '12px', width: '12px', y: -2, rotate: 0, borderRadius: '50%' })
        return { izq: g, der: g }
      }
      if (interaccionActiva === 'fastidio') {
        return {
          izq: base({ height: '6px', width: '10px', y: 1, rotate: 16, borderRadius: '3px' }),
          der: base({ height: '6px', width: '10px', y: 1, rotate: -16, borderRadius: '3px' }),
        }
      }
      if (interaccionActiva === 'advertencia') {
        return {
          izq: base({ height: '5.5px', width: '11px', y: 1, rotate: 24, borderRadius: '3px' }),
          der: base({ height: '5.5px', width: '11px', y: 1, rotate: -24, borderRadius: '3px' }),
        }
      }
      if (subEstado === 'durmiendo') {
        const g = base({ height: '2px', width: '10px', y: 3, rotate: 0, borderRadius: '2px' })
        return { izq: g, der: g }
      }
      if (subEstado === 'somnolienta') {
        const g = base({
          height: '5px',
          width: '10px',
          y: 2,
          rotate: 0,
          borderRadius: '2px 2px 50% 50%',
          scaleY: [0.92, 0.24, 0.56, 0.18],
        })
        return { izq: g, der: g }
      }
      if (subEstado === 'bostezo') {
        return {
          izq: base({ height: '4px', width: '10px', y: -1, rotate: -10, borderRadius: '50% 50% 20% 20%' }),
          der: base({ height: '4px', width: '10px', y: -1, rotate: 10, borderRadius: '50% 50% 20% 20%' }),
        }
      }
      if (actividadActual === 'jugar_orbe') {
        const g = base({ height: '10px', width: '10px', y: -1, rotate: 0, borderRadius: '50%' })
        return { izq: g, der: g }
      }
      if (actividadActual === 'explorar_formas') {
        return {
          izq: base({ height: '7.5px', width: '9px', y: 0, rotate: -6, borderRadius: '40%' }),
          der: base({ height: '11px', width: '9.5px', y: -2, rotate: 0, borderRadius: '50%' }),
        }
      }
      if (actividadActual === 'leer_libre') {
        const g = base({ height: '5px', width: '5px', y: -1, rotate: 0, borderRadius: '50%' })
        return { izq: g, der: g }
      }
      if (actividadActual === 'accesorio_audio') {
        const g = base({ height: '5px', width: '11px', y: -1, rotate: 0, borderRadius: '50% 50% 0 0' })
        return { izq: g, der: g }
      }
    }

    if (estadoReal === 'error') {
      return {
        izq: base({ height: '6px', width: '10px', y: 1, rotate: 20, borderRadius: '3px' }),
        der: base({ height: '10px', width: '10px', y: 0, rotate: -12, borderRadius: '50%' }),
      }
    }

    if (estadoReal === 'procesando_sistema') {
      return {
        izq: base({ height: '8px', width: '9.5px', y: -1, rotate: -3, borderRadius: '38%' }),
        der: base({ height: '8px', width: '9.5px', y: -1, rotate: 3, borderRadius: '38%' }),
      }
    }
    if (estadoReal === 'procesando_doc') {
      const g = base({ height: '5px', width: '5px', y: -1, rotate: 0, borderRadius: '50%' })
      return { izq: g, der: g }
    }
    if (estadoReal === 'procesando_rag' || estadoReal === 'procesando_git') {
      const g = base({ height: '10px', width: '10px', y: -1, rotate: 0, borderRadius: '50%' })
      return { izq: g, der: g }
    }

    if (estadoReal === 'procesando_pregunta') {
      if (gesto === 'mirada_arriba') {
        const g = base({ height: '8px', width: '9px', y: -4, rotate: 0, borderRadius: '50%' })
        return { izq: g, der: g }
      }
      if (gesto === 'ceja_alzada') {
        return {
          izq: base({ height: '6px', width: '9px', y: 0, rotate: -8, borderRadius: '35%' }),
          der: base({ height: '11px', width: '9px', y: -2, rotate: 0, borderRadius: '50%' }),
        }
      }
      if (gesto === 'concentracion') {
        const g = base({ height: '6px', width: '10px', y: 0, rotate: 0, borderRadius: '30%', scaleY: 0.85 })
        return { izq: g, der: g }
      }
      if (gesto === 'casi') {
        const g = base({ height: '9.5px', width: '9.5px', y: -1, rotate: 0, borderRadius: '50%', scaleY: 1.1 })
        return { izq: g, der: g }
      }
      return {
        izq: base({ height: '9px', width: '9px', y: -1, rotate: -6, borderRadius: '50%' }),
        der: base({ height: '7px', width: '9px', y: 0, rotate: 8, borderRadius: '40%' }),
      }
    }

    if (escribiendoAhora) {
      if (gestoHabla.tipo === 'enfasis_ceja') {
        return {
          izq: base({ height: '7px', width: '9px', y: 0, rotate: -6, borderRadius: '40%' }),
          der: base({ height: '11px', width: '9px', y: -2, rotate: 4, borderRadius: '50%' }),
        }
      }
      if (gestoHabla.tipo === 'calido') {
        const g = base({ height: '6.5px', width: '10px', y: -1, rotate: 0, borderRadius: '50% 50% 25% 25%' })
        return { izq: g, der: g }
      }
      if (gestoHabla.tipo === 'enfocado') {
        const g = base({ height: '7px', width: '9.5px', y: 0, rotate: 0, borderRadius: '35%' })
        return { izq: g, der: g }
      }
      return {
        izq: base({ height: '8.5px', width: '9px', y: -1, rotate: -4, borderRadius: '4px 4px 50% 50%' }),
        der: base({ height: '8.5px', width: '9px', y: -1, rotate: 4, borderRadius: '4px 4px 50% 50%' }),
      }
    }

    if (escuchandoAhora) {
      if (hayVoz) {
        const g = base({ height: '13px', width: '13px', y: -1, rotate: 0, borderRadius: '50%' })
        return { izq: g, der: g }
      }
      if (gestoEscucha === 'ladeaIzq') {
        return {
          izq: base({ height: '10px', width: '10px', y: -1, rotate: -8, borderRadius: '50%', scaleY: 1.08 }),
          der: base({ height: '11px', width: '11px', y: -1, rotate: 4, borderRadius: '50%', scaleY: 1.08 }),
        }
      }
      if (gestoEscucha === 'ladeaDer') {
        return {
          izq: base({ height: '11px', width: '11px', y: -1, rotate: -4, borderRadius: '50%', scaleY: 1.08 }),
          der: base({ height: '10px', width: '10px', y: -1, rotate: 8, borderRadius: '50%', scaleY: 1.08 }),
        }
      }
      const g = base({ height: '11px', width: '11px', y: -2, rotate: 0, borderRadius: '50%', scaleY: 1.12 })
      return { izq: g, der: g }
    }

    const normal = base({ height: '9px', width: '9px', y: 0, rotate: 0, borderRadius: '50%' })
    return { izq: normal, der: normal }
  }

  const getBoca = () => {
    const base = (cfgBoca) => ({ scaleY: 1, rotate: 0, ...cfgBoca })

    if (feedbackActivo) {
      return feedbackActivo.tipo === 'autorizado'
        ? base({ width: '14px', height: '6.5px', borderRadius: '0 0 10px 10px', y: 2 })
        : base({ width: '12px', height: '2.8px', borderRadius: '2px', rotate: -8, y: 1 })
    }
    if (semaforoActivo === 'seguridad') {
      return base({ width: '8px', height: '2.5px', borderRadius: '2px', rotate: -4, y: 1.5 })
    }
    if (semaforoActivo === 'archivos') {
      return base({ width: '6px', height: '5px', borderRadius: '50%', y: 1.5 })
    }

    if (estadoReal === 'reposo') {
      if (interaccionActiva === 'escudo') return base({ width: '10px', height: '2.5px', borderRadius: '1px', rotate: -4, y: 1 })
      if (interaccionActiva === 'caricia') return base({ width: '14px', height: '6.5px', borderRadius: '0 0 10px 10px', y: 2 })
      if (interaccionActiva === 'sorpresa') return base({ width: '7px', height: '7px', borderRadius: '50%', y: 2 })
      if (interaccionActiva === 'fastidio') return base({ width: '11px', height: '3px', borderRadius: '2px', rotate: -8, y: 1 })
      if (interaccionActiva === 'advertencia') return base({ width: '13px', height: '3px', borderRadius: '2px', rotate: -12, y: 1 })
      if (subEstado === 'durmiendo') return base({ width: '6px', height: '2px', borderRadius: '1px', y: 3 })
      if (subEstado === 'somnolienta') return base({ width: '7px', height: '2.5px', borderRadius: '2px', y: 2.5 })
      if (subEstado === 'bostezo') {
        return base({
          width: ['9px', '10.5px', '10px', '8px'],
          height: ['3px', '13px', '12px', '4.5px'],
          borderRadius: '45%',
          y: 1,
        })
      }
      if (actividadActual === 'jugar_orbe' || actividadActual === 'accesorio_audio') {
        return base({ width: '13px', height: '5.5px', borderRadius: '0 0 10px 10px', y: 2 })
      }
      if (actividadActual === 'explorar_formas') return base({ width: '6px', height: '4px', borderRadius: '50%', y: 1 })
      if (actividadActual === 'leer_libre') return base({ width: '5px', height: '2px', borderRadius: '1px', y: 1 })
    }

    if (estadoReal === 'error') return base({ width: '13px', height: '3px', borderRadius: '2px', rotate: -14, y: 1 })
    if (estadoReal === 'procesando_doc') return base({ width: '5px', height: '2px', borderRadius: '1px', y: 1 })
    if (['procesando_rag', 'procesando_git', 'procesando_sistema'].includes(estadoReal)) {
      return base({ width: '5px', height: '5px', borderRadius: '50%', y: 0 })
    }

    if (estadoReal === 'procesando_pregunta') {
      if (gesto === 'mirada_arriba') return base({ width: '5px', height: '5px', borderRadius: '50%', y: 0 })
      if (gesto === 'ceja_alzada') return base({ width: '7px', height: '3px', borderRadius: '2px', rotate: 5, y: 1 })
      if (gesto === 'concentracion') return base({ width: '9px', height: '2px', borderRadius: '1px', y: 2 })
      if (gesto === 'casi') return base({ width: '6px', height: '6px', borderRadius: '50%', y: 1 })
      return base({ width: '4.5px', height: '4.5px', borderRadius: '50%', y: 1 })
    }

    if (escribiendoAhora) {
      if (gestoHabla.tipo === 'calido') {
        return { width: '15px', height: '6px', borderRadius: '2px 2px 10px 10px', scaleY: [0.85, 1.35, 0.95, 1.25, 0.85], rotate: 0, y: 0 }
      }
      if (gestoHabla.tipo === 'enfasis_ceja') {
        return { width: '13px', height: '6px', borderRadius: '4px 4px 10px 10px', scaleY: [0.9, 1.48, 0.85, 1.35, 0.9], rotate: -3, y: 0 }
      }
      return { width: '14px', height: '5.5px', borderRadius: '3px 3px 10px 10px', scaleY: [0.85, 1.42, 0.92, 1.28, 0.85], rotate: 0, y: 0 }
    }

    if (escuchandoAhora) {
      return hayVoz
        ? base({ width: '8px', height: '8px', borderRadius: '50%', y: 2 })
        : base({ width: '5px', height: '5px', borderRadius: '50%', y: 2 })
    }

    return base({ width: '10px', height: '3px', borderRadius: '1px 1px 6px 6px', y: 1 })
  }

  const ojosCfg = getOjos()
  const bocaCfg = getBoca()

  const posturaRotate =
    feedbackActivo ? 0 :
    semaforoActivo === 'seguridad' ? 0 :
    semaforoActivo === 'archivos' ? 3 :
    interaccionActiva === 'escudo' ? -8 :
    interaccionActiva === 'fastidio' ? -10 :
    interaccionActiva === 'advertencia' ? -12 :
    interaccionActiva === 'caricia' ? 4 :
    subEstado === 'bostezo' ? -4 :
    subEstado === 'somnolienta' ? 3 :
    escuchandoAhora && !hayVoz
      ? ({ ladeaIzq: -9, ladeaDer: 9 }[gestoEscucha] ?? 0)
      : escribiendoAhora
        ? ({ ladea_izq: -5.5, ladea_der: 5.5, enfasis_ceja: -3 }[gestoHabla.tipo] ?? 0)
        : estadoReal === 'procesando_pregunta'
          ? ({ duda: 12, mirada_arriba: -6, ceja_alzada: 8, concentracion: -4, casi: 0 }[gesto] ?? 0)
          : actividadActual === 'explorar_formas' ? 5 : 0

  const ETIQUETA_ACTIVIDAD = {
    jugar_orbe: 'JUGANDO EN ESPERA...',
    explorar_formas: 'EXPLORANDO GEOMETRÍA...',
    leer_libre: 'LEYENDO REGISTROS...',
    accesorio_audio: 'MODO SINTONÍA...',
  }

  const textoEtiqueta =
    feedbackActivo
      ? (feedbackActivo.tipo === 'autorizado'
          ? (feedbackActivo.origen === 'archivos' ? 'ARCHIVO SELECCIONADO' : 'AUTORIZACIÓN CONCEDIDA')
          : (feedbackActivo.origen === 'archivos' ? 'BÚSQUEDA CANCELADA' : 'ACCIÓN ABORTADA')) :
    semaforoActivo === 'seguridad' ? 'ESPERANDO AUTORIZACIÓN...' :
    semaforoActivo === 'archivos' ? 'ESPERANDO SELECCIÓN...' :
    interaccionActiva && etiquetaTactil ? etiquetaTactil :
    escuchandoAhora ? (hayVoz ? 'ESCUCHANDO...' : 'ESPERANDO VOZ...') :
    subEstado === 'durmiendo' ? 'SUSPENDIDA (REPOSO)' :
    (subEstado === 'bostezo' || subEstado === 'somnolienta') ? 'ENTRANDO EN REPOSO...' :
    actividadActual ? ETIQUETA_ACTIVIDAD[actividadActual] :
    pensando && mensajeEspera ? mensajeEspera.toUpperCase() :
    pensando && FRASES_PENSAMIENTO[estadoReal]
      ? FRASES_PENSAMIENTO[estadoReal][rondaGesto % FRASES_PENSAMIENTO[estadoReal].length]
      : label

  const zIndexOverride = modoColapso ? { zIndex: 10001, position: 'relative' } : {}
  const c = modoColapso
    ? '#ff0033'
    : feedbackActivo
      ? (feedbackActivo.tipo === 'autorizado' ? '#34d399' : '#f43f5e')
      : (interaccionActiva === 'advertencia' ? '#f43f5e' : color)
  const mostrarLentes =
    mostrarEscenaBase &&
    (estadoReal === 'procesando_doc' || actividadActual === 'leer_libre')
  const ojoTransicion =
    !feedbackActivo && !semaforoActivo && subEstado === 'somnolienta'
      ? { scaleY: { duration: 4.0, times: [0, 0.36, 0.64, 1], ease: 'easeInOut' }, default: { type: 'spring', stiffness: 120, damping: 20 } }
      : { type: 'spring', stiffness: 280, damping: 22 }

  return (
    <div
      ref={wrapperRef}
      className={`nucleo-wrapper nucleo-lia ${(modoColapso || glitchPoke) ? 'glitch-rgb' : ''}`}
      style={zIndexOverride}
    >
      <motion.div
        className="nucleo-halo"
        style={{ background: `radial-gradient(circle, ${c}30 0%, ${c}12 42%, transparent 72%)` }}
        animate={{
          scale: (subEstado === 'durmiendo' || subEstado === 'somnolienta') ? [0.95, 1.0, 0.95] : [0.96, 1.05, 0.96],
          opacity: [0.65, 1, 0.65],
        }}
        transition={{ repeat: Infinity, duration: pulso, ease: 'easeInOut' }}
      />

      {/* MINI-ESCENAS HOLOGRÁFICAS, SEMÁFOROS Y ACTIVIDADES AUTÓNOMAS (0 MB VRAM · GPU) */}
      <AnimatePresence>
        {mostrarEscenaBase && estadoReal === 'procesando_sistema' && <EscenaSistema color={c} />}
        {mostrarEscenaBase && estadoReal === 'procesando_git' && <EscenaGit color={c} />}
        {mostrarEscenaBase && estadoReal === 'procesando_rag' && <EscenaRAG color={c} />}
        {mostrarEscenaBase && (estadoReal === 'procesando_doc' || actividadActual === 'leer_libre') && (
          <EscenaDoc color={c} />
        )}
        {actividadActual === 'jugar_orbe' && <ActividadOrbe color={c} />}
        {actividadActual === 'explorar_formas' && <ActividadFormas color={c} />}
        {mostrarEscenaBase && escuchandoAhora && <ArcosAcusticos color={c} hayVoz={hayVoz} />}
        {mostrarEscenaBase && escribiendoAhora && <ChispasEscritura color={c} />}
        {mostrarEscenaBase && interaccionActiva === 'escudo' && <EscudoHexagonal pulsoRebote={escudoRebote} />}
        {semaforoActivo === 'seguridad' && <EscenaAlertaSeguridad color={c} />}
        {semaforoActivo === 'archivos' && <EscenaOpcionesArchivos color={c} />}
        {feedbackActivo && <EscenaFeedbackDecision key={`fb-${feedbackActivo.id}`} tipo={feedbackActivo.tipo} />}
      </AnimatePresence>

      {/* AUREOLA DE ESCUCHA */}
      <AnimatePresence>
        {mostrarEscenaBase && escuchandoAhora && (
          <motion.div
            key="aureola"
            className="aureola-escucha"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ duration: 0.25 }}
          >
            <motion.div
              className="aureola-voz"
              style={{
                scale: escalaAureola,
                opacity: opacidadAureola,
                borderColor: color,
                background: `radial-gradient(circle, transparent 52%, ${color}33 74%, transparent 100%)`,
              }}
            />
            {[0, 1, 2].map(i => (
              <motion.span
                key={i}
                className="onda-escucha"
                style={{ borderColor: color }}
                animate={{ scale: [1.85, 1], opacity: [0, 0.75, 0] }}
                transition={{ repeat: Infinity, duration: 1.8, delay: i * 0.6, ease: 'easeIn' }}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Onda expansiva al cambiar de estado */}
      <motion.div
        key={`onda-${estadoReal}`}
        className="aureola-voz"
        style={{ borderColor: c }}
        initial={{ scale: 0.72, opacity: 0.75 }}
        animate={{ scale: 1.65, opacity: 0 }}
        transition={{ duration: 0.75, ease: 'easeOut' }}
      />

      {/* PARTÍCULAS ORBITALES CON INERCIA ANGULAR */}
      <motion.div className="anillo-particulas" style={{ rotate: rotPart }}>
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <span
            key={i}
            className="particula"
            style={{
              '--i': i,
              background: c,
              opacity: subEstado === 'durmiendo' ? 0.45 : subEstado === 'somnolienta' ? 0.65 : 0.9,
            }}
          />
        ))}
      </motion.div>

      {/* ANILLOS CON INERCIA ANGULAR */}
      <motion.div
        className="anillo-exterior"
        style={{ borderColor: c, rotate: rotExt }}
      />
      <motion.div
        className="anillo-medio"
        style={{ borderTopColor: modoColapso ? '#00ffff' : c, borderBottomColor: c, rotate: rotMed }}
      />
      <motion.div
        className="anillo-interior"
        style={{ borderTopColor: modoColapso ? '#00ffff' : c, borderBottomColor: modoColapso ? '#00ffff' : c }}
        animate={{ scale: [1, 1.12, 1], opacity: [0.55, 1, 0.55] }}
        transition={{ repeat: Infinity, duration: pulso, ease: 'easeInOut' }}
      />

      {/* NÚCLEO: Levitación orgánica ±3px + Impulso puntual + Postura/Cabeceo + Esfera */}
      <motion.div
        className="nucleo-levitacion-wrap"
        animate={{
          y:
            estadoReal === 'error'
              ? 0
              : subEstado === 'durmiendo'
                ? [-1, 1, -1]
                : subEstado === 'somnolienta'
                  ? [-1.8, 1.8, -1.8]
                  : [-3, 3, -3],
        }}
        transition={{
          repeat: Infinity,
          duration: subEstado === 'durmiendo' ? 5.0 : subEstado === 'somnolienta' ? 4.4 : 3.6,
          ease: 'easeInOut',
        }}
      >
        <motion.div className="nucleo-impulso-wrap" animate={controlesGesto}>
          <motion.div
            className="nucleo-postura-wrap"
            animate={{
              rotate: actividadActual === 'accesorio_audio' ? [-5, 5, -5] : posturaRotate,
              scale: escuchandoAhora && hayVoz && mostrarEscenaBase ? 1.04 : 1,
              y: escuchandoAhora && hayVoz && mostrarEscenaBase ? -2 : 0,
            }}
            transition={
              actividadActual === 'accesorio_audio'
                ? {
                    rotate: { repeat: Infinity, duration: 1.8, ease: 'easeInOut' },
                    scale: { type: 'spring', stiffness: 165, damping: 16 },
                    y: { type: 'spring', stiffness: 165, damping: 16 },
                  }
                : { type: 'spring', stiffness: 165, damping: 16 }
            }
          >
            <motion.div
              className="centro-nucleo"
              onClick={manejarClickNucleo}
              onPointerMove={manejarPointerMoveEsfera}
              onPointerLeave={manejarPointerLeaveEsfera}
              style={{
                x: esferaX,
                y: esferaY,
                background: modoColapso
                  ? 'radial-gradient(circle at 45% 35%, #ffffff 0%, #ffaaaa 20%, #cc00ff 50%, #ff0033 90%)'
                  : `radial-gradient(circle at 45% 35%, #ffffff 0%, #cffafe 28%, ${c} 82%)`,
                boxShadow: `0 0 22px ${c}aa, 0 0 44px ${c}44`,
                overflow: 'visible',
              }}
              animate={{
                scale:
                  feedbackActivo ? 1 :
                  semaforoActivo === 'seguridad' ? [1, 1.07, 1] :
                  escribiendoAhora ? [1, 1.12, 0.98, 1.07, 1] :
                  escuchandoAhora ? (hayVoz ? 1.06 : [1, 1.03, 1]) :
                  subEstado === 'bostezo' ? [1, 1.11, 1.04, 0.99] :
                  subEstado === 'somnolienta' ? [1, 1.02, 1] :
                  [1, 1.05, 1],
                opacity: subEstado === 'durmiendo' ? 0.72 : subEstado === 'somnolienta' ? 0.84 : 1,
              }}
              transition={{
                scale: feedbackActivo
                  ? { duration: 0.25 }
                  : subEstado === 'bostezo'
                    ? { duration: 4.6, times: [0, 0.35, 0.75, 1], ease: 'easeInOut' }
                    : { repeat: Infinity, duration: subEstado === 'somnolienta' ? 4.2 : pulso, ease: 'easeInOut' },
                opacity: {
                  duration: (subEstado === 'somnolienta' || subEstado === 'durmiendo') ? 1.5 : 0.4,
                  ease: 'easeInOut',
                },
              }}
            >
              {/* ICONOS FLOTANTES DE EMOCIÓN, TÁCTILES Y ACCESORIOS */}
              <AnimatePresence>
                {mostrarEscenaBase && interaccionActiva === 'caricia' && <DestellosCaricia />}
                {actividadActual === 'accesorio_audio' && <AccesorioAuriculares color={c} />}
                {mostrarEscenaBase && !interaccionActiva && subEstado === 'durmiendo' && (
                  <motion.div
                    key="zzz-group"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.85 }}
                    style={{ position: 'absolute', top: '-14px', right: '-14px', zIndex: 10, pointerEvents: 'none' }}
                  >
                    {[0, 1, 2].map((i) => (
                      <motion.span
                        key={`zzz-${i}`}
                        className="particula-zzz"
                        style={{ color: c, fontSize: '12px' }}
                        initial={{ opacity: 0, y: 0, x: 0, scale: 0.5 }}
                        animate={{ opacity: [0, 1, 0], y: -22 - i * 11, x: 10 + i * 7, scale: [0.5, 1.05, 0.8] }}
                        transition={{ repeat: Infinity, duration: 2.4, delay: i * 0.7, ease: 'easeOut' }}
                      >
                        Z
                      </motion.span>
                    ))}
                  </motion.div>
                )}
                {mostrarEscenaBase && (interaccionActiva === 'fastidio' || interaccionActiva === 'advertencia') && (
                  <motion.div
                    key="molesta"
                    className="glifo-molesta"
                    initial={{ opacity: 0, scale: 0.5, rotate: -12 }}
                    animate={{ opacity: [0.75, 1, 0.75], scale: [1, 1.12, 1], rotate: 0 }}
                    exit={{ opacity: 0, scale: 0.5 }}
                    transition={{
                      opacity: { repeat: Infinity, duration: 0.9 },
                      scale: { repeat: Infinity, duration: 0.9 },
                      rotate: { type: 'spring', stiffness: 260, damping: 18 },
                    }}
                  >
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                      <path
                        d="M2 6H6V2M14 6H10V2M2 10H6V14M14 10H10V14"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* ESCÁNER RAG (100% GPU con translateY) */}
              <AnimatePresence>
                {mostrarEscenaBase && estadoReal === 'procesando_rag' && (
                  <motion.div
                    key="escaner-rag"
                    className="escaner-rag"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.25 }}
                  >
                    <motion.div
                      className="escaner-rag-barra"
                      animate={{ y: ['-110%', '350%'] }}
                      transition={{ repeat: Infinity, duration: 1.25, ease: 'easeInOut' }}
                    />
                  </motion.div>
                )}
              </AnimatePresence>

              {/* ROSTRO CON SEGUIMIENTO 2.5D + LENTES ACOPLADOS */}
              <motion.div
                className="rostro-holografico"
                style={{ x: miradaX, y: miradaY }}
              >
                <div className="ojos-con-lentes">
                  <div className="fila-ojos">
                    <motion.div className="ojo-parpado" style={{ scaleY: parpadeoIzq }}>
                      <motion.div
                        className="ojo"
                        style={{ background: colorRostro }}
                        animate={ojosCfg.izq}
                        transition={ojoTransicion}
                      />
                    </motion.div>
                    <motion.div className="ojo-parpado" style={{ scaleY: parpadeoDer }}>
                      <motion.div
                        className="ojo"
                        style={{ background: colorRostro }}
                        animate={ojosCfg.der}
                        transition={ojoTransicion}
                      />
                    </motion.div>
                  </div>

                  {/* LENTES DE LECTURA: hijos de .rostro-holografico para seguir miradaX/miradaY */}
                  <AnimatePresence>
                    {mostrarLentes && (
                      <div className="lentes-lectura-ancla">
                        <motion.div
                          key="lentes"
                          className="lentes-lectura"
                          initial={{ opacity: 0, y: -10, scale: 0.82 }}
                          animate={{ opacity: 1, y: -1, scale: 1 }}
                          exit={{ opacity: 0, y: 6, scale: 0.85 }}
                          transition={{ type: 'spring', stiffness: 240, damping: 20 }}
                        >
                          <div className="lente" style={{ borderColor: c, background: `${c}28` }} />
                          <div className="puente-lentes" style={{ background: c }} />
                          <div className="lente" style={{ borderColor: c, background: `${c}28` }} />
                        </motion.div>
                      </div>
                    )}
                  </AnimatePresence>
                </div>

                <motion.div
                  className="boca-audio-wrap"
                  style={escuchandoAhora && mostrarEscenaBase ? { scaleY: escalaBocaVoz, scaleX: escalaBocaAnchoVoz } : undefined}
                >
                  <motion.div
                    className="boca"
                    style={{ background: colorRostro }}
                    animate={bocaCfg}
                    transition={
                      feedbackActivo || semaforoActivo
                        ? { type: 'spring', stiffness: 260, damping: 20 }
                        : subEstado === 'bostezo'
                          ? {
                              width: { duration: 4.6, times: [0, 0.3, 0.72, 1], ease: 'easeInOut' },
                              height: { duration: 4.6, times: [0, 0.3, 0.72, 1], ease: 'easeInOut' },
                              default: { type: 'spring', stiffness: 160, damping: 22 },
                            }
                          : escribiendoAhora
                            ? {
                                scaleY: { repeat: Infinity, duration: 0.42, ease: 'easeInOut' },
                                default: { type: 'spring', stiffness: 260, damping: 20 },
                              }
                            : { type: 'spring', stiffness: 260, damping: 20 }
                    }
                  />
                </motion.div>
              </motion.div>
            </motion.div>
          </motion.div>
        </motion.div>
      </motion.div>

      {/* BARRAS DE VOZ (GPU scaleY) */}
      <AnimatePresence>
        {mostrarEscenaBase && escribiendoAhora && (
          <motion.div
            key="barras-voz"
            className="barras-voz"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 6 }}
            transition={{ duration: 0.2 }}
          >
            {BARRAS_VOZ_CFG.map((b, i) => (
              <motion.span
                key={i}
                style={{ background: c, boxShadow: `0 0 6px ${c}88` }}
                animate={{ scaleY: b.escalas }}
                transition={{ repeat: Infinity, duration: b.dur, delay: b.delay, ease: 'easeInOut' }}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* DESTELLO ERROR */}
      <AnimatePresence>
        {estadoReal === 'error' && (
          <motion.div
            key="destello-error"
            className="destello-error"
            style={{ borderColor: c }}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: [0.15, 0.7, 0.15], scale: [1, 1.1, 1] }}
            exit={{ opacity: 0, scale: 1.25 }}
            transition={{ repeat: Infinity, duration: 0.55, ease: 'easeInOut' }}
          />
        )}
      </AnimatePresence>

      {/* ETIQUETA */}
      <AnimatePresence mode="wait">
        <motion.div
          key={`${estadoReal}-${subEstado === 'somnolienta' ? 'bostezo' : subEstado}-${estadoReal === 'procesando_pregunta' ? rondaGesto : 0}-${interaccionActiva ?? 'none'}-${etiquetaTactil ?? ''}-${semaforoActivo ?? 'none'}-${feedbackActivo?.id ?? 0}-${modoColapso}`}
          className="etiqueta-estado"
          style={{ color: c, textShadow: `0 0 8px ${c}88` }}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.22 }}
        >
          {textoEtiqueta}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
