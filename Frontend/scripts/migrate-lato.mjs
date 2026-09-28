/**
 * Migration pass: Tactic Sans UI → FONT_FAMILY_UI (Lato).
 */
import fs from "node:fs";
import path from "node:path";

const SRC = path.join(process.cwd(), "src");
const TYPO_FILE = path.join(SRC, "theme", "typography.ts");

function walk(dir, acc = []) {
  for (const name of fs.readdirSync(dir)) {
    const p = path.join(dir, name);
    const st = fs.statSync(p);
    if (st.isDirectory()) {
      if (name === "assets" || name === "documentos") continue;
      walk(p, acc);
    } else if (/\.(ts|tsx)$/.test(name) && !/\.test\.(ts|tsx)$/.test(name)) {
      acc.push(p);
    }
  }
  return acc;
}

function importPath(fromFile) {
  let rel = path.relative(path.dirname(fromFile), TYPO_FILE).replace(/\\/g, "/");
  if (!rel.startsWith(".")) rel = `./${rel}`;
  return rel.replace(/\.ts$/, "");
}

function ensureImport(content, fromFile) {
  if (!content.includes("FONT_FAMILY_UI")) return content;
  if (/from\s+['"].*typography['"]/.test(content)) return content;
  const imp = `import { FONT_FAMILY_UI } from "${importPath(fromFile)}";\n`;
  const imports = [...content.matchAll(/^import .+;\r?\n/gm)];
  if (imports.length > 0) {
    const last = imports[imports.length - 1];
    const idx = last.index + last[0].length;
    return content.slice(0, idx) + imp + content.slice(idx);
  }
  return imp + content;
}

function migrate(content) {
  let c = content;

  c = c.replace(/const tacticFont\s*=\s*[^;]+;?\r?\n?/g, "");
  c = c.replace(/const tactic\s*=\s*[^;]+;?\r?\n?/g, "");
  c = c.replace(/const TACTIC\s*=\s*[^;]+;?\r?\n?/g, "");

  c = c.replace(/\btacticFont\b/g, "FONT_FAMILY_UI");
  c = c.replace(/\btactic\b/g, "FONT_FAMILY_UI");
  c = c.replace(/\bTACTIC\b/g, "FONT_FAMILY_UI");

  c = c.replace(/'"\s*Tactic Sans\s*",\s*sans-serif\s*'/gi, "FONT_FAMILY_UI");
  c = c.replace(/"\s*Tactic Sans\s*",\s*sans-serif"/gi, "FONT_FAMILY_UI");
  c = c.replace(/"\s*Tactic Sans\s*",\s*-apple-system[^"]*"/gi, "FONT_FAMILY_UI");
  c = c.replace(/fontFamily:\s*FONT_FAMILY_UI,\s*sans-serif/gi, "fontFamily: FONT_FAMILY_UI");
  c = c.replace(/fontFamily:\s*['"]tactic sans['"]/gi, "fontFamily: FONT_FAMILY_UI");
  c = c.replace(/fontFamily:\s*['"]Tactic Sans['"]/gi, "fontFamily: FONT_FAMILY_UI");
  c = c.replace(/fontFamily=\{['"]Tactic Sans['"]\}/g, "fontFamily={FONT_FAMILY_UI}");
  c = c.replace(/"Tactic Sans",\s*"Roboto",\s*"Arial",\s*sans-serif/g, "FONT_FAMILY_UI");

  return c;
}

let changed = 0;
for (const file of walk(SRC)) {
  if (file === TYPO_FILE) continue;
  if (file.endsWith("configs\\theme.ts") || file.endsWith("configs/theme.ts")) continue;
  const raw = fs.readFileSync(file, "utf8");
  if (!/Tactic Sans|tactic sans|\btacticFont\b|\btactic\b|\bTACTIC\b/i.test(raw)) continue;
  let next = migrate(raw);
  if (next.includes("FONT_FAMILY_UI")) {
    next = ensureImport(next, file);
  }
  if (next !== raw) {
    fs.writeFileSync(file, next, "utf8");
    changed++;
  }
}

console.log(`Updated ${changed} files.`);
