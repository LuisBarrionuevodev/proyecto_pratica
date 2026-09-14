import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("TablaCargarRelevamientosGlideStyled — TAB navigation", () => {
  const src = read(
    "src/Containers/CargarRelevamientos/Components/TablaCargarRelevamientosGlideStyled.tsx"
  );

  it("usa util canónico con event.location + índices de datos", () => {
    expect(src).toContain("resolveRelevamientoTabForwardStep");
    expect(src).toContain("relevamientoResolveTabDataCol");
    expect(src).toContain("event.location");
    expect(src).toContain("gridSelectionRef.current?.current?.cell");
    expect(src).not.toContain("RELEVAMIENTO_ROW_MARKERS_BOTH_OFFSET");
  });

  it("intercepta Turno→Está abierto y Está abierto→siguiente fila", () => {
    const nav = read("src/Containers/CargarRelevamientos/utils/relevamientoGridNavigation.ts");
    expect(src).toContain('forward.type === "next-col"');
    expect(nav).toContain("RELEVAMIENTO_PENULTIMATE_EDITABLE_COL_INDEX");
    expect(src).toContain("relevamientoInspectorGridCell(forward.row)");
    expect(src).toContain("gridSelectionRef.current?.current?.cell");
  });

  it("trailing row apunta a primera editable", () => {
    expect(src).toContain("targetColumn: RELEVAMIENTO_FIRST_EDITABLE_COL_INDEX");
  });
});

describe("TablaCargarRelevamientosGlideStyled — headers", () => {
  const src = read(
    "src/Containers/CargarRelevamientos/Components/TablaCargarRelevamientosGlideStyled.tsx"
  );
  const cols = read("src/Containers/CargarRelevamientos/config/columnDefinitions.ts");

  it("headers sin iconos de tipo en columnas", () => {
    expect(src).not.toContain("icon: col.icon");
    expect(cols).not.toContain("icon: col.icon");
    expect(cols).not.toContain("GridColumnIcon.HeaderNumber");
    expect(cols).toContain('title: "Ángulo esquina"');
  });
});

describe("columnDefinitions — Ángulo esquina", () => {
  const cols = read("src/Containers/CargarRelevamientos/config/columnDefinitions.ts");

  it("ancho suficiente para label completo", () => {
    expect(cols).toContain("RELEVAMIENTO_ANGULO_ESQUINA_COL_WIDTH = 148");
    expect(cols).toContain("width: RELEVAMIENTO_ANGULO_ESQUINA_COL_WIDTH");
  });
});

describe("TablaCargarRelevamientosGlideStyled — session drafts", () => {
  const src = read(
    "src/Containers/CargarRelevamientos/Components/TablaCargarRelevamientosGlideStyled.tsx"
  );

  it("usa sessionStorage vía util con usuario de sesión", () => {
    expect(src).toContain("useAppSession");
    expect(src).toContain("readRelevamientoDrafts");
    expect(src).toContain("writeRelevamientoDrafts");
    expect(src).toContain("flushRelevamientoDraftsToSession");
    expect(src).not.toContain("localStorage");
  });

  it("RELEVAMIENTOS-UX.1.1: flush inmediato en pagehide y unmount", () => {
    expect(src).toContain("RELEVAMIENTO_DRAFT_SAVE_DEBOUNCE_MS = 300");
    expect(src).toContain('addEventListener("pagehide"');
    expect(src).toContain("scheduleRelevamientoDraftSave");
  });
});
