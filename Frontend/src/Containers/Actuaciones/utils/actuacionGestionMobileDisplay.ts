import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import { formatCrudDialogOtReference } from "../../../components/crudDialog/crudDialogReference";
import { formatActuacionListDomicilioLinea } from "../../../utils/formatDomicilioLineaVisible";
import { tipoActuacionBandejaSegment } from "../Components/bandejaTableCells";

export function actuacionGestionMobileIdentificador(row: IActuacionListItem): string {
  const ot = formatCrudDialogOtReference(row.orden_trabajo_numero);
  if (ot) return ot;
  const id = row.id != null ? String(row.id).trim() : "";
  return id ? `Actuación #${id}` : "Actuación";
}

export function actuacionGestionMobileFecha(row: IActuacionListItem): string {
  return (row.fecha_actuacion ?? "").trim() || "—";
}

export function actuacionGestionMobileOrigen(row: IActuacionListItem): string {
  const tipo = tipoActuacionBandejaSegment(row.tipo_actuacion);
  const contra = (row.contraproducencia ?? "").trim();
  if (tipo && contra) return `${tipo} · ${contra}`;
  return tipo || contra || "—";
}

export function actuacionGestionMobileTitular(row: IActuacionListItem): string {
  const rs = (row.razon_social ?? "").trim();
  if (rs) return rs;
  const parts = [(row.contrib_apellido ?? "").trim(), (row.contrib_nombre ?? "").trim()].filter(Boolean);
  if (parts.length) return parts.join(", ");
  const doc = (row.doc_nro ?? "").trim();
  return doc || "—";
}

export function actuacionGestionMobileDomicilio(row: IActuacionListItem): string {
  return formatActuacionListDomicilioLinea(row).trim() || "—";
}

export function actuacionGestionMobileEstado(row: IActuacionListItem): string {
  if (row.actuacion_editable === false) {
    return (row.motivo_bloqueo_edicion ?? "").trim() || "No editable";
  }
  if (row.actuacion_bloqueada_por_expediente) {
    return "Bloqueada por expediente";
  }
  const contra = (row.contraproducencia ?? "").trim();
  return contra || "Activa";
}
