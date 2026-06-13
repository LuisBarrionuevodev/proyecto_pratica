import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { INICIO_ACCESOS } from "../Containers/Inicio/inicioAccesosData";
import { menuSections } from "../constants/menuItems";

describe("UX-FILTROS-NAV-3 Gestión usuarios", () => {
  it("filtro usa estilos comunes filtroStyles", () => {
    const path = resolve(process.cwd(), "src/Containers/GestionDeUsuarios/Components/FiltroUsuarios.tsx");
    const src = readFileSync(path, "utf8");
    expect(src).toContain("filtroContainerStyles");
    expect(src).toContain("filtroGridStyles");
    expect(src).toContain("filtroButtonPrimaryStyles");
    expect(src).toContain("Filtros de Usuarios");
    expect(src).not.toContain("Refrescar");
  });
});

describe("UX-FILTROS-NAV-3 Inicio", () => {
  it("no muestra cards compactas duplicadas", () => {
    const grid = resolve(process.cwd(), "src/Containers/Inicio/Components/InicioOperacionesGrid.tsx");
    const inicio = resolve(process.cwd(), "src/Containers/Inicio/index.tsx");
    const gridSrc = readFileSync(grid, "utf8");
    const inicioSrc = readFileSync(inicio, "utf8");
    expect(gridSrc).not.toContain("InicioRutaHoyCard");
    expect(gridSrc).not.toContain("InicioActasPendientesCompactCard");
    expect(gridSrc).not.toContain("InicioIndicadoresCompactCard");
    expect(inicioSrc).not.toContain("InicioMapaResumenCard");
  });

  it("13 cards alineadas al menú sin Configuración", () => {
    expect(INICIO_ACCESOS).toHaveLength(13);
    const labels = menuSections.map((s) => s.label);
    expect(labels).not.toContain("CONFIGURACIÓN");
    const paths = INICIO_ACCESOS.map((c) => c.to);
    expect(paths).toContain("/gestionarDomicilios");
    expect(paths).toContain("/rutasTrabajo");
    expect(paths).toContain("/dashboard");
    expect(paths).toContain("/mapa");
    expect(paths).toContain("/gestionDeUsuarios");
  });
});

describe("UX-FILTROS-NAV-3 Urgentes Ruta", () => {
  it("panel urgentes tiene filtro tipo y limpiar", () => {
    const filtro = resolve(
      process.cwd(),
      "src/Containers/RutasTrabajo/planificacion/UrgentesFiltroPanel.tsx"
    );
    const panel = resolve(process.cwd(), "src/Containers/RutasTrabajo/planificacion/UrgentesPanel.tsx");
    const filtroSrc = readFileSync(filtro, "utf8");
    const panelSrc = readFileSync(panel, "utf8");
    expect(filtroSrc).toContain("Tipo urgente");
    expect(filtroSrc).toContain("DENUNCIA");
    expect(filtroSrc).toContain("NOTIFICACION");
    expect(filtroSrc).toContain("OFICIO");
    expect(filtroSrc).toContain("Limpiar");
    expect(panelSrc).toContain("UrgentesFiltroPanel");
  });

  it("indicadores usan metricasVisibles del controller", () => {
    const ctrl = resolve(
      process.cwd(),
      "src/Containers/RutasTrabajo/planificacion/hooks/usePlanificacionController.ts"
    );
    const view = resolve(process.cwd(), "src/Containers/RutasTrabajo/planificacion/PlanificacionView.tsx");
    const ctrlSrc = readFileSync(ctrl, "utf8");
    const viewSrc = readFileSync(view, "utf8");
    expect(ctrlSrc).toContain("computeMetricasCardsDesdeMapa");
    expect(ctrlSrc).toContain("metricasVisibles");
    expect(viewSrc).toContain("ctrl.metricasVisibles");
  });
});
