// Herramienta de desarrollo: renderiza TODAS las caras para afinarlas a ojo.
import React, { useState } from 'react'
import { NucleoColapso, EXPRESIONES, ACTORES } from './ColapsoSistema'
import './App.css'

export default function GaleriaExpresiones() {
  const [actor, setActor] = useState('nucleo')
  const [hablando, setHablando] = useState(false)
  const [zoom, setZoom] = useState(2)

  return (
    <div style={{ background: '#05080c', color: '#fff', minHeight: '100vh', padding: 16 }}>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', marginBottom: 16 }}>
        {Object.keys(ACTORES).map(a => (
          <button key={a} onClick={() => setActor(a)} style={{ opacity: a === actor ? 1 : 0.5 }}>{a}</button>
        ))}
        <button onClick={() => setHablando(h => !h)}>{hablando ? 'callar' : 'hablar'}</button>
        <label style={{ marginLeft: 12 }}>
          zoom {zoom}x{' '}
          <input type="range" min="2" max="10" step="1" value={zoom} onChange={e => setZoom(+e.target.value)} />
        </label>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 8 }}>
        {Object.keys(EXPRESIONES).map(e => (
          <div key={e} style={{ height: 260, position: 'relative', border: '1px solid #123', overflow: 'hidden' }}>
            <div style={{ position: 'absolute', top: 6, left: 8, fontSize: 13, opacity: 0.9, zIndex: 2 }}>{e}</div>
            <div
              className="overlay-colapso"
              style={{
                position: 'absolute', inset: 0, width: '100%', height: '100%',
                background: 'transparent', boxShadow: 'none', padding: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                transform: `scale(${zoom})`, transformOrigin: 'center center',
              }}
            >
              <NucleoColapso actor={actor} expresion={e} hablando={hablando} etiqueta={false} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}