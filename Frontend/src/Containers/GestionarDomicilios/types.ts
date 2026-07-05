import type { PendingItem } from "../../api/mapApi";
import type { CalleCatalogoItem } from "../../api/geolocalizacionApi";

export type DomicilioPendienteItem = PendingItem;

/** Slice operativo PR2/PR3 — query ``GET /map/pendientes?slice=``. */
export type DomiciliosSlice =
  | "nomenclatura_pendiente"
  | "geo_pendiente"
  | "baja_confianza"
  | "ok"
  | "validado_manual"
  | "error"
  | "all";

/** Tab activa en Gestión Domicilios (alias de slice). */
export type DomiciliosTab = DomiciliosSlice;

export interface DomiciliosFilters {
  desde: string;
  hasta: string;
  scope: "all" | "actuaciones" | "relevamientos";
}

export type NomenclaturaCalleMode = "CATALOGO" | "MANUAL";
export type NomenclaturaEsquinaMode = "CATALOGO" | "MANUAL";

export interface DomicilioNomenclaturaEditCache {
  calleMode?: NomenclaturaCalleMode;
  esquinaMode?: NomenclaturaEsquinaMode;
  calle_catalogo_id?: number | null;
  numero_tipo?: "NUMERO" | "ESQUINA" | null;
  numero?: string | null;
  esquina_catalogo_id?: number | null;
  calleSearchText?: string;
  esquinaSearchText?: string;
  calleOptions?: CalleCatalogoItem[];
  esquinaOptions?: CalleCatalogoItem[];
}
