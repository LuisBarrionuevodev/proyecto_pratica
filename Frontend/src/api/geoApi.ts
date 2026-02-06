import { apiClient } from "./apiClient";

export interface GeoPendingItem {
  domicilio_id: number;
  calle_normalizada?: string | null;
  numero?: string | null;
  esquina_normalizada?: string | null;
  ciudad?: string | null;
  rubro_id?: number | null;
  contribuyente_id?: number | null;
  geo_status?: string | null;
  error_msg?: string | null;
  checked_at?: string | null;
}

export const getGeoPending = async () => {
  const { data } = await apiClient.get<{ items: GeoPendingItem[] }>("/geo/pending");
  return data.items;
};

export const retryGeo = async (domicilioId: number) => {
  const { data } = await apiClient.post(`/geo/${domicilioId}/retry`);
  return data;
};

export const setGeoManual = async (domicilioId: number, lat: number, lng: number) => {
  const { data } = await apiClient.post(`/geo/${domicilioId}/manual`, { lat, lng });
  return data;
};

export const reverseGeo = async (domicilioId: number, lat: number, lng: number) => {
  const { data } = await apiClient.post(`/geo/${domicilioId}/reverse`, { lat, lng });
  return data;
};
