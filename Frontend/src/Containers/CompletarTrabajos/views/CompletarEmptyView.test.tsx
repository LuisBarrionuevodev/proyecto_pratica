import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("CompletarEmptyView — COMPLETAR-UX.1 / 1.1", () => {
  const view = read("src/Containers/CompletarTrabajos/views/CompletarEmptyView.tsx");

  it("no renderiza carrusel de trabajos pendientes", () => {
    expect(view).not.toContain("DiaCarouselCard");
    expect(view).not.toContain("diasCarrusel");
    expect(view).not.toContain("carruselRef");
    expect(view).not.toContain("Trabajos pendientes");
  });

  it("carga resumen del mes visible al navegar (no rango fijo stale)", () => {
    expect(view).not.toContain("defaultResumenRango");
    expect(view).toContain("monthBoundsIso(calMes)");
    expect(view).toContain("fecha_desde: mesVisible.desde");
    expect(view).toContain("fecha_hasta: mesVisible.hasta");
    expect(view).toContain("[mesVisible.desde, mesVisible.hasta]");
    expect(view).toContain("onMonthChange={setCalMes}");
  });

  it("usa calendario ampliado como centro visual", () => {
    expect(view).toContain("InstitutionalMonthCalendarGrid");
    expect(view).toContain("COMPLETAR_CALENDAR_CELL_MIN_HEIGHT = 72");
    expect(view).toContain("COMPLETAR_CALENDAR_CELL_GAP = 1");
    expect(view).toContain("p: { xs: 2.5, md: 3.5 }");
  });

  it("semántica por cantidad y footer gris desde util compartido", () => {
    expect(view).toContain("resolvePendienteCeldaTono");
    expect(view).toContain("completarCeldaSurfaceSx");
    expect(view).toContain("completarPendingFooterSx");
    expect(view).toContain("pendientesFooterLabel(diasMap.get(ctx.iso))");
    expect(view).not.toContain("atrasado");
  });

  it("mantiene selección de día y navegación a grilla", () => {
    expect(view).toContain("onSelectDay={setSelectedCalDay}");
    expect(view).toContain("selectedIso={selectedCalDay}");
    expect(view).toContain("Ir a la grilla del día");
    expect(view).toContain("onVerTrabajos?.(fechaIso)");
  });

  it("COMPLETAR-UX.1.2: no duplica indicador HOY (lo provee el grid base)", () => {
    expect(view).not.toContain("&::after");
    expect(view).not.toContain("GLASS_COLORS");
    expect(view).toContain("resolvePendienteCeldaTono");
    expect(view).toContain("completarCeldaSurfaceSx");
  });
});

describe("InstitutionalMonthCalendarGrid — selección preserva estilos del llamador", () => {
  const grid = read("src/components/calendar/InstitutionalMonthCalendarGrid.tsx");

  it("aplica ring primary en selected antes del spread extraSx", () => {
    const idx = grid.indexOf("boxShadow: ctx.selected");
    const spreadIdx = grid.indexOf("...extraSx");
    expect(idx).toBeGreaterThan(-1);
    expect(spreadIdx).toBeGreaterThan(idx);
  });

  it("tipografía ampliada para celdas grandes", () => {
    expect(grid).toContain('cellMinHeight >= 68 ? "1.05rem"');
  });
});
