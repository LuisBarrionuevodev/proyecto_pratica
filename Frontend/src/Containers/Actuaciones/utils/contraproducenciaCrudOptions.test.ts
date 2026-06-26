import { describe, expect, it } from "vitest";
import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import {
  applyContraproducenciaClearFlag,
  buildContraproducenciaCrudSelectOptions,
  detectContraproducenciaClearedByUser,
} from "./contraproducenciaCrudOptions";

const baseRow = (): IActuacionListItem =>
  ({
    id: 1,
    orden_trabajo_numero: "000001",
    fecha_actuacion: "2026-06-10",
    tipo_actuacion: "INSPECCION",
    contraproducencia: "LOCAL CERRADO",
    rubro_nombre: "Bar",
    calle: "Calle",
    numero: "1",
    inspector1: "A",
    inspector2: "B",
    inspector3: null,
    doc_nro: "30123456",
    contrib_apellido: "Ap",
    contrib_nombre: "No",
    acta_inspeccion_num: "000042",
    acta_notificacion_num: null,
    notificacion_motivo_1: null,
    notificacion_motivo_2: null,
    notificacion_motivo_3: null,
    acta_comprobacion_num: null,
    comprobacion_motivo: null,
    acta_clausura_num: null,
    acta_decomiso_num: null,
    decomiso_kilos_total: null,
    expediente_numero: null,
    expediente_anio: null,
    oficio_numero: null,
    oficio_anio: null,
    oficio_causa: null,
  }) as IActuacionListItem;

describe("contraproducenciaCrudOptions", () => {
  it("detecta borrado de contraproducencia", () => {
    const original = baseRow();
    const draft = { ...original, contraproducencia: null };
    expect(detectContraproducenciaClearedByUser(original, draft)).toBe(true);
    expect(detectContraproducenciaClearedByUser(draft, draft)).toBe(false);
  });

  it("aplica flag limpiar_contraproducencia", () => {
    const original = baseRow();
    const draft = { ...original, contraproducencia: null };
    const out = applyContraproducenciaClearFlag(original, draft);
    expect(out.limpiar_contraproducencia).toBe(true);
    expect(out.contraproducencia).toBeNull();
  });

  it("oculta NO_HUBO salvo valor legacy", () => {
    const opts = buildContraproducenciaCrudSelectOptions(
      ["LOCAL CERRADO", "NO_HUBO", "CLIMA"],
      "LOCAL CERRADO"
    );
    const labels = opts.map((o) => o.value);
    expect(labels).not.toContain("NO_HUBO");
    const legacy = buildContraproducenciaCrudSelectOptions(["NO_HUBO", "CLIMA"], "NO_HUBO");
    expect(legacy.some((o) => o.value === "NO_HUBO")).toBe(true);
  });
});
