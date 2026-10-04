import type { IActuacionListItem } from "../../../api/actuacionesListApi";

const EM_DASH = "—";
const HABILITACION_CODIGO = "TIENE_HABILITACION";

export type FormatActuacionExportDetallesOptions = {
  /** Si false, nunca incluye el número de teléfono (solo «—» en esa línea). */
  exposeTelefono: boolean;
};

function formatSiNo(value: boolean | null | undefined): string {
  if (value === true) return "Sí";
  if (value === false) return "No";
  return EM_DASH;
}

function habilitacionSiNo(row: IActuacionListItem): string {
  const items = row.items_acta_inspeccion;
  if (!items?.length) return EM_DASH;
  const hit = items.find((it) => {
    if (!it || typeof it !== "object") return false;
    const codigo = "codigo" in it ? String(it.codigo ?? "").trim() : "";
    return codigo === HABILITACION_CODIGO;
  });
  if (!hit || typeof hit !== "object") return EM_DASH;
  if ("valor_si_no" in hit && hit.valor_si_no !== undefined && hit.valor_si_no !== null) {
    return formatSiNo(hit.valor_si_no);
  }
  return EM_DASH;
}

function telefonoLinea(row: IActuacionListItem, exposeTelefono: boolean): string {
  if (!exposeTelefono) return `${EM_DASH}`;
  if (row.solicita_carnet_manipulador !== true) return EM_DASH;
  const tel = (row.telefono_contacto_solicitud_carnet ?? "").trim();
  return tel || EM_DASH;
}

/**
 * Texto multilínea para columna «Detalles» en exportaciones Excel/PDF de actuaciones.
 */
export function formatActuacionExportDetalles(
  row: IActuacionListItem,
  options: FormatActuacionExportDetallesOptions
): string {
  const lines = [
    `Habilitación: ${habilitacionSiNo(row)}`,
    `Carnet de manipulador solicitado: ${formatSiNo(row.solicita_carnet_manipulador)}`,
    `Teléfono de contacto: ${telefonoLinea(row, options.exposeTelefono)}`,
  ];
  return lines.join("\n");
}
