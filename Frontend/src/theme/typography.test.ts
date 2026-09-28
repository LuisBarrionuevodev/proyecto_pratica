import { describe, expect, it } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";

import { appTheme } from "../configs/theme";
import { FONT_FAMILY_UI } from "./typography";

const FRONTEND_ROOT = resolve(process.cwd());
const SRC_ROOT = join(FRONTEND_ROOT, "src");

/** Archivos donde "Tactic Sans" está permitido (branding / @font-face). */
const TACTIC_ALLOWLIST = new Set([
  join(SRC_ROOT, "theme", "typography.ts"),
  join(SRC_ROOT, "index.css"),
]);

function walkTsFiles(dir: string, acc: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    const st = statSync(full);
    if (st.isDirectory()) {
      if (name === "documentos") continue;
      walkTsFiles(full, acc);
    } else if (/\.(tsx?|css)$/.test(name)) {
      acc.push(full);
    }
  }
  return acc;
}

describe("FRONT-PROD.1 — tipografía Lato (producto)", () => {
  it("appTheme.typography.fontFamily usa Lato (FONT_FAMILY_UI)", () => {
    expect(appTheme.typography.fontFamily).toBe(FONT_FAMILY_UI);
    expect(String(appTheme.typography.fontFamily)).toContain("Lato");
    expect(String(appTheme.typography.fontFamily)).not.toContain("Tactic");
  });

  it('no hay hardcode de "Tactic Sans" en UI fuera de allowlist', () => {
    const offenders: string[] = [];
    const files = walkTsFiles(SRC_ROOT).filter((f) => f.endsWith(".ts") || f.endsWith(".tsx"));
    files.push(join(SRC_ROOT, "index.css"));

    for (const file of files) {
      if (TACTIC_ALLOWLIST.has(file)) continue;
      if (file.endsWith(".test.ts") || file.endsWith(".test.tsx")) continue;
      const content = readFileSync(file, "utf8");
      if (/Tactic Sans|tactic sans/i.test(content)) {
        offenders.push(file.replace(FRONTEND_ROOT + "\\", "").replace(FRONTEND_ROOT + "/", ""));
      }
    }

    expect(offenders).toEqual([]);
  });
});
