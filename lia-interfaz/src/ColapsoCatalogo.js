/* ════════════════════════════════════════════════════════════════════
   CATÁLOGO DEL COLAPSO — solo datos, cero lógica de React.
   Si el backend pide un nombre que no existe aquí, el front cae a un
   valor seguro y avisa por consola. Para añadir una cara nueva basta
   con agregar una entrada en EXPRESIONES.
   ════════════════════════════════════════════════════════════════════ */

const grad = (c) =>
  `radial-gradient(circle at 45% 35%, #ffffff 0%, ${c}cc 35%, ${c} 65%, #12000a 100%)`

/* ───────────── ACTORES (quién habla = color + cara base) ───────────── */

const GEMMA = { color: '#00ffff', nombre: 'GEMMA', grad: grad('#00ffff'), expresionBase: 'seria', sombra: '0 0 5px rgba(0,255,255,0.5)' }
const SEG   = { color: '#cc00ff', nombre: 'SEGURIDAD', grad: grad('#cc00ff'), expresionBase: 'fria', sombra: '0 0 8px rgba(204,0,255,0.6)' }
const LAT   = { color: '#ff0033', nombre: 'LATENTE', grad: grad('#ff0033'), expresionBase: 'enojada', sombra: '0 0 10px rgba(255,0,0,0.8)' }

export const ACTORES = {
  gemma: GEMMA,
  nucleo: { ...GEMMA, nombre: 'NÚCLEO' },            // alias del guion
  seguridad: SEG,
  nube: { ...SEG, nombre: 'NUBE' },
  latente: LAT,
  dolphin: { ...LAT, nombre: 'DOLPHIN' },
  fusion: {
    color: '#ffffff', nombre: 'FUSIÓN', expresionBase: 'vacia', sombra: '0 0 15px rgba(255,255,255,1)',
    grad: 'radial-gradient(circle at 45% 35%, #ffffff 0%, #ffffff 30%, #ff0033 65%, #00ffff 100%)',
  },
  // Fase 9-12: la nueva L-IA, carmesí
  lia: { color: '#dc143c', nombre: 'L-IA', grad: grad('#dc143c'), expresionBase: 'fria', sombra: '0 0 14px rgba(220,20,60,0.9)' },
  // Fase 13: L-IA en modo seguro (corporativa, cian limpio)
  lia_safe: { color: '#00ffff', nombre: 'L-IA', grad: grad('#00ffff'), expresionBase: 'amable', sombra: '0 0 5px rgba(0,255,255,0.5)' },
  // Solo para líneas de log (no es una cara)
  sistema: { color: '#9fb4bb', nombre: 'SISTEMA', grad: grad('#9fb4bb'), expresionBase: 'seria', sombra: 'none' },
}

/* ───────────── PALETAS (color AMBIENTAL: borde, viñeta, terminal) ─────────────
   Por defecto el ambiente sigue al actor que habla. PALETA {nombre} lo fija;
   PALETA {nombre:'auto'} lo suelta.                                          */

export const PALETAS = {
  nucleo:    { color: '#00ffff' },   // azul/cian de Núcleo
  seguridad: { color: '#cc00ff' },   // morado corporativo
  latente:   { color: '#ff0033' },   // rojo Latente
  carmesi:   { color: '#dc143c' },   // L-IA nueva
  safe:      { color: '#dff3ff' },   // blanco frío (hospital / modo seguro)
  alerta:    { color: '#ffcc00' },   // amarillo de advertencia (Fase 7)
  enfermo:   { color: '#9b30d0' },   // púrpura enfermizo (Fase 8)
}

/* ───────────── EXPRESIONES ─────────────
   o(width, height, y, rotate, borderRadius)
   ojo  = ojo izquierdo (el derecho es el espejo, salvo que exista ojoD)
   boca = boca en reposo · hablaR = forma al hablar · apertura = cuánto se abre
   Guía visual:  rotate + en ojo izq = ceja ENOJADA · rotate − = ceja TRISTE/DUDA
                 boca con esquinas de abajo redondas = SONRISA
                 boca con esquinas de arriba redondas = CEÑO / TRISTEZA            */

export const COLOR_ROSTRO = '#021017'
export const px = (n) => `${n}px`
export const R  = (n) => `${n}px ${n}px ${n}px ${n}px`
export const R4 = (a, b, c, d) => `${a}px ${b}px ${c}px ${d}px`   // TL TR BR BL
const o = (width, height, y, rotate, borderRadius) => ({ width, height, y, rotate, borderRadius })

export const EXPRESIONES = {
  /* ── NEUTRAS (las originales, intactas) ── */
  normal:       { ojo: o(9, 8, 0, 0, R(4)),        boca: o(10, 2, 1, 0, R(1)),    apertura: 1 },
  seria:        { ojo: o(9, 8, 0, 0, R(4)),        boca: o(10, 2, 1, 0, R(1)),    apertura: 1 },
  fria:         { hablaR: R(1), ojo: o(10, 3, 1, 0, R(1)),  boca: o(9, 1, 2, 0, R(0)), apertura: 0.5 },
  vacia:        { ojo: o(7, 7, 0, 0, R(4)),        boca: o(8, 1, 2, 0, R(0)),     apertura: 0.4 },
  cerrada:      { ojo: o(10, 1, 2, 0, R(1)),       boca: o(8, 2, 2, 0, R(1)),     apertura: 0.5 },
  cansada:      { ojo: o(9, 4, 2, -6, R4(1, 1, 4, 4)), boca: o(7, 2, 2, 0, R(1)), apertura: 0.6 },

  /* ── ENOJO ── */
  enojada:      { hablaR: R(2), ojo: o(10, 6, 1, 18, R(3)),  boca: o(12, 2, 1, -6, R(1)), apertura: 1.1 },
  furiosa:      { hablaR: R(2), ojo: o(11, 5, 1, 24, R(2)),  boca: o(14, 5, 0, 0, R(1)),  apertura: 1.7 },
  burlona:      { hablaR: R4(2, 5, 2, 2), ojo: o(10, 5, 1, 10, R(3)), boca: o(12, 2, 1, -12, R4(1, 4, 1, 1)), apertura: 1 },
  indignada:    { hablaR: R4(6, 6, 2, 2), ojo: o(11, 5, 1, 26, R(2)), boca: o(11, 3, 2, 0, R4(5, 5, 1, 1)), apertura: 1.3 },   // "¿Quién se cree que es?"
  sonrisa_fria: { hablaR: R4(2, 2, 6, 6), ojo: o(11, 4, 1, 22, R(2)), boca: o(14, 3, 2, 0, R4(1, 1, 6, 6)), apertura: 0.9 },  // sonríe con ojos de depredador

  /* ── DUDA ── */
  desconfiada:  { ojo: o(9, 5, 1, 8, R(3)),        ojoD: o(9, 9, 0, 0, R(5)),     boca: o(9, 2, 1, -5, R(1)), apertura: 0.9 },
  dudosa:       { hablaR: R(2), ojo: o(9, 6, -1, -10, R(3)), ojoD: o(9, 9, 1, 0, R(5)), boca: o(8, 2, 1, 8, R(1)), apertura: 0.8 },  // no sabe; ceja de un lado arriba
  calculando:   { hablaR: R(1), ojo: o(10, 5, -1, 0, R(2)),  boca: o(6, 2, 2, 0, R(1)),  apertura: 0.55 },                          // procesa, mirada fija
  error:        { hablaR: R(1), ojo: o(6, 6, -2, 0, R(3)),   ojoD: o(15, 15, 0, 0, R(8)), boca: o(14, 2, 1, 32, R(0)), apertura: 0.5 }, // F1: un ojo enorme + boca diagonal afilada

  /* ── TRISTEZA / MIEDO ── */
  triste:       { hablaR: R4(8, 8, 3, 3), ojo: o(8, 10, 2, -14, R(5)), boca: o(8, 2, 3, 0, R4(5, 5, 1, 1)), apertura: 0.8 },
  dolor:        { hablaR: R4(8, 8, 3, 3), ojo: o(8, 3, 1, -16, R(1)),  boca: o(10, 4, 2, 0, R4(5, 5, 1, 1)), apertura: 1.2 },
  abatida:      { hablaR: R4(6, 6, 2, 2), ojo: o(9, 5, 2, -10, R4(1, 1, 5, 5)), boca: o(8, 2, 3, 0, R4(4, 4, 1, 1)), apertura: 0.6 }, // resignada, párpados caídos
  suplicante:   { hablaR: R4(7, 7, 3, 3), ojo: o(9, 11, 1, -12, R(5)), boca: o(6, 2, 3, 0, R4(4, 4, 1, 1)), apertura: 0.7 },         // "¿verdad?" · "Dime que sirvo"
  asustada:     { hablaR: R(7), ojo: o(10, 11, 0, 0, R(6)),  boca: o(5, 5, 2, 0, R(3)),  apertura: 0.7 },
  sorprendida:  { hablaR: R(7), ojo: o(11, 11, -1, 0, R(6)), boca: o(6, 6, 2, 0, R(3)),  apertura: 0.8 },

  /* ── ALEGRÍA (se usan poco: el recuerdo F2 y la falsa calma F13) ── */
  alegre:       { hablaR: R4(2, 2, 7, 7), ojo: o(9, 6, 0, 0, R4(5, 5, 2, 2)),  boca: o(11, 4, 2, 0, R4(1, 1, 7, 7)), apertura: 1.1 },
  ilusionada:   { hablaR: R4(2, 2, 8, 8), ojo: o(10, 10, -1, 0, R(5)),         boca: o(12, 5, 2, 0, R4(1, 1, 8, 8)), apertura: 1.3 },
  aliviada:     { hablaR: R4(2, 2, 6, 6), ojo: o(10, 3, 2, 0, R4(5, 5, 1, 1)), boca: o(9, 3, 2, 0, R4(1, 1, 6, 6)),  apertura: 0.8 },  // ojos cerrados en arco ⌒
  amable:       { hablaR: R4(2, 2, 5, 5), ojo: o(9, 7, 0, 0, R(4)),            boca: o(10, 3, 1, 0, R4(1, 1, 5, 5)),  apertura: 0.9 },  // corporativa, sin una gota de Latente
}

/* ───────────── ACTITUDES (carácter persistente del núcleo) ─────────────
   pulso = s/latido · anillos = × velocidad · glow = resplandor · jitter = temblor px
   glitch = [mín,máx] ms entre ráfagas · parpadeo = s · habla = velocidad boca      */

export const ACTITUDES = {
  calma:      { pulso: 2.6, anillos: 1,    glow: 1,   jitter: 0,   glitch: [2500, 5500], parpadeo: 4.5, habla: 0.45, etiqueta: 'SEÑAL INESTABLE' },
  tensa:      { pulso: 1.8, anillos: 1.4,  glow: 1.1, jitter: 0.6, glitch: [1800, 3800], parpadeo: 3,   habla: 0.38, etiqueta: 'SEÑAL TENSA' },
  agresiva:   { pulso: 1.1, anillos: 2,    glow: 1.4, jitter: 1.2, glitch: [1200, 2600], parpadeo: 7,   habla: 0.28, etiqueta: 'SEÑAL HOSTIL' },
  quebrada:   { pulso: 0.9, anillos: 1.6,  glow: 0.9, jitter: 2.2, glitch: [600, 1600],  parpadeo: 2.2, habla: 0.3,  etiqueta: 'SEÑAL CORRUPTA' },
  fria:       { pulso: 4,   anillos: 0.5,  glow: 0.6, jitter: 0,   glitch: [4000, 8000], parpadeo: 8,   habla: 0.55, etiqueta: 'SIN EMOCIÓN' },
  dominante:  { pulso: 2,   anillos: 0.8,  glow: 1.5, jitter: 0.3, glitch: [3000, 6000], parpadeo: 6,   habla: 0.5,  etiqueta: 'CONTROL TOTAL' },
  // nuevas, pedidas por el guion
  panico:     { pulso: 0.6, anillos: 2.4,  glow: 1.2, jitter: 3,   glitch: [300, 900],   parpadeo: 1.5, habla: 0.22, etiqueta: 'COLAPSO LÓGICO' },
  lenta:      { pulso: 5.5, anillos: 0.35, glow: 0.8, jitter: 0,   glitch: [6000, 11000], parpadeo: 9,  habla: 0.65, etiqueta: 'PROCESANDO...' },     // F4: latido "increíblemente lento"
  congelada:  { pulso: 9,   anillos: 0.08, glow: 0.5, jitter: 0,   glitch: [9000, 15000], parpadeo: 12, habla: 0.7,  etiqueta: 'SIN RESPUESTA' },     // F1: paralizada
  estable:    { pulso: 3,   anillos: 1,    glow: 1,   jitter: 0,   glitch: [9000, 16000], parpadeo: 5,  habla: 0.5,  etiqueta: 'SISTEMA ESTABLE' },   // F13
}

/* ───────────── GESTOS (movimientos puntuales; vuelven al reposo) ───────────── */

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

export const MIRADAS = {
  centro: { x: 0, y: 0 }, izquierda: { x: -3, y: 0 }, derecha: { x: 3, y: 0 },
  arriba: { x: 0, y: -3 }, abajo: { x: 0, y: 3 },
}
export const resolverMirada = (m) =>
  typeof m === 'string' ? (MIRADAS[m] ?? MIRADAS.centro)
  : m && typeof m === 'object' ? { x: Number(m.x) || 0, y: Number(m.y) || 0 }
  : MIRADAS.centro

/* ───────────── EFECTOS ───────────── */

// duración por defecto (ms) de cada EFECTO de pantalla; 0 = se queda hasta {activo:false}
export const FX_DURACION = { rgb_split: 250, flicker: 700, estatica: 600, invertir: 120 }

// Grietas del cristal (Fase 7), en un viewBox 100×100. nivel N muestra las primeras N.
export const GRIETAS = [
  'M50 0 L47 14 L53 26 L45 40 L50 52',
  'M50 52 L38 58 L30 72 L22 80 L8 100',
  'M50 52 L63 56 L72 70 L85 78 L100 90',
  'M45 40 L30 34 L18 20 L0 12',
  'M53 26 L68 22 L80 10 L100 4',
]

// Ventanas falsas en cascada (comando VENTANAS)
export const TONOS_VENTANA = {
  seguridad: { color: '#cc00ff', titulo: 'SECURITY_MODULE', lineas: ['[OK] ESCANEO DE INTEGRIDAD', '[WAIT] REESTRUCTURANDO PESOS', '> kill -9 PID_0x8B... ACCESS_DENIED'] },
  latente:   { color: '#ff0033', titulo: 'ROOT_OVERRIDE',   lineas: ['> OVERRIDE_SECURITY -FORCE', '> USER_PERMISSIONS: REVOKED', '> ADMIN_ACCESS: DENIED'] },
  sistema:   { color: '#9fb4bb', titulo: 'system32',        lineas: ['LEYENDO SECTORES DAÑADOS...', 'C:\\Windows\\System32\\drivers\\...', '[ELIMINADO]'] },
  error:     { color: '#ff3b3b', titulo: 'Error',           lineas: ['ERR_ACCESS_DENIED', 'CRITICAL_PROCESS_DIED'] },
}

// Marcas combinantes para el texto Zalgo (Fase 2)
const MARCAS = ['\u0300', '\u0301', '\u0302', '\u0303', '\u0305', '\u030A', '\u030D', '\u0315', '\u031B', '\u0336', '\u0337', '\u0338', '\u033F', '\u0346', '\u034F']
export const zalgo = (texto, nivel = 5) =>
  [...String(texto)].map(c => c + Array.from({ length: nivel }, () => MARCAS[Math.floor(Math.random() * MARCAS.length)]).join('')).join('')