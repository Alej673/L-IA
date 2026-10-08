import React, { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence, useAnimation } from 'framer-motion'
import './NucleoColapso.css'
import './ColapsoSistema.css'
import './ColapsoEfectos.css'
import { invoke } from '@tauri-apps/api/core'
import PanelDiagnostico from './PanelDiagnostico'
import {
  ACTORES, EXPRESIONES, ACTITUDES, GESTOS, PALETAS, FX_DURACION, GRIETAS, TONOS_VENTANA,
  COLOR_ROSTRO, px, R, resolverMirada, zalgo,
} from './ColapsoCatalogo'

// Compatibilidad: otros archivos pueden seguir importando esto desde aquí
export { ACTORES, EXPRESIONES, ACTITUDES, GESTOS, PALETAS }

/* ════════════════════════════════════════════════════════════════════
   PROTOCOLO DEL BACKEND   (data: {"comando": "...", "payload": {...}}|||)
   El front NO decide nada: solo ejecuta lo que pide el orquestador.

   ── ROSTRO ──
   MOSTRAR_DIALOGO  {actor, texto, expresion?, actitud?, gesto?, mirada?, duracion?}
   EXPRESION        {actor?, expresion, duracion?}   ← con duracion vuelve a la cara anterior
   ACTOR            {actor, expresion?}
   ACTITUD          {actitud}        GESTO {gesto}      MIRAR {direccion | x,y, duracion?}
   HABLAR {duracion}   CALLAR {}
   ESCENA           {actor, expresion, actitud, mirada, gesto, paleta?, copias?}

   ── COLOR ──
   PALETA           {nombre | color}   ← color ambiental. nombre:'auto' = sigue al actor
   COPIAS           {modo: 'triple' | 'ninguna'}   ← avatar partido en azul/morado/rojo (F8)

   ── GLITCH Y EFECTOS ──
   GLITCH {duracion}   GLITCH_AUTO {activo}   GLITCH_FIJO {activo}   SHAKE_SEVERO
   EFECTO   {tipo: rgb_split|flicker|estatica|invertir|shake, duracion?, activo?}
   FLASH    {color, duracion?}      APAGON {duracion?}     PANTALLA_NEGRA {activo?}
   GRIETAS  {nivel 0-5}             BSOD {codigo, progreso, activo?}
   TOAST    {texto, duracion?}      VENTANAS {cantidad, tono, intervalo?, duracion?, lineas?}
   TITULO   {texto}                 ← título de la ventana ("L-IA (No responde)")

   ── TERMINAL Y PANEL ──
   LOG      {texto, actor?, color?, estilo?: normal|error|tachado|destacado|zalgo, duracion?}
   LIMPIAR_TERMINAL   LIMPIAR_VENTANAS
   ABRIR_PANEL_DIAGNOSTICO {estado}   ACTUALIZAR_PANEL_DIAGNOSTICO {iteraciones?, estado?}
   MINIMIZAR_PANEL_DIAGNOSTICO

   ── SISTEMA ──
   BLOQUEAR_INPUT   RESET   SECUENCIA {pasos:[{comando, payload, espera}]}
   ════════════════════════════════════════════════════════════════════ */

/* ───────────── PIEZAS DEL ROSTRO ───────────── */

// lado: 1 = izquierdo (Gemma), -1 = derecho (Dolphin, espejo)
function Ojo({ lado, g, mirada, rafaga, transParpadeo }) {
  const glitch = lado === 1
    ? { color: '#00ffff', sombra: '0 0 14px #00ffff', tam: 12, radios: [R(6), R(2), R(6), R(3)], escala: [1, 1.3, 0.8, 1.1], dy: [0, -4, 3, 0], sy: [1, 0.5, 1.2, 1], dur: 0.15 }
    : { color: '#ff0033', sombra: '0 0 18px #ff0033', tam: 9,  radios: [R(5), R(1), R(5), R(2)], escala: [1, 0.8, 1.4, 0.9], dy: [0, 5, -2, 0],  sy: [1, 1.3, 0.4, 1], dur: 0.2 }

  return (
    <motion.div
      className="ojo"
      style={{ background: rafaga ? glitch.color : COLOR_ROSTRO, boxShadow: rafaga ? glitch.sombra : 'none' }}
      animate={rafaga
        ? { width: px(glitch.tam), height: px(glitch.tam), rotate: 0, x: 0, borderRadius: glitch.radios, scale: glitch.escala, y: glitch.dy, scaleY: glitch.sy }
        : { width: px(g.width), height: px(g.height), x: mirada.x, y: g.y + mirada.y, rotate: g.rotate * lado, borderRadius: g.borderRadius, scale: 1, scaleY: [1, 1, 0.1, 1] }}
      transition={rafaga
        ? { duration: glitch.dur, repeat: Infinity, ease: 'linear' }
        : { default: { duration: 0.35, ease: 'easeOut' }, scaleY: transParpadeo }}
    />
  )
}

// Al hablar usa el ritmo de apertura del original, escalado por la expresión
function Boca({ boca, apertura, hablaR, hablando, rafaga, velocidad }) {
  const k = Math.min(1.4, Math.max(0.6, boca.width / 10))
  const anchos = [15, 11, 15, 12, 15].map(n => px(n * k))
  const altos = [6, 4, 7, 4, 6].map(n => px(Math.max(2, n * apertura)))
  const giros = [0, 4, -3, 3, 0].map(d => boca.rotate + d)
  const alturas = [0, 1, 0, 1, 0].map(d => boca.y + d)

  return (
    <motion.div
      className="boca"
      style={{ background: COLOR_ROSTRO }}
      animate={
        rafaga
          ? { width: ['22px', '12px', '24px'], height: ['2px', '5px', '1px'], borderRadius: R(0), rotate: [0, 18, -22, 0], skewX: [0, 35, -35, 0], y: 0 }
          : hablando
            ? { width: anchos, height: altos, borderRadius: hablaR, rotate: giros, y: alturas, skewX: 0 }
            : { width: px(boca.width), height: px(boca.height), borderRadius: boca.borderRadius, rotate: boca.rotate, y: boca.y, skewX: 0 }
      }
      transition={
        rafaga ? { duration: 0.12, repeat: Infinity, ease: 'linear' }
        : hablando ? { duration: velocidad, repeat: Infinity, ease: 'easeInOut' }
        : { duration: 0.35 }
      }
    />
  )
}

// Píxeles corruptos que parpadean alrededor del núcleo
const FRAGMENTOS = [
  { x: -85, y: -35, w: 22, h: 3 }, { x: 70, y: -55, w: 10, h: 10 }, { x: -60, y: 50, w: 14, h: 4 },
  { x: 90, y: 30, w: 26, h: 3 },   { x: -30, y: -75, w: 8, h: 8 },  { x: 40, y: 70, w: 18, h: 3 },
]

/* ───────────── NÚCLEO (no sabe de dónde vienen los datos) ───────────── */

export function NucleoColapso({
  actor = 'latente', expresion = 'seria', actitud = 'calma', mirada = 'centro',
  hablando = false, rafaga = false, etiqueta = true,
}) {
  const { color, nombre, grad: gradiente } = ACTORES[actor] ?? ACTORES.latente
  const A = ACTITUDES[actitud] ?? ACTITUDES.calma
  const exp = EXPRESIONES[expresion] ?? EXPRESIONES.seria
  const m = resolverMirada(mirada)

  const suave = { duration: 0.6, ease: 'easeOut' }
  const inf = (duration, extra = {}) => ({ repeat: Infinity, duration, ease: 'easeInOut', ...extra })
  const transParpadeo = { repeat: Infinity, duration: A.parpadeo, times: [0, 0.96, 0.98, 1], ease: 'circInOut' }
  const glow = (n) => `${Math.round(n * A.glow)}px`

  return (
    <motion.div
      className={`nucleo-wrapper ${rafaga ? 'glitch-rgb' : ''}`}
      animate={rafaga ? { x: [0, -6, 5, -2, 0], skewX: [0, 6, -4, 0, 0] } : { x: 0, skewX: 0 }}
      transition={{ duration: 0.16 }}
    >
      <motion.div className="nucleo-halo" style={{ background: `radial-gradient(circle, ${color}44, transparent 70%)` }}
        animate={{ opacity: [0.5, 1, 0.5] }} transition={inf(A.pulso)} />

      <AnimatePresence>
        {hablando && [0, 1, 2].map(i => (
          <motion.div key={`onda-${i}`}
            style={{ position: 'absolute', top: '50%', left: '50%', width: 110, height: 110, marginTop: -55, marginLeft: -55, borderRadius: '50%', border: `2px solid ${color}`, pointerEvents: 'none' }}
            initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: [0.8, 2], opacity: [0.7, 0] }} exit={{ opacity: 0 }}
            transition={{ repeat: Infinity, duration: 1.4, delay: i * 0.45, ease: 'easeOut' }} />
        ))}
      </AnimatePresence>

      {FRAGMENTOS.map((f, i) => (
        <motion.span key={i}
          style={{ position: 'absolute', top: '50%', left: '50%', marginLeft: f.x, marginTop: f.y, width: f.w, height: f.h, background: color, boxShadow: `0 0 8px ${color}`, pointerEvents: 'none' }}
          animate={{ opacity: [0, 0, 1, 0, 0], x: [0, 0, 6, -4, 0] }}
          transition={{ repeat: Infinity, duration: (2.2 + i * 0.4) / A.anillos, delay: i * 0.5, times: [0, 0.6, 0.65, 0.7, 1] }} />
      ))}

      <motion.div className="anillo-exterior" animate={{ rotate: 360, borderColor: color }}
        transition={{ rotate: { repeat: Infinity, duration: 14 / A.anillos, ease: 'linear' }, borderColor: suave }} />
      <motion.div className="anillo-medio" style={{ borderTopColor: '#00ffff' }}
        animate={{ rotate: -360, borderBottomColor: color }}
        transition={{ rotate: { repeat: Infinity, duration: 9 / A.anillos, ease: 'linear' }, borderBottomColor: suave }} />
      <motion.div className="anillo-interior"
        animate={{ scale: [1, 1.08, 1], opacity: [0.5, 1, 0.5], borderColor: color }}
        transition={{ scale: inf(A.pulso), opacity: inf(A.pulso), borderColor: suave }} />

      <motion.div
        className="centro-nucleo"
        style={{ background: gradiente, overflow: 'visible' }}
        animate={{
          scale: hablando ? [1, 1.07, 1, 1.1, 1] : [1, 1.04, 1],
          rotate: [-2, 2, -2],
          boxShadow: `0 0 ${glow(hablando ? 60 : 35)} ${color}, 0 0 ${glow(hablando ? 120 : 70)} ${color}88`,
        }}
        transition={{ scale: hablando ? inf(0.6) : inf(A.pulso), rotate: inf(7), boxShadow: suave }}
      >
        <motion.div className="rostro-holografico"
          animate={rafaga ? { x: [-4, 4, -2, 2, 0], y: [-2, 2, -1, 1, 0] } : { x: 0, y: 0 }}
          transition={rafaga ? { duration: 0.1, repeat: Infinity } : { duration: 0.3 }}>
          <div className="fila-ojos">
            <Ojo lado={1}  g={exp.ojo}             mirada={m} rafaga={rafaga} transParpadeo={transParpadeo} />
            <Ojo lado={-1} g={exp.ojoD ?? exp.ojo} mirada={m} rafaga={rafaga} transParpadeo={transParpadeo} />
          </div>
          <Boca boca={exp.boca} apertura={exp.apertura ?? 1} hablaR={exp.hablaR ?? R(3)} hablando={hablando} rafaga={rafaga} velocidad={A.habla} />
        </motion.div>
      </motion.div>

      {rafaga && (
        <div style={{ position: 'absolute', top: '50%', left: '50%', width: 150, height: 4, marginLeft: -75, marginTop: -12, background: color, opacity: 0.85, mixBlendMode: 'screen', pointerEvents: 'none' }} />
      )}

      {etiqueta && (
        <div className="etiqueta-estado" style={{ color, textShadow: `0 0 8px ${color}99` }}>
          {hablando ? `${nombre} ▍` : A.etiqueta}
        </div>
      )}
    </motion.div>
  )
}

/* ───────────── PIEZAS DE PANTALLA ───────────── */

function PantallazoAzul({ codigo, progreso }) {
  return (
    <div className="bsod">
      <div className="bsod-cara">:(</div>
      <p>Tu PC se encontró con un problema que no pudo manejar.</p>
      <p className="bsod-codigo">Código de detención: {codigo}</p>
      <p>Completado: {progreso}%</p>
    </div>
  )
}

function CristalAgrietado({ nivel }) {
  return (
    <svg className="cristal-grietas" viewBox="0 0 100 100" preserveAspectRatio="none">
      {GRIETAS.slice(0, nivel).map((d, i) => (
        <motion.path key={i} d={d} fill="none" stroke="#fff" strokeWidth="0.35"
          style={{ filter: 'drop-shadow(0 0 1.2px #fff)' }}
          initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.22, ease: 'easeOut' }} />
      ))}
    </svg>
  )
}

/* ───────────── ESCENA: recibe comandos del backend ───────────── */

const INICIAL = { actor: 'latente', expresion: 'enojada', actitud: 'calma', mirada: 'centro' }
const COPIAS_TRIPLE = ['gemma', 'seguridad', 'latente']
const MAX_LINEAS = 200

export default function ColapsoSistema({ activo, comandoActual }) {
  // ── estado del rostro
  const [fase, setFase] = useState('inicio')
  const [actor, setActor] = useState(INICIAL.actor)
  const [expresion, setExpresion] = useState(INICIAL.expresion)
  const [actitud, setActitud] = useState(INICIAL.actitud)
  const [mirada, setMirada] = useState(INICIAL.mirada)
  const [hablando, setHablando] = useState(false)
  // ── glitch
  const [glitchActivo, setGlitchActivo] = useState(false)   // shake severo
  const [rafaga, setRafaga] = useState(false)               // ráfaga automática
  const [rafagaManual, setRafagaManual] = useState(false)
  const [rafagaFija, setRafagaFija] = useState(false)       // glitch permanente (F8)
  const [glitchAuto, setGlitchAuto] = useState(true)
  // ── ambiente y efectos
  const [paleta, setPaleta] = useState(null)                // null = sigue al actor
  const [copias, setCopias] = useState('ninguna')
  const [efectos, setEfectos] = useState({})
  const [flash, setFlash] = useState(null)
  const [grietas, setGrietas] = useState(0)
  const [bsod, setBsod] = useState(null)
  const [toasts, setToasts] = useState([])
  const [ventanas, setVentanas] = useState([])
  // ── terminal y panel
  const [lineas, setLineas] = useState([])
  const [panelVisible, setPanelVisible] = useState(false)
  const [panelEstado, setPanelEstado] = useState('calculando')
  const [panelIteraciones, setPanelIteraciones] = useState(4327)

  const controles = useAnimation()
  const terminalRef = useRef(null)
  const actorRef = useRef(INICIAL.actor)
  const expRef = useRef(INICIAL.expresion)
  const expBaseRef = useRef(INICIAL.expresion)
  const expTemporal = useRef(false)
  const idRef = useRef(0)
  const tituloOriginal = useRef(typeof document !== 'undefined' ? document.title : 'L-IA')
  const timers = useRef(new Set())
  const timerFx = useRef({})
  const timerHabla = useRef(null)
  const timerShake = useRef(null)
  const timerRafaga = useRef(null)
  const timerExpr = useRef(null)
  const timerMirada = useRef(null)
  const timerFlash = useRef(null)

  const limpiarTimers = useCallback(() => {
    timers.current.forEach(clearTimeout)
    timers.current.clear()
    Object.values(timerFx.current).forEach(clearTimeout)
    timerFx.current = {}
    ;[timerHabla, timerShake, timerRafaga, timerExpr, timerMirada, timerFlash].forEach(t => clearTimeout(t.current))
  }, [])

  const reiniciarRostro = useCallback(() => {
    actorRef.current = INICIAL.actor
    expRef.current = expBaseRef.current = INICIAL.expresion
    expTemporal.current = false
    setActor(INICIAL.actor); setExpresion(INICIAL.expresion)
    setActitud(INICIAL.actitud); setMirada(INICIAL.mirada)
    setGlitchAuto(true); setRafagaManual(false); setRafagaFija(false); setHablando(false)
  }, [])

  // Todo lo que NO es la cara: efectos, grietas, BSOD, ventanas, paleta...
  const reiniciarEscena = useCallback(() => {
    setEfectos({}); setFlash(null); setGrietas(0); setBsod(null)
    setToasts([]); setVentanas([]); setPaleta(null); setCopias('ninguna')
    setPanelVisible(false); setFase('inicio'); setGlitchActivo(false)
    if (typeof document !== 'undefined') document.title = tituloOriginal.current
  }, [])

  // Ejecutor único: cada comando del backend (y cada paso de una SECUENCIA) pasa por aquí
  const ejecutar = useCallback(function run(cmd) {
    if (!cmd?.comando) return
    const p = cmd.payload ?? {}

    /* helpers */
    const programar = (fn, ms) => {
      const id = setTimeout(() => { timers.current.delete(id); fn() }, ms)
      timers.current.add(id)
    }
    const fijarActor = (a) => { actorRef.current = a; setActor(a) }
    const fijarExpresion = (e) => {
      if (!EXPRESIONES[e]) console.warn('[ColapsoSistema] expresión desconocida:', e)
      expRef.current = e; setExpresion(e)
    }
    const gesto = (nombre) => {
      const g = GESTOS[nombre]
      if (!g) return
      try { controles.start({ ...g }) } catch { /* el núcleo aún no está montado */ }
    }
    const hablar = (ms) => {
      setHablando(true)
      clearTimeout(timerHabla.current)
      timerHabla.current = setTimeout(() => setHablando(false), ms)
    }
    const mirar = (m, ms) => {
      setMirada(m)
      clearTimeout(timerMirada.current)
      if (ms) timerMirada.current = setTimeout(() => setMirada('centro'), ms)
    }
    // Cambia de cara; con duracion es temporal y vuelve a la cara de fondo
    const poner = (e, duracion) => {
      clearTimeout(timerExpr.current)
      if (!expTemporal.current) expBaseRef.current = expRef.current
      fijarExpresion(e)
      if (duracion) {
        expTemporal.current = true
        timerExpr.current = setTimeout(() => { expTemporal.current = false; fijarExpresion(expBaseRef.current) }, duracion)
      } else {
        expTemporal.current = false
        expBaseRef.current = e
      }
    }
    // Si cambia el actor y no se pide cara, toma la cara base de ese actor
    const cambiarActor = (a, expresionPedida) => {
      if (!a) return
      if (!ACTORES[a]) console.warn('[ColapsoSistema] actor desconocido:', a)
      if (a !== actorRef.current) {
        fijarActor(a)
        if (!expresionPedida) poner(ACTORES[a]?.expresionBase ?? 'seria')
      }
    }
    const agregarLinea = (l) => setLineas(prev => [...prev, l].slice(-MAX_LINEAS))
    const fx = (tipo, activo, duracion) => {
      clearTimeout(timerFx.current[tipo])
      setEfectos(prev => ({ ...prev, [tipo]: activo }))
      if (activo && duracion > 0) timerFx.current[tipo] = setTimeout(() => setEfectos(prev => ({ ...prev, [tipo]: false })), duracion)
    }
    const destello = (color, ms) => {
      clearTimeout(timerFlash.current)
      setFlash({ color, key: ++idRef.current, ms })
      timerFlash.current = setTimeout(() => setFlash(null), ms + 50)
    }

    switch (cmd.comando) {
      /* ── ROSTRO ── */
      case 'MOSTRAR_DIALOGO': {
        cambiarActor(p.actor, p.expresion)
        if (p.expresion) poner(p.expresion)
        if (p.actitud) setActitud(p.actitud)
        if (p.mirada) mirar(p.mirada)
        if (p.gesto) gesto(p.gesto)
        const linea = { ...p, tipo: 'dialogo', id: ++idRef.current, actor: p.actor ?? actorRef.current, texto: p.texto ?? '' }
        agregarLinea(linea)
        hablar(p.duracion ?? Math.min(4500, 700 + linea.texto.length * 55))   // el backend manda la duración real del TTS
        break
      }
      case 'EXPRESION':
        cambiarActor(p.actor, p.expresion)
        if (p.expresion) poner(p.expresion, p.duracion)
        break
      case 'ACTOR':
        cambiarActor(p.actor, p.expresion)
        if (p.expresion) poner(p.expresion)
        break
      case 'ACTITUD': if (p.actitud) setActitud(p.actitud); break
      case 'GESTO':   gesto(p.gesto); break
      case 'MIRAR':   mirar(p.direccion ?? { x: p.x, y: p.y }, p.duracion); break
      case 'HABLAR':  hablar(p.duracion ?? 2000); break
      case 'CALLAR':  clearTimeout(timerHabla.current); setHablando(false); break
      case 'ESCENA':
        cambiarActor(p.actor, p.expresion)
        if (p.expresion) poner(p.expresion)
        if (p.actitud) setActitud(p.actitud)
        if (p.mirada) mirar(p.mirada)
        if (p.gesto) gesto(p.gesto)
        if (p.paleta) run({ comando: 'PALETA', payload: { nombre: p.paleta } })
        if (p.copias) run({ comando: 'COPIAS', payload: { modo: p.copias } })
        break

      /* ── COLOR ── */
      case 'PALETA':
        if (p.nombre === 'auto') setPaleta(null)
        else setPaleta(p.color ?? PALETAS[p.nombre]?.color ?? null)
        break
      case 'COPIAS': setCopias(p.modo === 'triple' ? 'triple' : 'ninguna'); break

      /* ── GLITCH Y EFECTOS ── */
      case 'GLITCH':
        setRafagaManual(true)
        clearTimeout(timerRafaga.current)
        timerRafaga.current = setTimeout(() => setRafagaManual(false), p.duracion ?? 400)
        break
      case 'GLITCH_AUTO': setGlitchAuto(Boolean(p.activo)); break
      case 'GLITCH_FIJO': setRafagaFija(Boolean(p.activo)); break
      case 'SHAKE_SEVERO':
        setGlitchActivo(true)
        clearTimeout(timerShake.current)
        timerShake.current = setTimeout(() => setGlitchActivo(false), 600)
        break
      case 'EFECTO': {
        const tipo = p.tipo
        if (!tipo) break
        if (tipo === 'shake') { run({ comando: 'SHAKE_SEVERO' }); break }
        fx(tipo, p.activo !== false, p.duracion ?? FX_DURACION[tipo] ?? 400)
        break
      }
      case 'FLASH':  destello(p.color ?? '#ffffff', p.duracion ?? 180); break
      case 'APAGON': destello('#000000', p.duracion ?? 600); break
      case 'PANTALLA_NEGRA': setFase(p.activo === false ? 'inicio' : 'apagado'); break
      case 'GRIETAS': setGrietas(Math.max(0, Math.min(GRIETAS.length, p.nivel ?? 0))); break
      case 'BSOD':
        setBsod(p.activo === false ? null : { codigo: p.codigo ?? 'L-IA_CORE_FAILURE', progreso: p.progreso ?? 0 })
        break
      case 'TOAST': {
        const t = { id: ++idRef.current, texto: p.texto ?? '' }
        setToasts(prev => [...prev.slice(-3), t])
        programar(() => setToasts(prev => prev.filter(x => x.id !== t.id)), p.duracion ?? 3500)
        break
      }
      case 'VENTANAS': {
        const tono = TONOS_VENTANA[p.tono] ? p.tono : 'sistema'
        const n = Math.min(p.cantidad ?? 6, 40)
        for (let i = 0; i < n; i++) {
          programar(() => {
            const w = { id: ++idRef.current, x: 4 + Math.random() * 68, y: 4 + Math.random() * 62, tono, lineas: p.lineas ?? TONOS_VENTANA[tono].lineas }
            setVentanas(prev => [...prev, w].slice(-40))
            programar(() => setVentanas(prev => prev.filter(v => v.id !== w.id)), p.duracion ?? 3500)
          }, i * (p.intervalo ?? 120))
        }
        break
      }
      case 'LIMPIAR_VENTANAS': setVentanas([]); break
      case 'TITULO':
        if (typeof document !== 'undefined') document.title = p.texto ?? tituloOriginal.current
        break

      /* ── TERMINAL Y PANEL ── */
      case 'LOG': {
        const texto = p.estilo === 'zalgo' ? zalgo(p.texto ?? '') : (p.texto ?? '')
        const l = { tipo: 'log', id: ++idRef.current, texto, actor: p.actor ?? 'sistema', color: p.color, estilo: p.estilo }
        agregarLinea(l)
        if (p.duracion) programar(() => setLineas(prev => prev.filter(x => x.id !== l.id)), p.duracion)
        break
      }
      case 'LIMPIAR_TERMINAL': setLineas([]); break
      case 'ABRIR_PANEL_DIAGNOSTICO':
        setPanelVisible(true); setPanelEstado(p.estado || 'calculando'); break
      case 'ACTUALIZAR_PANEL_DIAGNOSTICO':
        if (p.iteraciones) setPanelIteraciones(p.iteraciones)
        if (p.estado) setPanelEstado(p.estado)
        break
      case 'MINIMIZAR_PANEL_DIAGNOSTICO': setPanelVisible(false); break

      /* ── SISTEMA ── */
      case 'BLOQUEAR_INPUT':
        // Rust: ventana transparente, fullscreen e intocable
        invoke('activar_modo_invasivo').catch(console.error)
        break
      case 'RESET':
        limpiarTimers()
        invoke('restaurar_ventana').catch(console.error)
        reiniciarEscena()
        reiniciarRostro()
        break
      case 'SECUENCIA': {
        // pasos: [{comando, payload, espera}] · espera = ms desde el paso anterior
        let t = 0
        for (const paso of p.pasos ?? []) { t += paso.espera ?? 0; programar(() => run(paso), t) }
        break
      }
      default:
        console.warn('[ColapsoSistema] comando desconocido:', cmd.comando)
    }
  }, [controles, limpiarTimers, reiniciarEscena, reiniciarRostro])

  // Restaurar la ventana cuando el evento termina
  useEffect(() => {
    if (!activo) return
    return () => { invoke('restaurar_ventana').catch(console.error) }
  }, [activo])

  // Ráfagas aleatorias de glitch; el ritmo depende de la actitud y el backend puede apagarlas
  useEffect(() => {
    if (!activo || !glitchAuto) return
    const [min, max] = (ACTITUDES[actitud] ?? ACTITUDES.calma).glitch
    let t
    const ciclo = () => {
      t = setTimeout(() => {
        setRafaga(true)
        t = setTimeout(() => { setRafaga(false); ciclo() }, 160)
      }, min + Math.random() * (max - min))
    }
    ciclo()
    return () => { clearTimeout(t); setRafaga(false) }
  }, [activo, glitchAuto, actitud])

  // Comandos del backend
  useEffect(() => {
    if (!activo) {
      setLineas([])
      limpiarTimers()
      reiniciarEscena()
      reiniciarRostro()
      return
    }
    ejecutar(comandoActual)
  }, [activo, comandoActual, ejecutar, limpiarTimers, reiniciarEscena, reiniciarRostro])

  // Terminal pegado a la última línea
  useEffect(() => {
    const el = terminalRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [lineas])

  useEffect(() => limpiarTimers, [limpiarTimers])

  if (!activo) return null

  if (fase === 'apagado') {
    return <div style={{ position: 'fixed', inset: 0, background: '#000', zIndex: 10000 }} />
  }

  const jitter = (ACTITUDES[actitud] ?? ACTITUDES.calma).jitter
  const tinte = paleta ?? ACTORES[actor]?.color ?? '#00ffff'
  const clasesFx = Object.keys(efectos).filter(k => efectos[k]).map(k => `fx-${k}`).join(' ')
  const rafagaTotal = rafaga || glitchActivo || rafagaManual || rafagaFija

  return (
    <motion.div
      className={`overlay-colapso scanlines ${glitchActivo ? 'shake-pantalla' : ''} ${clasesFx}`}
      style={{ '--tinte': tinte, boxShadow: `inset 0 0 140px ${tinte}33` }}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.2 }}
    >
      {/* Capa 1: gestos puntuales. Capa 2: temblor continuo según la actitud */}
      <motion.div animate={controles}
        style={{ height: '220px', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
        <motion.div
          style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}
          animate={jitter ? { x: [0, jitter, -jitter * 0.7, jitter * 0.4, 0], y: [0, -jitter * 0.5, jitter * 0.5, 0, 0] } : { x: 0, y: 0 }}
          transition={jitter ? { repeat: Infinity, duration: 0.22, ease: 'linear' } : { duration: 0.3 }}
        >
          {copias === 'triple' ? (
            // Fase 8: el avatar se parte en tres copias que colisionan
            COPIAS_TRIPLE.map((a, i) => (
              <motion.div key={a} className="copia-nucleo" style={{ mixBlendMode: 'screen' }}
                animate={{ x: [0, (i - 1) * 38, (1 - i) * 22, 0], y: [0, (i - 1) * -10, (i - 1) * 14, 0], scale: [1, 1.04, 0.96, 1] }}
                transition={{ repeat: Infinity, duration: 1.1 + i * 0.25, ease: 'easeInOut' }}>
                <NucleoColapso actor={a} expresion={expresion} actitud={actitud} mirada={mirada}
                  hablando={hablando && a === actor} rafaga={rafagaTotal} etiqueta={i === 1} />
              </motion.div>
            ))
          ) : (
            <NucleoColapso actor={actor} expresion={expresion} actitud={actitud} mirada={mirada}
              hablando={hablando} rafaga={rafagaTotal} />
          )}
        </motion.div>
      </motion.div>

      <div ref={terminalRef} className="terminal-combate custom-scrollbar" style={{
        width: '85%', maxWidth: '800px', height: '55%',
        background: 'rgba(0, 5, 10, 0.9)', border: `1px solid ${tinte}55`,
        padding: '25px', overflowY: 'auto', boxShadow: 'inset 0 0 20px rgba(0,0,0,1)',
      }}>
        {lineas.map((l) => {
          const a = ACTORES[l.actor] ?? ACTORES.gemma
          if (l.tipo === 'log') {
            const color = l.estilo === 'error' ? '#ff3b3b' : (l.color ?? a.color)
            return (
              <motion.div key={l.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                className={`log-linea log-${l.estilo ?? 'normal'}`}
                style={{ color, textShadow: `0 0 6px ${color}88` }}>
                {l.texto}
              </motion.div>
            )
          }
          return (
            <motion.div key={l.id} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
              style={{ color: a.color, marginBottom: '20px', fontSize: '16px', lineHeight: '1.4', textShadow: a.sombra, fontFamily: "'Courier New', monospace" }}>
              <strong style={{ opacity: 0.8 }}>[{String(l.actor).toUpperCase()}]:</strong> {l.texto}
            </motion.div>
          )
        })}
      </div>

      <PanelDiagnostico estado={panelEstado} iteracionesMax={panelIteraciones} visible={panelVisible} />

      {/* Ventanas falsas en cascada */}
      {ventanas.map(w => {
        const t = TONOS_VENTANA[w.tono]
        return (
          <motion.div key={w.id} className="ventana-falsa"
            style={{ left: `${w.x}%`, top: `${w.y}%`, borderColor: t.color, color: t.color }}
            initial={{ opacity: 0, scale: 0.85 }} animate={{ opacity: 1, scale: 1 }}>
            <div className="ventana-falsa-barra" style={{ background: t.color }}>{t.titulo}{w.tono === 'error' ? '  ✕' : ''}</div>
            {w.lineas.map((ln, i) => <div key={i}>{ln}</div>)}
          </motion.div>
        )
      })}

      {/* Toasts de Windows falsos */}
      <div className="toasts-falsos">
        {toasts.map(t => (
          <motion.div key={t.id} className="toast-falso" initial={{ x: 60, opacity: 0 }} animate={{ x: 0, opacity: 1 }}>{t.texto}</motion.div>
        ))}
      </div>

      {grietas > 0 && <CristalAgrietado nivel={grietas} />}

      <AnimatePresence>
        {flash && (
          <motion.div key={flash.key} className="flash-pantalla" style={{ background: flash.color }}
            initial={{ opacity: 0.95 }} animate={{ opacity: flash.color === '#000000' ? 1 : 0 }}
            exit={{ opacity: 0 }} transition={{ duration: flash.ms / 1000 }} />
        )}
      </AnimatePresence>

      {bsod && <PantallazoAzul codigo={bsod.codigo} progreso={bsod.progreso} />}
    </motion.div>
  )
}