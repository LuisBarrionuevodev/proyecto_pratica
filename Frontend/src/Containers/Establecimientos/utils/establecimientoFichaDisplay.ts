type ContribuyenteFichaInput = {
  razon_social?: string | null;
  contrib_nombre?: string | null;
  contrib_apellido?: string | null;
};

/**
 * Texto de presentación cuando el local no tiene nombre. Solo UI: no se persiste.
 */
export const ESTABLECIMIENTO_NOMBRE_LOCAL_SIN_REGISTRAR = "Sin nombre registrado";

function dash(value: string | null | undefined): string {
  const t = value?.trim();
  return t ? t : "—";
}

/**
 * Nombre visible del contribuyente en la ficha: razón social o nombre y apellido.
 *
 * Parámetros: campos de titular de la ficha operativa.
 * Retorno: texto de presentación; "—" si no hay datos (no inventa "Establecimiento #id").
 */
export function establecimientoFichaContribuyenteNombre(row: ContribuyenteFichaInput): string {
  const rs = row.razon_social?.trim();
  if (rs) return rs;
  const nom = [row.contrib_nombre, row.contrib_apellido]
    .map((s) => (s ?? "").trim())
    .filter(Boolean)
    .join(" ");
  return nom || "—";
}

/**
 * Documento visible en la ficha (mismo criterio que hoy: guión si falta).
 */
export function establecimientoFichaDocumentoVisible(documento?: string | null): string {
  return dash(documento);
}

/**
 * Nombre del local para la ficha. Vacío o solo espacios → "Sin nombre registrado".
 * No sustituye por el contribuyente ni altera el valor de origen.
 */
export function establecimientoFichaNombreLocalVisible(nombreLocal?: string | null): string {
  const t = nombreLocal?.trim();
  return t ? t : ESTABLECIMIENTO_NOMBRE_LOCAL_SIN_REGISTRAR;
}

/**
 * True cuando el nombre visible es el placeholder de presentación.
 */
export function establecimientoFichaNombreLocalEsPlaceholder(nombreLocal?: string | null): boolean {
  return !(nombreLocal ?? "").trim();
}

/**
 * Rubro visible: valor trimmeado o "—" (sin inventar catálogo).
 */
export function establecimientoFichaRubroVisible(rubroNombre?: string | null): string {
  return dash(rubroNombre);
}
