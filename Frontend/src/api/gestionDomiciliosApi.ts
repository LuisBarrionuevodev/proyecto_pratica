import { apiClient } from "./apiClient";

/** Estado operativo de una fila (no incluye filtros agregados). */
export type GestionDomiciliosStatusOperativoRow =
  | "sin_punto"
  | "punto_dudoso"
  | "error"
  | "manual"
  | "geolocalizado";

/** Filtro operativo de la cola Gestión Domicilios (PR6C.2). */
export type GestionDomiciliosStatusOperativo =
  | "requiere_accion"
  | GestionDomiciliosStatusOperativoRow
  | "todos";

/** Chip geográfico visible al operador. */
export type GestionDomiciliosGeoChip = "EN_MAPA" | "SIN_COORDS";

export type GestionDomiciliosMapMode =
  | "problematic"
  | "visible"
  | "all"
  | "manual"
  | "errors";

export type GestionDomiciliosSort =
  | "requiere_accion_desc"
  | "updated_desc"
  | "domicilio_asc";

/** Campos técnicos opcionales (include_tecnico=1). No mostrar al operador común. */
export interface GestionDomiciliosRowTecnico {
  score_unificado?: number | null;
  match_strategy?: string | null;
  confidence_reason?: string | null;
  nomenclatura_estado?: string | null;
  geocode_estado?: string | null;
  motivos?: string[] | null;
}

export interface GestionDomiciliosRow {
  domicilio_id: number;
  domicilio_linea: string;
  calle_sugerida?: string | null;
  referencia_breve?: string | null;
  status_operativo: GestionDomiciliosStatusOperativoRow;
  status_operativo_label: string;
  geo_chip: GestionDomiciliosGeoChip;
  has_coordinates: boolean;
  lat?: number | null;
  lng?: number | null;
  requiere_accion: boolean;
  tecnico?: GestionDomiciliosRowTecnico | null;
}

export interface GestionDomiciliosMapPoint {
  domicilio_id: number;
  lat: number;
  lng: number;
  status_operativo: GestionDomiciliosStatusOperativoRow;
  status_operativo_label: string;
  label: string;
  geo_chip: GestionDomiciliosGeoChip;
  requiere_accion: boolean;
}

export interface GestionDomiciliosMapPointsMeta {
  returned: number;
  limit: number;
  truncated: boolean;
  total_matching: number;
  map_mode: GestionDomiciliosMapMode;
  bbox_applied: boolean;
}

export interface GestionDomiciliosSummary {
  total: number;
  requieren_accion: number;
  sin_punto: number;
  punto_dudoso: number;
  errores: number;
  manuales: number;
  geolocalizados: number;
}

export interface GestionDomiciliosPagination {
  page: number;
  page_size: number;
  total: number;
}

export interface GestionDomiciliosResponse {
  summary: GestionDomiciliosSummary;
  rows: GestionDomiciliosRow[];
  map_points: GestionDomiciliosMapPoint[];
  map_points_meta?: GestionDomiciliosMapPointsMeta | null;
  pagination: GestionDomiciliosPagination;
}

export interface GestionDomiciliosQuery {
  q?: string;
  page?: number;
  page_size?: number;
  status_operativo?: GestionDomiciliosStatusOperativo;
  include_map_points?: boolean;
  map_mode?: GestionDomiciliosMapMode;
  bbox?: string;
  sort?: GestionDomiciliosSort;
  include_tecnico?: boolean;
}

/**
 * GET /map/gestion-domicilios — cola operativa (PR6C.2+ contrato).
 * UI final aún no conectada.
 */
export const getGestionDomicilios = async (
  params?: GestionDomiciliosQuery
): Promise<GestionDomiciliosResponse> => {
  const { data } = await apiClient.get<GestionDomiciliosResponse>("/map/gestion-domicilios", {
    params: {
      ...params,
      include_map_points:
        params?.include_map_points === undefined ? undefined : params.include_map_points ? 1 : 0,
      include_tecnico:
        params?.include_tecnico === undefined ? undefined : params.include_tecnico ? 1 : 0,
    },
  });
  return data;
};
