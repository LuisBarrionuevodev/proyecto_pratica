import type { IActuacionListItem } from "../../../api/actuacionesListApi";

import type {
  IItemActaInspeccionCatalogItem,
  ItemActaInspeccionTipoRespuesta,
} from "../../../api/itemActaInspeccionCatalogApi";

export type ItemInspeccionEstado = "BIEN" | "OBSERVADO";
export type ItemInspeccionEstadoUx = ItemInspeccionEstado | "NONE";
export type ItemInspeccionSiNoUx = "SI" | "NO" | "NONE";
export type ChecklistUxValue = ItemInspeccionEstadoUx | ItemInspeccionSiNoUx;

export type ItemActaInspeccionWrite = {
  item_id: number;
  estado?: ItemInspeccionEstado;
  valor_si_no?: boolean;
};

export type InspeccionChecklistItemRead = {
  id: number;
  codigo?: string;
  nombre?: string;
  tipo_respuesta?: ItemActaInspeccionTipoRespuesta;
  estado?: ItemInspeccionEstado | null;
  valor_si_no?: boolean | null;
};

type ChecklistItemRaw = {
  id?: number;
  item_id?: number;
  codigo?: string;
  nombre?: string;
  tipo_respuesta?: ItemActaInspeccionTipoRespuesta;
  estado?: ItemInspeccionEstado | null;
  valor_si_no?: boolean | null;
};

/** Normaliza ítems de checklist (API puede enviar `id` o `item_id`). */
export function normalizeChecklistItems(
  items?: ChecklistItemRaw[] | null
): InspeccionChecklistItemRead[] {
  return (items ?? []).flatMap((item) => {
    const id = item.id ?? item.item_id;
    if (id == null) return [];
    return [
      {
        id,
        codigo: item.codigo,
        nombre: item.nombre,
        tipo_respuesta: item.tipo_respuesta,
        estado: item.estado,
        valor_si_no: item.valor_si_no,
      },
    ];
  });
}

function catalogTipoForItem(
  item: IItemActaInspeccionCatalogItem | undefined,
  read?: InspeccionChecklistItemRead
): ItemActaInspeccionTipoRespuesta {
  return read?.tipo_respuesta ?? item?.tipo_respuesta ?? "ESTADO";
}

export function estadosMapFromRow(
  row: { items_acta_inspeccion?: ChecklistItemRaw[] | null },
  catalog: IItemActaInspeccionCatalogItem[]
): Record<number, ChecklistUxValue> {
  const map: Record<number, ChecklistUxValue> = {};
  const byId = new Map(catalog.map((c) => [c.id, c]));

  for (const item of catalog) {
    map[item.id] = "NONE";
  }

  for (const read of normalizeChecklistItems(row.items_acta_inspeccion)) {
    const cat = byId.get(read.id);
    const tipo = catalogTipoForItem(cat, read);
    if (tipo === "SI_NO") {
      if (read.valor_si_no === true) map[read.id] = "SI";
      else if (read.valor_si_no === false) map[read.id] = "NO";
      continue;
    }
    const estado = read.estado;
    if (estado === "BIEN" || estado === "OBSERVADO") {
      map[read.id] = estado;
    }
  }

  return map;
}

export function itemsActaInspeccionWriteFromEstados(
  estados: Record<number, ChecklistUxValue>,
  catalog: IItemActaInspeccionCatalogItem[]
): ItemActaInspeccionWrite[] {
  const byId = new Map(catalog.map((c) => [c.id, c]));
  const out: ItemActaInspeccionWrite[] = [];

  for (const [rawId, value] of Object.entries(estados)) {
    if (value === "NONE") continue;
    const itemId = Number(rawId);
    const cat = byId.get(itemId);
    const tipo = cat?.tipo_respuesta ?? "ESTADO";

    if (tipo === "SI_NO") {
      if (value === "SI") out.push({ item_id: itemId, valor_si_no: true });
      else if (value === "NO") out.push({ item_id: itemId, valor_si_no: false });
      continue;
    }

    if (value === "BIEN" || value === "OBSERVADO") {
      out.push({ item_id: itemId, estado: value });
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
    const ai = a[i];
    const bi = b[i];
    if (ai.item_id !== bi.item_id) return false;
    if ((ai.estado ?? null) !== (bi.estado ?? null)) return false;
    if ((ai.valor_si_no ?? null) !== (bi.valor_si_no ?? null)) return false;
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
    estadosMapFromRow(baseline, cat.length ? cat : inferCatalogFromRow(baseline)),
    cat.length ? cat : inferCatalogFromRow(baseline)
  );

  const nextWrite = itemsActaInspeccionWriteFromEstados(
    estadosMapFromRow(row, cat.length ? cat : inferCatalogFromRow(row)),
    cat.length ? cat : inferCatalogFromRow(row)
  );

  const itemsChanged = touched?.items ?? !writeArraysEqual(origWrite, nextWrite);

  if (!itemsChanged) {
    delete copy.items_acta_inspeccion;
  } else {
    copy.items_acta_inspeccion = nextWrite;
  }

  return copy as unknown as IActuacionListItem;
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

  return copy as unknown as IActuacionListItem;
}

function inferCatalogFromRow(row: {
  items_acta_inspeccion?: ChecklistItemRaw[] | null;
}): IItemActaInspeccionCatalogItem[] {
  return normalizeChecklistItems(row.items_acta_inspeccion).map((i, idx) => ({
    id: i.id,
    codigo: i.codigo ?? "",
    nombre: i.nombre ?? "",
    orden: idx + 1,
    tipo_respuesta: i.tipo_respuesta ?? "ESTADO",
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
