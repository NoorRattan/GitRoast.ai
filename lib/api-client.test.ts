import { afterEach, describe, expect, it, vi } from "vitest";
import { buildCardImageUrl, camelToSnake, fetchCachedAudit, requestAudit, snakeToCamel } from "./api-client";

const auditPayload = {
  username: "newstarter",
  generated_at: "2026-07-27T00:00:00Z",
  schema_version: 3,
  cache_hit: false,
  roast_intensity_requested: "hell",
  roast_intensity_applied: "medium",
  intensity_downgraded: true,
  scores: {
    profile_strength: 70,
    project_depth: 60,
    commit_consistency: 50,
    tech_diversity: 80,
    percentile_benchmark: 65
  },
  flags: { green_square_farming: false, beginner_account: true },
  findings: [{ metric: "fork_ratio", detail: "many forks", value: 0.5, contributes_to: "profile_strength" }],
  roast_text: "text",
  strengths: ["a", "b", "c"],
  improvement_areas: ["x", "y", "z"],
  roadmap: [{ week: 1, focus: "Profile", actions: ["Pin better repos"] }]
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe("api-client translation", () => {
  it("converts snake_case payloads to camelCase", () => {
    const translated = snakeToCamel<{ schemaVersion: number; flags: { beginnerAccount: boolean } }>(auditPayload);

    expect(translated.schemaVersion).toBe(3);
    expect(translated.flags.beginnerAccount).toBe(true);
  });

  it("converts camelCase request bodies to snake_case", () => {
    const translated = camelToSnake<{ roast_intensity: string; nested_value: { cache_hit: boolean } }>({
      roastIntensity: "hell",
      nestedValue: { cacheHit: true }
    });

    expect(translated).toEqual({ roast_intensity: "hell", nested_value: { cache_hit: true } });
  });

  it("returns null for cached audit 404s", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ error: { code: "not_found", message: "Audit not found." } }), { status: 404 })));

    await expect(fetchCachedAudit("missing")).resolves.toBeNull();
  });

  it("posts audit requests with snake_case body and returns camelCase", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify(auditPayload), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await requestAudit("newstarter", "hell");
    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    const requestBody = JSON.parse(init.body as string) as Record<string, string>;

    expect(requestBody).toEqual({ username: "newstarter", roast_intensity: "hell" });
    expect(result.schemaVersion).toBe(3);
    expect(result.intensityDowngraded).toBe(true);
  });

  it("builds versioned card URLs from backend schemaVersion", () => {
    expect(buildCardImageUrl("Noor R", 7)).toBe("https://gitroast-card-preview.jnoorrattan.workers.dev/card/Noor%20R.png?v=7");
  });
});
