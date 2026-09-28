import { readFileSync, writeFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const SRC = join(process.cwd(), "src");

function walk(dir, acc = []) {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) walk(full, acc);
    else if (/\.(tsx?)$/.test(name)) acc.push(full);
  }
  return acc;
}

const patterns = [
  /^\s*const FONT_FAMILY_UI = FONT_FAMILY_UI as const;\s*\n/gm,
  /^\s*const FONT_FAMILY_UI = FONT_FAMILY_UI;\s*\n/gm,
];

let n = 0;
for (const file of walk(SRC)) {
  let c = readFileSync(file, "utf8");
  const orig = c;
  for (const re of patterns) c = c.replace(re, "");
  if (c !== orig) {
    writeFileSync(file, c, "utf8");
    n++;
  }
}
console.log(`Fixed ${n} files (removed circular FONT_FAMILY_UI const).`);
