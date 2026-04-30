export const getCurrentMonthRange = (): { desde: string; hasta: string } => {
  const today = new Date();
  const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
  const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);

  const toIso = (d: Date) => d.toISOString().slice(0, 10);

  return {
    desde: toIso(firstDay),
    hasta: toIso(lastDay),
  };
};

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
