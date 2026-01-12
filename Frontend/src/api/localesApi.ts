import { apiClient } from "./apiClient"; // tu axios preconfigurado
import type { ILocal } from "../types/Local";

export const getLocales = async (): Promise<ILocal[]> => {
  const { data } = await apiClient.get<ILocal[]>("/locales");
  return data;
};

export const createLocal = async (formData: FormData): Promise<ILocal> => {
  const { data } = await apiClient.post("/locales", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
};

export const updateLocal = async (id: number, body: Partial<ILocal>) => {
  const { data } = await apiClient.put(`/locales/${id}`, body);
  return data;
};

export const updateLocalPosition = async (id: number, lat: number, lng: number) => {
  const { data } = await apiClient.put(`/locales/${id}/position`, { lat, lng });
  return data;
};

export const deleteLocal = async (id: number) => {
  return apiClient.delete(`/locales/${id}`);
};

