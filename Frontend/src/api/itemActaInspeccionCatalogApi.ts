import { apiClient } from "./apiClient";

export type ItemActaInspeccionTipoRespuesta = "ESTADO" | "SI_NO";

export interface IItemActaInspeccionCatalogItem {
  id: number;
  codigo: string;
  nombre: string;
  orden: number;
  tipo_respuesta: ItemActaInspeccionTipoRespuesta;
}

export interface IItemActaInspeccionCatalogResponse {
  items: IItemActaInspeccionCatalogItem[];
}

export const fetchItemsActaInspeccionCatalog = async (): Promise<IItemActaInspeccionCatalogItem[]> => {
  const { data } = await apiClient.get<IItemActaInspeccionCatalogResponse>(
    "/grid/catalogs/items-acta-inspeccion"
  );
  return (data.items ?? []).map((item) => ({
    ...item,
    tipo_respuesta: item.tipo_respuesta ?? "ESTADO",
  }));
};
