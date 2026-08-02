import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const baseDir = fileURLToPath(new URL(".", import.meta.url));
const containerPath = resolve(baseDir, "ActuacionesContainer.tsx");
const filtroPath = resolve(baseDir, "Components/FiltroFechas.tsx");

describe("UI consistencia PR — Actuaciones", () => {
  it("no muestra textos explicativos largos en cabecera ni filtros", () => {
    const containerSrc = readFileSync(containerPath, "utf8");
    const filtroSrc = readFileSync(filtroPath, "utf8");
    expect(containerSrc).not.toContain("Buscá por acta, domicilio");
    expect(filtroSrc).not.toContain("filtroHintStyles");
    expect(filtroSrc).not.toContain("No usa el rango de fechas");
    expect(filtroSrc).not.toContain("Las fechas son opcionales");
  });

  it("mantiene labels y placeholders de filtros", () => {
    const filtroSrc = readFileSync(filtroPath, "utf8");
    expect(filtroSrc).toContain('label="Buscar por acta o texto"');
    expect(filtroSrc).toContain('placeholder="Nº de acta, calle, expediente, oficio…"');
    expect(filtroSrc).toContain('label="Desde (opcional)"');
    expect(filtroSrc).toContain('label="Hasta (opcional)"');
    expect(filtroSrc).toContain('label="Tipo de Actuación"');
    expect(filtroSrc).toContain('label="Contraproducencia"');
  });

  it("usa resumen bandeja Total / Mostrando / Página / Rango", () => {
    const src = readFileSync(containerPath, "utf8");
    expect(src).toContain("BandejaTableSummary");
    expect(src).toContain('label="Total"');
    expect(src).toContain('label="Mostrando"');
    expect(src).toContain('label="Página"');
    expect(src).toContain('label="Rango"');
  });

  it("mantiene mensajes de validación de filtros", () => {
    const filtroSrc = readFileSync(filtroPath, "utf8");
    expect(filtroSrc).toContain("validationError");
    expect(filtroSrc).toContain("Completá la búsqueda específica o el rango de fechas y filtros.");
  });
});
