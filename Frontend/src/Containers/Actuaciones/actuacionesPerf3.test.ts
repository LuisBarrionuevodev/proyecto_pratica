import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("ActuacionesContainer PERF.3", () => {
  const src = read("src/Containers/Actuaciones/ActuacionesContainer.tsx");

  it("Inspector no invoca pendientes/summary al montar", () => {
    expect(src).toMatch(/if\s*\(\s*isInspectorReadOnly\s*\)\s*return\s*;/);
    expect(src).toContain("getActuacionesPendientesSummary(pendientesDesde, pendientesHasta)");
    expect(src).toContain("isInspectorReadOnly");
  });

  it("Admin conserva refreshPendientes con summary", () => {
    expect(src).toContain("getActuacionesPendientesSummary(desde, hasta)");
    expect(src).toContain("refreshPendientes");
  });
});
