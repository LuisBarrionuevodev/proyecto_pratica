const INTERSECCION_SEP = /\s+Y\s+/i;
const REF_SUFFIX = /\s+ref\.\s+/i;

/**
 * Formatea domicilio para Orden de Trabajo Departamental (PR8.4).
 *
 * - Intersección: «Calle A y Calle B».
 * - Calle + número: rango «calle (n-20)-n» si n ≥ 20; si no, solo calle.
 * - Sin parseo seguro: solo la parte principal (sin ref.).
 */
export function buildDomicilioOrdenTrabajoDepartamental(domicilioTexto: string): string {
  const raw = (domicilioTexto ?? "").trim();
  if (!raw || raw === "—") return "—";

  if (INTERSECCION_SEP.test(raw)) {
    const parts = raw.split(INTERSECCION_SEP).map((p) => p.trim()).filter(Boolean);
    if (parts.length >= 2) {
      return `${parts[0]} y ${parts.slice(1).join(" y ")}`;
    }
    return raw.replace(INTERSECCION_SEP, " y ");
  }

  const mainPart = raw.split(REF_SUFFIX)[0]?.trim() || raw;
  const match = mainPart.match(/^(.+?)\s+(\d+)$/);
  if (match) {
    const calle = match[1].trim();
    const num = Number.parseInt(match[2], 10);
    if (Number.isFinite(num) && num >= 20) {
      return `${calle} ${num - 20}-${num}`;
    }
    if (calle) return calle;
  }

  return mainPart || raw;
}
