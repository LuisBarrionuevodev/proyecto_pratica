import { apiClient } from "./apiClient";
import type { IRelevamiento } from "../types/relevamientos";

export const getRelevamientos = async (): Promise<IRelevamiento[]> => {
  const { data } = await apiClient.get<IRelevamiento[]>("/relevamientos");
  return data;
};

export const createRelevamiento = async (
  body: Omit<IRelevamiento, "id">
): Promise<IRelevamiento> => {
  const { data } = await apiClient.post("/relevamientos", body);
  return data;
};


export const updateRelevamiento = async (
  id: number,
  body: Partial<IRelevamiento>
): Promise<IRelevamiento> => {
  const { data } = await apiClient.put(`/relevamientos/${id}`, body);
  return data;
};

export const deleteRelevamiento = async (id: number): Promise<void> => {
  await apiClient.delete(`/relevamientos/${id}`);
};
