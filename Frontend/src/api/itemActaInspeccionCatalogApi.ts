import { apiClient } from "./apiClient";

export interface IItemActaInspeccionCatalogItem {
  id: number;
  codigo: string;
  nombre: string;
  orden: number;
}

export interface IItemActaInspeccionCatalogResponse {
  items: IItemActaInspeccionCatalogItem[];
}

export const fetchItemsActaInspeccionCatalog = async (): Promise<IItemActaInspeccionCatalogItem[]> => {
  const { data } = await apiClient.get<IItemActaInspeccionCatalogResponse>(
    "/grid/catalogs/items-acta-inspeccion"
  );
  return data.items ?? [];
};
