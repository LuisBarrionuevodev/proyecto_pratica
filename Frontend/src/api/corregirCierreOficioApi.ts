import { apiClient } from "./apiClient";
import type { ActaCanalQuitarTipo, IActuacionListItem } from "./actuacionesListApi";

export type CorregirCierreOficioBody = {
  tipo_actuacion: string;
  resultado_cumplimiento_oficio?: string | null;
  contraproducencia?: string | null;
  realizo_nueva_inspeccion?: boolean | null;
  actas_a_quitar?: ActaCanalQuitarTipo[];
};

/**
 * Corrige resultado operativo de una actuación de circuito REINSPECCION_OFICIO.
 */
export async function corregirCierreOficio(
  actuacionId: number,
  body: CorregirCierreOficioBody
): Promise<IActuacionListItem> {
  const { data } = await apiClient.post<IActuacionListItem>(
    `/actuaciones/${actuacionId}/corregir-cierre-oficio`,
    body
  );
  return data;
}
