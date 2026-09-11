import type { IActuacionListItem } from "../../../api/actuacionesListApi";

import type { IItemActaInspeccionCatalogItem } from "../../../api/itemActaInspeccionCatalogApi";



export type ItemInspeccionEstado = "BIEN" | "OBSERVADO";

export type ItemInspeccionEstadoUx = ItemInspeccionEstado | "NONE";



export type ItemActaInspeccionWrite = {

  item_id: number;

  estado: ItemInspeccionEstado;

};



export type InspeccionChecklistItemRead = {

  id: number;

  codigo?: string;

  nombre?: string;

  estado?: ItemInspeccionEstado;

};



export function estadosMapFromRow(

  row: { items_acta_inspeccion?: InspeccionChecklistItemRead[] | null },

  catalog: IItemActaInspeccionCatalogItem[]

): Record<number, ItemInspeccionEstadoUx> {

  const map: Record<number, ItemInspeccionEstadoUx> = {};

  for (const item of catalog) {

    map[item.id] = "NONE";

  }

  for (const read of row.items_acta_inspeccion ?? []) {

    const estado = read.estado;

    if (estado === "BIEN" || estado === "OBSERVADO") {

      map[read.id] = estado;

    }

  }

  return map;

}



export function itemsActaInspeccionWriteFromEstados(

  estados: Record<number, ItemInspeccionEstadoUx>

): ItemActaInspeccionWrite[] {

  const out: ItemActaInspeccionWrite[] = [];

  for (const [rawId, estado] of Object.entries(estados)) {

    if (estado === "BIEN" || estado === "OBSERVADO") {

      out.push({ item_id: Number(rawId), estado });

    }

  }

  out.sort((a, b) => a.item_id - b.item_id);

  return out;

}



export function cantidadPersonasSinCarnetFromRow(

  row: { cantidad_personas_sin_carnet_sanidad?: number | null }

): string {

  const n = row.cantidad_personas_sin_carnet_sanidad;

  if (n === null || n === undefined) return "0";

  return String(Math.max(0, Number(n) || 0));

}



function writeArraysEqual(a: ItemActaInspeccionWrite[], b: ItemActaInspeccionWrite[]): boolean {

  if (a.length !== b.length) return false;

  for (let i = 0; i < a.length; i += 1) {

    if (a[i].item_id !== b[i].item_id || a[i].estado !== b[i].estado) return false;

  }

  return true;

}



/**

 * Omite checklist del PUT si el operador no lo modificó (legacy protection).

 */

export function stripUntouchedInspeccionChecklistFromPut(

  row: IActuacionListItem,

  originalRow?: IActuacionListItem | null,

  touched?: { items?: boolean },

  catalog?: IItemActaInspeccionCatalogItem[]

): IActuacionListItem {

  const copy: Record<string, unknown> = { ...row };

  delete copy.items_acta_inspeccion;



  const baseline = originalRow ?? row;

  const cat = catalog ?? [];

  const origWrite = itemsActaInspeccionWriteFromEstados(

    estadosMapFromRow(baseline, cat.length ? cat : inferCatalogFromRow(baseline))

  );

  const nextWrite =

    row.items_acta_inspeccion ??

    itemsActaInspeccionWriteFromEstados(

      estadosMapFromRow(row, cat.length ? cat : inferCatalogFromRow(row))

    );



  const itemsChanged = touched?.items ?? !writeArraysEqual(origWrite, nextWrite);



  if (!itemsChanged) {

    delete copy.items_acta_inspeccion;

  } else {

    copy.items_acta_inspeccion = nextWrite;

  }



  return copy as IActuacionListItem;

}



/**

 * Omite personas sin carnet del PUT si no se modificó.

 */

export function stripUntouchedPersonasSinCarnetFromPut(

  row: IActuacionListItem,

  originalRow?: IActuacionListItem | null,

  touched?: { carnets?: boolean }

): IActuacionListItem {

  const copy: Record<string, unknown> = { ...row };

  const baseline = originalRow ?? row;

  const orig = cantidadPersonasSinCarnetFromRow(baseline);

  const next = cantidadPersonasSinCarnetFromRow(row);

  const changed = touched?.carnets ?? orig !== next;



  if (!changed) {

    delete copy.cantidad_personas_sin_carnet_sanidad;

  }



  return copy as IActuacionListItem;

}



function inferCatalogFromRow(row: {

  items_acta_inspeccion?: InspeccionChecklistItemRead[] | null;

}): IItemActaInspeccionCatalogItem[] {

  return (row.items_acta_inspeccion ?? []).map((i, idx) => ({

    id: i.id,

    codigo: i.codigo ?? "",

    nombre: i.nombre ?? "",

    activo: true,

    orden: idx + 1,

  }));

}



export function sortCatalogItems(

  items: IItemActaInspeccionCatalogItem[]

): IItemActaInspeccionCatalogItem[] {

  return [...items].sort((a, b) => a.orden - b.orden || a.id - b.id);

}



export type ChecklistHydrationPlan = "close" | "act_change" | "catalog_late" | "skip";



/**

 * Decide si rehidratar estados del checklist al abrir/cambiar actuación o al llegar el catálogo.

 */

export function planChecklistHydration(input: {

  open: boolean;

  actId: number;

  hydratedActId: number | null;

  touched: boolean;

  catalogLength: number;

}): ChecklistHydrationPlan {

  if (!input.open) return "close";

  if (input.hydratedActId !== input.actId) return "act_change";

  if (!input.touched && input.catalogLength > 0) return "catalog_late";

  return "skip";

}


