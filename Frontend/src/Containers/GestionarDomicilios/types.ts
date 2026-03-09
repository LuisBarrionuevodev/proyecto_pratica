import type { PendingItem } from "../../api/mapApi";
import type { CalleCatalogoItem } from "../../api/geolocalizacionApi";

export type DomicilioPendienteItem = PendingItem;

export type DomiciliosTab = "nomenclatura" | "geolocalizacion";

export interface DomiciliosFilters {
  desde: string;
  hasta: string;
  scope: "all" | "actuaciones" | "relevamientos";
}

export interface DomicilioNomenclaturaEditCache {
  calle_catalogo_id?: number | null;
  numero_tipo?: "NUMERO" | "ESQUINA" | null;
  numero?: string | null;
  esquina_catalogo_id?: number | null;
  calleSearchText?: string;
  esquinaSearchText?: string;
  calleOptions?: CalleCatalogoItem[];
  esquinaOptions?: CalleCatalogoItem[];
}
