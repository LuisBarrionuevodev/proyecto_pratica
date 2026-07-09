/** @jsxImportSource react */
import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import {
  CONFIRMAR_UBICACION_MENSAJE,
} from "./components/ConfirmarUbicacionDialog";
import {
  createPendingManualSave,
  shouldExecuteManualSave,
} from "./services/manualMapPanelSaveFlow";
import { buildSearchQuery } from "./services/geocodeSearchProvider";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("PR6C.5 ConfirmarUbicacionDialog", () => {
  it("renderiza texto de confirmación", () => {
    expect(CONFIRMAR_UBICACION_MENSAJE).toBe(
      "¿Estás seguro de dejar el punto en esta ubicación?"
    );
    const src = read("src/Containers/GestionarDomicilios/components/ConfirmarUbicacionDialog.tsx");
    expect(src).toContain(CONFIRMAR_UBICACION_MENSAJE);
    expect(src).toContain("Cancelar");
    expect(src).toContain("Confirmar ubicación");
    expect(src).toContain("domicilioLinea");
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

describe("PR6C.5 ManualMapPanel integración", () => {
  it("ManualMapPanel ya no llama Nominatim directo", () => {
    const src = read("src/Containers/GestionarDomicilios/components/ManualMapPanel.tsx");
    expect(src).not.toContain("nominatim.openstreetmap.org");
    expect(src).toContain("geocodeSearchProvider");
    expect(src).toContain("searchAddress");
    expect(src).toContain("ConfirmarUbicacionDialog");
    expect(src).toContain("handleRequestSave");
    expect(src).toContain("handleConfirmSave");
    expect(src).not.toMatch(/onClick=\{handleSave\}/);
  });

  it("buildSearchQuery exportado para búsqueda contextual SMT", () => {
    expect(buildSearchQuery("San Martín 1009")).toContain("San Miguel de Tucumán");
  });
});
