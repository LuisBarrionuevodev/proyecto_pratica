import type { IEstablecimientoOperativoListItem } from "../../../api/establecimientosOperativosApi";

type ContribuyenteListInput = Pick<
  IEstablecimientoOperativoListItem,
  "razon_social" | "contrib_apellido" | "contrib_nombre" | "documento"
>;

/**
 * Título visible en listado Establecimientos: razón social antes que persona física.
 */
export function establecimientoContribuyenteTitulo(row: ContribuyenteListInput): string {
  const rs = (row.razon_social ?? "").trim();
  if (rs) return rs;
  const parts = [row.contrib_apellido, row.contrib_nombre]
    .map((s) => (s ?? "").trim())
    .filter(Boolean);
  if (parts.length) return parts.join(" ");
  return "—";
}

/**
 * Línea secundaria DNI/CUIT para listado Establecimientos.
 */
export function establecimientoContribuyenteDocumentoLinea(documento?: string | null): string {
  const d = (documento ?? "").trim();
  if (!d) return "";
  return `DNI/CUIT: ${d}`;
}
