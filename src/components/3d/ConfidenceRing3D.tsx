"use client";

import { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Text } from "@react-three/drei";
import * as THREE from "three";

interface ConfidenceRingProps {
  score: number; // 0-1
}

function Ring({ score }: ConfidenceRingProps) {
  const ringRef = useRef<THREE.Mesh>(null);

  // HSL: 0 (red) → 120 (green) mapped to score
  const color = useMemo(() => {
    const hue = score * 120;
    return new THREE.Color(`hsl(${hue}, 70%, 50%)`);
  }, [score]);

  const bgColor = useMemo(() => {
    return new THREE.Color("hsl(0, 0%, 20%)");
  }, []);

  useFrame((_, delta) => {
    if (ringRef.current) {
      ringRef.current.rotation.y += delta * 0.3;
    }
  });

  // Fill arc: score maps to arc length
  const arcLength = score * Math.PI * 2;

  return (
    <group ref={ringRef}>
      {/* Background ring (full) */}
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.8, 0.08, 16, 64]} />
        <meshBasicMaterial color={bgColor} opacity={0.3} transparent />
      </mesh>

      {/* Filled arc */}
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry
          args={[0.8, 0.1, 16, 64, arcLength]}
        />
        <meshBasicMaterial color={color} opacity={0.9} transparent />
      </mesh>

      {/* Center score text */}
      <Text
        fontSize={0.35}
        color={color.getStyle()}
        anchorX="center"
        anchorY="middle"
        font="/fonts/inter-medium.woff"
      >
        {Math.round(score * 100)}
      </Text>
    </group>
  );
}

export default function ConfidenceRing3D({ score }: ConfidenceRingProps) {
  return (
    <div className="h-[120px] w-[120px] select-none" aria-hidden="true">
      <Canvas
        camera={{ position: [0, 0, 2.2], fov: 45 }}
        dpr={[1, 1.5]}
        gl={{ antialias: true, alpha: true }}
        style={{ background: "transparent" }}
      >
        <Ring score={score} />
      </Canvas>
    </div>
  );
}
