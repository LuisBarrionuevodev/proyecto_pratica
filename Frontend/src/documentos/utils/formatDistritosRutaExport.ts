/**
 * Formatea distritos únicos de una ruta/grupo para exports (órdenes de salida, resumen lateral).
 * Orden numérico cuando el nombre sigue el patrón «Distrito N».
 */

function extraerNumeroDistrito(nombre: string): number | null {
  const m = /^Distrito\s+(\d+)$/i.exec(nombre.trim());
  if (m) return Number(m[1]);
  const solo = /^\d+$/.exec(nombre.trim());
  if (solo) return Number(solo[0]);
  return null;
}

function etiquetaCortaDistrito(nombre: string): string {
  const num = extraerNumeroDistrito(nombre);
  if (num != null) return String(num);
  return nombre.replace(/^Distrito\s+/i, "").trim() || nombre.trim();
}

/**
 * Formatea distritos para export de órdenes de salida.
 *
 * @param distritos — Nombres de distrito (p. ej. «Distrito 10») sin duplicar.
 * @returns `Distrito 10`, `Distritos 2 y 10`, `Distritos 2, 5 y 10`, o `—`.
 */
export function formatDistritosRutaExport(distritos: Iterable<string | null | undefined>): string {
  const uniq = new Set<string>();
  for (const raw of distritos) {
    const d = raw?.trim();
    if (d) uniq.add(d);
  }
  if (uniq.size === 0) return "—";

  const sorted = Array.from(uniq).sort((a, b) => {
    const na = extraerNumeroDistrito(a);
    const nb = extraerNumeroDistrito(b);
    if (na != null && nb != null) return na - nb;
    if (na != null) return -1;
    if (nb != null) return 1;
    return a.localeCompare(b, "es");
  });

  if (sorted.length === 1) {
    const name = sorted[0]!;
    if (/^distrito\b/i.test(name)) return name;
    const num = extraerNumeroDistrito(name);
    return num != null ? `Distrito ${num}` : name;
  }

  const labels = sorted.map(etiquetaCortaDistrito);
  if (labels.length === 2) {
    return `Distritos ${labels[0]} y ${labels[1]}`;
  }
  const last = labels.pop()!;
  return `Distritos ${labels.join(", ")} y ${last}`;
}
