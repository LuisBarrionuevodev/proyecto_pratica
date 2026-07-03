import type { ICompletarTrabajoPendienteRow } from "../../../api/completarTrabajoApi";
import { domicilioCalleCargadaEditable, domicilioNumeroEditable } from "../../../utils/domicilioCalleUi";

export type CompletarTrabajoOperativoPrefill = {
  calle: string;
  numero: string;
  rubroNombre: string;
  docNro: string;
  contribApellido: string;
  contribNombre: string;
  razonSocial: string;
  nombreLocal: string;
  actaInspeccion: string;
  actaNotificacion: string;
  notifMotivosSeleccion: string[];
  actaComprobacion: string;
  comprobacionMotivo: string;
  actaClausura: string;
  actaDecomiso: string;
  decomisoKilos: string;
};

/**
 * Preload operativo para REINSPECCION_NOTIFICACION: domicilio/titular desde fila,
 * sin acta ni motivos de notificación como formulario nuevo.
 */
export function prefillOperativoReinspeccionNotificacion(
  row: ICompletarTrabajoPendienteRow
): CompletarTrabajoOperativoPrefill {
  return {
    calle: domicilioCalleCargadaEditable(row),
    numero: domicilioNumeroEditable(row),
    rubroNombre: row.rubro_nombre ?? "",
    docNro: row.doc_nro ?? "",
    contribApellido: row.contrib_apellido ?? "",
    contribNombre: row.contrib_nombre ?? "",
    razonSocial: row.razon_social ?? "",
    nombreLocal: row.nombre_local ?? "",
    actaInspeccion: row.acta_inspeccion_num ?? "",
    actaNotificacion: "",
    notifMotivosSeleccion: [],
    actaComprobacion: row.acta_comprobacion_num ?? "",
    comprobacionMotivo: row.comprobacion_motivo ?? "",
    actaClausura: row.acta_clausura_num ?? "",
    actaDecomiso: row.acta_decomiso_num ?? "",
    decomisoKilos: row.decomiso_kilos_total == null ? "" : String(row.decomiso_kilos_total),
  };
}
