import type { DenunciaGestionUpdatePayload, IDenunciaGestionItem } from "../../../api/denunciasApi";
import {
  domicilioCalleCargadaEditable,
  domicilioEsTipoEsquina,
  domicilioNumeroEditable,
} from "../../../utils/domicilioCalleUi";

/**
 * Arma payload PUT de gestión con domicilio editable y sin metadata stale.
 */
export function applyDenunciaDomicilioSubmitGuard(
  row: IDenunciaGestionItem,
  originalRow?: IDenunciaGestionItem | null
): DenunciaGestionUpdatePayload {
  const baseline = originalRow ?? row;
  const baselineCalle = domicilioCalleCargadaEditable(baseline);
  const baselineNumero = domicilioNumeroEditable(baseline);
  const editedCalle = String(row.calle ?? "").trim();
  const editedNumero = String(row.numero ?? "").trim();

  const isEsquina = domicilioEsTipoEsquina(row);
  const numero_tipo = isEsquina ? "ESQUINA" : "NUMERO";
  const calle = editedCalle || baselineCalle;
  const numero = editedNumero || baselineNumero;

  return {
    id: row.id,
    fecha: row.fecha,
    calle: calle || "",
    numero: numero || "",
    numero_tipo,
    motivo: row.motivo ?? "",
    estado: row.estado ?? "ABIERTA",
  };
}
