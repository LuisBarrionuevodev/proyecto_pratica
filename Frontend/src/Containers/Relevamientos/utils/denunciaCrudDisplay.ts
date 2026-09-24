import type { IDenunciaGestionItem } from "../../../api/denunciasApi";

export function denunciaCalleDisplay(row: IDenunciaGestionItem): string | null {
  if (row.calle_estado === "OK" && row.calle_normalizada) {
    return row.calle_normalizada;
  }
  return row.calle ?? null;
}

export function denunciaNumeroDisplay(row: IDenunciaGestionItem): string | null {
  if (row.numero_tipo === "ESQUINA" && (row.numero_esquina || row.esquina_normalizada)) {
    return row.numero_esquina ?? row.esquina_normalizada ?? null;
  }
  return row.numero ?? null;
}
