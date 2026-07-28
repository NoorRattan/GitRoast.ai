import { Resvg, initWasm, type InitInput } from "@resvg/resvg-wasm";
import satori from "satori";
import { loadFonts } from "./fonts";
import type { CardData } from "./types";

export const CARD_WIDTH = 1200;
export const CARD_HEIGHT = 630;

let resvgInitPromise: Promise<void> | null = null;

export function cohortRankCopy(data: Pick<CardData, "percentile_benchmark" | "percentile_sample_size" | "percentile_cold_start">): {
  value: string | number;
  detail: string;
  fontSize: number;
} {
  if (data.percentile_cold_start) {
    return {
      value: "Not enough data",
      detail: "more comparable profiles needed",
      fontSize: 36
    };
  }
  return {
    value: data.percentile_benchmark,
    detail: `among ${data.percentile_sample_size} peers`,
    fontSize: 72
  };
}

export async function renderSvg(data: CardData, avatarDataUri: string): Promise<string> {
  const rankCopy = cohortRankCopy(data);

  return satori(
    <div
      style={{
        width: `${CARD_WIDTH}px`,
        height: `${CARD_HEIGHT}px`,
        display: "flex",
        flexDirection: "column",
        background: "#101111",
        color: "#f4f1ea",
        fontFamily: "Inter",
        padding: "52px",
        border: "1px solid #38342d"
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "24px" }}>
          <img src={avatarDataUri} width={112} height={112} style={{ borderRadius: "56px" }} />
          <div style={{ display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", fontSize: 48, fontWeight: 700 }}>{data.username}</div>
            <div style={{ display: "flex", fontSize: 24, color: "#b9b2a6" }}>GitRoast.ai audit card</div>
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end" }}>
          <div style={{ display: "flex", fontSize: rankCopy.fontSize, fontWeight: 800, color: "#e2b766" }}>
            {rankCopy.value}
          </div>
          <div style={{ display: "flex", fontSize: 22, color: "#b9b2a6" }}>
            {rankCopy.detail}
          </div>
        </div>
      </div>
      <div style={{ display: "flex", gap: "18px", marginTop: "54px" }}>
        <ScorePill label="Profile" value={data.scores.profile_strength} color="#e2b766" />
        <ScorePill label="Depth" value={data.scores.project_depth} color="#69c5b8" />
        <ScorePill label="Cadence" value={data.scores.commit_consistency} color="#f0786b" />
        <ScorePill label="Stack" value={data.scores.tech_diversity} color="#8ab4f8" />
      </div>
      <div style={{ display: "flex", marginTop: "54px", fontSize: 28, color: "#f4f1ea" }}>
        {`Rule-based profile audit, version ${data.schema_version}. Built for share previews at 1200x630.`}
      </div>
    </div>,
    {
      width: CARD_WIDTH,
      height: CARD_HEIGHT,
      fonts: loadFonts()
    }
  );
}

export async function rasterizeSvg(svg: string): Promise<Uint8Array> {
  await ensureResvgWasm();
  const renderer = new Resvg(svg, {
    fitTo: { mode: "width", value: CARD_WIDTH },
    background: "#101111"
  });
  try {
    return renderer.render().asPng();
  } finally {
    renderer.free();
  }
}

export async function ensureResvgWasm(input?: InitInput): Promise<void> {
  resvgInitPromise ??= initWasm(input ?? await loadBundledWasm());
  await resvgInitPromise;
}

async function loadBundledWasm(): Promise<InitInput> {
  const wasm = await import("@resvg/resvg-wasm/index_bg.wasm");
  return (wasm.default ?? wasm) as InitInput;
}

function ScorePill({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div
      style={{
        width: "250px",
        height: "155px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        padding: "22px",
        borderRadius: "18px",
        background: "#181a1b",
        border: "1px solid #38342d"
      }}
    >
      <div style={{ display: "flex", fontSize: 25, color: "#b9b2a6" }}>{label}</div>
      <div style={{ display: "flex", fontSize: 56, fontWeight: 800, color }}>{value}</div>
    </div>
  );
}
