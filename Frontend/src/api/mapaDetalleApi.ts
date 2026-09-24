import { apiClient } from "./apiClient";

export type PopupKind = "actuacion" | "relevamiento";

export interface MapaPopupDetalle {
  kind: PopupKind;
  title: string;
  fecha: string | null;
  created_at: string | null;
  domicilio: string;
  inspectores: string[];
  acta_inspeccion: string | null;
  tipo: string | null;
}

export const getMapaPopupDetalle = async (
  kind: PopupKind,
  id: number
): Promise<MapaPopupDetalle> => {
  const { data } = await apiClient.get<MapaPopupDetalle>("/api/mapa-detalle/popup", {
    params: { kind, id },
  });
  return data;
};
