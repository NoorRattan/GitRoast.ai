import type { CardData, Fetcher } from "./types";

const CARD_DATA_TIMEOUT_MS = 1800;

export async function fetchCardData(username: string, backendBaseUrl: string, fetcher: Fetcher = fetch): Promise<CardData> {
  const response = await fetcher(`${backendBaseUrl.replace(/\/$/, "")}/card-data/${encodeURIComponent(username)}`, {
    signal: AbortSignal.timeout(CARD_DATA_TIMEOUT_MS),
    headers: { accept: "application/json" }
  });
  if (!response.ok) {
    throw new Error(`card-data failed with status ${response.status}`);
  }
  return parseCardData(await response.json());
}

export function parseCardData(value: unknown): CardData {
  if (!isRecord(value) || typeof value.username !== "string" || typeof value.schema_version !== "number") {
    throw new Error("invalid card-data payload");
  }
  const scores = value.scores;
  if (!isRecord(scores)) {
    throw new Error("invalid card-data scores");
  }
  return {
    username: value.username,
    schema_version: value.schema_version,
    percentile_benchmark: numberField(value, "percentile_benchmark"),
    percentile_sample_size: optionalNumberField(value, "percentile_sample_size", 0),
    percentile_cold_start: typeof value.percentile_cold_start === "boolean" ? value.percentile_cold_start : true,
    avatar_url: typeof value.avatar_url === "string" ? value.avatar_url : null,
    scores: {
      profile_strength: numberField(scores, "profile_strength"),
      project_depth: numberField(scores, "project_depth"),
      commit_consistency: numberField(scores, "commit_consistency"),
      tech_diversity: numberField(scores, "tech_diversity"),
      percentile_benchmark: numberField(scores, "percentile_benchmark")
    }
  };
}

function optionalNumberField(record: Record<string, unknown>, key: string, fallback: number): number {
  const value = record[key];
  return typeof value === "number" ? value : fallback;
}

function numberField(record: Record<string, unknown>, key: string): number {
  const value = record[key];
  if (typeof value !== "number") {
    throw new Error(`invalid numeric field: ${key}`);
  }
  return value;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
