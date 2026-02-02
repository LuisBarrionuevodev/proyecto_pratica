import { apiClient } from "./apiClient";

interface CallesCatalogoItem {
  id: number;
  nombre?: string;
  nombre_canonico?: string;
}

interface CallesCatalogoResponse {
  items: CallesCatalogoItem[];
}

const mapNombreCanonico = (items: CallesCatalogoItem[] = []): string[] =>
  items
    .map((item) => item.nombre_canonico ?? item.nombre ?? "")
    .filter((value) => value.length > 0);

const fetchFromGeolocalizacion = async (limit: number): Promise<string[]> => {
  const params: Record<string, string> = { limit: String(limit) };
  const { data } = await apiClient.get<CallesCatalogoResponse>(
    "/geolocalizacion/calles/catalogo",
    { params }
  );
  return mapNombreCanonico(data.items);
};

const fetchFromGridCatalogs = async (): Promise<string[]> => {
  const { data } = await apiClient.get<CallesCatalogoResponse>("/grid/catalogs/calles");
  return mapNombreCanonico(data.items);
};

export const fetchCallesCatalogo = async (limit: number = 200): Promise<string[]> => {
  try {
    return await fetchFromGeolocalizacion(limit);
  } catch (error: any) {
    if (error?.response?.status === 404) {
      return fetchFromGridCatalogs();
    }
    throw error;
  }
};
