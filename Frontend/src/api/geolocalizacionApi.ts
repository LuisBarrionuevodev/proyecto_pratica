import { apiClient } from "./apiClient";

export interface CalleCatalogoItem {
  id: number;
  nombre: string;
}

export interface CalleCatalogoResponse {
  items: CalleCatalogoItem[];
}

export const fetchCallesCatalogo = async (
  search?: string,
  limit: number = 20
): Promise<CalleCatalogoResponse> => {
  const params: Record<string, string> = { limit: String(limit) };
  if (search) params.search = search;
  const { data } = await apiClient.get<CalleCatalogoResponse>("/geolocalizacion/calles/catalogo", { params });
  return data;
};

export const setCalleCanon = async (
  domicilioId: number,
  calleCatalogoId: number
): Promise<{ ok: boolean }> => {
  const { data } = await apiClient.post<{ ok: boolean }>(
    `/geolocalizacion/calles/set-canon/${domicilioId}`,
    { calle_catalogo_id: calleCatalogoId }
  );
  return data;
};

export const setEsquinaCanon = async (
  domicilioId: number,
  esquinaCatalogoId: number
): Promise<{ ok: boolean }> => {
  const { data } = await apiClient.post<{ ok: boolean }>(
    `/geolocalizacion/calles/set-esquina/${domicilioId}`,
    { esquina_catalogo_id: esquinaCatalogoId }
  );
  return data;
};
