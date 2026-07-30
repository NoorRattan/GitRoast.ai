"use client";

import { Bloom, DepthOfField, EffectComposer } from "@react-three/postprocessing";
import { Environment, Float, Lightformer, Sparkles } from "@react-three/drei";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useRef } from "react";
import * as THREE from "three";

export default function AmbientSceneCanvas(): JSX.Element {
  return (
    <Canvas
      camera={{ position: [0, 0.4, 7], fov: 32 }}
      dpr={[1, 1.5]}
      gl={{ alpha: true, antialias: true, powerPreference: "high-performance" }}
      frameloop="always"
    >
      <SpatialField />
    </Canvas>
  );
}

function SpatialField(): JSX.Element {
  const group = useRef<THREE.Group>(null);
  const { pointer } = useThree();

  useFrame((state, delta) => {
    if (!group.current) return;
    group.current.rotation.y = THREE.MathUtils.damp(group.current.rotation.y, pointer.x * 0.12, 2, delta);
    group.current.rotation.x = THREE.MathUtils.damp(group.current.rotation.x, -pointer.y * 0.08, 2, delta);
  });

  return (
    <>
      <color attach="background" args={["#050708"]} />
      <ambientLight intensity={0.35} />
      <directionalLight position={[3, 4, 5]} intensity={2.4} color="#ffd27b" />
      <directionalLight position={[-4, 1, 2]} intensity={1.1} color="#64e6d0" />
      <Environment resolution={64} frames={1}>
        <Lightformer intensity={3} color="#ffb54b" position={[2, 3, 2]} scale={[4, 2, 1]} />
        <Lightformer intensity={2} color="#4dd9c4" position={[-3, 0, 1]} scale={[3, 2, 1]} />
      </Environment>
      <Float speed={0.7} rotationIntensity={0.12} floatIntensity={0.28}>
        <group ref={group}>
          <mesh castShadow position={[1.9, 0.42, 0]} rotation={[0.4, 0.2, -0.3]}>
            <icosahedronGeometry args={[0.82, 2]} />
            <meshPhysicalMaterial color="#d69a43" emissive="#3b1f0a" emissiveIntensity={0.7} metalness={0.72} roughness={0.22} clearcoat={0.8} />
          </mesh>
          <mesh position={[1.9, 0.42, -0.03]} rotation={[Math.PI / 2.5, 0.1, 0]}>
            <torusGeometry args={[1.16, 0.018, 12, 96]} />
            <meshBasicMaterial color="#66e2ce" transparent opacity={0.7} />
          </mesh>
          <mesh position={[-2.2, -0.68, -0.8]} rotation={[0.2, 0.5, 0.3]}>
            <octahedronGeometry args={[0.42, 0]} />
            <meshPhysicalMaterial color="#55cdb9" emissive="#0c3830" emissiveIntensity={0.7} metalness={0.55} roughness={0.28} />
          </mesh>
        </group>
      </Float>
      <Sparkles count={34} scale={[9, 5, 3]} size={1.8} speed={0.22} color="#a7efe0" opacity={0.36} />
      <EffectComposer multisampling={0}>
        <Bloom intensity={0.75} luminanceThreshold={0.8} luminanceSmoothing={0.3} mipmapBlur />
        <DepthOfField focusDistance={0.03} focalLength={0.03} bokehScale={2.2} height={480} />
      </EffectComposer>
    </>
  );
}
