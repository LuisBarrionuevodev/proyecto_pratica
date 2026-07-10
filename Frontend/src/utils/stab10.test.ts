import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

describe("STAB-10 estilos filtros comunes", () => {
  it("define alias filterPrimaryButtonSx y filterSecondaryButtonSx", () => {
    const path = resolve(process.cwd(), "src/Containers/Actuaciones/styles/filtroStyles.ts");
    const src = readFileSync(path, "utf8");
    expect(src).toContain("export const filterPrimaryButtonSx");
    expect(src).toContain("export const filterSecondaryButtonSx");
    expect(src).toContain("export const filterActionsSx");
    expect(src).toContain("export const filterCompactPrimaryButtonSx");
  });

  it("urgentes usa estilos compactos comunes", () => {
    const path = resolve(
      process.cwd(),
      "src/Containers/RutasTrabajo/planificacion/UrgentesFiltroPanel.tsx"
    );
    const src = readFileSync(path, "utf8");
    expect(src).toContain("filterCompactPrimaryButtonSx");
    expect(src).toContain("filterCompactSecondaryButtonSx");
  });

  it("urgentes busca solo por botón", () => {
    const path = resolve(
      process.cwd(),
      "src/Containers/RutasTrabajo/planificacion/UrgentesFiltroPanel.tsx"
    );
    const src = readFileSync(path, "utf8");
    expect(src).toContain("onClick={handleFiltrar}");
    expect(src).not.toContain("useDebouncedValue");
  });

  it("urgentes expone domicilio compacto (sin identificador en vista)", () => {
    const path = resolve(
      process.cwd(),
      "src/Containers/RutasTrabajo/planificacion/UrgentesFiltroPanel.tsx"
    );
    const src = readFileSync(path, "utf8");
    expect(src).toContain('label="Domicilio"');
    expect(src).toContain("q_domicilio");
    expect(src).not.toContain("Nº oficio / comprobación / notificación");
  });
});

describe("STAB-10 planificación performance", () => {
  it("M1 solo sin distrito activo", () => {
    const path = resolve(
      process.cwd(),
      "src/Containers/RutasTrabajo/planificacion/hooks/usePlanificacionController.ts"
    );
    const src = readFileSync(path, "utf8");
    expect(src).toContain("if (distritoActivoId != null)");
    expect(src).toContain("void loadMetricas(null)");
    expect(src).not.toMatch(/void loadMetricas\(distritoActivoId\)/);
  });

  it("KPIs usan metricasVisibles desde mapa con cards múltiples", () => {
    const view = resolve(
      process.cwd(),
      "src/Containers/RutasTrabajo/planificacion/PlanificacionView.tsx"
    );
    const cards = resolve(
      process.cwd(),
      "src/Containers/RutasTrabajo/planificacion/PlanificacionSummaryCards.tsx"
    );
    expect(readFileSync(view, "utf8")).toContain("metricasVisibles");
    expect(readFileSync(cards, "utf8")).toContain("OFICIOS_URGENTES");
    expect(readFileSync(cards, "utf8")).toContain("onCardChange");
  });

  it("domicilios usa endpoint operativo nuevo", () => {
    const path = resolve(
      process.cwd(),
      "src/Containers/Mapa/views/MapaDomiciliosGeolocalizacion/hooks/useGestionDomicilios.ts"
    );
    const src = readFileSync(path, "utf8");
    expect(src).toContain("getGestionDomicilios");
    expect(src).not.toContain("getMapPendientes");
  });
});

describe("STAB-10 limpieza Inicio", () => {
  it("cards compactas eliminadas del filesystem", () => {
    const files = [
      "src/Containers/Inicio/Components/InicioRutaHoyCard.tsx",
      "src/Containers/Inicio/Components/InicioActasPendientesCompactCard.tsx",
      "src/Containers/Inicio/Components/InicioIndicadoresCompactCard.tsx",
      "src/Containers/Inicio/Components/InicioMapaResumenCard.tsx",
    ];
    for (const f of files) {
      expect(() => readFileSync(resolve(process.cwd(), f), "utf8")).toThrow();
    }
  });
});
