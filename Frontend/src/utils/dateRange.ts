export const getCurrentMonthRange = (): { desde: string; hasta: string } => {
  const today = new Date();
  const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
  const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);

  return {
    desde: toIsoDateLocal(firstDay),
    hasta: toIsoDateLocal(lastDay),
  };
};

/**
 * Rango operativo mensual alineado al Dashboard (Mensual): 1.er día del mes → hoy (local).
 * Usado por Mapa operativo e Indicadores para comparar el mismo universo por defecto.
 */
export function getOperativoMonthToDateRange(ref: Date = new Date()): { desde: string; hasta: string } {
  const hasta = new Date(ref.getFullYear(), ref.getMonth(), ref.getDate());
  const desde = new Date(ref.getFullYear(), ref.getMonth(), 1);
  return {
    desde: toIsoDateLocal(desde),
    hasta: toIsoDateLocal(hasta),
  };
}

/** ISO `YYYY-MM-DD` → `DD/MM/YYYY` para etiquetas de período en UI. */
export function formatIsoDateEs(iso: string): string {
  const [y, m, d] = iso.split("-");
  if (!y || !m || !d) return iso;
  return `${d}/${m}/${y}`;
}

/** Etiqueta legible del rango operativo activo. */
export function formatOperativoPeriodoLabel(desde: string, hasta: string): string {
  return `${formatIsoDateEs(desde)} — ${formatIsoDateEs(hasta)}`;
}
/** Fecha local YYYY-MM-DD (evita desfase UTC de `toISOString` en zonas positivas). */
export function fechaLocalHoyIso(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/** Cualquier fecha local → ISO `YYYY-MM-DD` (calendarios / filtros sin UTC). */
export function toIsoDateLocal(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}
