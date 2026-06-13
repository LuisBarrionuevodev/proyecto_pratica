import { apiClient } from "./apiClient";

export interface IRubroCatalogItem {
  id: number;
  nombre: string;
  /** Siempre true hasta migración de columna `activo` en DB. */
  activo?: boolean;
}

export interface IRubrosCatalogResponse {
  items: IRubroCatalogItem[];
}

export interface IRubrosCatalogParams {
  q?: string;
  limit?: number;
}

/**
 * Catálogo de rubros desde DB (GET /catalogos/rubros).
 */
export async function fetchRubrosCatalogo(
  params?: IRubrosCatalogParams,
  signal?: AbortSignal
): Promise<IRubroCatalogItem[]> {
  const query: Record<string, string> = {};
  if (params?.q) query.q = params.q;
  if (params?.limit) query.limit = String(params.limit);
  const { data } = await apiClient.get<IRubrosCatalogResponse>("/catalogos/rubros", {
    params: query,
    signal,
  });
  return data.items ?? [];
}
