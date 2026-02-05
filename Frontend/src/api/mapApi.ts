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
  numero_raw: string | null;
  numero_tipo: string | null;
  esquina_normalizada: string | null;
  calle_status: string | null;
  esquina_status: string | null;
  geo_status: string | null;
  error_msg: string | null;
  lat: number | null;
  lng: number | null;
  last_actuacion_id?: number | null;
  actuaciones_count?: number;
  last_relevamiento_id?: number | null;
  relevamientos_count?: number;
}

export const getMapPoints = async (params?: Record<string, any>) => {
  const { data } = await apiClient.get<MapPointFeatureCollection>("/map/puntos", { params });
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
