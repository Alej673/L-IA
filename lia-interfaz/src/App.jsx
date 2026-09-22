import React, { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Mic, Paperclip, Terminal, Cpu, Database, Upload, AlertTriangle, Activity, ShieldAlert } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import './App.css'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

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
function NucleoLIA({ estado }) {
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

  // --- TUS ESTADOS ORIGINALES INTACTOS ---
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

  // 2. Progresión de aburrimiento (Tu lógica exacta)
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

  // 4. Parpadeo
  useEffect(() => {
    if (subEstado === 'durmiendo') return;
    const ciclo = setInterval(() => {
      setParpadeo(true);
      setTimeout(() => setParpadeo(false), 140);
    }, Math.random() * 3500 + 2500);
    return () => clearInterval(ciclo);
  }, [subEstado]);

  // --- GEOMETRÍA FACIAL FUSIONADA (Tus Emociones + Mis Pensamientos) ---
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
    if (estadoReal === 'procesando_pregunta') return { width: '4px', height: '4px', borderRadius: '50%', scaleY: 1, rotate: 0, y: 1 }; // Boca pensativa "hmmm"

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
        {/* TUS ICONOS FLOTANTES DE EMOCIÓN (INTACTOS) */}
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
          {subEstado === 'durmiendo' ? 'SUSPENDIDA (REPOSO)' :
           subEstado === 'bostezo' ? 'MODO REPOSO...' :
           subEstado === 'molesta' ? 'ESPERANDO ÓRDENES...' :
           subEstado === 'impaciente' ? 'EN ESPERA' :
           pensando && FRASES_PENSAMIENTO[estadoReal]
             ? FRASES_PENSAMIENTO[estadoReal][rondaGesto % FRASES_PENSAMIENTO[estadoReal].length]
             : label}
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

  // CRÍTICO: Si no tiene saltos de línea y no tiene clase de lenguaje,
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
    // Solo vigila si L-IA está pensando (cualquier 'procesando_*') o escribiendo
    const piensaOEscribe = estadoLIA === 'escribiendo' || estadoLIA.startsWith('procesando');
    if (piensaOEscribe) {
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

    // 1. Estado por defecto (duda)
    let estadoTemporal = 'procesando_pregunta'; 
    const textoMinusculas = textoUsuario.toLowerCase();

    // Filtramos palabras clave para disparar las animaciones correctas
    if (textoMinusculas.includes('git') || textoMinusculas.includes('commit') || textoMinusculas.includes('ramas')) {
      estadoTemporal = 'procesando_git';
    } else if (textoMinusculas.includes('sistema') || textoMinusculas.includes('hardware') || textoMinusculas.includes('ram')) {
      estadoTemporal = 'procesando_sistema';
    } else if (textoMinusculas.includes('archivo') || textoMinusculas.includes('lee') || textoMinusculas.includes('revisa')) {
      estadoTemporal = 'procesando_doc';
    } else if (textoMinusculas.includes('?')) {
      estadoTemporal = 'procesando_pregunta';
    }

    setEstadoLIA(estadoTemporal);
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