/**
 * Entrada/salida de fecha en la grilla de relevamientos (valor interno ISO YYYY-MM-DD).
 */

const ISO_RE = /^(\d{4})-(\d{2})-(\d{2})$/;
const DMY_RE = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/;

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

/** ISO → DD/MM/AAAA para mostrar en celda de texto. */
export function formatFechaRelevamientoDisplay(isoOrRaw: string | null | undefined): string {
  if (!isoOrRaw || typeof isoOrRaw !== "string") return "";
  const t = isoOrRaw.trim();
  const m = t.match(ISO_RE);
  if (!m) return t;
  const y = Number(m[1]);
  const mo = Number(m[2]);
  const d = Number(m[3]);
  if (!y || !mo || !d) return t;
  return `${pad2(d)}/${pad2(mo)}/${y}`;
}

/**
 * Acepta DD/MM/AAAA o YYYY-MM-DD (y variantes con espacios).
 * Retorna ISO YYYY-MM-DD o null si no es parseable.
 */
export function parseFechaRelevamientoInput(raw: string | null | undefined): string | null {
  if (raw == null) return null;
  const s = String(raw).trim();
  if (!s) return null;

  let m = s.match(ISO_RE);
  if (m) {
    const y = Number(m[1]);
    const mo = Number(m[2]);
    const d = Number(m[3]);
    const dt = new Date(y, mo - 1, d);
    if (dt.getFullYear() !== y || dt.getMonth() !== mo - 1 || dt.getDate() !== d) return null;
    return `${y}-${pad2(mo)}-${pad2(d)}`;
  }

  m = s.match(DMY_RE);
  if (m) {
    const d = Number(m[1]);
    const mo = Number(m[2]);
    const y = Number(m[3]);
    if (!y || !mo || !d) return null;
    const dt = new Date(y, mo - 1, d);
    if (dt.getFullYear() !== y || dt.getMonth() !== mo - 1 || dt.getDate() !== d) return null;
    return `${y}-${pad2(mo)}-${pad2(d)}`;
  }

  return null;
}
