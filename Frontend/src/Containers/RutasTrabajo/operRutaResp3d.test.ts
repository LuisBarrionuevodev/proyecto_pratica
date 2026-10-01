import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("V1.1-RESP.3-D — asignación mobile-first", () => {
  it("vista asignación apila columnas y evita overflow horizontal", () => {
    const view = read("src/Containers/RutasTrabajo/views/RutasPlanificacionView.tsx");
    expect(view).toContain('data-testid="rutas-asignacion-view"');
    expect(view).toContain('overflowX: "hidden"');
    expect(view).toContain("size={{ xs: 12, md: 7 }}");
    expect(view).toContain("size={{ xs: 12, md: 5 }}");
  });

  it("pool usa MRT en desktop y cards móviles bajo md", () => {
    const tabla = read("src/Containers/RutasTrabajo/Components/TablaIniciadoresPendientes.tsx");
    expect(tabla).toContain("layoutShell.desktopMinBreakpoint");
    expect(tabla).toContain("AsignacionPoolMobileCardList");
    expect(tabla).toContain("AsignacionPoolSelectionActions");
    expect(tabla).toContain("IniciadoresPoolTableMrtMemo");
    const mobile = read("src/Containers/RutasTrabajo/Components/AsignacionPoolMobileCardList.tsx");
    expect(mobile).toContain('data-testid="asignacion-pool-mobile-list"');
    expect(mobile).toContain("Checkbox");
  });

  it("acciones de selección compartidas entre móvil y MRT", () => {
    const actions = read("src/Containers/RutasTrabajo/Components/AsignacionPoolSelectionActions.tsx");
    expect(actions).toContain("Asignar seleccionados");
    expect(actions).toContain('data-testid="asignacion-eliminar-del-pool"');
    expect(actions).toContain('direction={{ xs: "column", sm: "row" }}');
  });

  it("modales operativos de asignación usan mobileFullScreen", () => {
    expect(read("src/Containers/RutasTrabajo/Components/ModalAsignarSeleccionAGrupo.tsx")).toContain("mobileFullScreen");
    expect(read("src/Containers/RutasTrabajo/Components/ModalCrearGrupoRuta.tsx")).toContain("mobileFullScreen");
    expect(read("src/Containers/RutasTrabajo/Components/ModalAsignarInspectoresGrupo.tsx")).toContain("mobileFullScreen");
    expect(read("src/Containers/RutasTrabajo/Components/ModalEditarOrdenTrabajoItem.tsx")).toContain("mobileFullScreen");
  });

  it("grupos mantienen panel vertical legible en móvil", () => {
    const panel = read("src/Containers/RutasTrabajo/Components/PanelGruposRuta.tsx");
    expect(panel).toContain('direction={{ xs: "column", sm: "row" }}');
    expect(panel).toContain('maxHeight: { xs: "none", md:');
  });
});
