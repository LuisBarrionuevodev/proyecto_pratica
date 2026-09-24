import type { IHistorialContribuyenteRow } from "../../../api/historialContribuyenteApi";

/**
 * Domicilio visible en historial por contribuyente: prioriza `domicilio_texto` del API.
 */
export function historialContribuyenteDomicilioTexto(
  row: Pick<IHistorialContribuyenteRow, "domicilio_texto">
): string {
  const fromApi = row.domicilio_texto?.trim();
  return fromApi || "—";
}
