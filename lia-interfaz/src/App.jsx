import React, { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence, useDragControls } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import './App.css'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Mic, Paperclip, Terminal, Cpu, Database, Upload, AlertTriangle, Activity, ShieldAlert, MessageSquare, Plus, Folder, Pencil, Trash2, Check, X, Menu} from 'lucide-react'

const API = "http://127.0.0.1:8000";

// Extensiones que el backend sabe leer (ajústalas a tu /ingestar)
const EXTENSIONES_VALIDAS = ['txt', 'md', 'py', 'js', 'php', 'html', 'css', 'json', 'docx', 'pdf', 'pptx', 'xlsx'];

const MENSAJE_INICIAL = 'L-IA v3.2.1 inicializada. Esperando directivas...';

// =========================================
// CONFIGURACIÓN VISUAL POR ESTADO DEL NÚCLEO
// =========================================
const CONFIG_ESTADOS = {
  reposo: { tonos: ['#00ffff', '#33e0ff', '#00d4ff', '#33e0ff'], label: 'EN ESPERA', icon: Mic, giro: 14, pulso: 3 },
  // Nuevos estados de pensamiento táctico
  procesando_pregunta: { tonos: ['#ffaa00', '#ffcc33', '#ffdd55', '#ffaa00'], label: 'ANALIZANDO DUDA...', icon: Cpu, giro: 2.2, pulso: 0.9 },
  procesando_doc: { tonos: ['#00ffaa', '#33ffcc', '#00e699', '#00ffaa'], label: 'LEYENDO DOCUMENTO...', icon: Database, giro: 1.5, pulso: 0.8 },
  procesando_sistema: { tonos: ['#0055ff', '#3388ff', '#0066ff', '#0033ee'], label: 'AUDITANDO SISTEMA...', icon: Terminal, giro: 0.8, pulso: 0.4 },
  procesando_git: { tonos: ['#ff3366', '#ff6688', '#ee1144', '#ff3366'], label: 'ENRUTANDO REPOSITORIO...', icon: Activity, giro: 1.2, pulso: 0.6 },
  procesando_rag: { tonos: ['#ff00ff', '#cc00ff', '#ff55ff', '#e000e6'], label: 'ANALIZANDO VECTOR...', icon: Database, giro: 1.6, pulso: 0.7 },
  // Estados originales
  escribiendo: { tonos: ['#39ff88', '#00ffc3', '#7bffb0', '#22ffaa'], label: 'ESCRIBIENDO...', icon: Activity, giro: 1.4, pulso: 0.5 },
  error: { tonos: ['#ff0033', '#ff5500', '#ff0055', '#ff2200'], label: 'ERROR CRÍTICO', icon: ShieldAlert, giro: 0.6, pulso: 0.25 },
}

// Frases rotativas mientras L-IA "piensa" (una por estado de procesamiento)
const FRASES_PENSAMIENTO = {
  procesando_pregunta: ['ANALIZANDO DUDA...', 'CRUZANDO DATOS...', 'VALIDANDO...', 'CASI LISTO...', 'UN MOMENTO MÁS...'],
  procesando_sistema:  ['AUDITANDO SISTEMA...', 'LEYENDO SENSORES...', 'VERIFICANDO HARDWARE...', 'CONSULTANDO NÚCLEO...', 'CASI...'],
  procesando_git:      ['ENRUTANDO REPOSITORIO...', 'REVISANDO COMMITS...', 'LEYENDO DIFF...', 'COMPARANDO RAMAS...', 'CASI...'],
  procesando_doc:      ['LEYENDO DOCUMENTO...', 'EXTRAYENDO CONTENIDO...', 'INDEXANDO...', 'PROCESANDO TEXTO...', 'CASI...'],
};

function useCicloDeTono(tonos, intervaloMs = 1800) {
  const [indice, setIndice] = useState(0)
  useEffect(() => {
    setIndice(0)
    const id = setInterval(() => setIndice(i => (i + 1) % tonos.length), intervaloMs)
    return () => clearInterval(id)
  }, [tonos, intervaloMs])
  return tonos[indice]
}

// Rota entre gestos de "pensamiento" mientras estadoReal empiece con 'procesando_',
// sin depender de saber cuánto va a tardar el backend.
const GESTOS_PENSAMIENTO = ['duda', 'mirada_arriba', 'ceja_alzada', 'concentracion', 'casi'];

function useGestoPensamiento(activo, intervaloMs = 1400) {
  const [ronda, setRonda] = useState(0);
  useEffect(() => {
    if (!activo) { setRonda(0); return; }
    const id = setInterval(() => setRonda(r => r + 1), intervaloMs);
    return () => clearInterval(id);
  }, [activo, intervaloMs]);
  return [GESTOS_PENSAMIENTO[ronda % GESTOS_PENSAMIENTO.length], ronda];
}

// =========================================
// NÚCLEO L-IA: Expresividad, Micro-Estados y Tareas
// =========================================
// `mensajeEspera` (opcional): texto que manda el backend vía callback_estado
// (ej. "Analizando arquitectura..." cuando responde Gemini Pro). Si llega,
// reemplaza las frases rotativas mientras L-IA piensa.
function NucleoLIA({ estado, mensajeEspera }) {
  // Fallback a procesando_pregunta si enviamos un estado 'procesando' genérico
  const estadoReal = estado === 'procesando' ? 'procesando_pregunta' : estado;

  // Mientras estadoReal empiece con 'procesando_', L-IA está "pensando":
  // el gesto va rotando cada 1.4s sin importar cuánto tarde el backend.
  const pensando = estadoReal.startsWith('procesando');
  const [gesto, rondaGesto] = useGestoPensamiento(pensando);

  const cfg = CONFIG_ESTADOS[estadoReal] || CONFIG_ESTADOS.reposo;
  const { label, giro, pulso, tonos } = cfg;
  const color = useCicloDeTono(tonos, estadoReal === 'error' ? 600 : 1800);
  const colorRostro = '#021017';

  const [parpadeo, setParpadeo] = useState(false);
  const [mouseOffset, setMouseOffset] = useState({ x: 0, y: 0 });
  const [miradaVagante, setMiradaVagante] = useState({ x: 0, y: 0 });
  const [tiempoInactiva, setTiempoInactiva] = useState(0);
  const [subEstado, setSubEstado] = useState('normal');

  // 1. Detección de movimiento
  useEffect(() => {
    const handleMouseMove = (e) => {
      setTiempoInactiva(0);
      setSubEstado('normal');
      const windowCenterX = window.innerWidth / 2;
      const windowCenterY = window.innerHeight / 2;
      const offsetX = (e.clientX - windowCenterX) / 45;
      const offsetY = (e.clientY - windowCenterY) / 60;
      const limit = (val, max) => Math.min(Math.max(val, -max), max);
      setMouseOffset({ x: limit(offsetX, 10), y: limit(offsetY, 7) });
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  // Interceptor global para Drag & Drop en Tauri v2
  useEffect(() => {
    const evitarNavegacionNativa = (e) => {
      e.preventDefault();
      // Solo detenemos la propagación en el drop a nivel ventana
      // para evitar que Tauri abra el archivo.
    };

    window.addEventListener('dragover', evitarNavegacionNativa);
    window.addEventListener('drop', evitarNavegacionNativa);

    return () => {
      window.removeEventListener('dragover', evitarNavegacionNativa);
      window.removeEventListener('drop', evitarNavegacionNativa);
    };
  }, []);

  // 2. Progresión de aburrimiento
  useEffect(() => {
    if (estadoReal !== 'reposo') {
      setSubEstado('normal');
      return;
    }
    const timer = setInterval(() => {
      setTiempoInactiva(prev => {
        const t = prev + 1;
        if (t > 40) setSubEstado('durmiendo');
        else if (t > 34) setSubEstado('bostezo');
        else if (t > 24) setSubEstado('molesta');
        else if (t > 15) setSubEstado('impaciente');
        else if (t > 7) setSubEstado('alegre');
        else setSubEstado('normal');
        return t;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [estadoReal]);

  // 3. Mirada errante natural
  useEffect(() => {
    if (estadoReal !== 'reposo' || subEstado === 'durmiendo') {
      setMiradaVagante({ x: 0, y: 0 });
      return;
    }
    const intervaloMirada = setInterval(() => {
      if (tiempoInactiva > 3) {
        const angulo = Math.random() * Math.PI * 2;
        const radio = 4 + Math.random() * 5;
        setMiradaVagante({ x: Math.cos(angulo) * radio, y: Math.sin(angulo) * (radio * 0.6) });
      } else {
        setMiradaVagante({ x: 0, y: 0 });
      }
    }, 2800);
    return () => clearInterval(intervaloMirada);
  }, [estadoReal, subEstado, tiempoInactiva]);

  // 4. Parpadeo (con limpieza del timeout interno para no tocar estado desmontado)
  useEffect(() => {
    if (subEstado === 'durmiendo') return;
    let timeoutId;
    const ciclo = setInterval(() => {
      setParpadeo(true);
      timeoutId = setTimeout(() => setParpadeo(false), 140);
    }, Math.random() * 3500 + 2500);
    return () => {
      clearInterval(ciclo);
      clearTimeout(timeoutId);
    };
  }, [subEstado]);

  // --- GEOMETRÍA FACIAL ---
  const getOjos = () => {
    // 1. Estados de reposo/aburrimiento
    if (parpadeo || subEstado === 'durmiendo') return { height: '2px', width: '10px', y: 3, rotate: 0, borderRadius: '2px', scaleY: 1 };
    if (subEstado === 'bostezo') return { height: '3px', width: '9px', y: -2, rotate: -15, borderRadius: '2px', scaleY: 1 };
    if (subEstado === 'alegre') return { height: '6px', width: '10px', y: -1, rotate: 0, borderRadius: '50% 50% 0 0', scaleY: 1 };
    if (subEstado === 'impaciente') return { height: '8px', width: '10px', y: 0, rotate: -8, borderRadius: '30%', scaleY: 1 };
    if (subEstado === 'molesta' || estadoReal === 'error') return { height: '7px', width: '10px', y: 1, rotate: 18, borderRadius: '4px', scaleY: 1 };

    // 2. Gestos rotativos mientras "piensa"
    if (pensando && gesto === 'mirada_arriba') return { height: '7px', width: '9px', y: -6, rotate: 0, borderRadius: '50%', scaleY: 1 };
    if (pensando && gesto === 'ceja_alzada')   return { height: '10px', width: '8px', y: -3, rotate: 10, borderRadius: '40%', scaleY: 1 };
    if (pensando && gesto === 'concentracion') return { height: '6px', width: '10px', y: 0, rotate: 0, borderRadius: '30%', scaleY: 0.8 };
    if (pensando && gesto === 'casi')          return { height: '9px', width: '9px', y: -2, rotate: 0, borderRadius: '50%', scaleY: 1.15 };

    // 3. Estados de procesamiento táctico (fallback / gesto 'duda')
    if (estadoReal === 'procesando_pregunta') return { height: '9px', width: '9px', y: -3, rotate: 0, borderRadius: '50%', scaleY: 1 };
    if (estadoReal === 'procesando_sistema') return { height: '2px', width: '18px', y: -2, rotate: 0, borderRadius: '1px', scaleX: 1.2, scaleY: 1 };
    if (estadoReal === 'procesando_doc') return { height: '4px', width: '4px', y: -2, rotate: 0, borderRadius: '50%', scaleY: 1 };

    // 4. Generales
    if (estadoReal === 'procesando_rag' || estadoReal === 'procesando_git') return { height: '10px', width: '10px', y: -2, rotate: 0, borderRadius: '50%', scaleY: 1 };
    if (estadoReal === 'escribiendo') return { height: '8px', width: '9px', y: -2, rotate: -5, borderRadius: '4px 4px 50% 50%', scaleY: 1 };

    return { height: '9px', width: '9px', y: 0, rotate: 0, borderRadius: '50%', scaleY: 1 };
  };

  const getBoca = () => {
    // 1. Estados de reposo/aburrimiento
    if (subEstado === 'durmiendo') return { width: '6px', height: '2px', borderRadius: '1px', scaleY: 1, rotate: 0, y: 3 };
    if (subEstado === 'bostezo') return { width: '10px', height: '14px', borderRadius: '40%', scaleY: 1.2, rotate: 0, y: 1 };
    if (subEstado === 'alegre') return { width: '13px', height: '6px', borderRadius: '0 0 10px 10px', scaleY: 1, rotate: 0, y: 2 };
    if (subEstado === 'impaciente') return { width: '9px', height: '3px', borderRadius: '2px', scaleY: 1, rotate: 6, y: 1 };
    if (subEstado === 'molesta' || estadoReal === 'error') return { width: '12px', height: '3px', borderRadius: '2px', scaleY: 1, rotate: -8, y: 1 };

    // 2. Gestos rotativos mientras "piensa"
    if (pensando && gesto === 'mirada_arriba') return { width: '5px', height: '5px', borderRadius: '50%', scaleY: 1, rotate: 0, y: 0 };
    if (pensando && gesto === 'ceja_alzada')   return { width: '7px', height: '3px', borderRadius: '2px', scaleY: 1, rotate: 4, y: 1 };
    if (pensando && gesto === 'concentracion') return { width: '9px', height: '2px', borderRadius: '1px', scaleY: 1, rotate: 0, y: 2 };
    if (pensando && gesto === 'casi')          return { width: '6px', height: '6px', borderRadius: '50%', scaleY: 1, rotate: 0, y: 1 };

    // 3. Estados de procesamiento táctico (fallback / gesto 'duda')
    if (estadoReal === 'procesando_pregunta') return { width: '4px', height: '4px', borderRadius: '50%', scaleY: 1, rotate: 0, y: 1 };

    // 4. Generales
    if (estadoReal === 'escribiendo') return { width: '15px', height: '6px', borderRadius: '3px 3px 10px 10px', scaleY: [1, 1.4, 0.8, 1.2], rotate: 0, y: 0 };
    if (estadoReal === 'procesando_rag' || estadoReal === 'procesando_git' || estadoReal === 'procesando_sistema' || estadoReal === 'procesando_doc') return { width: '5px', height: '5px', borderRadius: '50%', scaleY: 1, rotate: 0, y: 0 };

    return { width: '10px', height: '3px', borderRadius: '1px 1px 6px 6px', scaleY: 1, rotate: 0, y: 1 };
  };

  const ojosCfg = getOjos();
  const bocaCfg = getBoca();

  const faceOffset = estadoReal === 'reposo' && subEstado !== 'durmiendo'
    ? {
        x: tiempoInactiva > 3 ? miradaVagante.x : mouseOffset.x,
        y: tiempoInactiva > 3 ? miradaVagante.y : mouseOffset.y,
      }
    : { x: 0, y: subEstado === 'durmiendo' ? 4 : 0 };

  // Texto de la etiqueta inferior
  const textoEtiqueta =
    subEstado === 'durmiendo' ? 'SUSPENDIDA (REPOSO)' :
    subEstado === 'bostezo' ? 'MODO REPOSO...' :
    subEstado === 'molesta' ? 'ESPERANDO ÓRDENES...' :
    subEstado === 'impaciente' ? 'EN ESPERA' :
    pensando && mensajeEspera ? mensajeEspera.toUpperCase() :
    pensando && FRASES_PENSAMIENTO[estadoReal]
      ? FRASES_PENSAMIENTO[estadoReal][rondaGesto % FRASES_PENSAMIENTO[estadoReal].length]
      : label;

  return (
    <div className="nucleo-wrapper">
      <div className="nucleo-halo" style={{ background: `radial-gradient(circle, ${color}33, transparent 70%)` }} />

      {/* NODO DE GIT BRANCHING */}
      <AnimatePresence>
        {estadoReal === 'procesando_git' && (
          <motion.div
            className="nodo-git"
            style={{ background: color, color: color, top: '50%', left: '50%', marginTop: '-7px', marginLeft: '-7px' }}
            initial={{ x: 0, y: 0, opacity: 0 }}
            animate={{ x: 50, y: -30, opacity: 1 }}
            exit={{ x: 0, y: 0, opacity: 0 }}
            transition={{ type: "spring", stiffness: 50, damping: 10 }}
          >
             <motion.div style={{ position: 'absolute', top: '50%', right: '100%', height: '2px', width: '50px', background: color, transformOrigin: 'right', rotate: '30deg' }} />
          </motion.div>
        )}
      </AnimatePresence>

      <motion.div className="anillo-particulas" animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: giro * 2.2, ease: 'linear' }}>
        {[...Array(6)].map((_, i) => (
          <span key={i} className="particula" style={{ background: color, boxShadow: `0 0 8px ${color}`, transform: `rotate(${i * 60}deg) translateX(88px)` }} />
        ))}
      </motion.div>

      <motion.div className="anillo-exterior" style={{ borderColor: color }} animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: giro, ease: 'linear' }} />
      <motion.div className="anillo-medio" style={{ borderTopColor: color, borderBottomColor: color }} animate={{ rotate: -360 }} transition={{ repeat: Infinity, duration: giro * 1.5, ease: 'linear' }} />
      <motion.div className="anillo-interior" style={{ borderColor: color }} animate={{ scale: [1, 1.15, 1], opacity: [0.55, 1, 0.55] }} transition={{ repeat: Infinity, duration: pulso }} />

      <motion.div
        className="centro-nucleo"
        style={{
          background: `radial-gradient(circle at 45% 35%, #ffffff 0%, #a6ffff 30%, ${color} 80%)`,
          boxShadow: `0 0 25px ${color}, 0 0 55px ${color}66`,
          overflow: 'visible',
        }}
        animate={{
          scale: estadoReal === 'escribiendo' ? [1, 1.2, 0.95, 1.1, 1] :
                 subEstado === 'bostezo' ? [1, 1.15, 0.95, 1] :
                 [1, 1.06, 1],
          opacity: subEstado === 'durmiendo' ? 0.7 : 1,
          rotate: pensando
            ? ({ duda: 15, mirada_arriba: -8, ceja_alzada: 10, concentracion: -4, casi: 0 }[gesto] ?? 0)
            : 0
        }}
        transition={{ repeat: Infinity, duration: subEstado === 'bostezo' ? 2.5 : pulso, ease: 'easeInOut' }}
      >
        {/* ICONOS FLOTANTES DE EMOCIÓN */}
        <AnimatePresence>
          {subEstado === 'durmiendo' && (
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
          {subEstado === 'impaciente' && (
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
          {subEstado === 'molesta' && (
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
          {subEstado === 'alegre' && (
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
          {estadoReal === 'procesando_doc' && (
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
        {estadoReal === 'procesando_rag' && (
          <div className="escaner-rag">
            <motion.div className="escaner-rag-barra" animate={{ top: ['-10%', '110%'] }} transition={{ repeat: Infinity, duration: 1.3, ease: 'linear' }} />
          </div>
        )}

        <motion.div
          className="rostro-holografico"
          animate={{ x: faceOffset.x, y: faceOffset.y }}
          transition={{ type: 'spring', stiffness: 100, damping: 18 }}
        >
          <div className="fila-ojos">
            <motion.div className="ojo" style={{ background: colorRostro }} animate={ojosCfg} transition={{ duration: 0.15 }} />
            {/* Animación asimétrica de la ceja al dudar */}
            <motion.div className="ojo" style={{ background: colorRostro }} animate={{ ...ojosCfg, rotate: -ojosCfg.rotate, scaleY: estadoReal === 'procesando_pregunta' ? 1.4 : ojosCfg.scaleY }} transition={{ duration: 0.15 }} />
          </div>
          <motion.div
            className="boca"
            style={{ background: colorRostro }}
            animate={bocaCfg}
            transition={{ duration: estadoReal === 'escribiendo' ? 0.4 : 0.2, repeat: estadoReal === 'escribiendo' ? Infinity : 0, ease: 'easeInOut' }}
          />
        </motion.div>
      </motion.div>

      {estadoReal === 'escribiendo' && (
        <div className="barras-voz">
          {[0, 1, 2, 3, 4].map((i) => (
            <motion.span key={i} style={{ background: color, boxShadow: `0 0 6px ${color}` }} animate={{ height: ['20%', '85%', '35%', '65%', '20%'] }} transition={{ repeat: Infinity, duration: 0.9, delay: i * 0.09, ease: 'easeInOut' }} />
          ))}
        </div>
      )}

      {estadoReal === 'error' && (
        <motion.div className="destello-error" style={{ borderColor: color }} animate={{ opacity: [0, 0.5, 0], scale: [1, 1.08, 1] }} transition={{ repeat: Infinity, duration: 0.5 }} />
      )}

      <AnimatePresence mode="wait">
        <motion.div
          key={`${estadoReal}-${subEstado}-${pensando ? rondaGesto : 0}`}
          className="etiqueta-estado"
          style={{ color, textShadow: `0 0 8px ${color}99` }}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.25 }}
        >
          {textoEtiqueta}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}

// Sub-componente para renderizar bloques de código vs código en línea
function BloqueDeCodigo({ node, inline, className, children, ...props }) {
  const [copiado, setCopiado] = useState(false);

  const match = /language-(\w+)/.exec(className || '');
  const lenguaje = match ? match[1] : 'text';
  const codigoString = String(children).replace(/\n$/, '');

  // Si no tiene saltos de línea y no tiene clase de lenguaje,
  // es código en línea (como `readline()` o `$mayor`)
  const esMultilinea = Boolean(match) || codigoString.includes('\n');

  if (!esMultilinea) {
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
    );
  }

  const manejarCopia = async () => {
    try {
      await navigator.clipboard.writeText(codigoString);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    } catch (err) {
      console.error("Error al copiar", err);
    }
  };

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

      <SyntaxHighlighter
        children={codigoString}
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
        {...props}
      />
    </div>
  );
}

function App() {
  const [estadoLIA, setEstadoLIA] = useState('reposo')
  const [input, setInput] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const [escuchando, setEscuchando] = useState(false)
  const [mensajes, setMensajes] = useState([
    { rol: 'ia', texto: MENSAJE_INICIAL }
  ])

  // Mensaje de espera que manda el backend (ej. "Analizando arquitectura..." con Gemini Pro)
  const [mensajeEspera, setMensajeEspera] = useState(null)

  // ESTADO DEL WORKSPACE ACTIVO (archivo en el que L-IA está enfocada)
  const [workspaceActivo, setWorkspaceActivo] = useState(null)

  // ---> ESTADOS MULTI-SESIÓN <---
  const [sesiones, setSesiones] = useState([])
  const [sesionActual, setSesionActual] = useState('default')
  const [sidebarAbierto, setSidebarAbierto] = useState(false)

  const [editandoSesion, setEditandoSesion] = useState(null)
  const [tituloTemp, setTituloTemp] = useState("")

  const guardarNuevoTitulo = async (id, e) => {
    if (e) e.stopPropagation();
    if (!tituloTemp.trim()) { setEditandoSesion(null); return; }
    try {
      const urlDirecta = API + "/sesiones/" + id;
      const res = await fetch(urlDirecta, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ titulo: tituloTemp })
      });

      if (!res.ok) {
        console.error("Error renombrando. Status:", res.status);
        return;
      }

      setEditandoSesion(null);
      cargarSesiones();
    } catch (err) {
      console.error("Error renombrando", err);
    }
  };

  const eliminarSesion = async (id, e) => {
    e.stopPropagation();

    agregarSistema("[SISTEMA] Botón de borrado presionado. Intentando eliminar ID: " + id);

    try {
      const urlDirecta = API + "/sesiones/" + id;
      const res = await fetch(urlDirecta, { method: 'DELETE' });

      agregarSistema("[SISTEMA] Respuesta del núcleo (Status): " + res.status);

      if (res.ok) {
        if (sesionActual === id) {
          cargarContextoSesion("default");
        }
        cargarSesiones();
      } else {
        agregarSistema("[ERROR] FastAPI rechazó la orden. Status: " + res.status);
      }
    } catch (err) {
      agregarSistema("[ERROR CRÍTICO] Fallo de red al borrar: " + err.message);
    }
  };

  const finalDelChatRef = useRef(null)
  const archivoInputRef = useRef(null)
  const textareaRef = useRef(null)

  // Contador de entradas/salidas del arrastre: evita el parpadeo al cruzar elementos hijos
  const dragContador = useRef(0)

  // ESTADO DEL SEMÁFORO
  const [semaforo, setSemaforo] = useState({ activa: false, herramienta: '', argumentos: '' })

  const [cargando, setCargando] = useState(false);
  const abortControllerRef = useRef(null);

  const overlayRef = useRef(null)
const dragControls = useDragControls()

  // ---------- Helpers de estado inmutable ----------
  // Siempre se crea un objeto nuevo (evita duplicar texto en React StrictMode).
  const actualizarUltimoMensaje = (fn) => {
    setMensajes(prev => {
      if (prev.length === 0) return prev
      const copia = [...prev]
      copia[copia.length - 1] = fn(copia[copia.length - 1])
      return copia
    })
  }

  const agregarSistema = (texto) =>
    setMensajes(prev => [...prev, { rol: 'sistema', texto }])

  const nombreDeRuta = (ruta) => (ruta ? String(ruta).split(/[\\/]/).pop() : null)

  useEffect(() => {
    finalDelChatRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [mensajes])

  // =========================================
  // MULTI-SESIÓN
  // =========================================
  const cargarSesiones = async () => {
    try {
      const res = await fetch(`${API}/sesiones`)
      if (res.ok) {
        const data = await res.json()
        setSesiones(data)
      }
    } catch (e) {
      console.error("Fallo al cargar lista de sesiones", e)
    }
  }

  // Carga el historial y el workspace de una pestaña
  const cargarContextoSesion = async (idSesion) => {
    try {
      const res = await fetch(`${API}/sesiones/${idSesion}/contexto`)
      if (res.ok) {
        const data = await res.json()
        const mapeados = (data.historial || []).map(m => ({
          rol: m.rol === 'model' ? 'ia' : 'usuario',
          texto: m.mensaje
        }))
        if (mapeados.length === 0) {
          mapeados.push({ rol: 'ia', texto: MENSAJE_INICIAL })
        }
        // Solo cambiamos de sesión cuando el contexto llegó bien
        setSesionActual(idSesion)
        setMensajes(mapeados)
        setWorkspaceActivo(nombreDeRuta(data.workspace_activo))
      }
    } catch (e) {
      console.error("Fallo al cargar contexto de sesión", e)
    }
  }

  const crearNuevaSesion = async () => {
    if (cargando) return
    try {
      const res = await fetch(`${API}/sesiones/nueva`, { method: "POST" })
      if (res.ok) {
        const data = await res.json()
        await cargarSesiones()
        cargarContextoSesion(data.sesion_id)
      }
    } catch (e) {
      console.error("Fallo al crear sesión", e)
    }
  }

  // Al montar: lista de pestañas + historial de "default"
  // (esto reemplaza al antiguo GET /workspace, porque el contexto ya trae el workspace)
  useEffect(() => {
    cargarSesiones()
    cargarContextoSesion("default")
  }, [])

  // Evita que el navegador abra el archivo en otra pestaña si se suelta fuera de la zona de drop
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

  // Vigía del Semáforo
  useEffect(() => {
    let intervalo;
    // Solo vigila si L-IA está pensando (cualquier 'procesando_*') o escribiendo
    const piensaOEscribe = estadoLIA === 'escribiendo' || estadoLIA.startsWith('procesando');
    if (piensaOEscribe) {
      intervalo = setInterval(async () => {
        try {
          const res = await fetch(`${API}/semaforo`)
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
      await fetch(`${API}/semaforo/responder`, {
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
    if (textareaRef.current) textareaRef.current.style.height = '42px';

    // 1. Estado por defecto (duda)
    let estadoTemporal = 'procesando_pregunta';
    const textoMinusculas = textoUsuario.toLowerCase();

    // Filtramos palabras clave para disparar las animaciones correctas.
    // `\bram\b` evita que "programa" o "diagrama" activen el estado de sistema.
    if (/\b(git|commit|commits|ramas)\b/.test(textoMinusculas)) {
      estadoTemporal = 'procesando_git';
    } else if (/\b(sistema|hardware|ram)\b/.test(textoMinusculas)) {
      estadoTemporal = 'procesando_sistema';
    } else if (/(archivo|documento|workspace|\blee\b|\brevisa)/.test(textoMinusculas)) {
      estadoTemporal = 'procesando_doc';
    } else if (textoMinusculas.includes('?')) {
      estadoTemporal = 'procesando_pregunta';
    }

    setEstadoLIA(estadoTemporal);
    setMensajeEspera(null);
    let huboError = false;

    try {
      const respuesta = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // MANDAMOS LA SESIÓN ACTIVA AL BACKEND
        body: JSON.stringify({ texto: textoUsuario, sesion_id: sesionActual }),
        signal: abortControllerRef.current.signal
      });

      if (!respuesta.ok || !respuesta.body) {
        throw new Error(`HTTP ${respuesta.status}`)
      }

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
          if (!parte.startsWith("data: ")) continue
          const dataStr = parte.replace("data: ", "")
          try {
            const data = JSON.parse(dataStr)

            if (data.tipo === "estado") {
              // El backend reenvía lo que manda callback_estado en cerebro.py
              // ({ perfil, etiqueta, modelo, motivo, mensaje_espera }).
              if (!yaEscribiendo) setMensajeEspera(data.mensaje_espera || null)

            } else if (data.tipo === "chunk") {
              // en cuanto llega el primer chunk, pasamos a "escribiendo"
              if (!yaEscribiendo) {
                yaEscribiendo = true
                setMensajeEspera(null)
                setEstadoLIA('escribiendo')
              }

              if (data.texto.length > 50) {
                actualizarUltimoMensaje(m => ({ ...m, texto: m.texto + data.texto }))
              } else {
                const letras = data.texto.split("");
                for (let i = 0; i < letras.length; i++) {
                  actualizarUltimoMensaje(m => ({ ...m, texto: m.texto + letras[i] }))
                  await new Promise(resolve => setTimeout(resolve, 15));
                }
              }

            } else if (data.tipo === "fin") {
              actualizarUltimoMensaje(m => ({
                ...m,
                origen: data.origen,
                documento: data.documento || m.documento
              }))

              // ---> SINCRONIZACIÓN VISUAL <---
              if (data.workspace !== undefined) {
                setWorkspaceActivo(data.workspace);
              }
              // Refresca la barra lateral (títulos nuevos e iconos de workspace)
              cargarSesiones();

            } else if (data.tipo === "error") {
              huboError = true
              actualizarUltimoMensaje(m => ({ ...m, texto: m.texto + `\n[ERROR]: ${data.texto}` }))
            }
          } catch (err) {
            console.error("Error parseando el chunk:", err)
          }
        }
      }

    } catch (error) {
      if (error.name === 'AbortError') {
        actualizarUltimoMensaje(m => ({ ...m, texto: m.texto + '\n\n*(Respuesta abortada)*', cancelado: true }))
      } else {
        huboError = true;
        actualizarUltimoMensaje(m => ({ ...m, texto: m.texto + '\n\n[ERROR] Caída del enlace con el núcleo.' }))
      }
    } finally {
      setCargando(false);
      setMensajeEspera(null);
      if (huboError) {
        // el núcleo destella un momento antes de calmarse
        setEstadoLIA('error');
        setTimeout(() => setEstadoLIA('reposo'), 1600);
      } else {
        setEstadoLIA('reposo');
      }
    }
  }

  const procesarArchivoRAG = async (archivo) => {
    setEstadoLIA('procesando_rag')
    agregarSistema(`[SISTEMA] Ingestando ${archivo.name}...`)
    const formData = new FormData()
    formData.append("archivo", archivo)
    formData.append("sesion_id", sesionActual) // a qué chat pertenece
    try {
      const respuesta = await fetch(`${API}/ingestar`, { method: "POST", body: formData })
      const data = await respuesta.json()
      setMensajes(prev => [...prev, { rol: 'ia', texto: data.mensaje }])

      // Activa el indicador de workspace solo si la ingesta salió bien
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

  // Libera el archivo en el que L-IA está enfocada (en la sesión actual)
  const limpiarWorkspace = async () => {
    try {
      const respuesta = await fetch(`${API}/workspace/limpiar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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
      console.error("Error al limpiar workspace", error)
      agregarSistema('[ERROR] Sin enlace con el núcleo al liberar el workspace.')
    }
  }

  // =========================================
  // DRAG & DROP
  // =========================================
  const tieneArchivos = (e) =>
    Array.from(e.dataTransfer?.types || []).includes('Files')

  const manejarDragEnter = (e) => {
    if (!tieneArchivos(e)) return
    e.preventDefault()
    dragContador.current += 1
    setIsDragging(true)
  }

  const manejarDragOver = (e) => {
    if (!tieneArchivos(e)) return
    e.preventDefault() // obligatorio para que el navegador permita el drop
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

    const archivos = Array.from(e.dataTransfer.files || [])
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

  const manejarClickArchivo = () => archivoInputRef.current?.click()
  const manejarSeleccionArchivo = (e) => {
    if (e.target.files.length > 0) procesarArchivoRAG(e.target.files[0])
    e.target.value = null
  }

  const manejarMicrofono = () => {
    setEscuchando(!escuchando)
  }

  const detenerGeneracion = async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setCargando(false);

    try {
      await fetch(`${API}/cancelar`, { method: "POST" });
    } catch (error) {
      console.error("Error al abortar en el backend:", error);
    }
  };

  return (
    <div
      className="hud-container"
      onDragEnter={manejarDragEnter}
      onDragOver={manejarDragOver}
      onDragLeave={manejarDragLeave}
      onDrop={manejarDrop}
    >
      {/* FRANJA DE ARRASTRE INVISIBLE (Solo los primeros 35px de arriba) */}
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

      {/* CAPA DE DRAG & DROP (pointer-events: none para no robar los eventos del arrastre) */}
      {isDragging && (
        <div className="capa-drag" style={{ pointerEvents: 'none' }}>
          <Upload size={40} />
          <p>Suelta el archivo para ingestarlo</p>
        </div>
      )}

      {/* --- PANEL LATERAL IZQUIERDO (SIDEBAR MULTI-SESIÓN) --- */}
      {sidebarAbierto && <div className="sidebar-backdrop" onClick={() => setSidebarAbierto(false)} />}
      <div className={`panel lateral-izquierdo ${sidebarAbierto ? 'abierto' : ''}`} style={{ padding: '15px' }}>
        <h2 className="hud-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          HISTORIAL DE CONVERSACIÓN
          <button
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
            const isActiva = s.id === sesionActual;
            const nombreArchivo = s.workspace_activo ? s.workspace_activo.split(/[\\/]/).pop() : null;
            return (
              <div 
                key={s.id} 
                onClick={() => !isActiva && !editandoSesion && cargarContextoSesion(s.id)}
                className="item-sesion"
                style={{
                  background: isActiva ? 'rgba(0, 255, 255, 0.15)' : 'rgba(0, 0, 0, 0.4)',
                  border: `1px solid ${isActiva ? '#00ffff' : 'rgba(0,255,255,0.1)'}`,
                  padding: '10px',
                  borderRadius: '6px',
                  cursor: isActiva ? 'default' : 'pointer',
                  transition: 'all 0.2s ease',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '5px'
                }}
              >
                {editandoSesion === s.id ? (
                  // --- MODO EDICIÓN ---
                  <div style={{ display: 'flex', alignItems: 'center', gap: '5px', width: '100%' }}>
                    <input
                      autoFocus
                      value={tituloTemp}
                      onChange={e => setTituloTemp(e.target.value)}
                      onKeyDown={e => {
                        if (e.key === 'Enter') {
                          e.preventDefault(); // Evita recargas indeseadas al presionar Enter
                          guardarNuevoTitulo(s.id, e);
                        }
                        if (e.key === 'Escape') setEditandoSesion(null);
                      }}
                      style={{ flex: 1, minWidth: 0, background: '#021017', color: '#00ffff', border: '1px solid #00ffff', borderRadius: '4px', padding: '4px', fontSize: '11px', outline: 'none' }}
                      onClick={e => e.stopPropagation()}
                    />
                    <button onClick={(e) => guardarNuevoTitulo(s.id, e)} className="hud-btn" style={{ padding: '4px', border: 'none', flexShrink: 0 }}><Check size={14} color="#39ff88" /></button>
                    <button onClick={(e) => { e.stopPropagation(); setEditandoSesion(null); }} className="hud-btn" style={{ padding: '4px', border: 'none', flexShrink: 0 }}><X size={14} color="#ff0055" /></button>
                  </div>
                ) : (
                  // --- MODO LECTURA NORMAL ---
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', gap: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, minWidth: 0, color: isActiva ? '#fff' : '#88ccff', fontSize: '12px' }}>
                      <MessageSquare size={14} style={{ flexShrink: 0 }} /> 
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: isActiva ? 'bold' : 'normal' }}>
                        {s.titulo || 'Conversación'}
                      </span>
                    </div>
                    {/* Botones de acción con flexShrink: 0 para que no se aplasten */}
                    {s.id !== "default" && (
                      <div className="acciones-sesion" style={{ display: 'flex', gap: '6px', flexShrink: 0 }}>
                        <button onClick={(e) => { e.stopPropagation(); setEditandoSesion(s.id); setTituloTemp(s.titulo); }} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }} title="Editar Título"><Pencil size={13} color="#00ffff" /></button>
                        <button onClick={(e) => eliminarSesion(s.id, e)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }} title="Borrar Historial"><Trash2 size={13} color="#ff0055" /></button>
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
            {/* Capa de arrastre: solo se mueve al tirar de la cabecera */}
            <motion.div
              drag
              dragControls={dragControls}
              dragListener={false}
              dragMomentum={false}
              dragElastic={0}
              dragConstraints={overlayRef}
              style={{ width: '85%', maxWidth: '400px' }}
            >
              {/* Capa de animación de entrada/salida (la tuya, sin cambios) */}
              <motion.div
                className="modal-semaforo"
                style={{ width: '100%', maxWidth: 'none', boxSizing: 'border-box' }}
                initial={{ scale: 0.8, y: 50 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.8, opacity: 0 }}
                transition={{ type: "spring", bounce: 0.5 }}
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
          </motion.div>
        )}
      </AnimatePresence>

      {/* --- PANEL CENTRAL --- */}
      <div className="panel central">
        {/* BOTÓN PARA ABRIR EL SIDEBAR (solo visible en ventana pequeña) */}
        <button type="button" className="hud-btn btn-menu-sidebar" onClick={() => setSidebarAbierto(true)} title="Sesiones">
          <Menu size={18} />
        </button>

        {/* NÚCLEO ESTÁTICO (NO HACE SCROLL) */}
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

        {/* ZONA EXCLUSIVA DE SCROLL */}
        <div className="chat-terminal custom-scrollbar">
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
                  <ReactMarkdown components={{ code: BloqueDeCodigo }}>
                    {msg.texto}
                  </ReactMarkdown>
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
            ref={textareaRef}
            className="hud-input custom-scrollbar"
            placeholder="Ingresa texto..."
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              e.target.style.height = '42px';
              e.target.style.height = `${Math.min(e.target.scrollHeight, 100)}px`;
            }}
            readOnly={cargando}  // readOnly (no disabled): un textarea disabled no recibe eventos de arrastre
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

      {/* PANEL DERECHO (para controles extra / telemetría más adelante) */}
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

export default App