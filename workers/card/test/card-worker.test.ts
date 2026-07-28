import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { Resvg, initWasm } from "@resvg/resvg-wasm";
import { avatarToDataUri } from "../src/avatar";
import { CARD_CACHE_CONTROL, PLACEHOLDER_AVATAR_DATA_URI, getFallbackCard } from "../src/fallback";
import { getFontLoadCount, resetFontCacheForTests } from "../src/fonts";
import { handleCardRequest } from "../src/index";
import { CARD_HEIGHT, CARD_WIDTH, cohortRankCopy, renderSvg } from "../src/render";
import type { CardData } from "../src/types";

const env = { BACKEND_BASE_URL: "https://api.gitroast.test/api/v1" };

const cardData: CardData = {
  username: "octocat",
  schema_version: 4,
  percentile_benchmark: 82,
  percentile_sample_size: 42,
  percentile_cold_start: false,
  avatar_url: "https://avatars.test/octocat.png",
  scores: {
    profile_strength: 71,
    project_depth: 88,
    commit_consistency: 64,
    tech_diversity: 55,
    percentile_benchmark: 82
  }
};

beforeEach(() => {
  resetFontCacheForTests();
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("card Worker pipeline", () => {
  it("renders a card with real card-data and avatar data", async () => {
    const fetchMock = mockFetchSequence([
      jsonResponse(cardData),
      new Response(getFallbackCard().slice(), { status: 200, headers: { "content-type": "image/png" } })
    ]);
    const seen = { username: "", avatar: "" };

    const response = await handleCardRequest(new Request("https://card.test/card/octocat.png?v=4"), env, {
      renderSvg: async (data, avatarDataUri) => {
        seen.username = data.username;
        seen.avatar = avatarDataUri;
        return "<svg />";
      },
      rasterizeSvg: async () => new Uint8Array([1, 2, 3])
    });

    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toBe("image/png");
    expect(response.headers.get("cache-control")).toBe(CARD_CACHE_CONTROL);
    expect(seen.username).toBe("octocat");
    expect(seen.avatar).toMatch(/^data:image\/png;base64,/);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("card-data 404 returns static fallback, not a 500", async () => {
    mockFetchSequence([new Response("missing", { status: 404 })]);

    const response = await handleCardRequest(new Request("https://card.test/card/missing.png?v=1"), env);
    const bytes = new Uint8Array(await response.arrayBuffer());

    expect(response.status).toBe(200);
    expect(bytes.length).toBe(getFallbackCard().length);
  });

  it("card-data network error returns static fallback, not a 500", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new Error("network down");
    }));

    const response = await handleCardRequest(new Request("https://card.test/card/error.png?v=1"), env);
    const bytes = new Uint8Array(await response.arrayBuffer());

    expect(response.status).toBe(200);
    expect(bytes.length).toBe(getFallbackCard().length);
  });

  it("avatar fetch failure uses placeholder avatar while the card still renders", async () => {
    mockFetchSequence([
      jsonResponse(cardData),
      new Response("avatar missing", { status: 404 })
    ]);
    const seen = { avatar: "" };

    const response = await handleCardRequest(new Request("https://card.test/card/octocat.png?v=4"), env, {
      renderSvg: async (_data, avatarDataUri) => {
        seen.avatar = avatarDataUri;
        return "<svg />";
      },
      rasterizeSvg: async () => new Uint8Array([9, 9, 9])
    });

    expect(response.status).toBe(200);
    expect(seen.avatar).toBe(PLACEHOLDER_AVATAR_DATA_URI);
  });

  it("avatar helper falls back independently on timeout or fetch failure", async () => {
    const fetcher = vi.fn(async () => {
      throw new DOMException("timed out", "TimeoutError");
    });

    await expect(avatarToDataUri("https://avatars.test/slow.png", fetcher as typeof fetch)).resolves.toBe(PLACEHOLDER_AVATAR_DATA_URI);
  });

  it("Satori render exceptions return static fallback", async () => {
    mockFetchSequence([jsonResponse({ ...cardData, username: "x".repeat(400) })]);

    const response = await handleCardRequest(new Request("https://card.test/card/long.png?v=1"), env, {
      renderSvg: async () => {
        throw new Error("layout exploded");
      }
    });

    expect(response.status).toBe(200);
    expect(new Uint8Array(await response.arrayBuffer()).length).toBe(getFallbackCard().length);
  });

  it("resvg rasterize exceptions return static fallback", async () => {
    mockFetchSequence([jsonResponse(cardData)]);

    const response = await handleCardRequest(new Request("https://card.test/card/octocat.png?v=1"), env, {
      renderSvg: async () => "<svg />",
      rasterizeSvg: async () => {
        throw new Error("wasm failed");
      }
    });

    expect(response.status).toBe(200);
    expect(new Uint8Array(await response.arrayBuffer()).length).toBe(getFallbackCard().length);
  });

  it("fonts load exactly once across multiple Satori renders", async () => {
    await renderSvg(cardData, PLACEHOLDER_AVATAR_DATA_URI);
    await renderSvg(cardData, PLACEHOLDER_AVATAR_DATA_URI);

    expect(getFontLoadCount()).toBe(1);
  });

  it("does not render a cohort rank number during cold start", async () => {
    expect(cohortRankCopy({
      ...cardData,
      percentile_benchmark: 75,
      percentile_sample_size: 1,
      percentile_cold_start: true
    })).toEqual({
      value: "Not enough data",
      detail: "more comparable profiles needed",
      fontSize: 36
    });
  });

  it("successful render rasterizes to exactly 1200x630 PNG", async () => {
    const svg = await renderSvg(cardData, PLACEHOLDER_AVATAR_DATA_URI);
    await initWasm(readFileSync("node_modules/@resvg/resvg-wasm/index_bg.wasm"));
    const renderer = new Resvg(svg, { fitTo: { mode: "width", value: CARD_WIDTH }, background: "#101111" });
    const png = renderer.render().asPng();
    renderer.free();
    const dimensions = pngDimensions(png);

    expect(dimensions).toEqual({ width: CARD_WIDTH, height: CARD_HEIGHT });
  });
});

function mockFetchSequence(responses: Response[]): ReturnType<typeof vi.fn> {
  const fetchMock = vi.fn(async () => {
    const response = responses.shift();
    if (!response) {
      throw new Error("unexpected fetch");
    }
    return response;
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function jsonResponse(value: unknown): Response {
  return new Response(JSON.stringify(value), {
    status: 200,
    headers: { "content-type": "application/json" }
  });
}

function pngDimensions(bytes: Uint8Array): { width: number; height: number } {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  return {
    width: view.getUint32(16),
    height: view.getUint32(20)
  };
}
