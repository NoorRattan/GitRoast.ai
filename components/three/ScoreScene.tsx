"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import type { Scores } from "@/lib/api-client";
import { buildCardImageUrl } from "@/lib/api-client";

const orderedScores: Array<[keyof Scores, string, string]> = [
  ["profileStrength", "Profile", "#e2b766"],
  ["projectDepth", "Depth", "#69c5b8"],
  ["commitConsistency", "Cadence", "#f0786b"],
  ["techDiversity", "Stack", "#8ab4f8"],
  ["percentileBenchmark", "Rank", "#a3d977"]
];

/** Animated Three.js score field with a static card fallback for reduced motion. */
export default function ScoreScene({ scores, username, schemaVersion }: { scores: Scores; username: string; schemaVersion: number }): JSX.Element {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const reducedMotion = usePrefersReducedMotion();
  const imageUrl = buildCardImageUrl(username, schemaVersion);
  const signature = orderedScores.map(([key]) => scores[key]).join("-");

  useEffect(() => {
    if (reducedMotion) {
      return;
    }

    let frame = 0;
    let cleanup = () => undefined;
    let cancelled = false;

    async function renderScene() {
      const canvas = canvasRef.current;
      if (!canvas) {
        return;
      }

      const THREE = await import("three");
      if (cancelled) {
        return;
      }

      const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
      renderer.setClearColor(0x000000, 0);

      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
      camera.position.set(0, 0.45, 7.6);

      const group = new THREE.Group();
      scene.add(group);
      scene.add(new THREE.AmbientLight(0xffffff, 1.7));
      const keyLight = new THREE.DirectionalLight(0xffffff, 2.6);
      keyLight.position.set(3, 4, 5);
      scene.add(keyLight);

      const core = new THREE.Mesh(
        new THREE.IcosahedronGeometry(0.62, 2),
        new THREE.MeshStandardMaterial({ color: 0xe2b766, roughness: 0.38, metalness: 0.34 })
      );
      core.position.set(-2.45, 0, 0.42);
      group.add(core);

      const ring = new THREE.Mesh(
        new THREE.TorusGeometry(1.02, 0.035, 12, 72),
        new THREE.MeshStandardMaterial({ color: 0x69c5b8, emissive: 0x133c37, roughness: 0.42 })
      );
      ring.position.copy(core.position);
      ring.rotation.x = Math.PI / 2.7;
      group.add(ring);

      const bars = orderedScores.map(([key, , color], index) => {
        const score = Math.max(2, Math.min(100, scores[key]));
        const width = 0.35 + score / 24;
        const material = new THREE.MeshStandardMaterial({
          color,
          emissive: color,
          emissiveIntensity: 0.12,
          roughness: 0.5,
          metalness: 0.16
        });
        const mesh = new THREE.Mesh(new THREE.BoxGeometry(width, 0.2, 0.44), material);
        mesh.position.set(0.25 + width / 2, 1.55 - index * 0.78, (index % 2) * 0.2);
        group.add(mesh);
        return { mesh, score };
      });

      const resize = () => {
        const rect = canvas.getBoundingClientRect();
        const width = Math.max(1, rect.width);
        const height = Math.max(1, rect.height);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        renderer.setSize(width, height, false);
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
      };

      const animate = () => {
        const now = performance.now() / 1000;
        group.rotation.y = Math.sin(now * 0.38) * 0.17;
        group.rotation.x = Math.sin(now * 0.31) * 0.08;
        core.rotation.x += 0.012;
        core.rotation.y += 0.018;
        ring.rotation.z -= 0.014;
        bars.forEach(({ mesh, score }, index) => {
          mesh.position.z = Math.sin(now * 1.15 + index) * 0.08 + score / 450;
        });
        renderer.render(scene, camera);
        frame = window.requestAnimationFrame(animate);
      };

      resize();
      window.addEventListener("resize", resize);
      animate();

      cleanup = () => {
        window.cancelAnimationFrame(frame);
        window.removeEventListener("resize", resize);
        renderer.dispose();
        bars.forEach(({ mesh }) => {
          mesh.geometry.dispose();
          if (Array.isArray(mesh.material)) {
            mesh.material.forEach((material) => material.dispose());
          } else {
            mesh.material.dispose();
          }
        });
        core.geometry.dispose();
        ring.geometry.dispose();
      };
    }

    void renderScene();

    return () => {
      cancelled = true;
      cleanup();
    };
  }, [scores, reducedMotion]);

  if (reducedMotion) {
    return <FallbackImage username={username} imageUrl={imageUrl} />;
  }

  return (
    <section className="panel score-visual" aria-label="Animated 3D score visualization" data-testid="score-scene" data-score-signature={signature}>
      <canvas ref={canvasRef} data-testid="score-canvas" aria-hidden="true" />
      <div className="score-visual-overlay">
        <span className="score-visual-kicker">3D score field</span>
        <div className="score-visual-labels">
          {orderedScores.map(([key, label, color]) => (
            <div key={key}>
              <span>{label}</span>
              <strong style={{ color }}>{scores[key]}</strong>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function FallbackImage({ username, imageUrl }: { username: string; imageUrl: string }): JSX.Element {
  return (
    <section className="panel" data-testid="score-fallback" style={{ padding: 12 }}>
      <Image src={imageUrl} alt={`${username} static audit card`} width={1200} height={630} unoptimized style={{ width: "100%", height: "auto", borderRadius: 8 }} />
    </section>
  );
}

function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(media.matches);
    const listener = () => setReduced(media.matches);
    media.addEventListener("change", listener);
    return () => media.removeEventListener("change", listener);
  }, []);
  return reduced;
}
