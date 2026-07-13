const INTERSECCION_SEP = /\s+Y\s+/i;
const REF_SUFFIX = /\s+ref\.\s+/i;

/**
 * Formatea domicilio para Orden de Trabajo Departamental.
 *
 * - Intersección: «Calle A y Calle B»; ángulo opcional en línea aparte.
 * - Calle + número: rango «calle (n-5) - (n+10)» si el rango es seguro.
 * - Sin parseo seguro: solo la parte principal (sin ref.).
 */
export function buildDomicilioOrdenTrabajoDepartamental(
  domicilioTexto: string,
  anguloEsquina?: string | null
): string {
  const raw = (domicilioTexto ?? "").trim();
  if (!raw || raw === "—") return "—";

  const angulo = (anguloEsquina ?? "").trim();

  if (INTERSECCION_SEP.test(raw)) {
    const parts = raw.split(INTERSECCION_SEP).map((p) => p.trim()).filter(Boolean);
    const interseccion =
      parts.length >= 2 ? `${parts[0]} y ${parts.slice(1).join(" y ")}` : raw.replace(INTERSECCION_SEP, " y ");
    return angulo ? `${interseccion}\nÁngulo: ${angulo}` : interseccion;
  }

  const mainPart = raw.split(REF_SUFFIX)[0]?.trim() || raw;
  const match = mainPart.match(/^(.+?)\s+(\d+)$/);
  if (match) {
    const calle = match[1].trim();
    const num = Number.parseInt(match[2], 10);
    const desde = num - 5;
    const hasta = num + 10;
    if (Number.isFinite(num) && num > 0 && desde >= 0 && calle) {
      return `${calle} ${desde} - ${hasta}`;
    }
    if (calle) return calle;
  }

  return mainPart || raw;
}
