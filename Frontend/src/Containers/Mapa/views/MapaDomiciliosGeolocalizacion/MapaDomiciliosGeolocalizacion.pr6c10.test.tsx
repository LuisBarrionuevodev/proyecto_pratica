/** @jsxImportSource react */
import { describe, expect, it } from "vitest";
import { existsSync } from "node:fs";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const SHARED = "src/Containers/Mapa/views/MapaDomiciliosGeolocalizacion";
const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");
const exists = (rel: string) => existsSync(resolve(process.cwd(), rel));

describe("PR6C.10 vista compartida MapaDomiciliosGeolocalizacion", () => {
  it("exporta MapaDomiciliosGeolocalizacionView con props configurables", () => {
    const view = read(`${SHARED}/MapaDomiciliosGeolocalizacionView.tsx`);
    const types = read(`${SHARED}/types.ts`);
    expect(view).toContain("MapaDomiciliosGeolocalizacionView");
    expect(types).toContain("filterVariant");
    expect(types).toContain("actionVariant");
    expect(types).toContain("showDetailPanel");
    expect(types).toContain("defaultStatus");
    expect(view).toContain("useGestionDomicilios");
    expect(view).not.toContain("GestionarDomiciliosContainer");
  });

  it("componentes extraídos viven en módulo compartido", () => {
    const paths = [
      `${SHARED}/components/MapaDomiciliosGeolocalizacionMapPanel.tsx`,
      `${SHARED}/components/MapaDomiciliosGeolocalizacionLista.tsx`,
      `${SHARED}/components/MapaDomiciliosGeolocalizacionFiltro.tsx`,
      `${SHARED}/hooks/useGestionDomicilios.ts`,
      `${SHARED}/hooks/useMapaEdicionManual.ts`,
      `${SHARED}/services/geocodeSearchProvider.ts`,
      `${SHARED}/services/manualMapPanelSaveFlow.ts`,
      `${SHARED}/components/ConfirmarUbicacionDialog.tsx`,
    ];
    for (const path of paths) {
      expect(exists(path), `falta ${path}`).toBe(true);
    }
  });

  it("layout mapa 65% + lista 35% preservado", () => {
    const view = read(`${SHARED}/MapaDomiciliosGeolocalizacionView.tsx`);
    expect(view).toContain("MapaDomiciliosGeolocalizacionMapPanel");
    expect(view).toContain("MapaDomiciliosGeolocalizacionLista");
    expect(view).toContain("0 0 65%");
    expect(view).toContain("0 0 35%");
  });

  it("chips EN MAPA / SIN COORDS en lista y detalle", () => {
    const lista = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionLista.tsx`);
    const filters = read(`${SHARED}/mapaDomiciliosOperativoFilters.ts`);
    expect(lista).toContain("labelGeoChip");
    expect(filters).toContain("EN MAPA");
    expect(filters).toContain("SIN COORDS");
  });

  it("geolocalizar/reubicar, confirmación y refetch parcial", () => {
    const view = read(`${SHARED}/MapaDomiciliosGeolocalizacionView.tsx`);
    const mapa = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionMapPanel.tsx`);
    expect(view).toContain("startGeolocalizar");
    expect(view).toContain("startReubicar");
    expect(view).toContain("guardarPuntoManual");
    expect(view).toContain('feedback.success("Ubicación guardada correctamente.")');
    expect(view).toContain("await refetch()");
    expect(mapa).toContain("ConfirmarUbicacionDialog");
    expect(mapa).toContain("useMapaEdicionManual");
  });
});

describe("PR6C.10 Mapa integrado en MapPage (PR6C.11)", () => {
  it("MapPage monta vista compartida en geolocalizacion", () => {
    const mapPage = read("src/Containers/Mapa/MapPage.tsx");
    expect(mapPage).toContain("MapaDomiciliosGeolocalizacionView");
    expect(mapPage).toContain('modo === "geolocalizacion"');
  });

  it("MapaModoTabs usa Geolocalización", () => {
    const tabs = read("src/Containers/Mapa/Components/MapaModoTabs.tsx");
    expect(tabs).toContain("Geolocalización");
    expect(tabs).not.toContain('label="Pendientes"');
  });
});

describe("PR6C.10 redirect legacy sin wrapper", () => {
  it("ruta legacy redirige a /mapa (PR6C.12); container eliminado (PR6C.15)", () => {
    const app = read("src/App.tsx");
    expect(app).toContain('<Navigate to="/mapa" replace />');
    expect(app).not.toContain('element={<GestionarDomicilios');
    expect(app).not.toContain("GestionarDomiciliosContainer");
    expect(exists("src/Containers/GestionarDomicilios/GestionarDomiciliosContainer.tsx")).toBe(
      false
    );
  });

  it("no quedan duplicados activos en GestionarDomicilios", () => {
    const legacy = [
      "src/Containers/GestionarDomicilios/components/GestionDomiciliosVistaUnica.tsx",
      "src/Containers/GestionarDomicilios/hooks/useGestionDomicilios.ts",
      "src/Containers/GestionarDomicilios/components/GestionDomiciliosMapaPanel.tsx",
      "src/Containers/GestionarDomicilios/services/geocodeSearchProvider.ts",
    ];
    for (const path of legacy) {
      expect(exists(path), `duplicado aún presente: ${path}`).toBe(false);
    }
  });
});
