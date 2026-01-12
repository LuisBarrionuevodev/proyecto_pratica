import { apiClient } from "./apiClient";
import type { IPoligono, IPoligonoCreate } from "../types/poligonos";



export const getPoligonos = async (): Promise<IPoligono[]> => {
  const { data } = await apiClient.get<IPoligono[]>("/poligonos");
  return data;
};

export const createPoligono = async (body: IPoligonoCreate): Promise<IPoligono> => {
  const { data } = await apiClient.post("/poligonos", body);
  return data;
};

export const updatePoligono = async (
  id: number,
  body: Partial<{
    nombre: string;
    descripcion: string;
    wkt: string;
  }>
): Promise<IPoligono> => {
  const { data } = await apiClient.put(`/poligonos/${id}`, body);
  return data;
};

export const deletePoligono = async (id: number) => {
  return apiClient.delete(`/poligonos/${id}`);
};
