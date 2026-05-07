import { useMemo } from 'react'
import { Canvas } from '@react-three/fiber'
import { Environment } from '@react-three/drei'
import * as THREE from 'three'

// SVG viewBox 200x280, center (100,140).
// Three.js: x = (svgX - 100) / 100 * 1.2,  y = -(svgY - 140) / 140 * 1.2
// (flip Y because SVG y-down, Three.js y-up)

const EXTRUDE = {
  depth: 0.18,
  bevelEnabled: true,
  bevelThickness: 0.055,
  bevelSize: 0.042,
  bevelSegments: 8,
}

function buildTopBlade() {
  // M 130 12 C 138 60, 132 96, 96 132 L 86 138 C 122 102, 128 64, 122 18 Z
  const s = new THREE.Shape()
  s.moveTo(0.36, 1.097)
  s.bezierCurveTo(0.456, 0.686, 0.384, 0.377, -0.048, 0.069)
  s.lineTo(-0.168, 0.017)
  s.bezierCurveTo(0.264, 0.326, 0.336, 0.651, 0.264, 1.04)
  s.closePath()
  return new THREE.ExtrudeGeometry(s, EXTRUDE)
}

function buildBotBlade() {
  // M 70 268 C 62 220, 68 184, 104 148 L 114 142 C 78 178, 72 216, 78 262 Z
  const s = new THREE.Shape()
  s.moveTo(-0.36, -1.097)
  s.bezierCurveTo(-0.456, -0.686, -0.384, -0.377, 0.048, -0.069)
  s.lineTo(0.168, -0.017)
  s.bezierCurveTo(-0.264, -0.326, -0.336, -0.651, -0.264, -1.04)
  s.closePath()
  return new THREE.ExtrudeGeometry(s, EXTRUDE)
}

function Scene() {
  const topGeo = useMemo(buildTopBlade, [])
  const botGeo = useMemo(buildBotBlade, [])

  const mat = useMemo(() => new THREE.MeshPhysicalMaterial({
    color: new THREE.Color('#C8A86A'),
    metalness: 1.0,
    roughness: 0.14,
    reflectivity: 1.0,
    envMapIntensity: 2.2,
  }), [])

  return (
    <>
      <Environment preset="studio" />
      <directionalLight position={[2, 5, 4]}  intensity={5}   color="#FFFFFF" />
      <directionalLight position={[-3, -4, 2]} intensity={1.5} color="#B89464" />
      <ambientLight intensity={0.06} />
      {/* top blade in front at top, bot blade in front at bottom */}
      <mesh geometry={topGeo} material={mat} position={[0, 0, 0.02]} />
      <mesh geometry={botGeo} material={mat} position={[0, 0, 0]}    />
    </>
  )
}

export function SonderMark3D({ size = 80 }) {
  const w = Math.round(size * (200 / 280))
  return (
    <div style={{ width: w, height: size, flexShrink: 0 }}>
      <Canvas
        style={{ width: '100%', height: '100%' }}
        camera={{ position: [0, 0, 3.4], fov: 36 }}
        frameloop="demand"
        gl={{ antialias: true, alpha: true }}
      >
        <Scene />
      </Canvas>
    </div>
  )
}

// Full horizontal lockup: 3D mark + wordmark + tagline as HTML
export function SonderNav3D({ markSize = 56 }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <SonderMark3D size={markSize} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
        <span style={{
          fontFamily: '"Cormorant Garamond", serif',
          fontWeight: 400,
          fontSize: markSize * 0.38,
          letterSpacing: '0.42em',
          textIndent: '0.42em',
          lineHeight: 1,
          background: 'linear-gradient(180deg, #F0DCB0 0%, #E8D4A8 35%, #D4B686 55%, #B89464 80%, #8A6F4A 100%)',
          WebkitBackgroundClip: 'text',
          backgroundClip: 'text',
          color: 'transparent',
          display: 'inline-block',
        }}>
          SONDER
        </span>
        <span style={{
          fontFamily: '"Inter Tight", sans-serif',
          fontWeight: 300,
          fontSize: markSize * 0.12,
          letterSpacing: '0.42em',
          textIndent: '0.42em',
          textTransform: 'uppercase',
          color: 'rgba(244, 237, 224, 0.45)',
          display: 'inline-block',
        }}>
          TRAVEL, TOGETHER
        </span>
      </div>
    </div>
  )
}
