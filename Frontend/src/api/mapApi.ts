import { apiClient } from "./apiClient";

export interface MapPointFeature {
  type: "Feature";
  geometry: { type: "Point"; coordinates: [number, number] };
  properties: Record<string, any>;
}

export interface MapPointFeatureCollection {
  type: "FeatureCollection";
  features: MapPointFeature[];
}

export interface HeatmapItem {
  lat: number;
  lng: number;
  weight: number;
}

export interface DistrictMetricItem {
  distrito_id: number;
  nombre: string | null;
  value: number;
}

export interface PendingItem {
  domicilio_id: number;
  calle_raw: string | null;
  calle_normalizada: string | null;
  calle_catalogo_id?: number | null;
  numero_raw: string | null;
  numero?: string | null;
  numero_tipo: string | null;
  esquina_catalogo_id?: number | null;
  esquina_normalizada: string | null;
  esquina_raw?: string | null;
  calle_status: string | null;
  esquina_status: string | null;
  geo_status: string | null;
  score?: number | null;
  quality?: string | null;
  provider?: string | null;
  source?: string | null;
  addr_hash?: string | null;
  error_msg: string | null;
  lat: number | null;
  lng: number | null;
  last_actuacion_id?: number | null;
  actuaciones_count?: number;
  last_relevamiento_id?: number | null;
  relevamientos_count?: number;
  /** Clasificación compuesta PR2 (solo con ``slice=`` en backend). */
  nomenclatura_estado?: string | null;
  geocode_estado?: string | null;
  estado_compuesto?: string | null;
  score_unificado?: number | null;
  slice?: string | null;
  motivos?: string[] | null;
}

export const getMapPoints = async (params?: Record<string, any>) => {
  const { data } = await apiClient.get<MapPointFeatureCollection>("/map/puntos", { params });
  return data;
};

export const getMapPointsV2 = async (params?: Record<string, any>) => {
  const { data } = await apiClient.get<MapPointFeatureCollection>("/map/points", { params });
  return data;
};

/** Mapa operativo DIGITALIZA — pendientes (iniciadores + EN_PROCESO). */
export const getMapOperativoPendientesFC = async (params: {
  desde: string;
  hasta: string;
  distrito_id?: number;
  tipo?: string;
  inspector_id?: number;
  /** Query opaca (p. ej. timestamp) para evitar respuesta cacheada del navegador al refrescar. */
  _?: number;
}) => {
  const { data } = await apiClient.get<MapPointFeatureCollection>("/map/operativo/pendientes", { params });
  return data;
};

/** Mapa operativo DIGITALIZA — realizados (visita realizada / ítem finalizado). */
export const getMapOperativoRealizadosFC = async (params: {
  desde: string;
  hasta: string;
  distrito_id?: number;
  tipo?: string;
  inspector_id?: number;
  /** Clausura / decomiso / ambos (mismo contrato que UI mapa operativo). */
  definicion?: string;
  _?: number;
}) => {
  const { data } = await apiClient.get<MapPointFeatureCollection>("/map/operativo/realizados", { params });
  return data;
};

export const getMapHeatmap = async (params?: Record<string, any>) => {
  const { data } = await apiClient.get<{ items: HeatmapItem[] }>("/map/heatmap", { params });
  return data.items;
};

export const getMapDistricts = async (params?: Record<string, any>) => {
  const { data } = await apiClient.get<{ items: DistrictMetricItem[] }>("/map/distritos", { params });
  return data.items;
};

export const getMapPendientes = async (params?: Record<string, any>) => {
  const { data } = await apiClient.get<{ items: PendingItem[] }>("/map/pendientes", { params });
  return data.items;
};

export const getMapDetails = async (domicilioId: number, params?: Record<string, any>) => {
  const { data } = await apiClient.get(`/map/details/${domicilioId}`, { params });
  return data;
};

export const saveManualGeocode = async (payload: {
  domicilio_id: number;
  lat: number;
  lng: number;
  do_reverse?: boolean;
}) => {
  const { data } = await apiClient.post("/api/map/geocode/manual", payload);
  return data;
};
