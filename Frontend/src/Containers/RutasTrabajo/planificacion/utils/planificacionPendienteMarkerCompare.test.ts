import { describe, expect, it } from "vitest";

import type { IRutaIniciadorPendienteRow } from "../../../../api/rutasTrabajoApi";
import {
  arePendienteMarkerPropsEqual,
  pendienteMarkerComparePropsFromRow,
  pendienteMarkerRowSignature,
} from "./planificacionPendienteMarkerCompare";

function row(overrides: Partial<IRutaIniciadorPendienteRow> & { id: number }): IRutaIniciadorPendienteRow {
  return {
    id: overrides.id,
    tipo_iniciador: "RELEVAMIENTO",
    domicilio_texto: "Calle 1",
    rubro_nombre: "Bar",
    lat: -26.82,
    lng: -65.22,
    prioridad_categoria: "MEDIA",
    ...overrides,
  } as IRutaIniciadorPendienteRow;
}

function baseCompare(
  r: IRutaIniciadorPendienteRow,
  partial: Parameters<typeof pendienteMarkerComparePropsFromRow>[3]
) {
  return pendienteMarkerComparePropsFromRow(r, -26.82, -65.22, partial);
}

describe("planificacionPendienteMarkerCompare — 2B.3B", () => {
  it("props equivalentes → equal (skip rerender)", () => {
    const r = row({ id: 1 });
    const a = baseCompare(r, {
      isFocus: false,
      showPopup: false,
      popupOpenNonce: 0,
      inPool: false,
      agregando: false,
    });
    const b = { ...a };
    expect(arePendienteMarkerPropsEqual(a, b)).toBe(true);
  });

  it("cambiar isFocus → no equal", () => {
    const r = row({ id: 1 });
    const a = baseCompare(r, {
      isFocus: false,
      showPopup: false,
      popupOpenNonce: 0,
      inPool: false,
      agregando: false,
    });
    const b = { ...a, isFocus: true };
    expect(arePendienteMarkerPropsEqual(a, b)).toBe(false);
  });

  it("cambiar showPopup → no equal", () => {
    const r = row({ id: 1 });
    const base = {
      isFocus: false,
      popupOpenNonce: 0,
      inPool: false,
      agregando: false,
    };
    const closed = baseCompare(r, { ...base, showPopup: false });
    const open = baseCompare(r, { ...base, showPopup: true });
    expect(arePendienteMarkerPropsEqual(closed, open)).toBe(false);
  });

  it("cambiar popupOpenNonce → no equal", () => {
    const r = row({ id: 1 });
    const a = baseCompare(r, {
      isFocus: true,
      showPopup: true,
      popupOpenNonce: 0,
      inPool: false,
      agregando: false,
    });
    const b = { ...a, popupOpenNonce: 1 };
    expect(arePendienteMarkerPropsEqual(a, b)).toBe(false);
  });

  it("cambiar lat/lng → no equal", () => {
    const r = row({ id: 1 });
    const a = baseCompare(r, {
      isFocus: false,
      showPopup: false,
      popupOpenNonce: 0,
      inPool: false,
      agregando: false,
    });
    const b = { ...a, lat: -26.9 };
    expect(arePendienteMarkerPropsEqual(a, b)).toBe(false);
  });

  it("cambiar prioridad → no equal", () => {
    const r = row({ id: 1, prioridad_categoria: "BAJA" });
    const a = baseCompare(r, {
      isFocus: false,
      showPopup: false,
      popupOpenNonce: 0,
      inPool: false,
      agregando: false,
    });
    const r2 = row({ id: 1, prioridad_categoria: "ALTA" });
    const b = baseCompare(r2, {
      isFocus: false,
      showPopup: false,
      popupOpenNonce: 0,
      inPool: false,
      agregando: false,
    });
    expect(arePendienteMarkerPropsEqual(a, b)).toBe(false);
  });

  it("cambiar inPool → no equal", () => {
    const r = row({ id: 1 });
    const a = baseCompare(r, {
      isFocus: false,
      showPopup: false,
      popupOpenNonce: 0,
      inPool: false,
      agregando: false,
    });
    const b = { ...a, inPool: true };
    expect(arePendienteMarkerPropsEqual(a, b)).toBe(false);
  });

  it("cambiar agregando → no equal", () => {
    const r = row({ id: 1 });
    const a = baseCompare(r, {
      isFocus: false,
      showPopup: false,
      popupOpenNonce: 0,
      inPool: false,
      agregando: false,
    });
    const b = { ...a, agregando: true };
    expect(arePendienteMarkerPropsEqual(a, b)).toBe(false);
  });

  it("cambiar domicilio en row → rowSignature distinta → no equal", () => {
    const r1 = row({ id: 1, domicilio_texto: "Calle Vieja 10" });
    const r2 = row({ id: 1, domicilio_texto: "Calle Nueva 20" });
    expect(pendienteMarkerRowSignature(r1)).not.toBe(pendienteMarkerRowSignature(r2));
    const a = baseCompare(r1, {
      isFocus: false,
      showPopup: false,
      popupOpenNonce: 0,
      inPool: false,
      agregando: false,
    });
    const b = baseCompare(r2, {
      isFocus: false,
      showPopup: false,
      popupOpenNonce: 0,
      inPool: false,
      agregando: false,
    });
    expect(arePendienteMarkerPropsEqual(a, b)).toBe(false);
  });
});
