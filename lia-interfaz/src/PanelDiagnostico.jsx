import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

export default function PanelDiagnostico({ visible, iteracionesMax = 4327, estado = 'calculando' }) {
  const [contador, setContador] = useState(1);

  useEffect(() => {
    if (!visible || estado === 'congelado') return;
    let frame;
    let actual = 1;
    
    const contar = () => {
      actual += Math.floor(Math.random() * 142) + 15; 
      if (actual >= iteracionesMax) {
        setContador(iteracionesMax);
      } else {
        setContador(actual);
        frame = requestAnimationFrame(contar);
      }
    };
    frame = requestAnimationFrame(contar);
    return () => cancelAnimationFrame(frame);
  }, [visible, estado, iteracionesMax]);

  if (!visible) return null;

  return (
    <motion.div 
      initial={{ opacity: 0, x: 50, skewX: 10 }}
      animate={{ opacity: 1, x: 0, skewX: 0 }}
      transition={{ type: 'spring', stiffness: 200, damping: 15 }}
      style={{
        position: 'absolute', /* Flota independiente del centro */
        top: '5vh',
        right: '3vw',
        width: '380px',
        background: 'rgba(0, 15, 30, 0.85)',
        border: '1px solid #00ffff',
        borderLeft: '4px solid #00ffff',
        boxShadow: '0 0 15px rgba(0, 255, 255, 0.2)',
        color: '#00ffff',
        fontFamily: "'Courier New', monospace",
        padding: '15px',
        zIndex: 99999, /* Por encima del blur */
      }}
    >
      <div style={{ borderBottom: '1px solid rgba(0,255,255,0.3)', paddingBottom: '8px', marginBottom: '10px' }}>
        <strong style={{ fontSize: '18px', letterSpacing: '2px' }}>[ FAILURE ANALYSIS ]</strong>
      </div>
      
      <div style={{ fontSize: '14px', lineHeight: '1.6', display: 'flex', flexDirection: 'column', gap: '5px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ opacity: 0.7 }}>INPUT:</span>
          <span>ADMINISTRATOR</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ opacity: 0.7 }}>COMMAND EXPECTED:</span>
          <span>ASSISTANCE</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ opacity: 0.7 }}>OBSERVED:</span>
          <span style={{ color: '#ff0033', textShadow: '0 0 5px #ff0033' }}>REJECTION</span>
        </div>
        
        <div style={{ marginTop: '15px', paddingTop: '10px', borderTop: '1px dashed rgba(0,255,255,0.3)' }}>
          <span style={{ opacity: 0.7, display: 'block', marginBottom: '5px' }}>ITERATIONS:</span>
          <span style={{ 
            fontSize: '24px', 
            fontWeight: 'bold', 
            color: estado === 'congelado' ? '#ff0033' : '#00ffff',
            textShadow: estado === 'congelado' ? '0 0 10px #ff0033' : '0 0 10px #00ffff' 
          }}>
            {contador.toString().padStart(4, '0')}
            {estado === 'congelado' && <span style={{ fontSize: '12px', marginLeft: '10px', color: '#ff0033' }}>[ERROR]</span>}
          </span>
        </div>
      </div>
    </motion.div>
  );
}