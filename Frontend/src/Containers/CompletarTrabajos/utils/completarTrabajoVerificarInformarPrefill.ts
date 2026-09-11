import type { ICompletarTrabajoPendienteRow } from "../../../api/completarTrabajoApi";
import { domicilioRowParaHidratacionCompletarTrabajo } from "../../../utils/domicilioCalleUi";
import { motivosNotificacionFromSlots } from "../../../utils/motivosNotificacionSlots";
import type { IItemActaInspeccionCatalogItem } from "../../../api/itemActaInspeccionCatalogApi";
import {
  cantidadPersonasSinCarnetFromRow,
  estadosMapFromRow,
  itemsActaInspeccionWriteFromEstados,
} from "../../Actuaciones/utils/inspeccionChecklistSubmit";
import type { ItemInspeccionEstadoUx } from "../../Actuaciones/utils/inspeccionChecklistSubmit";

export type CompletarTrabajoOperativoHydration = {
  calle: string;
  numero: string;
  numeroTipo: "NUMERO" | "ESQUINA";
  rubroNombre: string;
  docNro: string;
  contribApellido: string;
  contribNombre: string;
  razonSocial: string;
  nombreLocal: string;
  actaInspeccion: string;
  checklistEstados: Record<number, ItemInspeccionEstadoUx>;
  personasSinCarnet: string;
  actaNotificacion: string;
  notifMotivosSeleccion: string[];
  actaComprobacion: string;
  comprobacionMotivo: string;
  actaClausura: string;
  actaDecomiso: string;
  decomisoKilos: string;
};

/**
 * Hidrata campos operativos de inspección normal desde la fila de Completar trabajo.
 */
export function operativoHydrationFromRow(
  row: ICompletarTrabajoPendienteRow,
  catalog: IItemActaInspeccionCatalogItem[] = []
): CompletarTrabajoOperativoHydration {
  const domicilio = domicilioRowParaHidratacionCompletarTrabajo(row);
  const kilos = row.decomiso_kilos_total;
  return {
    calle: domicilio.calle ?? "",
    numero: domicilio.numero ?? "",
    numeroTipo: domicilio.numero_tipo === "ESQUINA" ? "ESQUINA" : "NUMERO",
    rubroNombre: row.rubro_nombre ?? "",
    docNro: row.doc_nro ?? "",
    contribApellido: row.contrib_apellido ?? "",
    contribNombre: row.contrib_nombre ?? "",
    razonSocial: row.razon_social ?? "",
    nombreLocal: row.nombre_local ?? "",
    actaInspeccion: row.acta_inspeccion_num ?? "",
    checklistEstados: estadosMapFromRow(row, catalog),
    personasSinCarnet: cantidadPersonasSinCarnetFromRow(row),
    actaNotificacion: row.acta_notificacion_num ?? "",
    notifMotivosSeleccion: motivosNotificacionFromSlots(
      row.notificacion_motivo_1,
      row.notificacion_motivo_2,
      row.notificacion_motivo_3
    ),
    actaComprobacion: row.acta_comprobacion_num ?? "",
    comprobacionMotivo: row.comprobacion_motivo ?? "",
    actaClausura: row.acta_clausura_num ?? "",
    actaDecomiso: row.acta_decomiso_num ?? "",
    decomisoKilos: kilos == null ? "" : String(kilos),
  };
}

export function checklistWriteFromEstados(
  estados: Record<number, ItemInspeccionEstadoUx>
) {
  return itemsActaInspeccionWriteFromEstados(estados);
}
