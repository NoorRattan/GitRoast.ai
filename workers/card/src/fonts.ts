import type { Font } from "satori";
import interRegularBase64 from "./font-base64";

let cachedFonts: Font[] | null = null;
let fontLoadCount = 0;

export function loadFonts(): Font[] {
  if (cachedFonts === null) {
    fontLoadCount += 1;
    cachedFonts = [
      {
        name: "Inter",
        data: base64ToArrayBuffer(interRegularBase64),
        weight: 400,
        style: "normal"
      }
    ];
  }
  return cachedFonts;
}

export function getFontLoadCount(): number {
  return fontLoadCount;
}

export function resetFontCacheForTests(): void {
  cachedFonts = null;
  fontLoadCount = 0;
}

function base64ToArrayBuffer(value: string): ArrayBuffer {
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes.buffer;
}
