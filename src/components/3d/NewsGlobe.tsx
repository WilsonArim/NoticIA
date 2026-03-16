"use client";

import { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Sphere, Line } from "@react-three/drei";
import * as THREE from "three";

// Map of approximate lat/lng to 3D sphere coordinates
const CITY_COORDS: Array<{ name: string; lat: number; lng: number }> = [
  { name: "Lisboa", lat: 38.7, lng: -9.1 },
  { name: "Londres", lat: 51.5, lng: -0.1 },
  { name: "Bruxelas", lat: 50.8, lng: 4.4 },
  { name: "Washington", lat: 38.9, lng: -77.0 },
  { name: "Moscovo", lat: 55.8, lng: 37.6 },
  { name: "Pequim", lat: 39.9, lng: 116.4 },
  { name: "Tóquio", lat: 35.7, lng: 139.7 },
  { name: "Brasília", lat: -15.8, lng: -47.9 },
  { name: "Nova Deli", lat: 28.6, lng: 77.2 },
  { name: "Cairo", lat: 30.0, lng: 31.2 },
  { name: "Nairobi", lat: -1.3, lng: 36.8 },
  { name: "Sydney", lat: -33.9, lng: 151.2 },
  { name: "Berlim", lat: 52.5, lng: 13.4 },
  { name: "Paris", lat: 48.9, lng: 2.3 },
  { name: "Genebra", lat: 46.2, lng: 6.1 },
  { name: "Kiev", lat: 50.4, lng: 30.5 },
  { name: "Seul", lat: 37.6, lng: 127.0 },
  { name: "Riade", lat: 24.7, lng: 46.7 },
  { name: "Cidade do México", lat: 19.4, lng: -99.1 },
  { name: "Buenos Aires", lat: -34.6, lng: -58.4 },
];

function latLngToVec3(lat: number, lng: number, radius: number): THREE.Vector3 {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lng + 180) * (Math.PI / 180);
  return new THREE.Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta),
  );
}

function WireframeGlobe() {
  const groupRef = useRef<THREE.Group>(null);

  useFrame((_, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.08;
    }
  });

  const dots = useMemo(
    () =>
      CITY_COORDS.map((city) => ({
        ...city,
        position: latLngToVec3(city.lat, city.lng, 1.02),
      })),
    [],
  );

  // Generate wireframe lines (latitude and longitude circles)
  const wireframeLines = useMemo(() => {
    const lines: THREE.Vector3[][] = [];
    // Longitude lines
    for (let lng = -180; lng < 180; lng += 30) {
      const points: THREE.Vector3[] = [];
      for (let lat = -90; lat <= 90; lat += 5) {
        points.push(latLngToVec3(lat, lng, 1));
      }
      lines.push(points);
    }
    // Latitude lines
    for (let lat = -60; lat <= 60; lat += 30) {
      const points: THREE.Vector3[] = [];
      for (let lng = -180; lng <= 180; lng += 5) {
        points.push(latLngToVec3(lat, lng, 1));
      }
      lines.push(points);
    }
    return lines;
  }, []);

  return (
    <group ref={groupRef}>
      {/* Wireframe sphere */}
      {wireframeLines.map((points, i) => (
        <Line
          key={i}
          points={points}
          color="#22c55e"
          lineWidth={0.5}
          opacity={0.15}
          transparent
        />
      ))}

      {/* News dots */}
      {dots.map((dot) => (
        <Sphere key={dot.name} args={[0.02, 8, 8]} position={dot.position}>
          <meshBasicMaterial color="#22c55e" opacity={0.7} transparent />
        </Sphere>
      ))}
    </group>
  );
}

export default function NewsGlobe() {
  return (
    <div className="h-[280px] w-full select-none" aria-hidden="true">
      <Canvas
        camera={{ position: [0, 0, 2.5], fov: 45 }}
        dpr={[1, 1.5]}
        gl={{ antialias: true, alpha: true }}
        style={{ background: "transparent" }}
      >
        <ambientLight intensity={0.3} />
        <WireframeGlobe />
      </Canvas>
    </div>
  );
}
