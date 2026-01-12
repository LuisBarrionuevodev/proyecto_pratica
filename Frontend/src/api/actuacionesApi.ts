import { apiClient } from "./apiClient";
import type { IActuacion } from "../types/actuaciones";

export const getActuaciones = async (): Promise<IActuacion[]> => {
  const { data } = await apiClient.get("/actuaciones");
  return data;
};

export const createActuacion = async (body: IActuacion): Promise<IActuacion> => {
  const { data } = await apiClient.post("/actuaciones", body);
  return data;
};

export const updateActuacion = async (id: Number, body: IActuacion): Promise<IActuacion> => {
  const { data } = await apiClient.put(`/actuaciones/${id}`, body);
  return data;
};

export const deleteActuacion = async (id: number): Promise<void> => {
  await apiClient.delete(`/actuaciones/${id}`);
};
