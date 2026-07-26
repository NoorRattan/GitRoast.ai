import { gzipSync } from "node:zlib";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const ceilingBytes = 3 * 1024 * 1024;
const roots = [".next/static/chunks", ".next/server/app"].filter((path) => {
  try {
    return statSync(path).isDirectory();
  } catch {
    return false;
  }
});

function filesUnder(directory) {
  return readdirSync(directory).flatMap((entry) => {
    const path = join(directory, entry);
    return statSync(path).isDirectory() ? filesUnder(path) : [path];
  });
}

const files = roots.flatMap(filesUnder).filter((path) => /\.(js|css)$/.test(path));
const totalGzipBytes = files.reduce((total, path) => total + gzipSync(readFileSync(path)).length, 0);
const mib = (totalGzipBytes / (1024 * 1024)).toFixed(2);
const ceilingMib = (ceilingBytes / (1024 * 1024)).toFixed(2);

process.stdout.write(`Cloudflare free-tier bundle check: ${mib} MiB gzip / ${ceilingMib} MiB ceiling\n`);

if (totalGzipBytes > ceilingBytes) {
  process.stderr.write("Bundle exceeds the Cloudflare Workers free-tier gzip ceiling.\n");
  process.exit(1);
}
