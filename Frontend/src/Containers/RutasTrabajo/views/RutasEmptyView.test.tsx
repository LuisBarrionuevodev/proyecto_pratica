import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("RutasEmptyView — V1.1-RESP.3-B", () => {
  const view = read("src/Containers/RutasTrabajo/views/RutasEmptyView.tsx");

  it("usa tabs responsive institucionales Borradores/Publicadas", () => {
    expect(view).toContain("ResponsiveScrollableTabs");
    expect(view).toContain('label="Borradores"');
    expect(view).toContain('label="Publicadas"');
    expect(view).toContain('variant="fullWidth"');
  });

  it("calendario alineado a Completar trabajo (celdas amplias, solo selección)", () => {
    expect(view).toContain("InstitutionalMonthCalendarGrid");
    expect(view).toContain("INSTITUTIONAL_CALENDAR_CELL_MIN_HEIGHT");
    expect(view).toContain("onSelectDay={(iso) => setSelectedIso(iso)}");
    expect(view).toMatch(/renderDayFooter[\s\S]*String\(n\)/);
  });

  it("títulos de calendario por tab", () => {
    expect(view).toContain("Calendario · Planificación");
    expect(view).toContain("Calendario · Publicadas");
  });

  it("listado móvil en cards y desktop conserva botones", () => {
    expect(view).toContain("RutasDiaRutaMobileCard");
    expect(view).toContain("isDesktopShell");
    expect(view).toContain("rutasLabelFilaRutaListado");
  });
});
