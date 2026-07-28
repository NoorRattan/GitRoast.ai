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

const BAR_W = 0.74;
const BAR_D = 0.74;
const MAX_BAR_H = 4.2;
const SPACING = 1.44;

type HoveredBar = { index: number; screenX: number; screenY: number };

/** Animated Three.js vertical bar-chart score field. Freezes on one frame for reduced motion. */
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
  const reducedMotion = usePrefersReducedMotion();
  const orderedScores = percentileColdStart ? baseScores : [...baseScores, rankScore];
  const signature = orderedScores.map(([key]) => scores[key]).join("-");
  const [hoveredBar, setHoveredBar] = useState<HoveredBar | null>(null);
  const [webglFailed, setWebglFailed] = useState(false);

  useEffect(() => {
    let frame = 0;
    let cleanup = () => undefined as void;
    let cancelled = false;
    setWebglFailed(false);

    async function renderScene() {
      const canvas = canvasRef.current;
      if (!canvas) return;

      const THREE = await import("three");
      if (cancelled) return;

      function isDark(): boolean {
        return document.documentElement.getAttribute("data-theme") !== "light";
      }

      let renderer: import("three").WebGLRenderer;
      try {
        renderer = new THREE.WebGLRenderer({
          canvas,
          antialias: true,
          alpha: true,
          powerPreference: "high-performance",
          preserveDrawingBuffer: true
        });
      } catch {
        setWebglFailed(true);
        return;
      }
      renderer.setClearColor(0x000000, 0);
      renderer.shadowMap.enabled = true;

      const scene = new THREE.Scene();

      // Camera angled slightly downward to show vertical bars with depth.
      const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
      camera.position.set(0, 3.6, 10.2);
      camera.lookAt(0, 1.4, 0);

      const group = new THREE.Group();
      scene.add(group);

      // ── Lighting ──────────────────────────────────────────────────────────
      const ambientLight = new THREE.AmbientLight(0xffffff, isDark() ? 1.4 : 2.0);
      scene.add(ambientLight);

      const keyLight = new THREE.DirectionalLight(0xffffff, isDark() ? 2.8 : 2.0);
      keyLight.position.set(4, 8, 6);
      keyLight.castShadow = true;
      scene.add(keyLight);

      const fillLight = new THREE.DirectionalLight(0x8ab4f8, isDark() ? 0.6 : 0.3);
      fillLight.position.set(-5, 2, 3);
      scene.add(fillLight);

      // ── Decorative sphere + ring ───────────────────────────────────────────
      const core = new THREE.Mesh(
        new THREE.IcosahedronGeometry(0.58, 3),
        new THREE.MeshStandardMaterial({
          color: 0xe2b766,
          roughness: 0.3,
          metalness: 0.5,
          emissive: 0xe2b766,
          emissiveIntensity: 0.08
        })
      );
      core.position.set(-4.2, 0.72, -0.8);
      group.add(core);

      const ring = new THREE.Mesh(
        new THREE.TorusGeometry(0.96, 0.038, 14, 80),
        new THREE.MeshStandardMaterial({
          color: 0x69c5b8,
          emissive: 0x133c37,
          roughness: 0.38,
          metalness: 0.1
        })
      );
      ring.position.copy(core.position);
      ring.rotation.x = Math.PI / 2.6;
      group.add(ring);

      // ── Floor plane ────────────────────────────────────────────────────────
      const floorMat = new THREE.MeshStandardMaterial({
        color: isDark() ? 0x161a1e : 0xdedad4,
        roughness: 0.9,
        metalness: 0
      });
      const floor = new THREE.Mesh(new THREE.PlaneGeometry(16, 10), floorMat);
      floor.rotation.x = -Math.PI / 2;
      floor.position.y = -0.01;
      floor.receiveShadow = true;
      group.add(floor);

      // ── Vertical score bars ────────────────────────────────────────────────
      const totalW = (orderedScores.length - 1) * SPACING;

      const bars = orderedScores.map(([key, , color], index) => {
        const score = Math.max(4, Math.min(100, scores[key]));
        const barH = (score / 100) * MAX_BAR_H;
        const x = index * SPACING - totalW / 2;

        const material = new THREE.MeshStandardMaterial({
          color,
          emissive: color,
          emissiveIntensity: 0.14,
          roughness: 0.42,
          metalness: 0.22
        });

        // Geometry centered at origin — we control position.y to pin base at y=0.
        const mesh = new THREE.Mesh(
          new THREE.BoxGeometry(BAR_W, barH, BAR_D),
          material
        );
        mesh.position.set(x, 0, 0); // will be updated in animate
        mesh.scale.y = 0;           // starts invisible; entrance grows it upward
        mesh.castShadow = true;
        group.add(mesh);

        // Subtle shadow blob on floor
        const blobMat = new THREE.MeshBasicMaterial({
          color: 0x000000,
          transparent: true,
          opacity: isDark() ? 0.22 : 0.1
        });
        const blob = new THREE.Mesh(new THREE.CircleGeometry(BAR_W * 0.52, 20), blobMat);
        blob.rotation.x = -Math.PI / 2;
        blob.position.set(x, 0.001, 0);
        group.add(blob);

        return { mesh, score, barH, targetCenterY: barH / 2 };
      });

      // ── Raycasting ─────────────────────────────────────────────────────────
      const raycaster = new THREE.Raycaster();
      const pointer = new THREE.Vector2();
      const barMeshes = bars.map(({ mesh }) => mesh);

      let dragging = false;
      let dragMoved = false;
      let pointerX = 0;
      let pointerY = 0;
      let dragRotY = 0;
      let dragRotX = 0;
      let hoverRotY = 0;
      let hoverRotX = 0;
      const startedAt = performance.now();

      function updateHover(clientX: number, clientY: number): void {
        const cv = canvasRef.current;
        if (!cv) return;
        const rect = cv.getBoundingClientRect();
        pointer.x = ((clientX - rect.left) / rect.width) * 2 - 1;
        pointer.y = -((clientY - rect.top) / rect.height) * 2 + 1;
        raycaster.setFromCamera(pointer, camera);
        const hits = raycaster.intersectObjects(barMeshes);
        if (hits.length > 0) {
          const idx = barMeshes.findIndex((m) => m === hits[0].object);
          if (idx !== -1) {
            const pos = new THREE.Vector3();
            hits[0].object.getWorldPosition(pos);
            pos.project(camera);
            const r2 = cv.getBoundingClientRect();
            const sx = (pos.x * 0.5 + 0.5) * r2.width;
            const sy = (-pos.y * 0.5 + 0.5) * r2.height;
            // Highlight hovered bar
            barMeshes.forEach((m, i) => {
              (m.material as import("three").MeshStandardMaterial).emissiveIntensity =
                i === idx ? 0.44 : 0.14;
            });
            setHoveredBar({ index: idx, screenX: sx, screenY: sy });
            return;
          }
        }
        barMeshes.forEach((m) => {
          (m.material as import("three").MeshStandardMaterial).emissiveIntensity = 0.14;
        });
        setHoveredBar(null);
      }

      const onPointerDown = (e: PointerEvent) => {
        dragging = true;
        dragMoved = false;
        pointerX = e.clientX;
        pointerY = e.clientY;
        canvas.setPointerCapture(e.pointerId);
      };
      const onPointerMove = (e: PointerEvent) => {
        if (dragging) {
          const dx = e.clientX - pointerX;
          const dy = e.clientY - pointerY;
          if (Math.abs(dx) > 2 || Math.abs(dy) > 2) dragMoved = true;
          dragRotY += dx * 0.007;
          dragRotX += dy * 0.005;
          pointerX = e.clientX;
          pointerY = e.clientY;
          return;
        }
        const rect = canvas.getBoundingClientRect();
        hoverRotY = ((e.clientX - rect.left) / rect.width - 0.5) * 0.22;
        hoverRotX = ((e.clientY - rect.top) / rect.height - 0.5) * 0.1;
        updateHover(e.clientX, e.clientY);
      };
      const onPointerUp = (e: PointerEvent) => {
        dragging = false;
        if (canvas.hasPointerCapture(e.pointerId)) canvas.releasePointerCapture(e.pointerId);
        if (!dragMoved) updateHover(e.clientX, e.clientY);
      };
      const onPointerLeave = () => {
        if (!dragging) {
          hoverRotY = 0;
          hoverRotX = 0;
          barMeshes.forEach((m) => {
            (m.material as import("three").MeshStandardMaterial).emissiveIntensity = 0.14;
          });
          setHoveredBar(null);
        }
      };

      const resize = () => {
        const rect = canvas.getBoundingClientRect();
        const w = Math.max(1, rect.width);
        const h = Math.max(1, rect.height);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        renderer.setSize(w, h, false);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        if (reducedMotion) renderer.render(scene, camera);
      };

      function applyTheme(): void {
        const dark = isDark();
        ambientLight.intensity = dark ? 1.4 : 2.0;
        keyLight.intensity = dark ? 2.8 : 2.0;
        fillLight.intensity = dark ? 0.6 : 0.3;
        floorMat.color.set(dark ? 0x161a1e : 0xdedad4);
        if (reducedMotion) renderer.render(scene, camera);
      }

      const themeObserver = new MutationObserver(() => applyTheme());
      themeObserver.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ["data-theme"]
      });

      const resizeObserver = typeof ResizeObserver !== "undefined"
        ? new ResizeObserver(resize)
        : null;

      // ── Animation loop ─────────────────────────────────────────────────────
      const animate = () => {
        const now = performance.now() / 1000;
        const elapsed = performance.now() - startedAt;

        // Group gentle idle sway + drag/hover response
        group.rotation.y += (
          Math.sin(now * 0.3) * 0.06 + dragRotY + hoverRotY - group.rotation.y
        ) * 0.072;
        group.rotation.x += (
          Math.sin(now * 0.22) * 0.03 + dragRotX + hoverRotX - group.rotation.x
        ) * 0.072;

        // Sphere and ring spin
        core.rotation.x += 0.01;
        core.rotation.y += 0.016;
        ring.rotation.z -= 0.012;

        // Bars: entrance grow from bottom + idle float
        bars.forEach(({ mesh, barH, targetCenterY }, index) => {
          const stagger = index * 100;
          const t = Math.min(1, Math.max(0, (elapsed - stagger) / 560));
          // Cubic ease-out
          const entrance = 1 - Math.pow(1 - t, 3);

          mesh.scale.y = Math.max(0.001, entrance);
          // Pin base to y=0: center moves up proportionally to scale
          mesh.position.y = targetCenterY * entrance
            + Math.sin(now * 1.05 + index * 0.9) * 0.035 * entrance;

          // Subtle X/Z drift for liveliness
          mesh.position.z = Math.sin(now * 0.8 + index * 1.2) * 0.04;
        });

        renderer.render(scene, camera);
        frame = window.requestAnimationFrame(animate);
      };

      resize();
      resizeObserver?.observe(canvas);
      window.addEventListener("resize", resize);

      if (reducedMotion) {
        // Snap to full height immediately
        bars.forEach(({ mesh, targetCenterY }) => {
          mesh.scale.y = 1;
          mesh.position.y = targetCenterY;
        });
        renderer.render(scene, camera);
      } else {
        canvas.addEventListener("pointerdown", onPointerDown);
        canvas.addEventListener("pointermove", onPointerMove);
        canvas.addEventListener("pointerup", onPointerUp);
        canvas.addEventListener("pointercancel", onPointerUp);
        canvas.addEventListener("pointerleave", onPointerLeave);
        animate();
      }

      cleanup = () => {
        window.cancelAnimationFrame(frame);
        window.removeEventListener("resize", resize);
        resizeObserver?.disconnect();
        canvas.removeEventListener("pointerdown", onPointerDown);
        canvas.removeEventListener("pointermove", onPointerMove);
        canvas.removeEventListener("pointerup", onPointerUp);
        canvas.removeEventListener("pointercancel", onPointerUp);
        canvas.removeEventListener("pointerleave", onPointerLeave);
        themeObserver.disconnect();
        renderer.dispose();
        bars.forEach(({ mesh }) => {
          mesh.geometry.dispose();
          if (Array.isArray(mesh.material)) {
            mesh.material.forEach((m) => m.dispose());
          } else {
            mesh.material.dispose();
          }
        });
        core.geometry.dispose();
        (core.material as import("three").Material).dispose();
        ring.geometry.dispose();
        (ring.material as import("three").Material).dispose();
        floor.geometry.dispose();
        floorMat.dispose();
        setHoveredBar(null);
      };
    }

    void renderScene();
    return () => { cancelled = true; cleanup(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scores, reducedMotion, percentileColdStart]);

  // Build findings per bar for tooltip
  const findingsPerBar: Finding[][] = orderedScores.map(([key]) =>
    findings.filter(
      (f) =>
        key !== "percentileBenchmark" &&
        f.contributesTo === (key as Finding["contributesTo"])
    )
  );

  const ariaLabel = reducedMotion
    ? "Static 3D score bar chart"
    : "Animated 3D score bar chart. Drag to rotate; hover a bar to see scoring evidence.";

  return (
    <section
      className="panel score-visual"
      aria-label={ariaLabel}
      data-testid="score-scene"
      data-score-signature={signature}
      data-motion={reducedMotion ? "static" : "animated"}
      data-profile={username}
      data-schema-version={schemaVersion}
    >
      {webglFailed ? (
        <div className="score-visual-loading">
          <p className="muted" style={{ textAlign: "center", padding: "20px" }}>
            3D view unavailable — WebGL is not supported in this browser.
          </p>
        </div>
      ) : (
        <canvas ref={canvasRef} data-testid="score-canvas" aria-hidden="true" />
      )}

      <div className="score-visual-overlay">
        <span className="score-visual-kicker">
          3D score field
        </span>
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
  const style: React.CSSProperties = {
    left: Math.min(screenX + 14, 9999),
    top: Math.max(screenY - 130, 8),
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
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const listener = () => setReduced(mq.matches);
    mq.addEventListener("change", listener);
    return () => mq.removeEventListener("change", listener);
  }, []);
  return reduced;
}
