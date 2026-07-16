import type { IRelevamientoListItem } from "../../../api/relevamientosListApi";
import {
  domicilioRowParaEdicionCalle,
} from "../../../utils/domicilioCalleUi";

export type RelevamientoAnguloEsquina = "NE" | "NO" | "SE" | "SO";

export const NOMBRE_FANTASIA_MAX_LEN = 255;

export const ANGULO_ESQUINA_VALUES: readonly RelevamientoAnguloEsquina[] = ["NE", "NO", "SE", "SO"];

const ONLY_DIGITS_RE = /^\d+(\s+\d+)*$/;
const HAS_LETTERS_RE = /[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]/;
const HAS_DIGITS_RE = /\d/;
const OTRO_PATTERNS = [
  /^S\/?N(º|°)?$/i,
  /^SN$/i,
  /^SIN\s*(NUMERO|NRO)$/i,
  /^S\/?NRO$/i,
  /^KM\s*\d+(\.\d+)?$/i,
];

/**
 * Replica la heurística de backend `detect_numero_o_esquina` para UI (solo letras → esquina).
 */
export function detectNumeroLooksLikeEsquina(valor: string | null | undefined): boolean {
  const s = (valor ?? "").trim();
  if (!s) return false;
  const sNorm = s.split(/\s+/).join(" ");
  if (ONLY_DIGITS_RE.test(sNorm)) return false;
  for (const pattern of OTRO_PATTERNS) {
    if (pattern.test(sNorm)) return false;
  }
  const hasLetters = HAS_LETTERS_RE.test(sNorm);
  const hasDigits = HAS_DIGITS_RE.test(sNorm);
  return hasLetters && !hasDigits && sNorm.length > 2;
}

/**
 * Indica si el ángulo de esquina aplica en UI (tipo ESQUINA o número con forma de intersección).
 */
export function relevamientoAnguloEsAplicable(params: {
  numero_tipo?: string | null;
  numero?: string | null;
}): boolean {
  if ((params.numero_tipo ?? "").toUpperCase() === "ESQUINA") return true;
  return detectNumeroLooksLikeEsquina(params.numero);
}

/**
 * Normaliza nombre de fantasía: trim, colapsa espacios, trunca a 255, vacío → null.
 */
export function normalizarNombreFantasiaFrontend(value: string | null | undefined): string | null {
  if (value === null || value === undefined) return null;
  const s = value.trim().replace(/\s+/g, " ");
  if (!s) return null;
  return s.slice(0, NOMBRE_FANTASIA_MAX_LEN);
}

/**
 * Normaliza ángulo de esquina para payload. Fuera de ESQUINA devuelve null sin error (backend también limpia).
 */
export function normalizarAnguloEsquinaFrontend(
  value: string | null | undefined,
  opts?: { numero_tipo?: string | null; numero?: string | null }
): { value: RelevamientoAnguloEsquina | null; error?: string } {
  if (value === null || value === undefined) return { value: null };
  const s = value.trim().toUpperCase();
  if (!s) return { value: null };
  if (!ANGULO_ESQUINA_VALUES.includes(s as RelevamientoAnguloEsquina)) {
    return { value: null, error: "Ángulo de esquina inválido. Use NE, NO, SE o SO." };
  }
  if (opts && !relevamientoAnguloEsAplicable(opts)) {
    return { value: null };
  }
  return { value: s as RelevamientoAnguloEsquina };
}

/**
 * Hidrata fila de bandeja para edición en modal (calle/número humanos, no claves técnicas).
 */
export function relevamientoRowParaEdicion(row: IRelevamientoListItem): IRelevamientoListItem {
  return domicilioRowParaEdicionCalle({ ...row });
}

/**
 * Patch al cambiar modo número/esquina en el modal: limpia ángulo si deja de ser ESQUINA.
 */
export function buildNumeroTipoDraftPatch(
  editorMode: "NUMERO" | "ESQUINA",
  current?: Pick<IRelevamientoListItem, "numero" | "numero_tipo">
): Partial<IRelevamientoListItem> {
  const patch: Partial<IRelevamientoListItem> = { numero_tipo: editorMode };
  if (editorMode === "NUMERO") {
    patch.angulo_esquina = null;
    if ((current?.numero_tipo ?? "").toUpperCase() === "ESQUINA") {
      patch.numero = "";
    }
  }
  return patch;
}

/**
 * Aplica normalización suave de campos de establecimiento sobre una fila para API.
 */
export function applyEstablecimientoCamposToPayload(
  row: IRelevamientoListItem
): IRelevamientoListItem {
  const copy = { ...row };
  copy.nombre_fantasia = normalizarNombreFantasiaFrontend(copy.nombre_fantasia ?? null);
  const ang = normalizarAnguloEsquinaFrontend(copy.angulo_esquina ?? null, {
    numero_tipo: copy.numero_tipo,
    numero: copy.numero,
  });
  copy.angulo_esquina = ang.value;
  return copy;
}
