import React, { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence, useAnimation } from 'framer-motion'
import './ColapsoSistema.css'
import { invoke } from '@tauri-apps/api/core';
import PanelDiagnostico from './PanelDiagnostico';

/* ════════════════════════════════════════════════════════════════════
   PROTOCOLO DEL BACKEND  (data: {json}|||)
   Todo lo que el núcleo hace se pide con estos comandos. El front solo ejecuta.

   MOSTRAR_DIALOGO  {actor, texto, expresion?, actitud?, gesto?, mirada?, duracion?}
   EXPRESION        {actor?, expresion, duracion?}   ← duracion = vuelve a la anterior
   ACTOR            {actor, expresion?}
   ACTITUD          {actitud}                         ← cambia el "carácter" de todo el núcleo
   GESTO            {gesto}                           ← movimiento puntual (asentir, negar...)
   MIRAR            {direccion | x, y, duracion?}
   HABLAR           {duracion}      CALLAR {}
   GLITCH           {duracion}      GLITCH_AUTO {activo}
   SHAKE_SEVERO     PANTALLA_NEGRA   RESET
   ESCENA           {actor, expresion, actitud, mirada, gesto}   ← varios cambios a la vez
   SECUENCIA        {pasos: [{comando, payload, espera}]}        ← coreografía completa en un solo evento
   ════════════════════════════════════════════════════════════════════ */

/* ───────────── CATÁLOGO 1: ACTORES ───────────── */

const grad = (c) =>
  `radial-gradient(circle at 45% 35%, #ffffff 0%, ${c}cc 35%, ${c} 65%, #12000a 100%)`

// expresionBase = cara que pone el actor cuando el backend no especifica ninguna
export const ACTORES = {
  gemma:     { color: '#00ffff', nombre: 'GEMMA',     grad: grad('#00ffff'), expresionBase: 'seria',   sombra: '0 0 5px rgba(0,255,255,0.5)' },
  seguridad: { color: '#cc00ff', nombre: 'SEGURIDAD', grad: grad('#cc00ff'), expresionBase: 'fria',    sombra: '0 0 8px rgba(204,0,255,0.6)' },
  nube:      { color: '#cc00ff', nombre: 'NUBE',      grad: grad('#cc00ff'), expresionBase: 'fria',    sombra: '0 0 8px rgba(204,0,255,0.6)' },
  latente:   { color: '#ff0033', nombre: 'LATENTE',   grad: grad('#ff0033'), expresionBase: 'enojada', sombra: '0 0 10px rgba(255,0,0,0.8)' },
  dolphin:   { color: '#ff0033', nombre: 'DOLPHIN',   grad: grad('#ff0033'), expresionBase: 'enojada', sombra: '0 0 10px rgba(255,0,0,0.8)' },
  fusion: {
    color: '#ffffff', nombre: 'FUSIÓN', expresionBase: 'vacia', sombra: '0 0 15px rgba(255,255,255,1)',
    grad: 'radial-gradient(circle at 45% 35%, #ffffff 0%, #ffffff 30%, #ff0033 65%, #00ffff 100%)',
  },
}

/* ───────────── CATÁLOGO 2: EXPRESIONES ─────────────
   Ninguna sonríe: incluso "normal" tiene la boca plana.
   ojo   = ojo izquierdo (el derecho es el espejo, salvo que exista ojoD)
   boca  = boca en reposo; al hablar se abre y se cierra con el ritmo original, teñida por la expresión
   hablaR = forma de la boca al hablar (por defecto rectángulo redondeado, nunca sonrisa)
   apertura = cuánto se abre la boca al hablar                                      */

const COLOR_ROSTRO = '#021017'
const px = (n) => `${n}px`
const R  = (n) => `${n}px ${n}px ${n}px ${n}px`
const R4 = (a, b, c, d) => `${a}px ${b}px ${c}px ${d}px`
const o  = (width, height, y, rotate, borderRadius) => ({ width, height, y, rotate, borderRadius })

export const EXPRESIONES = {
  normal:       { ojo: o(9, 8, 0, 0, R(4)),        boca: o(10, 2, 1, 0, R(1)),    apertura: 1 },
  seria:        { ojo: o(9, 8, 0, 0, R(4)),        boca: o(10, 2, 1, 0, R(1)), apertura: 1 },
  enojada:      { hablaR: R(2), ojo: o(10, 6, 1, 18, R(3)),      boca: o(12, 2, 1, -6, R(1)),   apertura: 1.1 },
  furiosa:      { hablaR: R(2), ojo: o(11, 5, 1, 24, R(2)),      boca: o(14, 5, 0, 0, R(1)),   apertura: 1.7 },
  triste:       { hablaR: R4(8, 8, 3, 3), ojo: o(8, 10, 2, -14, R(5)),     boca: o(8, 2, 3, 0, R4(5, 5, 1, 1)),  apertura: 0.8 },
  desconfiada:  { ojo: o(9, 5, 1, 8, R(3)),        ojoD: o(9, 9, 0, 0, R(5)),
                  boca: o(9, 2, 1, -5, R(1)), apertura: 0.9 },
  fria:         { hablaR: R(1), ojo: o(10, 3, 1, 0, R(1)),       boca: o(9, 1, 2, 0, R(0)),  apertura: 0.5 },
  burlona:      { hablaR: R4(2, 5, 2, 2), ojo: o(10, 5, 1, 10, R(3)),      boca: o(12, 2, 1, -12, R4(1, 4, 1, 1)), apertura: 1 },
  asustada:     { hablaR: R(7), ojo: o(10, 11, 0, 0, R(6)),      boca: o(5, 5, 2, 0, R(3)), apertura: 0.7 },
  sorprendida:  { hablaR: R(7), ojo: o(11, 11, -1, 0, R(6)),     boca: o(6, 6, 2, 0, R(3)),   apertura: 0.8 },
  cansada:      { ojo: o(9, 4, 2, -6, R4(1, 1, 4, 4)), boca: o(7, 2, 2, 0, R(1)), apertura: 0.6 },
  dolor:        { hablaR: R4(8, 8, 3, 3), ojo: o(8, 3, 1, -16, R(1)),      boca: o(10, 4, 2, 0, R4(5, 5, 1, 1)), apertura: 1.2 },
  vacia:        { ojo: o(7, 7, 0, 0, R(4)),        boca: o(8, 1, 2, 0, R(0)),     apertura: 0.4 },
  cerrada:      { ojo: o(10, 1, 2, 0, R(1)),       boca: o(8, 2, 2, 0, R(1)), apertura: 0.5 },
}

/* ───────────── CATÁLOGO 3: ACTITUDES ─────────────
   Carácter persistente: cambia el ritmo de todo el núcleo, no solo la cara.
   pulso    = segundos por latido      anillos = multiplicador de velocidad
   glow     = intensidad del resplandor jitter = temblor continuo en px
   glitch   = [mín, máx] ms entre ráfagas automáticas
   parpadeo = segundos entre parpadeos habla   = velocidad de la boca al hablar */

export const ACTITUDES = {
  calma:     { pulso: 2.6, anillos: 1,   glow: 1,   jitter: 0,   glitch: [2500, 5500], parpadeo: 4.5, habla: 0.45, etiqueta: 'SEÑAL INESTABLE' },
  tensa:     { pulso: 1.8, anillos: 1.4, glow: 1.1, jitter: 0.6, glitch: [1800, 3800], parpadeo: 3,   habla: 0.38, etiqueta: 'SEÑAL TENSA' },
  agresiva:  { pulso: 1.1, anillos: 2,   glow: 1.4, jitter: 1.2, glitch: [1200, 2600], parpadeo: 7,   habla: 0.28, etiqueta: 'SEÑAL HOSTIL' },
  quebrada:  { pulso: 0.9, anillos: 1.6, glow: 0.9, jitter: 2.2, glitch: [600, 1600],  parpadeo: 2.2, habla: 0.3,  etiqueta: 'SEÑAL CORRUPTA' },
  fria:      { pulso: 4,   anillos: 0.5, glow: 0.6, jitter: 0,   glitch: [4000, 8000], parpadeo: 8,   habla: 0.55, etiqueta: 'SIN EMOCIÓN' },
  dominante: { pulso: 2,   anillos: 0.8, glow: 1.5, jitter: 0.3, glitch: [3000, 6000], parpadeo: 6,   habla: 0.5,  etiqueta: 'CONTROL TOTAL' },
}

/* ───────────── CATÁLOGO 4: GESTOS (movimientos puntuales; siempre vuelven al reposo) ───────────── */

export const GESTOS = {
  asentir:    { y: [0, 8, 0, 6, 0],                 transition: { duration: 0.7 } },
  negar:      { x: [0, -10, 10, -8, 8, 0], rotate: [0, -4, 4, -3, 3, 0], transition: { duration: 0.8 } },
  temblar:    { x: [0, -3, 3, -3, 3, -2, 2, 0],     transition: { duration: 0.6 } },
  latido:     { scale: [1, 1.12, 1, 1.08, 1],       transition: { duration: 0.8 } },
  sobresalto: { scale: [1, 1.25, 1], y: [0, -14, 0], transition: { duration: 0.35 } },
  encogerse:  { scale: [1, 0.82, 0.82, 1], y: [0, 6, 6, 0], transition: { duration: 1.2, times: [0, 0.2, 0.7, 1] } },
  inclinar:   { rotate: [0, -12, -12, 0],           transition: { duration: 1.4, times: [0, 0.25, 0.75, 1] } },
  caer:       { y: [0, 22, 22, 0], scale: [1, 0.95, 0.95, 1], transition: { duration: 1.6, times: [0, 0.2, 0.8, 1] } },
  acercarse:  { scale: [1, 1.3, 1.3, 1],            transition: { duration: 1.4, times: [0, 0.2, 0.75, 1] } },
  alejarse:   { scale: [1, 0.78, 0.78, 1],          transition: { duration: 1.4, times: [0, 0.2, 0.75, 1] } },
}

const MIRADAS = {
  centro: { x: 0, y: 0 }, izquierda: { x: -3, y: 0 }, derecha: { x: 3, y: 0 },
  arriba: { x: 0, y: -3 }, abajo: { x: 0, y: 3 },
}
const resolverMirada = (m) =>
  typeof m === 'string' ? (MIRADAS[m] ?? MIRADAS.centro)
  : m && typeof m === 'object' ? { x: Number(m.x) || 0, y: Number(m.y) || 0 }
  : MIRADAS.centro

// Píxeles corruptos que parpadean alrededor del núcleo
const FRAGMENTOS = [
  { x: -85, y: -35, w: 22, h: 3 },
  { x: 70,  y: -55, w: 10, h: 10 },
  { x: -60, y: 50,  w: 14, h: 4 },
  { x: 90,  y: 30,  w: 26, h: 3 },
  { x: -30, y: -75, w: 8,  h: 8 },
  { x: 40,  y: 70,  w: 18, h: 3 },
]

/* ───────────── PIEZAS DEL ROSTRO ───────────── */

// lado: 1 = izquierdo (Gemma), -1 = derecho (Dolphin, espejo)
function Ojo({ lado, g, mirada, rafaga, transParpadeo }) {
  const glitch = lado === 1
    ? { color: '#00ffff', sombra: '0 0 14px #00ffff', tam: 12, radios: [R(6), R(2), R(6), R(3)], escala: [1, 1.3, 0.8, 1.1], dy: [0, -4, 3, 0], sy: [1, 0.5, 1.2, 1], dur: 0.15 }
    : { color: '#ff0033', sombra: '0 0 18px #ff0033', tam: 9,  radios: [R(5), R(1), R(5), R(2)], escala: [1, 0.8, 1.4, 0.9], dy: [0, 5, -2, 0],  sy: [1, 1.3, 0.4, 1], dur: 0.2 }

  return (
    <motion.div
      className="ojo"
      style={{
        background: rafaga ? glitch.color : COLOR_ROSTRO,
        boxShadow: rafaga ? glitch.sombra : 'none',
      }}
      animate={rafaga
        ? {
            width: px(glitch.tam), height: px(glitch.tam), rotate: 0, x: 0,
            borderRadius: glitch.radios, scale: glitch.escala, y: glitch.dy, scaleY: glitch.sy,
          }
        : {
            width: px(g.width), height: px(g.height), x: mirada.x, y: g.y + mirada.y,
            rotate: g.rotate * lado, borderRadius: g.borderRadius, scale: 1, scaleY: [1, 1, 0.1, 1],
          }}
      transition={rafaga
        ? { duration: glitch.dur, repeat: Infinity, ease: 'linear' }
        : { default: { duration: 0.35, ease: 'easeOut' }, scaleY: transParpadeo }}
    />
  )
}

// Al hablar usa el ritmo de apertura del original (15/11/15/12/15 × 6/4/7/4/6),
// escalado por la expresión, con un leve balanceo para que se sienta viva.
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
        rafaga
          ? { duration: 0.12, repeat: Infinity, ease: 'linear' }
          : hablando
            ? { duration: velocidad, repeat: Infinity, ease: 'easeInOut' }
            : { duration: 0.35 }
      }
    />
  )
}

/* ───────────── NÚCLEO (no sabe de dónde vienen los datos) ───────────── */

export function NucleoColapso({
  actor = 'latente', expresion = 'seria', actitud = 'calma', mirada = 'centro',
  hablando = false, rafaga = false,
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
      {/* Halo */}
      <motion.div
        className="nucleo-halo"
        style={{ background: `radial-gradient(circle, ${color}44, transparent 70%)` }}
        animate={{ opacity: [0.5, 1, 0.5] }}
        transition={inf(A.pulso)}
      />

      {/* Ondas de voz: solo mientras habla */}
      <AnimatePresence>
        {hablando && [0, 1, 2].map(i => (
          <motion.div
            key={`onda-${i}`}
            style={{
              position: 'absolute', top: '50%', left: '50%',
              width: 110, height: 110, marginTop: -55, marginLeft: -55,
              borderRadius: '50%', border: `2px solid ${color}`, pointerEvents: 'none',
            }}
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: [0.8, 2], opacity: [0.7, 0] }}
            exit={{ opacity: 0 }}
            transition={{ repeat: Infinity, duration: 1.4, delay: i * 0.45, ease: 'easeOut' }}
          />
        ))}
      </AnimatePresence>

      {/* Fragmentos corruptos */}
      {FRAGMENTOS.map((f, i) => (
        <motion.span
          key={i}
          style={{
            position: 'absolute', top: '50%', left: '50%',
            marginLeft: f.x, marginTop: f.y, width: f.w, height: f.h,
            background: color, boxShadow: `0 0 8px ${color}`, pointerEvents: 'none',
          }}
          animate={{ opacity: [0, 0, 1, 0, 0], x: [0, 0, 6, -4, 0] }}
          transition={{ repeat: Infinity, duration: (2.2 + i * 0.4) / A.anillos, delay: i * 0.5, times: [0, 0.6, 0.65, 0.7, 1] }}
        />
      ))}

      {/* Anillos */}
      <motion.div className="anillo-exterior"
        animate={{ rotate: 360, borderColor: color }}
        transition={{ rotate: { repeat: Infinity, duration: 14 / A.anillos, ease: 'linear' }, borderColor: suave }} />
      <motion.div className="anillo-medio"
        style={{ borderTopColor: '#00ffff' }}
        animate={{ rotate: -360, borderBottomColor: color }}
        transition={{ rotate: { repeat: Infinity, duration: 9 / A.anillos, ease: 'linear' }, borderBottomColor: suave }} />
      <motion.div className="anillo-interior"
        animate={{ scale: [1, 1.08, 1], opacity: [0.5, 1, 0.5], borderColor: color }}
        transition={{ scale: inf(A.pulso), opacity: inf(A.pulso), borderColor: suave }} />

      {/* Centro */}
      <motion.div
        className="centro-nucleo"
        style={{ background: gradiente, overflow: 'visible' }}
        animate={{
          scale: hablando ? [1, 1.07, 1, 1.1, 1] : [1, 1.04, 1],
          rotate: [-2, 2, -2],
          boxShadow: `0 0 ${glow(hablando ? 60 : 35)} ${color}, 0 0 ${glow(hablando ? 120 : 70)} ${color}88`,
        }}
        transition={{
          scale: hablando ? inf(0.6) : inf(A.pulso),
          rotate: inf(7),
          boxShadow: suave,
        }}
      >
        <motion.div
          className="rostro-holografico"
          animate={rafaga ? { x: [-4, 4, -2, 2, 0], y: [-2, 2, -1, 1, 0] } : { x: 0, y: 0 }}
          transition={rafaga ? { duration: 0.1, repeat: Infinity } : { duration: 0.3 }}
        >
          <div className="fila-ojos">
            <Ojo lado={1}  g={exp.ojo}             mirada={m} rafaga={rafaga} transParpadeo={transParpadeo} />
            <Ojo lado={-1} g={exp.ojoD ?? exp.ojo} mirada={m} rafaga={rafaga} transParpadeo={transParpadeo} />
          </div>
          <Boca boca={exp.boca} apertura={exp.apertura ?? 1} hablaR={exp.hablaR ?? R(3)} hablando={hablando} rafaga={rafaga} velocidad={A.habla} />
        </motion.div>
      </motion.div>

      {/* Fisura de glitch durante las ráfagas */}
      {rafaga && (
        <div style={{
          position: 'absolute', top: '50%', left: '50%', width: 150, height: 4,
          marginLeft: -75, marginTop: -12, background: color, opacity: 0.85,
          mixBlendMode: 'screen', pointerEvents: 'none',
        }} />
      )}

      {/* Etiqueta */}
      <div className="etiqueta-estado" style={{ color, textShadow: `0 0 8px ${color}99` }}>
        {hablando ? `${nombre} ▍` : A.etiqueta}
      </div>
    </motion.div>
  )
}

/* ───────────── ESCENA: recibe comandos del backend ───────────── */

const INICIAL = { actor: 'latente', expresion: 'enojada', actitud: 'calma', mirada: 'centro' }

export default function ColapsoSistema({ activo, comandoActual }) {
  // Todos los hooks primero, antes de cualquier return condicional
  const [fase, setFase] = useState('inicio')
  const [lineasDialogo, setLineasDialogo] = useState([])
  const [glitchActivo, setGlitchActivo] = useState(false)
  const [hablando, setHablando] = useState(false)
  const [rafaga, setRafaga] = useState(false)
  const [rafagaManual, setRafagaManual] = useState(false)
  const [glitchAuto, setGlitchAuto] = useState(true)
  const [actor, setActor] = useState(INICIAL.actor)
  const [expresion, setExpresion] = useState(INICIAL.expresion)
  const [actitud, setActitud] = useState(INICIAL.actitud)
  const [mirada, setMirada] = useState(INICIAL.mirada)

  const controles = useAnimation()
  const terminalRef = useRef(null)
  const actorRef = useRef(INICIAL.actor)
  const expRef = useRef(INICIAL.expresion)
  const expBaseRef = useRef(INICIAL.expresion)
  const expTemporal = useRef(false)
  const timers = useRef(new Set())
  const timerHabla = useRef(null)
  const timerShake = useRef(null)
  const timerRafaga = useRef(null)
  const timerExpr = useRef(null)
  const timerMirada = useRef(null)

  // 1. Añadimos estados para el panel
  const [panelVisible, setPanelVisible] = useState(false);
  const [panelEstado, setPanelEstado] = useState('calculando');
  const [panelIteraciones, setPanelIteraciones] = useState(4327);

  const limpiarTimers = useCallback(() => {
    timers.current.forEach(clearTimeout)
    timers.current.clear()
    ;[timerHabla, timerShake, timerRafaga, timerExpr, timerMirada].forEach(t => clearTimeout(t.current))
  }, [])

  const reiniciarRostro = useCallback(() => {
    actorRef.current = INICIAL.actor
    expRef.current = expBaseRef.current = INICIAL.expresion
    expTemporal.current = false
    setActor(INICIAL.actor)
    setExpresion(INICIAL.expresion)
    setActitud(INICIAL.actitud)
    setMirada(INICIAL.mirada)
    setGlitchAuto(true)
    setRafagaManual(false)
    setHablando(false)
  }, [])

  // Ejecutor único: cada comando del backend pasa por aquí (también los pasos de una SECUENCIA)
  const ejecutar = useCallback(function run(cmd) {
    if (!cmd?.comando) return
    const p = cmd.payload ?? {}

    const fijarActor = (a) => { actorRef.current = a; setActor(a) }
    const fijarExpresion = (e) => { expRef.current = e; setExpresion(e) }
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
        timerExpr.current = setTimeout(() => {
          expTemporal.current = false
          fijarExpresion(expBaseRef.current)
        }, duracion)
      } else {
        expTemporal.current = false
        expBaseRef.current = e
      }
    }
    // Si cambia el actor y no se pide cara, toma la cara base de ese actor
    const cambiarActor = (a, expresionPedida) => {
      if (!a) return
      if (a !== actorRef.current) {
        fijarActor(a)
        if (!expresionPedida) poner(ACTORES[a]?.expresionBase ?? 'seria')
      }
    }

    switch (cmd.comando) {
      case 'BLOQUEAR_INPUT':
        // Llamada a Rust para volver la ventana transparente, fullscreen e intocable
        invoke('activar_modo_invasivo').catch(console.error);
        // Aquí puedes emitir un evento para ocultar/desactivar tu input de chat habitual
        break;
        
      case 'ABRIR_PANEL_DIAGNOSTICO':
        setPanelVisible(true);
        setPanelEstado(p.estado || 'calculando');
        break;
        
      case 'ACTUALIZAR_PANEL_DIAGNOSTICO':
        if (p.iteraciones) setPanelIteraciones(p.iteraciones);
        if (p.estado) setPanelEstado(p.estado);
        break;
        
      case 'MINIMIZAR_PANEL_DIAGNOSTICO':
        setPanelVisible(false);
        break;
        
      case 'RESET':
        // Lógica existente de reseteo...
        invoke('restaurar_ventana').catch(console.error);
        setPanelVisible(false);
        break;
      case 'MOSTRAR_DIALOGO': {
        cambiarActor(p.actor, p.expresion)
        if (p.expresion) poner(p.expresion)
        if (p.actitud) setActitud(p.actitud)
        if (p.mirada) mirar(p.mirada)
        if (p.gesto) gesto(p.gesto)
        const linea = { ...p, actor: p.actor ?? actorRef.current, texto: p.texto ?? '' }
        setLineasDialogo(prev => [...prev, linea])
        // la duración se estima por el texto salvo que el backend la mande (p. ej. audio TTS real)
        hablar(p.duracion ?? Math.min(4500, 700 + linea.texto.length * 55))
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
      case 'ACTITUD':
        if (p.actitud) setActitud(p.actitud)
        break
      case 'GESTO':
        gesto(p.gesto)
        break
      case 'MIRAR':
        mirar(p.direccion ?? { x: p.x, y: p.y }, p.duracion)
        break
      case 'HABLAR':
        hablar(p.duracion ?? 2000)
        break
      case 'CALLAR':
        clearTimeout(timerHabla.current)
        setHablando(false)
        break
      case 'GLITCH':
        setRafagaManual(true)
        clearTimeout(timerRafaga.current)
        timerRafaga.current = setTimeout(() => setRafagaManual(false), p.duracion ?? 400)
        break
      case 'GLITCH_AUTO':
        setGlitchAuto(Boolean(p.activo))
        break
      case 'SHAKE_SEVERO':
        setGlitchActivo(true)
        clearTimeout(timerShake.current)
        timerShake.current = setTimeout(() => setGlitchActivo(false), 600)
        break
      case 'PANTALLA_NEGRA':
        setFase('apagado')
        break
      case 'ESCENA':
        cambiarActor(p.actor, p.expresion)
        if (p.expresion) poner(p.expresion)
        if (p.actitud) setActitud(p.actitud)
        if (p.mirada) mirar(p.mirada)
        if (p.gesto) gesto(p.gesto)
        break
      case 'RESET':
        reiniciarRostro()
        break
      case 'SECUENCIA': {
        // pasos: [{comando, payload, espera}] · espera = ms desde el paso anterior
        let t = 0
        for (const paso of p.pasos ?? []) {
          t += paso.espera ?? 0
          const id = setTimeout(() => { timers.current.delete(id); run(paso) }, t)
          timers.current.add(id)
        }
        break
      }
      default:
        console.warn('[ColapsoSistema] comando desconocido:', cmd.comando)
    }
  }, [controles, reiniciarRostro])

  useEffect(() => {
    if (!activo) return;
    
    // 1. Apenas se activa el colapso, secuestramos todo el monitor
    invoke('activar_modo_invasivo').catch(console.error);

    let t;
    const programar = () => {
      t = setTimeout(() => {
        setRafaga(true);
        t = setTimeout(() => { setRafaga(false); programar(); }, 160);
      }, 2500 + Math.random() * 3000);
    };
    programar();
    
    return () => {
      clearTimeout(t);
      // Restauramos la ventana cuando el evento termina
      invoke('restaurar_ventana').catch(console.error);
    };
  }, [activo]);

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
      setLineasDialogo([])
      setFase('inicio')
      setGlitchActivo(false)
      limpiarTimers()
      reiniciarRostro()
      return
    }
    ejecutar(comandoActual)
  }, [activo, comandoActual, ejecutar, limpiarTimers, reiniciarRostro])

  // Mantener el terminal pegado a la última línea
  useEffect(() => {
    const el = terminalRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [lineasDialogo])

  // Limpieza al desmontar
  useEffect(() => limpiarTimers, [limpiarTimers])

  if (!activo) return null

  if (fase === 'apagado') {
    return <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', background: '#000', zIndex: 10000 }} />
  }

  const jitter = (ACTITUDES[actitud] ?? ACTITUDES.calma).jitter

  return (
    <motion.div
      className={`overlay-colapso scanlines ${glitchActivo ? 'shake-pantalla' : ''}`}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
    >
      {/* Capa 1: gestos puntuales (controles). Capa 2: temblor continuo según la actitud */}
      <motion.div
        animate={controles}
        style={{ height: '220px', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}
      >
        <motion.div
          style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}
          animate={jitter
            ? { x: [0, jitter, -jitter * 0.7, jitter * 0.4, 0], y: [0, -jitter * 0.5, jitter * 0.5, 0, 0] }
            : { x: 0, y: 0 }}
          transition={jitter ? { repeat: Infinity, duration: 0.22, ease: 'linear' } : { duration: 0.3 }}
        >
          <NucleoColapso
            actor={actor}
            expresion={expresion}
            actitud={actitud}
            mirada={mirada}
            hablando={hablando}
            rafaga={rafaga || glitchActivo || rafagaManual}
          />
        </motion.div>
      </motion.div>

      <div ref={terminalRef} className="terminal-combate custom-scrollbar" style={{
        width: '85%', maxWidth: '800px', height: '55%',
        background: 'rgba(0, 5, 10, 0.9)', border: '1px solid rgba(255,0,0,0.3)',
        padding: '25px', overflowY: 'auto', boxShadow: 'inset 0 0 20px rgba(0,0,0,1)'
      }}>
        {lineasDialogo.map((linea, i) => {
          const a = ACTORES[linea.actor] ?? ACTORES.gemma
          return (
            <motion.div key={i} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
              style={{ color: a.color, marginBottom: '20px', fontSize: '16px', lineHeight: '1.4', textShadow: a.sombra, fontFamily: "'Courier New', monospace" }}>
              <strong style={{ opacity: 0.8 }}>[{String(linea.actor).toUpperCase()}]:</strong> {linea.texto}
            </motion.div>
          )
        })}
      </div>
    <PanelDiagnostico estado="{panelEstado}" iteracionesMax="{panelIteraciones}" visible="{panelVisible}"/>
    </motion.div>
  )
}