import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import type { IRutaItemMin } from "../../api/rutasTrabajoApi";
import type { IRutaPoolDiaRow } from "../../api/rutaPoolDiaApi";
import { buildRutaPublicadaDocumentModel } from "../../documentos/builders/buildRutaPublicadaDocumentModel";
import {
  buildIniciadorByIdMap,
  detalleOperativoTexto,
  iniciadorPendienteDesdeItemMin,
  tipoLabelOperativo,
} from "./utils/iniciadorDetalleOperativo";
import { poolDiaRowToIniciadorPendiente } from "./utils/poolDiaDisplay";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

function poolRow(overrides: Partial<IRutaPoolDiaRow> = {}): IRutaPoolDiaRow {
  return {
    pool_id: 1,
    fecha: "2026-08-01",
    estado: "EN_POOL",
    origen_tipo: "INICIADOR",
    iniciador_id: 10,
    iniciador_ruta_id: 10,
    tipo_iniciador: "REINSPECCION_NOTIFICACION",
    tipo_iniciador_label: "Reinspección por notificación",
    prioridad: 3,
    detalle_operativo_texto: "Notif.: 222/2026 · Prórroga: 10 días",
    ...overrides,
  };
}

describe("RUTA-ASIG.1 poolDiaRowToIniciadorPendiente", () => {
  it("usa tipo_iniciador real y no origen_tipo del pool", () => {
    const row = poolDiaRowToIniciadorPendiente(
      poolRow({ origen_tipo: "ACTUACION_NOTIF", tipo_iniciador: "REINSPECCION_NOTIFICACION" })
    );
    expect(row.tipo_iniciador).toBe("REINSPECCION_NOTIFICACION");
    expect(row.tipo_iniciador_label).toBe("Reinspección por notificación");
    expect(row.prioridad).toBe(3);
  });

  it("expone detalle operativo de notificación", () => {
    const row = poolDiaRowToIniciadorPendiente(poolRow());
    expect(detalleOperativoTexto(row)).toContain("Notif.: 222/2026");
    expect(detalleOperativoTexto(row)).toContain("Prórroga");
  });

  it("oficio muestra acta, expediente y causa", () => {
    const row = poolDiaRowToIniciadorPendiente(
      poolRow({
        tipo_iniciador: "REINSPECCION_OFICIO",
        tipo_iniciador_label: "Reinspección por oficio",
        detalle_operativo_texto: "Acta comp.: 123/2026 · Exp.: 456/2026 · Oficio: 88/2026 · Causa: Ruidos",
      })
    );
    const detalle = detalleOperativoTexto(row)!;
    expect(detalle).toContain("Acta comp.: 123/2026");
    expect(detalle).toContain("Oficio: 88/2026");
    expect(detalle).toContain("Causa: Ruidos");
  });

  it("denuncia muestra motivo", () => {
    const row = poolDiaRowToIniciadorPendiente(
      poolRow({
        tipo_iniciador: "DENUNCIA",
        detalle_operativo_texto: "Motivo: Alimentos en mal estado",
      })
    );
    expect(detalleOperativoTexto(row)).toContain("Alimentos en mal estado");
  });

  it("sin prioridad no inventa etiqueta falsa", () => {
    const row = poolDiaRowToIniciadorPendiente(poolRow({ prioridad: null }));
    expect(row.prioridad).toBeNull();
  });
});

describe("RUTA-ASIG.1 buildIniciadorByIdMap", () => {
  it("conserva detalle de ítems asignados fuera del pool", () => {
    const item: IRutaItemMin = {
      id: 1,
      ruta_trabajo_id: 1,
      ruta_grupo_id: 2,
      iniciador_ruta_id: 99,
      tipo_iniciador: "DENUNCIA",
      tipo_iniciador_label: "Denuncia",
      detalle_operativo_texto: "Motivo: Basura",
      estado_ruta_item: "ASIGNADO",
      deleted_at: null,
    };
    const map = buildIniciadorByIdMap({}, [item]);
    expect(map[99].tipo_iniciador).toBe("DENUNCIA");
    expect(detalleOperativoTexto(map[99])).toContain("Basura");
  });
});

describe("RUTA-ASIG.1 export resumen", () => {
  it("incluye tipo y detalle operativo en el modelo PDF", () => {
    const model = buildRutaPublicadaDocumentModel(
      {
        id: 1,
        fecha: "2026-08-01",
        turno: "MANIANA",
        estado_ruta: "PUBLICADA",
        numero: 1,
        observaciones: null,
        created_by_user_id: 1,
        created_at: null,
        updated_at: null,
      },
      [
        {
          id: 10,
          ruta_trabajo_id: 1,
          nombre: "G1",
          estado: "ACTIVO",
          inspectores: [],
          created_by_user_id: 1,
          created_at: null,
          updated_at: null,
        },
      ],
      [
        {
          id: 501,
          ruta_trabajo_id: 1,
          ruta_grupo_id: 10,
          iniciador_ruta_id: 200,
          tipo_iniciador: "DENUNCIA",
          tipo_iniciador_label: "Denuncia",
          detalle_operativo_texto: "Motivo: Olores",
          estado_ruta_item: "ASIGNADO",
          deleted_at: null,
        },
      ]
    );
    const fila = model.grupos[0].items[0];
    expect(fila.tipoIniciadorLabel).toBe("Denuncia");
    expect(fila.detalleOperativo).toContain("Olores");
  });
});

describe("RUTA-ASIG.1 UI wiring", () => {
  it("tabla asignación muestra columna detalle operativo", () => {
    const tabla = read("src/Containers/RutasTrabajo/Components/TablaIniciadoresPendientes.tsx");
    expect(tabla).toContain("ASIGNACION_COL_DETALLE_OPERATIVO");
    expect(tabla).toContain("detalleOperativoTexto");
  });

  it("modal inspectores mantiene altura fija del listado", () => {
    const modal = read("src/Containers/RutasTrabajo/Components/ModalAsignarInspectoresGrupo.tsx");
    expect(modal).toContain("LIST_VIEWPORT_HEIGHT_PX");
    expect(modal).toContain("No hay inspectores que coincidan");
  });

  it("tipoLabelOperativo prioriza label del backend", () => {
    const row = iniciadorPendienteDesdeItemMin({
      id: 1,
      ruta_trabajo_id: 1,
      ruta_grupo_id: 1,
      iniciador_ruta_id: 5,
      tipo_iniciador: "REINSPECCION_OFICIO",
      tipo_iniciador_label: "Reinspección por oficio",
      estado_ruta_item: "ASIGNADO",
      deleted_at: null,
    });
    expect(tipoLabelOperativo(row)).toBe("Reinspección por oficio");
  });
});
