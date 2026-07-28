"use client";

import { useEffect, useRef, useState } from "react";
import type { Finding, Scores } from "@/lib/api-client";

const baseScores: Array<[keyof Scores, string, string]> = [
  ["profileStrength", "Profile", "#e2b766"],
  ["projectDepth", "Depth", "#69c5b8"],
  ["commitConsistency", "Cadence", "#f0786b"],
  ["techDiversity", "Stack", "#8ab4f8"]
];
const rankScore: [keyof Scores, string, string] = ["percentileBenchmark", "Rank", "#a3d977"];

type HoveredBar = {
  index: number;
  screenX: number;
  screenY: number;
};

/** Animated Three.js score field that freezes on one frame for reduced motion. */
export default function ScoreScene({
  scores,
  username,
  schemaVersion,
  findings = [],
  percentileColdStart = false
}: {
  scores: Scores;
  username: string;
  schemaVersion: number;
  findings?: Finding[];
  percentileColdStart?: boolean;
}): JSX.Element {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const sectionRef = useRef<HTMLElement | null>(null);
  const reducedMotion = usePrefersReducedMotion();
  const orderedScores = percentileColdStart ? baseScores : [...baseScores, rankScore];
  const signature = orderedScores.map(([key]) => scores[key]).join("-");
  const [hoveredBar, setHoveredBar] = useState<HoveredBar | null>(null);

  useEffect(() => {
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

      // Determine initial theme from <html> data-theme attribute.
      function isDarkTheme(): boolean {
        return document.documentElement.getAttribute("data-theme") !== "light";
      }

      const renderer = new THREE.WebGLRenderer({
        canvas,
        antialias: true,
        alpha: true,
        preserveDrawingBuffer: true
      });
      renderer.setClearColor(0x000000, 0);

      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
      camera.position.set(0, 0.45, 7.6);

      const group = new THREE.Group();
      scene.add(group);

      const ambientLight = new THREE.AmbientLight(0xffffff, isDarkTheme() ? 1.7 : 2.2);
      scene.add(ambientLight);
      const keyLight = new THREE.DirectionalLight(0xffffff, isDarkTheme() ? 2.6 : 1.8);
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

      // Raycaster for hover detection.
      const raycaster = new THREE.Raycaster();
      const pointer = new THREE.Vector2();
      const barMeshes = bars.map(({ mesh }) => mesh);

      let dragging = false;
      let dragMoved = false;
      let pointerX = 0;
      let pointerY = 0;
      let dragRotationX = 0;
      let dragRotationY = 0;
      let hoverRotationX = 0;
      let hoverRotationY = 0;
      const startedAt = performance.now();

      function updateHover(clientX: number, clientY: number): void {
        // canvas is guaranteed non-null here (we checked at the start of renderScene),
        // but we re-assert for strict null checks.
        const currentCanvas = canvasRef.current;
        if (!currentCanvas) return;
        const rect = currentCanvas.getBoundingClientRect();
        pointer.x = ((clientX - rect.left) / rect.width) * 2 - 1;
        pointer.y = -((clientY - rect.top) / rect.height) * 2 + 1;
        raycaster.setFromCamera(pointer, camera);
        const intersects = raycaster.intersectObjects(barMeshes);
        if (intersects.length > 0) {
          const barIndex = barMeshes.findIndex((m) => m === intersects[0].object);
          if (barIndex !== -1) {
            // Project bar position to screen coordinates.
            const barPos = new THREE.Vector3();
            intersects[0].object.getWorldPosition(barPos);
            barPos.project(camera);
            const rect2 = currentCanvas.getBoundingClientRect();
            const sx = (barPos.x * 0.5 + 0.5) * rect2.width;
            const sy = (-barPos.y * 0.5 + 0.5) * rect2.height;
            setHoveredBar({ index: barIndex, screenX: sx, screenY: sy });
            return;
          }
        }
        setHoveredBar(null);
      }

      const pointerDown = (event: PointerEvent) => {
        dragging = true;
        dragMoved = false;
        pointerX = event.clientX;
        pointerY = event.clientY;
        canvas.setPointerCapture(event.pointerId);
      };
      const pointerMove = (event: PointerEvent) => {
        if (dragging) {
          const dx = event.clientX - pointerX;
          const dy = event.clientY - pointerY;
          if (Math.abs(dx) > 2 || Math.abs(dy) > 2) {
            dragMoved = true;
          }
          dragRotationY += dx * 0.008;
          dragRotationX += dy * 0.006;
          pointerX = event.clientX;
          pointerY = event.clientY;
          return;
        }
        const rect = canvas.getBoundingClientRect();
        hoverRotationY = ((event.clientX - rect.left) / rect.width - 0.5) * 0.18;
        hoverRotationX = ((event.clientY - rect.top) / rect.height - 0.5) * 0.12;
        updateHover(event.clientX, event.clientY);
      };
      const pointerUp = (event: PointerEvent) => {
        dragging = false;
        if (canvas.hasPointerCapture(event.pointerId)) {
          canvas.releasePointerCapture(event.pointerId);
        }
        // Tap without significant drag = hover reveal.
        if (!dragMoved) {
          updateHover(event.clientX, event.clientY);
        }
      };
      const pointerLeave = () => {
        if (!dragging) {
          hoverRotationX = 0;
          hoverRotationY = 0;
          setHoveredBar(null);
        }
      };

      const resize = () => {
        const rect = canvas.getBoundingClientRect();
        const width = Math.max(1, rect.width);
        const height = Math.max(1, rect.height);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        renderer.setSize(width, height, false);
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
        if (reducedMotion) {
          renderer.render(scene, camera);
        }
      };

      // Update lighting when theme changes.
      function applyTheme(): void {
        const dark = isDarkTheme();
        ambientLight.intensity = dark ? 1.7 : 2.2;
        keyLight.intensity = dark ? 2.6 : 1.8;
        if (reducedMotion) {
          renderer.render(scene, camera);
        }
      }

      const themeObserver = new MutationObserver(() => applyTheme());
      themeObserver.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ["data-theme"]
      });

      const animate = () => {
        const now = performance.now() / 1000;
        group.rotation.y += (
          Math.sin(now * 0.38) * 0.12 + dragRotationY + hoverRotationY - group.rotation.y
        ) * 0.08;
        group.rotation.x += (
          Math.sin(now * 0.31) * 0.06 + dragRotationX + hoverRotationX - group.rotation.x
        ) * 0.08;
        core.rotation.x += 0.012;
        core.rotation.y += 0.018;
        ring.rotation.z -= 0.014;
        bars.forEach(({ mesh, score }, index) => {
          const entrance = Math.min(1, Math.max(0.001, (performance.now() - startedAt - index * 90) / 520));
          mesh.scale.x = 1 - Math.pow(1 - entrance, 3);
          mesh.position.z = Math.sin(now * 1.15 + index) * 0.08 + score / 450;
        });
        renderer.render(scene, camera);
        frame = window.requestAnimationFrame(animate);
      };

      resize();
      window.addEventListener("resize", resize);
      if (reducedMotion) {
        renderer.render(scene, camera);
      } else {
        canvas.addEventListener("pointerdown", pointerDown);
        canvas.addEventListener("pointermove", pointerMove);
        canvas.addEventListener("pointerup", pointerUp);
        canvas.addEventListener("pointercancel", pointerUp);
        canvas.addEventListener("pointerleave", pointerLeave);
        animate();
      }

      cleanup = () => {
        window.cancelAnimationFrame(frame);
        window.removeEventListener("resize", resize);
        canvas.removeEventListener("pointerdown", pointerDown);
        canvas.removeEventListener("pointermove", pointerMove);
        canvas.removeEventListener("pointerup", pointerUp);
        canvas.removeEventListener("pointercancel", pointerUp);
        canvas.removeEventListener("pointerleave", pointerLeave);
        themeObserver.disconnect();
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
        setHoveredBar(null);
      };
    }

    void renderScene();

    return () => {
      cancelled = true;
      cleanup();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scores, reducedMotion, percentileColdStart]);

  // Build findings per score index for the tooltip.
  const findingsPerBar: Finding[][] = orderedScores.map(([key]) =>
    findings.filter(
      (f) => key !== "percentileBenchmark" && f.contributesTo === (key as Finding["contributesTo"])
    )
  );

  return (
    <section
      ref={sectionRef}
      className="panel score-visual"
      aria-label={reducedMotion ? "Static 3D score visualization" : "Animated 3D score visualization. Drag to rotate; hover bars to see scoring evidence."}
      data-testid="score-scene"
      data-score-signature={signature}
      data-motion={reducedMotion ? "static" : "animated"}
      data-profile={username}
      data-schema-version={schemaVersion}
    >
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
      {hoveredBar !== null && (
        <FindingsTooltip
          barIndex={hoveredBar.index}
          screenX={hoveredBar.screenX}
          screenY={hoveredBar.screenY}
          label={orderedScores[hoveredBar.index][1]}
          findings={findingsPerBar[hoveredBar.index]}
        />
      )}
    </section>
  );
}

function FindingsTooltip({
  barIndex,
  screenX,
  screenY,
  label,
  findings
}: {
  barIndex: number;
  screenX: number;
  screenY: number;
  label: string;
  findings: Finding[];
}): JSX.Element {
  // Offset the tooltip above and slightly to the right of the bar.
  const style: React.CSSProperties = {
    left: Math.min(screenX + 12, 9999),
    top: Math.max(screenY - 120, 8),
    opacity: 1
  };

  return (
    <div
      className="scene-findings-tooltip"
      style={style}
      role="tooltip"
      id={`bar-tooltip-${barIndex}`}
      aria-live="polite"
    >
      <p className="scene-findings-tooltip-label">{label} — evidence</p>
      {findings.length > 0 ? (
        <ul>
          {findings.map((f) => (
            <li key={f.metric}>{f.detail}</li>
          ))}
        </ul>
      ) : (
        <p className="scene-findings-tooltip-empty">No specific signals for this score.</p>
      )}
    </div>
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
