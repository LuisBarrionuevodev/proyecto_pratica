/**
 * Arma una línea legible de domicilio para tablas, mapas y cards.
 *
 * - Intersección formal (``numero_tipo === "ESQUINA"``): ``<calle> Y <cruce>`` (separador en mayúsculas),
 *   sin duplicar número vs esquina ni mezclar formato ``(ref: …)``.
 * - Número u otro: ``<calle> <número>``; si hay texto en esquina distinto al número, `` ref. …``.
 */

/** Separador UI entre calle principal y cruce en intersección (convención producto). */
export const CALLE_ESQUINA_SEPARADOR = " Y ";

const REF_PREFIX_ESQ = /^ref\.?\s+/i;

function s(v: string | null | undefined): string {
  return (v ?? "").trim();
}

function mismoTexto(a: string, b: string): boolean {
  return a.length > 0 && b.length > 0 && a.toLowerCase() === b.toLowerCase();
}

function esquinaDisplayInterseccion(
  esquinaNormalizada: string | null | undefined,
  esquinaRaw: string | null | undefined,
  numero: string
): string {
  for (const cand of [s(esquinaNormalizada), s(esquinaRaw), numero]) {
    if (!cand) continue;
    const cleaned = cand.replace(REF_PREFIX_ESQ, "").trim() || cand;
    return cleaned;
  }
  return "";
}

export type DomicilioLineaVisibleInput = {
  calle_normalizada?: string | null;
  calle?: string | null;
  calle_raw?: string | null;
  numero?: string | null;
  numero_raw?: string | null;
  esquina_normalizada?: string | null;
  esquina_raw?: string | null;
  numero_tipo?: string | null;
};

export function formatDomicilioLineaVisible(item: DomicilioLineaVisibleInput): string {
  const calle = s(item.calle_normalizada) || s(item.calle) || s(item.calle_raw);
  const numero = s(item.numero) || s(item.numero_raw);
  const refEsq = s(item.esquina_normalizada) || s(item.esquina_raw);
  const nt = s(item.numero_tipo).toUpperCase();

  if (nt === "ESQUINA") {
    const esq = esquinaDisplayInterseccion(item.esquina_normalizada, item.esquina_raw, numero);
    if (calle && esq) return `${calle}${CALLE_ESQUINA_SEPARADOR}${esq}`;
    if (calle) return calle;
    if (esq) return esq;
    return "";
  }

  if (calle && numero) {
    if (refEsq && !mismoTexto(numero, refEsq)) {
      return `${calle} ${numero} ref. ${refEsq}`;
    }
    return `${calle} ${numero}`.trim();
  }
  if (calle && refEsq && !numero) {
    return `${calle} ref. ${refEsq}`;
  }
  if (calle) return calle;
  if (numero) return numero;
  if (refEsq) return `Ref. ${refEsq}`;
  return "";
}

/** Misma semántica que grilla actuaciones (calle a mostrar + esquina vs número). */
export type ActuacionListDomicilioLineaInput = {
  calle_estado?: string | null;
  calle_normalizada?: string | null;
  calle?: string | null;
  numero_tipo?: string | null;
  numero_esquina?: string | null;
  esquina_normalizada?: string | null;
  numero?: string | null;
};

export function formatActuacionListDomicilioLinea(row: ActuacionListDomicilioLineaInput): string {
  const calle =
    row.calle_estado === "OK" && (row.calle_normalizada ?? "").trim()
      ? (row.calle_normalizada ?? "").trim()
      : (row.calle ?? "").trim();
  const isEsquina = (row.numero_tipo ?? "").toUpperCase() === "ESQUINA";
  if (isEsquina) {
    const esq =
      (row.numero_esquina ?? "").trim() ||
      (row.esquina_normalizada ?? "").trim() ||
      (row.numero ?? "").trim();
    if (calle && esq) return `${calle}${CALLE_ESQUINA_SEPARADOR}${esq}`;
    return (calle || esq).trim();
  }
  const num = (row.numero ?? "").trim();
  if (calle && num) return `${calle} ${num}`;
  return (calle || num).trim();
}
