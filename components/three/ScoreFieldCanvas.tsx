"use client";

import { Bloom, DepthOfField, EffectComposer } from "@react-three/postprocessing";
import { Environment, Float, Lightformer, RoundedBox, Sparkles } from "@react-three/drei";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useMemo, useRef, useState } from "react";
import type { Finding, Scores } from "@/lib/api-client";
import * as THREE from "three";

type ScoreTuple = [keyof Scores, string, string];

export default function ScoreFieldCanvas({
  scores,
  orderedScores,
  findingsPerBar,
  reducedMotion
}: {
  scores: Scores;
  orderedScores: ScoreTuple[];
  findingsPerBar: Finding[][];
  reducedMotion: boolean;
}): JSX.Element {
  return (
    <Canvas
      shadows
      camera={{ position: [0, 3.3, 9.6], fov: 34 }}
      dpr={[1, 1.5]}
      gl={{ alpha: true, antialias: true, powerPreference: "high-performance" }}
      frameloop={reducedMotion ? "demand" : "always"}
      onCreated={({ gl }) => {
        gl.shadowMap.enabled = true;
        gl.shadowMap.type = THREE.PCFSoftShadowMap;
      }}
    >
      <ScoreFieldContent scores={scores} orderedScores={orderedScores} findingsPerBar={findingsPerBar} reducedMotion={reducedMotion} />
    </Canvas>
  );
}

function ScoreFieldContent({
  scores,
  orderedScores,
  findingsPerBar,
  reducedMotion
}: {
  scores: Scores;
  orderedScores: ScoreTuple[];
  findingsPerBar: Finding[][];
  reducedMotion: boolean;
}): JSX.Element {
  const [hovered, setHovered] = useState<number | null>(null);
  const group = useRef<THREE.Group>(null);
  const { pointer } = useThree();
  const totalWidth = (orderedScores.length - 1) * 1.45;

  useFrame((_, delta) => {
    if (!group.current || reducedMotion) return;
    group.current.rotation.y = THREE.MathUtils.damp(group.current.rotation.y, pointer.x * 0.16, 2.5, delta);
    group.current.rotation.x = THREE.MathUtils.damp(group.current.rotation.x, -pointer.y * 0.06, 2.5, delta);
  });

  return (
    <>
      <color attach="background" args={["#080b0c"]} />
      <ambientLight intensity={0.32} />
      <directionalLight castShadow position={[4, 7, 5]} intensity={3} color="#ffe0a7" shadow-mapSize={[1024, 1024]} />
      <directionalLight position={[-5, 2, 2]} intensity={1.2} color="#59d8c0" />
      <Environment resolution={64} frames={1}>
        <Lightformer intensity={3.2} color="#f1ab52" position={[3, 5, 3]} scale={[4, 2, 1]} />
        <Lightformer intensity={2} color="#53d5c0" position={[-4, 1, 2]} scale={[2, 3, 1]} />
      </Environment>
      <group ref={group}>
        {orderedScores.map(([key, label, color], index) => (
          <ScoreBar
            key={key}
            index={index}
            label={label}
            color={color}
            score={scores[key]}
            x={index * 1.45 - totalWidth / 2}
            highlighted={hovered === index}
            onHover={() => setHovered(index)}
            onLeave={() => setHovered(null)}
          />
        ))}
        <mesh position={[-3.6, 0.45, -0.8]} rotation={[0.4, 0.3, 0.1]}>
          <icosahedronGeometry args={[0.48, 2]} />
          <meshPhysicalMaterial color="#d69a43" emissive="#57240a" emissiveIntensity={0.68} metalness={0.72} roughness={0.23} clearcoat={0.85} />
        </mesh>
        <mesh position={[-3.6, 0.45, -0.84]} rotation={[Math.PI / 2.4, 0.1, 0]}>
          <torusGeometry args={[0.73, 0.02, 12, 72]} />
          <meshBasicMaterial color="#66e2ce" transparent opacity={0.7} />
        </mesh>
      </group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.02, 0]} receiveShadow>
        <planeGeometry args={[13, 8]} />
        <meshStandardMaterial color="#0b1112" roughness={0.95} metalness={0.02} />
      </mesh>
      <Sparkles count={28} scale={[8, 4, 3]} size={1.6} speed={reducedMotion ? 0 : 0.25} color="#a1eee1" opacity={0.42} />
      {hovered !== null && findingsPerBar[hovered].length > 0 ? <HoverEcho color={orderedScores[hovered][2]} /> : null}
      <EffectComposer multisampling={0}>
        <Bloom intensity={0.74} luminanceThreshold={0.86} luminanceSmoothing={0.32} mipmapBlur />
        <DepthOfField focusDistance={0.02} focalLength={0.035} bokehScale={1.8} height={420} />
      </EffectComposer>
    </>
  );
}

function ScoreBar({
  index,
  label,
  color,
  score,
  x,
  highlighted,
  onHover,
  onLeave
}: {
  index: number;
  label: string;
  color: string;
  score: number;
  x: number;
  highlighted: boolean;
  onHover: () => void;
  onLeave: () => void;
}): JSX.Element {
  const group = useRef<THREE.Group>(null);
  const height = 0.35 + (Math.max(0, Math.min(100, score)) / 100) * 3.8;
  const material = useMemo(() => ({ color, emissive: color }), [color]);

  useFrame((state, delta) => {
    if (!group.current) return;
    const target = highlighted ? 1.06 : 1;
    group.current.scale.x = THREE.MathUtils.damp(group.current.scale.x, target, 8, delta);
    group.current.scale.z = THREE.MathUtils.damp(group.current.scale.z, target, 8, delta);
    group.current.position.y = THREE.MathUtils.damp(group.current.position.y, Math.sin(state.clock.elapsedTime * 0.8 + index) * 0.04, 5, delta);
  });

  return (
    <group ref={group} position={[x, 0, 0]} onPointerOver={(event) => { event.stopPropagation(); onHover(); }} onPointerOut={onLeave}>
      <RoundedBox args={[0.82, height, 0.82]} radius={0.11} smoothness={5} position={[0, height / 2, 0]} castShadow>
        <meshPhysicalMaterial {...material} emissiveIntensity={highlighted ? 0.44 : 0.14} metalness={0.48} roughness={0.3} clearcoat={0.55} />
      </RoundedBox>
      <mesh position={[0, 0.012, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[0.36, 20]} />
        <meshBasicMaterial color="#000000" transparent opacity={0.26} />
      </mesh>
      <mesh position={[0, height + 0.05, 0]}>
        <sphereGeometry args={[0.065, 12, 12]} />
        <meshBasicMaterial color={color} transparent opacity={0.85} />
      </mesh>
    </group>
  );
}

function HoverEcho({ color }: { color: string }): JSX.Element {
  return (
    <Float speed={2.4} floatIntensity={0.25} rotationIntensity={0.15}>
      <mesh position={[0, 2.7, 0.5]}>
        <torusGeometry args={[0.56, 0.012, 8, 64]} />
        <meshBasicMaterial color={color} transparent opacity={0.48} />
      </mesh>
    </Float>
  );
}
