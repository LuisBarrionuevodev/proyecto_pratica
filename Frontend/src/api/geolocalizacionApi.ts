import { apiClient } from "./apiClient";

export interface CalleCatalogoItem {
  id: number;
  nombre: string;
}

export interface CalleCatalogoResponse {
  items: CalleCatalogoItem[];
}

/**
 * Catálogo de calles (fuente canónica: DB vía backend).
 * Búsqueda incremental: enviar `search` con el texto tecleado; el servidor filtra por letras.
 */
export const fetchCallesCatalogo = async (
  search?: string,
  limit: number = 20
): Promise<CalleCatalogoResponse> => {
  const params: Record<string, string> = { limit: String(limit) };
  if (search && search.trim()) params.search = search.trim();
  const { data } = await apiClient.get<CalleCatalogoResponse>("/geolocalizacion/calles/catalogo", { params });
  return data;
};

export interface DistritoCatalogoItem {
  id: number;
  codigo: number | null;
  nombre: string;
}

export interface DistritoCatalogoResponse {
  items: DistritoCatalogoItem[];
}

/**
 * Catálogo de distritos (tabla `distrito`), ordenado por nombre.
 */
export const fetchDistritosCatalogo = async (): Promise<DistritoCatalogoResponse> => {
  const { data } = await apiClient.get<DistritoCatalogoResponse>("/geolocalizacion/distritos/catalogo");
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

export const setNumeroEsquina = async (
  domicilioId: number,
  numero: string,
  numeroTipo?: string | null
): Promise<{ ok: boolean }> => {
  const { data } = await apiClient.post<{ ok: boolean }>(
    `/geolocalizacion/calles/set-numero/${domicilioId}`,
    { numero, numero_tipo: numeroTipo || null }
  );
  return data;
};

/** Payload para POST guardar-nomenclatura (calle/esquina híbrido). */
export type GuardarNomenclaturaCalle =
  | { mode: "CATALOGO"; calle_catalogo_id: number }
  | { mode: "MANUAL"; calle_texto: string };

export type GuardarNomenclaturaEsquina =
  | { mode: "CATALOGO"; esquina_catalogo_id: number }
  | { mode: "MANUAL" };

export interface GuardarNomenclaturaBody {
  calle: GuardarNomenclaturaCalle;
  numero: string;
  numero_tipo: "NUMERO" | "ESQUINA";
  esquina?: GuardarNomenclaturaEsquina;
}

export interface GuardarNomenclaturaResponse {
  ok: boolean;
  domicilio_id: number;
  calle: {
    mode: string;
    calle: string;
    calle_catalogo_id: number | null;
    calle_normalizada: string | null;
    calle_norm_status: string | null;
  };
  numero: string;
  numero_tipo: string | null;
  esquina?: {
    mode: string;
    esquina_catalogo_id: number | null;
    esquina_normalizada: string | null;
    esquina_norm_status: string | null;
  } | null;
}

/**
 * Guardado unificado de nomenclatura (catálogo o manual por eje).
 * Un solo commit en backend; reemplaza el encadenamiento set-numero + set-canon + set-esquina.
 */
export const guardarNomenclaturaHibrida = async (
  domicilioId: number,
  body: GuardarNomenclaturaBody
): Promise<GuardarNomenclaturaResponse> => {
  const { data } = await apiClient.post<GuardarNomenclaturaResponse>(
    `/geolocalizacion/calles/guardar-nomenclatura/${domicilioId}`,
    body
  );
  return data;
};
