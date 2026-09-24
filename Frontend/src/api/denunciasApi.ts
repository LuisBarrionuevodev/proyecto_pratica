import { apiClient } from "./apiClient";

export interface CreateDenunciaPayload {
  fecha: string;
  calle: string;
  numero?: string | null;
  interseccion?: string | null;
  motivo: string;
}

export interface DenunciaResponse {
  id: number;
  fecha: string;
  anio: number;
  mes: number;
  domicilio_id: number;
  motivo: string;
  estado: string;
  created_by_user_id: number;
  created_at?: string | null;
  updated_at?: string | null;
  deleted_at?: string | null;
  iniciador_ruta_id: number;
}

export interface IDenunciaGestionItem {
  id: number;
  fecha: string | null;
  calle: string | null;
  calle_raw?: string | null;
  calle_cargada?: string | null;
  calle_normalizada?: string | null;
  calle_estado?: string | null;
  numero: string | null;
  numero_esquina?: string | null;
  numero_tipo?: string | null;
  esquina_normalizada?: string | null;
  esquina_raw?: string | null;
  esquina_status?: string | null;
  motivo: string | null;
  estado: string | null;
  domicilio_id?: number | null;
  iniciador_ruta_id?: number | null;
  iniciador_estado?: string | null;
  editable?: boolean;
}

export type DenunciaGestionUpdatePayload = Pick<
  IDenunciaGestionItem,
  "id" | "fecha" | "calle" | "numero" | "numero_tipo" | "motivo" | "estado"
>;

export interface IDenunciasGestionMeta {
  total: number;
  page: number;
  page_size: number;
  desde: string | null;
  hasta: string | null;
  estado: string | null;
}

export interface IDenunciasGestionResponse {
  items: IDenunciaGestionItem[];
  meta: IDenunciasGestionMeta;
}

export interface IDenunciasGestionFilters {
  desde?: string | null;
  hasta?: string | null;
  estado?: "all" | "hechas" | "no_hechas";
  page?: number;
  page_size?: number;
}

export const createDenuncia = async (
  payload: CreateDenunciaPayload
): Promise<DenunciaResponse> => {
  const { data } = await apiClient.post<DenunciaResponse>("/api/denuncias", payload);
  return data;
};

export const getDenunciasGestion = async (
  filters?: IDenunciasGestionFilters
): Promise<IDenunciasGestionResponse> => {
  const params: Record<string, string> = {};
  if (filters?.desde) params.desde = filters.desde;
  if (filters?.hasta) params.hasta = filters.hasta;
  if (filters?.estado) params.estado = filters.estado;
  if (filters?.page) params.page = String(filters.page);
  if (filters?.page_size) params.page_size = String(filters.page_size);

  const { data } = await apiClient.get<IDenunciasGestionResponse>("/api/denuncias/gestion", {
    params,
  });
  return data;
};

export const getDenunciasGestionOperativa = async (
  filters?: IDenunciasGestionFilters
): Promise<IDenunciasGestionResponse> => {
  const params: Record<string, string> = {};
  if (filters?.desde) params.desde = filters.desde;
  if (filters?.hasta) params.hasta = filters.hasta;
  if (filters?.estado) params.estado = filters.estado;
  if (filters?.page) params.page = String(filters.page);
  if (filters?.page_size) params.page_size = String(filters.page_size);

  const { data } = await apiClient.get<IDenunciasGestionResponse>("/api/denuncias/gestion-operativa", {
    params,
  });
  return data;
};

export const updateDenunciaGestion = async (
  id: number,
  body: DenunciaGestionUpdatePayload
): Promise<IDenunciaGestionItem> => {
  const { data } = await apiClient.put<IDenunciaGestionItem>(`/api/denuncias/${id}`, body);
  return data;
};

export const deleteDenunciaGestion = async (id: number): Promise<void> => {
  await apiClient.delete(`/api/denuncias/${id}`);
};
