import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const indexHtml = readFileSync(resolve(frontendRoot, "index.html"), "utf8");

/**
 * HOTFIX-DIGITALIZA-TRADUCCION.1: el cascarón debe declararse en español y
 * pedir a Chrome Translate que no reescriba el DOM (modales MUI van a body).
 */
describe("cascarón HTML frente a Chrome Translate", () => {
  it("declara idioma español, no inglés", () => {
    expect(indexHtml).toMatch(/<html[^>]*\blang="es"/);
    expect(indexHtml).not.toMatch(/<html[^>]*\blang="en"/);
  });

  it("marca html, body, #root y #portal para que no se traduzcan", () => {
    expect(indexHtml).toMatch(/<html[^>]*\btranslate="no"/);
    expect(indexHtml).toMatch(/<html[^>]*\bclass="notranslate"/);
    expect(indexHtml).toMatch(/<meta name="google" content="notranslate"/);
    expect(indexHtml).toMatch(/<body[^>]*\btranslate="no"/);
    expect(indexHtml).toMatch(/id="root"[^>]*\btranslate="no"/);
    expect(indexHtml).toMatch(/id="portal"[^>]*\btranslate="no"/);
  });
});
