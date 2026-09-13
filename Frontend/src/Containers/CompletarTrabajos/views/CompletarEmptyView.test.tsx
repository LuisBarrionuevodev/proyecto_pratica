import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("CompletarEmptyView — COMPLETAR-UX.1", () => {
  const view = read("src/Containers/CompletarTrabajos/views/CompletarEmptyView.tsx");

  it("no renderiza carrusel de trabajos pendientes", () => {
    expect(view).not.toContain("DiaCarouselCard");
    expect(view).not.toContain("diasCarrusel");
    expect(view).not.toContain("carruselRef");
    expect(view).not.toContain("scrollCarrusel");
    expect(view).not.toContain("Trabajos pendientes");
    expect(view).not.toContain("ChevronLeft");
    expect(view).not.toContain("ChevronRight");
  });

  it("usa calendario como selector principal con celdas ampliadas", () => {
    expect(view).toContain("InstitutionalMonthCalendarGrid");
    expect(view).toContain("Calendario operativo");
    expect(view).toContain("cellMinHeight={COMPLETAR_CALENDAR_CELL_MIN_HEIGHT}");
    expect(view).toContain("cellGap={0.75}");
    expect(view).toContain("COMPLETAR_CALENDAR_CELL_MIN_HEIGHT = 56");
  });

  it("muestra contador de pendientes en footer de celda desde resumen", () => {
    expect(view).toContain("renderDayFooter");
    expect(view).toContain("pendientesFooterLabel(diasMap.get(ctx.iso))");
    expect(view).toContain("getCompletarTrabajoPendientesResumen");
    expect(view).toContain("buildDiasMap(dias)");
  });

  it("mantiene selección de día y navegación a grilla", () => {
    expect(view).toContain("onSelectDay={setSelectedCalDay}");
    expect(view).toContain("selectedIso={selectedCalDay}");
    expect(view).toContain("Ir a la grilla del día");
    expect(view).toContain("onVerTrabajos?.(fechaIso)");
  });
});
