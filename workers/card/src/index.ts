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

  try {
    const cardData = await fetchCardData(username, env.BACKEND_BASE_URL);
    const avatarDataUri = await avatarToDataUri(cardData.avatar_url);
    const svg = await (deps.renderSvg ?? renderSvg)(cardData, avatarDataUri);
    const png = await (deps.rasterizeSvg ?? rasterizeSvg)(svg);
    return new Response(png.slice(), {
      status: 200,
      headers: imageHeaders()
    });
  } catch {
    return new Response((deps.fallbackCard ?? fallbackResponseBytes()).slice(), {
      status: 200,
      headers: imageHeaders()
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
