import { avatarToDataUri } from "./avatar";
import { fetchCardData } from "./card-data";
import { fallbackResponse, getFallbackCard, imageHeaders } from "./fallback";
import { rasterizeSvg, renderSvg } from "./render";
import type { Env, RenderDeps } from "./types";

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    return handleCardRequest(request, env);
  }
};

export async function handleCardRequest(request: Request, env: Env, deps: RenderDeps = {}): Promise<Response> {
  const username = usernameFromRequest(request);
  if (username === null) {
    return fallbackResponse();
  }

  let stage = "card-data";
  try {
    const cardData = await fetchCardData(username, env.BACKEND_BASE_URL, env.GATEWAY_SHARED_SECRET);
    stage = "avatar";
    const avatarDataUri = await avatarToDataUri(cardData.avatar_url);
    stage = "svg";
    const svg = await (deps.renderSvg ?? renderSvg)(cardData, avatarDataUri);
    stage = "raster";
    const png = await (deps.rasterizeSvg ?? rasterizeSvg)(svg);
    return new Response(png.slice(), {
      status: 200,
      headers: imageHeaders()
    });
  } catch (error) {
    console.error("card render failed", { stage, error: error instanceof Error ? error.message : String(error) });
    return new Response((deps.fallbackCard ?? fallbackResponseBytes()).slice(), {
      status: 200,
      headers: imageHeaders(`fallback-${stage}`)
    });
  }
}

function usernameFromRequest(request: Request): string | null {
  const url = new URL(request.url);
  const match = /^\/card\/([^/]+)\.png$/.exec(url.pathname);
  return match ? decodeURIComponent(match[1]) : null;
}

function fallbackResponseBytes(): Uint8Array {
  return getFallbackCard();
}
