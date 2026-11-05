import type { IActuacionListItem } from "../../../api/actuacionesListApi";

export const GESTION_IDENTIDAD_PUT_KEYS = [
  "doc_nro",
  "contrib_apellido",
  "contrib_nombre",
  "razon_social",
] as const;

export type GestionIdentidadPutKey = (typeof GESTION_IDENTIDAD_PUT_KEYS)[number];

export type ContribuyenteIdentityTouched = Partial<Record<GestionIdentidadPutKey, boolean>>;

export type GestionIdentidadPutFields = Partial<
  Pick<IActuacionListItem, GestionIdentidadPutKey | "limpiar_contribuyente">
>;

export const CONTRIBUYENTE_CLEAR_CONFIRM_TITLE =
  "Vas a desvincular el contribuyente del domicilio. ¿Continuar?";

function trim(value: unknown): string {
  if (value == null) return "";
  return String(value).trim();
}

function normalizeIdentityValue(value: unknown): string | null {
  const s = trim(value);
  return s || null;
}

/** Snapshot semántico de identidad (flat + nested de GET /gestion). */
export function identitySnapshot(row: IActuacionListItem): Record<GestionIdentidadPutKey, string | null> {
  return {
    doc_nro: normalizeIdentityValue(row.doc_nro),
    contrib_apellido:
      normalizeIdentityValue(row.contrib_apellido) ||
      normalizeIdentityValue(row.contribuyente?.apellido),
    contrib_nombre:
      normalizeIdentityValue(row.contrib_nombre) ||
      normalizeIdentityValue(row.contribuyente?.nombre),
    razon_social: normalizeIdentityValue(row.razon_social),
  };
}

function filaTieneContribuyente(row: IActuacionListItem): boolean {
  const snap = identitySnapshot(row);
  return Boolean(snap.doc_nro || snap.contrib_apellido || snap.contrib_nombre || snap.razon_social);
}

function anyIdentidadTouched(touched?: ContribuyenteIdentityTouched | null): boolean {
  if (!touched) return false;
  return GESTION_IDENTIDAD_PUT_KEYS.some((key) => touched[key] === true);
}

/** Hidrata campos flat de identidad desde el objeto anidado del detalle. */
export function mergeActuacionIdentidadFromApiRow(row: IActuacionListItem): IActuacionListItem {
  const snap = identitySnapshot(row);
  return {
    ...row,
    doc_nro: snap.doc_nro,
    contrib_apellido: snap.contrib_apellido,
    contrib_nombre: snap.contrib_nombre,
    razon_social: snap.razon_social,
  };
}

/**
 * True si la fila baseline traía algún dato de contribuyente al abrir edición.
 */
export function baselineTeniaContribuyente(
  original: IActuacionListItem | null | undefined
): boolean {
  return original != null && filaTieneContribuyente(original);
}

/**
 * True si el usuario vació todos los campos de contribuyente respecto al baseline.
 */
export function detectContribuyenteClearedByUser(
  original: IActuacionListItem,
  draft: IActuacionListItem
): boolean {
  return baselineTeniaContribuyente(original) && !filaTieneContribuyente(draft);
}

export function identitySemanticChanged(
  current: IActuacionListItem,
  baseline: IActuacionListItem
): boolean {
  const a = identitySnapshot(current);
  const b = identitySnapshot(baseline);
  return GESTION_IDENTIDAD_PUT_KEYS.some((key) => a[key] !== b[key]);
}

/**
 * True si hay que pedir confirmación antes de desvincular (vacío + tocó identidad).
 */
export function shouldPromptContribuyenteClear(
  baseline: IActuacionListItem,
  draft: IActuacionListItem,
  touched?: ContribuyenteIdentityTouched | null
): boolean {
  if (draft.limpiar_contribuyente === true) return false;
  if (!detectContribuyenteClearedByUser(baseline, draft)) return false;
  if (touched == null) return true;
  return anyIdentidadTouched(touched);
}

export function applyExplicitContribuyenteClear(row: IActuacionListItem): IActuacionListItem {
  return {
    ...row,
    limpiar_contribuyente: true,
    doc_nro: null,
    contrib_apellido: null,
    contrib_nombre: null,
    razon_social: null,
  };
}

/** Quita siempre del body residual identidad y el flag de clear. */
export function stripGestionIdentidadResidualFromPut(row: IActuacionListItem): IActuacionListItem {
  const copy: Record<string, unknown> = { ...row };
  for (const key of GESTION_IDENTIDAD_PUT_KEYS) {
    delete copy[key];
  }
  delete copy.limpiar_contribuyente;
  return copy as unknown as IActuacionListItem;
}

/**
 * Campos de identidad para el PUT. Solo reinserta el grupo si el usuario tocó o cambió
 * semánticamente algún dato. Inputs vacíos no implican `limpiar_contribuyente`.
 */
export function buildGestionIdentidadPutFields(
  row: IActuacionListItem,
  baseline?: IActuacionListItem | null,
  touched?: ContribuyenteIdentityTouched | null
): GestionIdentidadPutFields {
  if (!baseline) {
    return {};
  }

  const current = identitySnapshot(row);
  const original = identitySnapshot(baseline);
  const anyTouched = anyIdentidadTouched(touched);
  const anyChanged = GESTION_IDENTIDAD_PUT_KEYS.some((key) => current[key] !== original[key]);
  if (!anyTouched && !anyChanged) {
    return {};
  }
  if (detectContribuyenteClearedByUser(baseline, row)) {
    return {};
  }

  const out: GestionIdentidadPutFields = {};
  for (const key of GESTION_IDENTIDAD_PUT_KEYS) {
    const fieldTouched = touched?.[key] === true;
    const fieldChanged = current[key] !== original[key];
    out[key] = fieldTouched || fieldChanged ? current[key] : original[key];
  }
  return out;
}

/**
 * Conserva un `limpiar_contribuyente` ya confirmado. No infiere el flag por inputs vacíos.
 */
export function applyContribuyenteClearFlag(
  _original: IActuacionListItem | null | undefined,
  row: IActuacionListItem
): IActuacionListItem {
  if (row.limpiar_contribuyente === true) {
    return applyExplicitContribuyenteClear(row);
  }
  if (row.limpiar_contribuyente) {
    const copy: Record<string, unknown> = { ...row };
    delete copy.limpiar_contribuyente;
    return copy as unknown as IActuacionListItem;
  }
  return row;
}
