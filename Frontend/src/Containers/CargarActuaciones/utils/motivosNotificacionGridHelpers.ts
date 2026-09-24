import type { GridRow } from "../../../api/gridApi";

import {
  motivosNotificacionFromSlots,
  slotsToMotivosApi,
} from "../../../utils/motivosNotificacionSlots";

const K1 = "Motivo notif 1" as const;
const K2 = "Motivo notif 2" as const;
const K3 = "Motivo notif 3" as const;

export const MOTIVOS_NOTIF_GRID_COLUMN = "Motivos notificación" as const;

/**
 * Lee los tres slots Glide y devuelve lista única (orden 1→2→3), máx. 3.
 */
export function getMotivosNotificacionListFromRow(row: GridRow): string[] {
  return motivosNotificacionFromSlots(
    row[K1] as string | null | undefined,
    row[K2] as string | null | undefined,
    row[K3] as string | null | undefined
  );
}

/**
 * Escribe en la fila los tres slots a partir de la selección múltiple (sin duplicados, máx. 3).
 */
export function applyMotivosNotificacionToRowPatch(row: GridRow, motivos: string[]): GridRow {
  const { m1, m2, m3 } = slotsToMotivosApi(motivos);
  return {
    ...row,
    [K1]: m1 || null,
    [K2]: m2 || null,
    [K3]: m3 || null,
  };
}

export function formatMotivosNotificacionCellDisplay(names: string[]): string {
  if (!names.length) return "";
  return names.join(" · ");
}

export function motivosNotificacionCellError(cellErrors: Record<string, string>): string | undefined {
  return cellErrors[K1] || cellErrors[K2] || cellErrors[K3];
}
