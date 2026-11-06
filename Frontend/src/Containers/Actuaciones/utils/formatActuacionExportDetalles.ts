import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import {
  caracterPersonaAtendioFromRow,
  contratoResiduosFromRow,
  labelCaracterPersonaAtendio,
} from "./inspeccionAtencion";
import {
  CODIGO_TIENE_BANO,
  CODIGO_TIENE_HABILITACION,
  displayChecklistEstadoBienLabel,
} from "./inspeccionChecklistSubmit";

const EM_DASH = "—";

export type FormatActuacionExportDetallesOptions = {
  /** Si false, nunca incluye el número de teléfono (solo «—» en esa línea). */
  exposeTelefono: boolean;
};

function formatSiNo(value: boolean | null | undefined): string {
  if (value === true) return "Sí";
  if (value === false) return "No";
  return EM_DASH;
}

function itemByCodigo(row: IActuacionListItem, codigo: string) {
  const items = row.items_acta_inspeccion;
  if (!items?.length) return null;
  return (
    items.find((it) => {
      if (!it || typeof it !== "object") return false;
      const hit = "codigo" in it ? String(it.codigo ?? "").trim() : "";
      return hit === codigo;
    }) ?? null
  );
}

function habilitacionSiNo(row: IActuacionListItem): string {
  const hit = itemByCodigo(row, CODIGO_TIENE_HABILITACION);
  if (!hit || typeof hit !== "object") return EM_DASH;
  if ("valor_si_no" in hit && hit.valor_si_no !== undefined && hit.valor_si_no !== null) {
    return formatSiNo(hit.valor_si_no);
  }
  return EM_DASH;
}

function banoEstadoTexto(row: IActuacionListItem, empty = EM_DASH): string {
  const hit = itemByCodigo(row, CODIGO_TIENE_BANO);
  if (!hit || typeof hit !== "object") return empty;
  const estado = "estado" in hit ? String(hit.estado ?? "").trim() : "";
  if (estado === "BIEN") return displayChecklistEstadoBienLabel(CODIGO_TIENE_BANO);
  if (estado === "OBSERVADO") return "Observado";
  return empty;
}

function telefonoLinea(row: IActuacionListItem, exposeTelefono: boolean): string {
  if (!exposeTelefono) return `${EM_DASH}`;
  if (row.solicita_carnet_manipulador !== true) return EM_DASH;
  const tel = (row.telefono_contacto_solicitud_carnet ?? "").trim();
  return tel || EM_DASH;
}

function caracterTexto(row: IActuacionListItem): string {
  return labelCaracterPersonaAtendio(caracterPersonaAtendioFromRow(row)) || EM_DASH;
}

/**
 * Texto multilínea para columna «Detalles» en exportaciones Excel/PDF de actuaciones.
 */
export function formatActuacionExportDetalles(
  row: IActuacionListItem,
  options: FormatActuacionExportDetallesOptions
): string {
  const lines = [
    `Carácter de quien atendió: ${caracterTexto(row)}`,
    `Contrato de retiro de residuos sólidos urbanos: ${formatSiNo(contratoResiduosFromRow(row))}`,
    `Baño: ${banoEstadoTexto(row)}`,
    `Habilitación: ${habilitacionSiNo(row)}`,
    `Carnet de manipulador solicitado: ${formatSiNo(row.solicita_carnet_manipulador)}`,
    `Teléfono de contacto: ${telefonoLinea(row, options.exposeTelefono)}`,
  ];
  return lines.join("\n");
}

export function formatCaracterAtendioExcel(row: IActuacionListItem): string {
  return labelCaracterPersonaAtendio(caracterPersonaAtendioFromRow(row));
}

export function formatSiNoExcel(value: boolean | null | undefined): string {
  if (value === true) return "Sí";
  if (value === false) return "No";
  return "";
}

export function formatBanoExcel(row: IActuacionListItem): string {
  return banoEstadoTexto(row, "");
}
