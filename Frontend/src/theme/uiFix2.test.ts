import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("V1.1-UI-FIX.2 — contraste y export detalles", () => {
  it("chips de bandeja usan borde semántico (no blanco hardcode)", () => {
    const src = read("src/Containers/Actuaciones/Components/bandejaTableCells.tsx");
    expect(src).toContain("borderColor: GLASS_COLORS.borderMedium");
    expect(src).not.toContain("borderColor: \"rgba(255,255,255,0.38)\"");
  });

  it("Completar trabajo: chips con borde visible en claro", () => {
    const src = read("src/Containers/CompletarTrabajos/components/CompletarTrabajoModal.tsx");
    expect(src).toContain("border: `1px solid ${GLASS_COLORS.borderMedium}`");
  });

  it("Oficio operativo: hints documentales sin texto blanco fijo", () => {
    const src = read("src/Containers/ActasComprobacion/components/ComprobacionOficioOperativoDialog.tsx");
    expect(src).toContain("docModalCaptionSx");
    expect(src).toContain('Primero el expediente de respuesta y la fecha compartida');
    expect(src).toContain("sx={docModalCaptionSx}");
  });

  it("Establecimiento detalle usa tokens de texto", () => {
    const src = read("src/Containers/Establecimientos/EstablecimientoDetallePage.tsx");
    expect(src).toContain("GLASS_COLORS.textPrimary");
    expect(src).not.toMatch(/color: COLORS\.white/);
  });

  it("mapa planificación: popup legible en claro", () => {
    const map = read("src/Containers/RutasTrabajo/planificacion/PlanificacionMapaDistritos.tsx");
    expect(map).toContain('mode === "light"');
    expect(map).toContain("colors.surface.tableRowEven");
    const card = read(
      "src/Containers/RutasTrabajo/planificacion/components/PlanificacionMapaGeopuntoOperativaCard.tsx"
    );
    expect(card).toContain("useDigitalizaTheme");
  });

  it("pool strip con superficie sólida", () => {
    const strip = read("src/Containers/RutasTrabajo/planificacion/PlanificacionPoolCardsStrip.tsx");
    expect(strip).toContain("surfacePanel");
    expect(strip).not.toContain("rgba(255,255,255,0.04)");
  });

  it("export actuaciones: formateador único y export_context", () => {
    expect(read("src/Containers/Actuaciones/utils/actuacionesExportNormalizedRows.ts")).toContain(
      "formatActuacionExportDetalles"
    );
    expect(read("src/Containers/Actuaciones/utils/actuacionesExportVisualRows.ts")).toContain(
      "formatActuacionExportDetalles"
    );
    expect(read("src/api/actuacionesExportApi.ts")).toContain("export_context: true");
  });
});
