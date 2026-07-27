import { readFile, writeFile } from "node:fs/promises";

const workerPath = new URL("../.open-next/worker.js", import.meta.url);
const marker = "globalThis.__gitroastPatchedChdir";
const patch = `\nif (globalThis.process?.chdir && !${marker}) {\n    const originalChdir = globalThis.process.chdir.bind(globalThis.process);\n    globalThis.process.chdir = (directory = \"\") => directory === \"\" ? undefined : originalChdir(directory);\n    ${marker} = true;\n}\n`;

let worker = await readFile(workerPath, "utf8");

if (!worker.includes(marker)) {
  const importTarget = 'import { maybeGetSkewProtectionResponse } from "./cloudflare/skew-protection.js";';
  worker = worker.replace(importTarget, `${importTarget}${patch}`);
  await writeFile(workerPath, worker);
}
