import fallbackBase64 from "./fallback-card-base64";

export const PNG_CONTENT_TYPE = "image/png";
export const CARD_CACHE_CONTROL = "public, max-age=21600, stale-while-revalidate=3600";

let fallbackCardBytes: Uint8Array | null = null;

export function getFallbackCard(): Uint8Array {
  if (fallbackCardBytes === null) {
    fallbackCardBytes = base64ToBytes(fallbackBase64);
  }
  return fallbackCardBytes;
}

export function imageHeaders(): HeadersInit {
  return {
    "content-type": PNG_CONTENT_TYPE,
    "cache-control": CARD_CACHE_CONTROL
  };
}

export function fallbackResponse(): Response {
  return new Response(getFallbackCard().slice(), {
    status: 200,
    headers: imageHeaders()
  });
}

export const PLACEHOLDER_AVATAR_DATA_URI =
  "data:image/svg+xml;base64," +
  btoa(
    '<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160" viewBox="0 0 160 160"><rect width="160" height="160" rx="80" fill="#202326"/><circle cx="80" cy="64" r="28" fill="#e2b766"/><path d="M36 132c8-28 80-28 88 0" fill="#69c5b8"/></svg>'
  );

function base64ToBytes(value: string): Uint8Array {
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes;
}
