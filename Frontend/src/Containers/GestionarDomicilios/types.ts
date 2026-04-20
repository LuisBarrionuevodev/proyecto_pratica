import type { PendingItem } from "../../api/mapApi";
import type { CalleCatalogoItem } from "../../api/geolocalizacionApi";

export type DomicilioPendienteItem = PendingItem;

export type DomiciliosTab = "nomenclatura" | "geolocalizacion";

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
