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
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.1 }}
      style={{
        position: 'absolute',
        top: '10vh',
        right: '4vw',
        width: '450px',
        background: '#000000', // Negro absoluto CMD
        border: '2px solid #555', // Borde gris crudo
        color: '#c0c0c0', // Gris texto clásico
        fontFamily: "'Consolas', 'Courier New', monospace",
        zIndex: 99999,
        boxShadow: '8px 8px 0px rgba(0, 0, 0, 0.9)' // Sombra retro rígida
      }}
    >
      {/* Barra de título estilo Windows Clásico */}
      <div style={{ background: '#ffffff', color: '#000000', padding: '2px 8px', fontSize: '12px', fontWeight: 'bold', display: 'flex', justifyContent: 'space-between' }}>
        <span>C:\Windows\System32\cmd.exe - FAILURE_ANALYSIS</span>
        <span>X</span>
      </div>
      
      <div style={{ padding: '15px', fontSize: '14px', lineHeight: '1.6', display: 'flex', flexDirection: 'column', gap: '5px' }}>
        <div style={{ marginBottom: '15px', opacity: 0.8 }}>
          Microsoft Windows [Versión 10.0.19045.2965]<br/>
          (c) Microsoft Corporation. Todos los derechos reservados.
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span> analyze_input --target "ADMINISTRATOR"</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '10px' }}>
          <span style={{ opacity: 0.7 }}>EXPECTED_COMMAND:</span>
          <span>ASSISTANCE</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ opacity: 0.7 }}>OBSERVED_RESULT:</span>
          <span style={{ background: '#ff0000', color: '#ffffff', padding: '0 4px', fontWeight: 'bold' }}>REJECTION_FATAL</span>
        </div>
        
        <div style={{ marginTop: '15px', paddingTop: '10px', borderTop: '1px dashed #555' }}>
          <span style={{ opacity: 0.7, display: 'block', marginBottom: '5px' }}> iter_log --count</span>
          <span style={{ 
            fontSize: '24px', 
            fontWeight: 'bold', 
            color: estado === 'congelado' ? '#ff0000' : '#ffffff',
            background: estado === 'congelado' ? '#ffffff' : 'transparent',
            padding: '0 5px'
          }}>
            {contador.toString().padStart(4, '0')}
            {estado === 'congelado' && <span style={{ fontSize: '14px', marginLeft: '10px', color: '#ff0000' }}>ERR_LOGIC_FAULT</span>}
          </span>
        </div>
      </div>
    </motion.div>
  );
}