/** @jsxImportSource react */
import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import {
  CONFIRMAR_UBICACION_MENSAJE,
  CONFIRMAR_UBICACION_SECUNDARIO,
} from "../Mapa/views/MapaDomiciliosGeolocalizacion/components/ConfirmarUbicacionDialog";
import {
  createPendingManualSave,
  shouldExecuteManualSave,
} from "../Mapa/views/MapaDomiciliosGeolocalizacion/services/manualMapPanelSaveFlow";
import { buildSearchQuery } from "../Mapa/views/MapaDomiciliosGeolocalizacion/services/geocodeSearchProvider";

const SHARED = "src/Containers/Mapa/views/MapaDomiciliosGeolocalizacion";
const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("PR6C.5 ConfirmarUbicacionDialog", () => {
  it("renderiza texto de confirmación", () => {
    expect(CONFIRMAR_UBICACION_MENSAJE).toBe(
      "¿Confirmás esta ubicación para el domicilio seleccionado?"
    );
    const src = read(`${SHARED}/components/ConfirmarUbicacionDialog.tsx`);
    expect(src).toContain(CONFIRMAR_UBICACION_MENSAJE);
    expect(src).toContain(CONFIRMAR_UBICACION_SECUNDARIO);
    expect(src).toContain("Cancelar");
    expect(src).toContain("Confirmar ubicación");
  });
});

describe("PR6C.5 manualMapPanelSaveFlow", () => {
  it("no guarda si cancela (sin confirmación)", () => {
    const pending = createPendingManualSave(10, { lat: -26.8, lng: -65.2 });
    expect(shouldExecuteManualSave(false, pending)).toBe(false);
  });

  it("guarda solo después de confirmar", () => {
    const pending = createPendingManualSave(10, { lat: -26.8, lng: -65.2 });
    expect(shouldExecuteManualSave(true, pending)).toBe(true);
    expect(shouldExecuteManualSave(true, null)).toBe(false);
  });
});

describe("PR6C.5 mapa edición integrada", () => {
  it("MapaDomiciliosGeolocalizacionMapPanel usa geocodeSearchProvider, no Nominatim directo", () => {
    const mapa = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionMapPanel.tsx`);
    const hook = read(`${SHARED}/hooks/useMapaEdicionManual.ts`);
    expect(mapa).not.toContain("nominatim.openstreetmap.org");
    expect(hook).toContain("searchAddress");
    expect(mapa).toContain("ConfirmarUbicacionDialog");
    expect(hook).toContain("shouldExecuteManualSave");
  });

  it("buildSearchQuery exportado para búsqueda contextual SMT", () => {
    expect(buildSearchQuery("San Martín 1009")).toContain("San Miguel de Tucumán");
  });
});
