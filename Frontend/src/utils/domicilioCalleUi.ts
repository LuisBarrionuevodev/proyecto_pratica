/**
 * Hidratación de calle/esquina en modales (Actuaciones / Completar Trabajo).
 * Claves técnicas (``calle_key``, ``esquina_key``, slug en ``numero``) no son editables.
 */

export type DomicilioCalleUiFields = {
  calle?: string | null;
  calle_raw?: string | null;
  calle_cargada?: string | null;
  calle_ingresada?: string | null;
  calle_key?: string | null;
  calle_normalizada?: string | null;
  calle_estado?: string | null;
  numero?: string | null;
  numero_tipo?: string | null;
  numero_esquina?: string | null;
  esquina?: string | null;
  esquina_raw?: string | null;
  esquina_cargada?: string | null;
  esquina_key?: string | null;
  esquina_normalizada?: string | null;
  esquina_status?: string | null;
};

function s(v: string | null | undefined): string {
  return (v ?? "").trim();
}

function sameSlug(a: string, b: string): boolean {
  if (!a || !b) return false;
  return a.toLowerCase() === b.toLowerCase();
}

export function domicilioEsTipoEsquina(row: DomicilioCalleUiFields): boolean {
  return (row.numero_tipo ?? "").toUpperCase() === "ESQUINA";
}

function esquinaKey(row: DomicilioCalleUiFields): string {
  return s(row.esquina_key);
}

/** True si el valor coincide con la clave técnica slug de calle. */
export function domicilioCalleEsClaveTecnica(value: string, row: DomicilioCalleUiFields): boolean {
  const key = s(row.calle_key);
  return Boolean(key && sameSlug(value, key));
}

/** True si el valor coincide con la clave técnica de esquina. */
export function domicilioEsquinaEsClaveTecnica(value: string, row: DomicilioCalleUiFields): boolean {
  const key = esquinaKey(row);
  return Boolean(key && sameSlug(value, key));
}

/**
 * Texto para input Calle al abrir modal.
 * Prioridad: calle_normalizada → calle → calle_raw → calle_cargada (nunca calle_key).
 */
export function domicilioCalleCargadaEditable(row: DomicilioCalleUiFields): string {
  const norm = s(row.calle_normalizada);
  if (norm) return norm;

  const key = s(row.calle_key);
  for (const candidate of [s(row.calle), s(row.calle_raw), s(row.calle_cargada), s(row.calle_ingresada)]) {
    if (candidate && !sameSlug(candidate, key)) return candidate;
  }
  return "";
}

/**
 * Valor del input Calle en edición CRUD Actuaciones.
 * Prioriza ``calle`` del draft (incluye string vacío mientras edita) sobre nomenclatura.
 */
export function domicilioCalleValorEdicion(row: DomicilioCalleUiFields): string {
  if (row.calle != null) return String(row.calle);
  return domicilioCalleCargadaEditable(row);
}

/**
 * Valor del input Número/Esquina en edición CRUD Actuaciones.
 * Prioriza ``numero`` del draft sobre nomenclatura persistida.
 */
export function domicilioNumeroValorEdicion(row: DomicilioCalleUiFields): string {
  if (row.numero != null) return String(row.numero);
  return domicilioNumeroEditable(row);
}

/**
 * Texto para input Esquina al abrir modal (solo ``numero_tipo=ESQUINA``).
 * Prioridad: esquina_normalizada → esquina/numero_esquina → esquina_raw → esquina_cargada.
 */
export function domicilioEsquinaCargadaEditable(row: DomicilioCalleUiFields): string {
  if (!domicilioEsTipoEsquina(row)) return "";

  const norm = s(row.esquina_normalizada);
  if (norm) return norm;

  const key = esquinaKey(row);
  for (const candidate of [
    s(row.esquina),
    s(row.numero_esquina),
    s(row.numero),
    s(row.esquina_raw),
    s(row.esquina_cargada),
  ]) {
    if (candidate && !sameSlug(candidate, key)) return candidate;
  }
  return "";
}

/** Número o esquina editable según ``numero_tipo``. */
export function domicilioNumeroEditable(row: DomicilioCalleUiFields): string {
  if (domicilioEsTipoEsquina(row)) {
    return domicilioEsquinaCargadaEditable(row);
  }
  return s(row.numero);
}

/** Prepara draft/fila al abrir edición: calle y esquina humanas, no claves. */
export function domicilioRowParaEdicionCalle<T extends DomicilioCalleUiFields>(row: T): T {
  return {
    ...row,
    calle: domicilioCalleCargadaEditable(row) || null,
    numero: domicilioEsTipoEsquina(row)
      ? domicilioEsquinaCargadaEditable(row) || null
      : row.numero ?? null,
  };
}

/**
 * Valor de calle para payload POST/PUT.
 * Omite si es calle_key o si el usuario no editó respecto al texto hidratado inicial.
 */
export function domicilioCalleParaPayload(
  editedCalle: string | null | undefined,
  row: DomicilioCalleUiFields,
  options?: { baselineRow?: DomicilioCalleUiFields }
): string | undefined {
  const t = s(editedCalle);
  if (!t) return undefined;
  if (domicilioCalleEsClaveTecnica(t, row)) return undefined;
  const baseline = domicilioCalleCargadaEditable(options?.baselineRow ?? row);
  if (baseline && t === baseline) return undefined;
  return t;
}

/**
 * Valor de esquina (campo ``numero`` con ``numero_tipo=ESQUINA``) para payload.
 * Omite si no aplica, es clave técnica o no hubo edición real.
 */
export function domicilioEsquinaParaPayload(
  editedEsquina: string | null | undefined,
  row: DomicilioCalleUiFields,
  options?: { baselineRow?: DomicilioCalleUiFields }
): string | undefined {
  if (!domicilioEsTipoEsquina(row)) return undefined;
  const t = s(editedEsquina);
  if (!t) return undefined;
  if (domicilioEsquinaEsClaveTecnica(t, row)) return undefined;
  const baseline = domicilioEsquinaCargadaEditable(options?.baselineRow ?? row);
  if (baseline && t === baseline) return undefined;
  return t;
}

/**
 * Valor de número (``numero_tipo=NUMERO``) para payload.
 * Omite si no hubo edición real respecto al texto hidratado inicial.
 */
export function domicilioNumeroParaPayload(
  editedNumero: string | null | undefined,
  row: DomicilioCalleUiFields,
  options?: { baselineRow?: DomicilioCalleUiFields }
): string | undefined {
  const t = s(editedNumero);
  if (!t) return undefined;
  const baseline = options?.baselineRow ?? row;
  const baselineNum = domicilioNumeroEditable(baseline);
  if (baselineNum && t === baselineNum) return undefined;
  return t;
}

/**
 * Calle visible/efectiva para payload cuando el bloque domicilio debe enviarse completo.
 * Usa el valor editado o, si falta, el texto hidratado del baseline.
 */
export function domicilioCalleEfectiva(
  editedCalle: string | null | undefined,
  row: DomicilioCalleUiFields,
  options?: { baselineRow?: DomicilioCalleUiFields }
): string | undefined {
  const baseline = options?.baselineRow ?? row;
  const t = s(editedCalle) || domicilioCalleCargadaEditable(baseline);
  if (!t) return undefined;
  if (domicilioCalleEsClaveTecnica(t, row)) return undefined;
  return t;
}

/**
 * Número o esquina visible/efectivo para payload cuando el bloque domicilio debe enviarse completo.
 */
export function domicilioNumeroEfectivo(
  editedNumero: string | null | undefined,
  row: DomicilioCalleUiFields,
  options?: { baselineRow?: DomicilioCalleUiFields; numeroTipo?: string }
): string | undefined {
  const baseline = options?.baselineRow ?? row;
  const tipo = (options?.numeroTipo ?? row.numero_tipo ?? "").toUpperCase();
  if (tipo === "ESQUINA") {
    const t = s(editedNumero) || domicilioEsquinaCargadaEditable(baseline);
    if (!t) return undefined;
    if (domicilioEsquinaEsClaveTecnica(t, row)) return undefined;
    return t;
  }
  const t = s(editedNumero) || domicilioNumeroEditable(baseline);
  return t || undefined;
}
