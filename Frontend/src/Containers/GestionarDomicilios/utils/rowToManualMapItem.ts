import type { GestionDomiciliosRow } from "../../../api/gestionDomiciliosApi";
import type { DomicilioPendienteItem } from "../types";

/** Adapta fila del endpoint nuevo al contrato de ``ManualMapPanel``. */
export function rowToManualMapItem(row: GestionDomiciliosRow): DomicilioPendienteItem {
  return {
    domicilio_id: row.domicilio_id,
    calle_raw: row.domicilio_linea,
    calle_normalizada: row.calle_sugerida ?? null,
    numero_raw: null,
    numero: null,
    numero_tipo: null,
    esquina_normalizada: null,
    calle_status: null,
    esquina_status: null,
    geo_status: row.status_operativo_label,
    error_msg: null,
    lat: row.lat ?? null,
    lng: row.lng ?? null,
  };
}
