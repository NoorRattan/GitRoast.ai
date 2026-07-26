import { PLACEHOLDER_AVATAR_DATA_URI } from "./fallback";
import type { Fetcher } from "./types";

const AVATAR_TIMEOUT_MS = 1200;

export async function avatarToDataUri(avatarUrl: string | null, fetcher: Fetcher = fetch): Promise<string> {
  if (!avatarUrl) {
    return PLACEHOLDER_AVATAR_DATA_URI;
  }
  try {
    const response = await fetcher(avatarUrl, { signal: AbortSignal.timeout(AVATAR_TIMEOUT_MS) });
    if (!response.ok) {
      return PLACEHOLDER_AVATAR_DATA_URI;
    }
    const contentType = response.headers.get("content-type") ?? "image/png";
    const buffer = await response.arrayBuffer();
    return `data:${contentType};base64,${arrayBufferToBase64(buffer)}`;
  } catch {
    return PLACEHOLDER_AVATAR_DATA_URI;
  }
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary);
}
