import type { IDenunciaGestionItem } from "../../../api/denunciasApi";
import { domicilioRowParaEdicionCalle } from "../../../utils/domicilioCalleUi";

/**
 * Hidrata fila de bandeja para edición en modal (calle/número humanos, no claves técnicas).
 */
export function denunciaRowParaEdicion(row: IDenunciaGestionItem): IDenunciaGestionItem {
  return domicilioRowParaEdicionCalle({ ...row });
}

/**
 * Patch al cambiar modo número/esquina en el modal.
 */
export function buildDenunciaNumeroTipoDraftPatch(
  editorMode: "NUMERO" | "ESQUINA",
  current?: Pick<IDenunciaGestionItem, "numero" | "numero_tipo">
): Partial<IDenunciaGestionItem> {
  const patch: Partial<IDenunciaGestionItem> = { numero_tipo: editorMode };
  if (editorMode === "NUMERO") {
    if ((current?.numero_tipo ?? "").toUpperCase() === "ESQUINA") {
      patch.numero = "";
    }
  }
  return patch;
}
