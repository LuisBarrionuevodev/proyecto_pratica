import { describe, expect, it } from "vitest";

import {
  estadosMapFromRow,
  itemsActaInspeccionWriteFromEstados,
  planChecklistHydration,
  stripUntouchedInspeccionChecklistFromPut,
  stripUntouchedPersonasSinCarnetFromPut,
} from "./inspeccionChecklistSubmit";
import type { IActuacionListItem } from "../../../api/actuacionesListApi";

const catalog = [
  { id: 1, codigo: "TIENE_BANO", nombre: "Baño", orden: 1, tipo_respuesta: "ESTADO" as const },
  { id: 2, codigo: "TIENE_SALON", nombre: "Salón", orden: 2, tipo_respuesta: "ESTADO" as const },
  { id: 6, codigo: "TIENE_HABILITACION", nombre: "Tiene habilitación", orden: 6, tipo_respuesta: "SI_NO" as const },
];

const baseRow = {
  id: 1,
  items_acta_inspeccion: [{ id: 1, codigo: "TIENE_BANO", nombre: "Baño", estado: "BIEN" as const, tipo_respuesta: "ESTADO" as const }],
  cantidad_personas_sin_carnet_sanidad: 2,
} as IActuacionListItem;

describe("inspeccionChecklistSubmit V2", () => {
  it("todos NONE → []", () => {
    const estados = estadosMapFromRow({}, catalog);
    expect(itemsActaInspeccionWriteFromEstados(estados, catalog)).toEqual([]);
  });

  it("BIEN y OBSERVADO en write", () => {
    const write = itemsActaInspeccionWriteFromEstados(
      {
        1: "BIEN",
        2: "OBSERVADO",
      },
      catalog
    );
    expect(write).toEqual([
      { item_id: 1, estado: "BIEN" },
      { item_id: 2, estado: "OBSERVADO" },
    ]);
  });

  it("SI y NO serializan valor_si_no", () => {
    const write = itemsActaInspeccionWriteFromEstados(
      {
        6: "SI",
        1: "BIEN",
      },
      catalog
    );
    expect(write).toEqual([
      { item_id: 1, estado: "BIEN" },
      { item_id: 6, valor_si_no: true },
    ]);
    const writeNo = itemsActaInspeccionWriteFromEstados({ 6: "NO" }, catalog);
    expect(writeNo).toEqual([{ item_id: 6, valor_si_no: false }]);
  });

  it("NONE no emite fila para SI_NO", () => {
    expect(itemsActaInspeccionWriteFromEstados({ 6: "NONE" }, catalog)).toEqual([]);
  });

  it("hidrata valor_si_no true/false", () => {
    const map = estadosMapFromRow(
      {
        items_acta_inspeccion: [
          {
            id: 6,
            codigo: "TIENE_HABILITACION",
            nombre: "Tiene habilitación",
            tipo_respuesta: "SI_NO",
            estado: null,
            valor_si_no: true,
          },
        ],
      },
      catalog
    );
    expect(map[6]).toBe("SI");
    const mapNo = estadosMapFromRow(
      {
        items_acta_inspeccion: [
          {
            id: 6,
            codigo: "TIENE_HABILITACION",
            nombre: "Tiene habilitación",
            tipo_respuesta: "SI_NO",
            valor_si_no: false,
          },
        ],
      },
      catalog
    );
    expect(mapNo[6]).toBe("NO");
  });

  it("stripUntouched omite checklist si no hubo cambios", () => {
    const draft = {
      ...baseRow,
      items_acta_inspeccion: [{ item_id: 1, estado: "BIEN" as const }],
    } as IActuacionListItem;
    const out = stripUntouchedInspeccionChecklistFromPut(draft, baseRow, undefined, catalog);
    expect(out.items_acta_inspeccion).toBeUndefined();
  });

  it("cambio de estado marca touched y envía payload", () => {
    const draft = {
      ...baseRow,
      items_acta_inspeccion: [{ item_id: 1, estado: "OBSERVADO" as const }],
    } as IActuacionListItem;
    const out = stripUntouchedInspeccionChecklistFromPut(draft, baseRow, { items: true }, catalog);
    expect(out.items_acta_inspeccion).toEqual([{ item_id: 1, estado: "OBSERVADO" }]);
  });

  it("personas 4→0 envía 0", () => {
    const draft = { ...baseRow, cantidad_personas_sin_carnet_sanidad: 0 } as IActuacionListItem;
    const out = stripUntouchedPersonasSinCarnetFromPut(draft, baseRow, { carnets: true });
    expect(out.cantidad_personas_sin_carnet_sanidad).toBe(0);
  });

  it("personas sin tocar se omite", () => {
    const draft = { ...baseRow, cantidad_personas_sin_carnet_sanidad: 2 } as IActuacionListItem;
    const out = stripUntouchedPersonasSinCarnetFromPut(draft, baseRow);
    expect(out.cantidad_personas_sin_carnet_sanidad).toBeUndefined();
  });

  it("planChecklistHydration: cambio de actuación resetea", () => {
    expect(
      planChecklistHydration({
        open: true,
        actId: 2,
        hydratedActId: 1,
        touched: true,
        catalogLength: 5,
      })
    ).toBe("act_change");
  });

  it("planChecklistHydration: catálogo tardío solo si no hubo touch", () => {
    expect(
      planChecklistHydration({
        open: true,
        actId: 1,
        hydratedActId: 1,
        touched: false,
        catalogLength: 5,
      })
    ).toBe("catalog_late");
    expect(
      planChecklistHydration({
        open: true,
        actId: 1,
        hydratedActId: 1,
        touched: true,
        catalogLength: 5,
      })
    ).toBe("skip");
  });
});
