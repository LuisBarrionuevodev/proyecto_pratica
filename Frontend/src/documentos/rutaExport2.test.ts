import { describe, expect, it } from "vitest";

import type { IRutaGrupoMin, IRutaItemMin, IRutaTrabajo } from "../../api/rutasTrabajoApi";
import { buildRutaPublicadaDocumentModel } from "./builders/buildRutaPublicadaDocumentModel";
import { buildDetalleOperativoResumenRutaExport } from "./utils/detalleOperativoResumenRutaExport";
import { formatDistritosRutaExport } from "./utils/formatDistritosRutaExport";

const rutaBase: IRutaTrabajo = {
  id: 1,
  fecha: "2026-08-26",
  turno: "MANIANA",
  estado_ruta: "PUBLICADA",
  numero: 42,
  observaciones: null,
  created_by_user_id: 1,
  created_at: null,
  updated_at: null,
};

const grupoBase: IRutaGrupoMin = {
  id: 10,
  ruta_trabajo_id: 1,
  nombre: "Grupo 1",
  estado: "ACTIVO",
  inspectores: [
    { id: 1, inspector_id: 100, inspector_nombre: "Pérez, Juan", inspector_legajo: "1234" },
  ],
  created_by_user_id: 1,
  created_at: null,
  updated_at: null,
};

function itemBase(overrides: Partial<IRutaItemMin> = {}): IRutaItemMin {
  return {
    id: 501,
    ruta_trabajo_id: 1,
    ruta_grupo_id: 10,
    iniciador_ruta_id: 200,
    tipo_iniciador: "RELEVAMIENTO",
    orden_trabajo_id: null,
    actuacion_id: null,
    orden_trabajo: null,
    estado_ruta_item: "ASIGNADO",
    deleted_at: null,
    domicilio_texto: "Maipú 500",
    distrito_nombre: "Distrito 10",
    rubro_nombre: "Panadería",
    ...overrides,
  };
}

describe("RUTA-EXPORT.2 formatDistritosRutaExport", () => {
  it("un solo distrito", () => {
    expect(formatDistritosRutaExport(["Distrito 10"])).toBe("Distrito 10");
  });

  it("dos distritos sin duplicar, orden numérico", () => {
    expect(formatDistritosRutaExport(["Distrito 10", "Distrito 2"])).toBe("Distritos 2 y 10");
  });

  it("tres distritos con coma y y final", () => {
    expect(formatDistritosRutaExport(["Distrito 10", "Distrito 2", "Distrito 5"])).toBe(
      "Distritos 2, 5 y 10"
    );
  });

  it("sin distrito devuelve guión", () => {
    expect(formatDistritosRutaExport([])).toBe("—");
  });
});

describe("RUTA-EXPORT.2 órdenes de salida — distritos", () => {
  it("muestra distrito único, no domicilio", () => {
    const model = buildRutaPublicadaDocumentModel(rutaBase, [grupoBase], [itemBase()]);
    const salida = model.inspectoresSalida[0];
    expect(salida?.distritosTexto).toBe("Distrito 10");
    expect(salida?.distritosTexto).not.toContain("Maipú");
  });

  it("agrupa distritos de varios ítems sin duplicar", () => {
    const itemA = itemBase({ id: 501, distrito_nombre: "Distrito 10" });
    const itemB = itemBase({ id: 502, distrito_nombre: "Distrito 2", domicilio_texto: "Otra 1" });
    const model = buildRutaPublicadaDocumentModel(rutaBase, [grupoBase], [itemA, itemB]);
    expect(model.inspectoresSalida[0]?.distritosTexto).toBe("Distritos 2 y 10");
  });
});

describe("RUTA-EXPORT.2 buildDetalleOperativoResumenRutaExport", () => {
  it("notificación con prórroga: solo notif y expediente, sin días ni vencimiento", () => {
    const segs = buildDetalleOperativoResumenRutaExport({
      tipo_iniciador: "REINSPECCION_NOTIFICACION",
      detalle_operativo_items: [
        { label: "Notif.", value: "123/2026" },
        { label: "Prórroga", value: "15 días · Exp. 456/2026 (2026-08-20)" },
        { label: "Vence", value: "2026-08-20" },
      ],
    });
    expect(segs).toEqual(["Notif. Nº 123/2026", "Exp. prórroga: 456/2026"]);
    expect(segs.join(" ")).not.toMatch(/d[ií]as|Vence|Vencimiento|Plazo|Por vencer/i);
  });

  it("notificación sin expediente de prórroga", () => {
    const segs = buildDetalleOperativoResumenRutaExport({
      tipo_iniciador: "REINSPECCION_NOTIFICACION",
      detalle_operativo_items: [
        { label: "Notif.", value: "123/2026" },
        { label: "Prórroga", value: "15 días" },
        { label: "Vence", value: "2026-08-20" },
      ],
    });
    expect(segs).toEqual(["Notif. Nº 123/2026"]);
  });

  it("oficio conserva expediente y causa sin prioridad", () => {
    const segs = buildDetalleOperativoResumenRutaExport({
      tipo_iniciador: "REINSPECCION_OFICIO",
      detalle_operativo_items: [
        { label: "Acta comp.", value: "008801/2026" },
        { label: "Exp.", value: "008805/2026" },
        { label: "Oficio", value: "9234/2026" },
        { label: "Causa", value: "123" },
      ],
      prioridad_label: "P3",
    });
    expect(segs).toContain("Acta comp.: 008801/2026");
    expect(segs).toContain("Exp.: 008805/2026");
    expect(segs.join(" ")).not.toMatch(/prioridad|Alta|Media|Baja/i);
  });
});

describe("RUTA-EXPORT.2 resumen — modelo sin prioridad en segmentos", () => {
  it("no incluye prioridad en detalleOperativoSegmentos", () => {
    const item = itemBase({
      tipo_iniciador: "RELEVAMIENTO",
      prioridad_label: "P1",
      prioridad_categoria: "ALTA",
    });
    const model = buildRutaPublicadaDocumentModel(rutaBase, [grupoBase], [item]);
    const fila = model.grupos[0]?.items[0];
    const joined = (fila?.detalleOperativoSegmentos ?? []).join(" ");
    expect(joined).not.toMatch(/Prioridad|Alta|Media|Baja/i);
  });
});
