export type RoastIntensity = "mild" | "medium" | "brutal" | "hell";
export type ReviewStatus = "pending" | "approved" | "rejected";

export type Scores = {
  profileStrength: number;
  projectDepth: number;
  commitConsistency: number;
  techDiversity: number;
  percentileBenchmark: number;
};

export type Finding = {
  metric: string;
  detail: string;
  value: number;
  contributesTo: keyof Omit<Scores, "percentileBenchmark">;
};

export type AuditResult = {
  username: string;
  generatedAt: string;
  schemaVersion: number;
  cacheHit: boolean;
  roastIntensityRequested: RoastIntensity;
  roastIntensityApplied: RoastIntensity;
  intensityDowngraded: boolean;
  scores: Scores;
  flags: {
    greenSquareFarming: boolean;
    beginnerAccount: boolean;
  };
  findings: Finding[];
  roastText: string;
  strengths: string[];
  improvementAreas: string[];
  roadmap: Array<{ week: number; focus: string; actions: string[] }>;
};

export type CardData = {
  username: string;
  schemaVersion: number;
  percentileBenchmark: number;
  scores: Scores;
  avatarUrl: string | null;
};

export type AdminReview = {
  id: number;
  auditId: number;
  generatedContent: Pick<AuditResult, "roastText" | "strengths" | "improvementAreas" | "roadmap">;
  reviewStatus: ReviewStatus;
  reason: string | null;
  createdAt: string;
};

export type AdminCredentials = {
  username: string;
  password: string;
};

const SERVER_API_BASE_URL = "https://gitroast-ai.onrender.com/api/v1";
const CLIENT_API_BASE_URL = "/api/v1";
const CARD_BASE_URL = process.env.NEXT_PUBLIC_CARD_BASE_URL ?? "https://gitroast-card-preview.jnoorrattan.workers.dev/card";

type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string
  ) {
    super(message);
  }
}

/** Builds the Session 5 card-worker URL shape without hardcoding schema_version. */
export function buildCardImageUrl(username: string, schemaVersion: number): string {
  return `${CARD_BASE_URL}/${encodeURIComponent(username)}.png?v=${schemaVersion}`;
}

/** Converts backend snake_case payloads to frontend camelCase. */
export function snakeToCamel<T>(value: JsonValue): T {
  if (Array.isArray(value)) {
    return value.map((item) => snakeToCamel<JsonValue>(item)) as T;
  }
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, child]) => [key.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase()), snakeToCamel<JsonValue>(child)])
    ) as T;
  }
  return value as T;
}

/** Converts frontend camelCase request bodies to backend snake_case. */
export function camelToSnake<T>(value: JsonValue): T {
  if (Array.isArray(value)) {
    return value.map((item) => camelToSnake<JsonValue>(item)) as T;
  }
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, child]) => [key.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`), camelToSnake<JsonValue>(child)])
    ) as T;
  }
  return value as T;
}

export async function fetchCachedAudit(username: string): Promise<AuditResult | null> {
  try {
    return await apiFetch<AuditResult>(`/audit/${encodeURIComponent(username)}`, { method: "GET", cache: "no-store" });
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export async function requestAudit(username: string, roastIntensity: RoastIntensity): Promise<AuditResult> {
  return apiFetch<AuditResult>("/audit", {
    method: "POST",
    body: JSON.stringify(camelToSnake({ username, roastIntensity })),
    headers: { "content-type": "application/json" }
  });
}

export async function fetchCardData(username: string): Promise<CardData | null> {
  try {
    return await apiFetch<CardData>(`/card-data/${encodeURIComponent(username)}`, { method: "GET", cache: "no-store" });
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export async function optOut(username: string): Promise<void> {
  await apiFetch<{ status: string }>("/opt-out", {
    method: "POST",
    body: JSON.stringify(camelToSnake({ username })),
    headers: { "content-type": "application/json" }
  });
}

export async function undoOptOut(username: string): Promise<void> {
  await apiFetch<{ status: string }>(`/opt-out/${encodeURIComponent(username)}`, { method: "DELETE" });
}

export async function fetchAdminReviews(credentials: AdminCredentials, status: ReviewStatus = "pending"): Promise<AdminReview[]> {
  const response = await apiFetch<{ reviews: AdminReview[] }>(`/admin/reviews?status=${status}`, {
    method: "GET",
    headers: adminHeaders(credentials)
  });
  return response.reviews;
}

export async function approveReview(credentials: AdminCredentials, id: number): Promise<void> {
  await apiFetch(`/admin/reviews/${id}/approve`, { method: "POST", headers: adminHeaders(credentials) });
}

export async function rejectReview(credentials: AdminCredentials, id: number, reason: string): Promise<void> {
  await apiFetch(`/admin/reviews/${id}/reject`, {
    method: "POST",
    headers: { ...adminHeaders(credentials), "content-type": "application/json" },
    body: JSON.stringify(camelToSnake({ reason }))
  });
}

function adminHeaders(credentials: AdminCredentials): Record<string, string> {
  return { authorization: `Basic ${encodeBasic(`${credentials.username}:${credentials.password}`)}` };
}

function encodeBasic(value: string): string {
  if (typeof window === "undefined") {
    return Buffer.from(value).toString("base64");
  }
  return window.btoa(value);
}

async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const apiBaseUrl = typeof window === "undefined" ? SERVER_API_BASE_URL : CLIENT_API_BASE_URL;
  const response = await fetch(`${apiBaseUrl}${path}`, init);
  const body = await response.json().catch(() => null) as JsonValue | null;
  if (!response.ok) {
    const errorBody = snakeToCamel<{ error?: { code?: string; message?: string } }>(body ?? {});
    throw new ApiError(response.status, errorBody.error?.code ?? "http_error", errorBody.error?.message ?? "Request failed");
  }
  return snakeToCamel<T>(body ?? {});
}
