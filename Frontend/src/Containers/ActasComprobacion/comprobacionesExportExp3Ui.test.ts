import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const baseDir = fileURLToPath(new URL(".", import.meta.url));
const comprobacionPage = resolve(baseDir, "ActasComprobacionPage.tsx");
const notificacionPage = resolve(baseDir, "../GestionNotificacion/GestionNotificacionPage.tsx");

describe("DOCS-EXP.3 — UI export y filtros", () => {
  it("Comprobación muestra export solo en tab Recorrido", () => {
    const src = readFileSync(comprobacionPage, "utf8");
    expect(src).toContain('tab === "recorrido"');
    expect(src).toMatch(/tab === "recorrido"[\s\S]*Exportar datos/);
  });

  it("Comprobación recorrido no muestra textos explicativos en filtros", () => {
    const src = readFileSync(comprobacionPage, "utf8");
    expect(src).not.toContain("filtroHintStyles");
    expect(src).not.toContain("No usa el período salvo que indiques");
  });

  it("Notificación oculta export en vencidas/reinspección", () => {
    const src = readFileSync(notificacionPage, "utf8");
    expect(src).toContain('plazoSlice !== "vencidas_o_hoy"');
  });

  it("Notificación historial no muestra textos explicativos en filtros", () => {
    const src = readFileSync(notificacionPage, "utf8");
    expect(src).not.toContain("filtroHintStyles");
    expect(src).not.toContain("No usa el período salvo que indiques");
  });
});
