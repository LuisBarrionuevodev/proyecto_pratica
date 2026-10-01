import type { ICompletarTrabajoPendienteRow } from "../../../api/completarTrabajoApi";
import { formatActuacionListDomicilioLinea } from "../../../utils/formatDomicilioLineaVisible";
import { tipoIniciadorDesdeCodigoApi } from "../../RutasTrabajo/planificacion/utils/iniciadorDisplay";
import { splitCommaList } from "../../Actuaciones/Components/bandejaTableCells";

export function completarTrabajoDomicilioLinea(row: ICompletarTrabajoPendienteRow): string {
  const t =
    row.domicilio_texto?.trim() || formatActuacionListDomicilioLinea(row).trim() || "";
  return t || "—";
}

export function completarTrabajoOrigenTipoSegments(row: ICompletarTrabajoPendienteRow): string[] {
  const segs: string[] = [];
  const origenLabel = tipoIniciadorDesdeCodigoApi(row.tipo_iniciador);
  const tipo = (row.tipo_actuacion ?? "").trim();
  if (origenLabel) segs.push(`Origen: ${origenLabel}`);
  if (tipo) segs.push(`Tipo: ${tipo}`);
  return segs;
}

export function completarTrabajoTitularLinea(row: ICompletarTrabajoPendienteRow): string {
  const local = (row.nombre_local ?? "").trim();
  if (local) return local;
  const rubro = (row.rubro_nombre ?? "").trim();
  const rs = (row.razon_social ?? "").trim();
  if (rs) return rs;
  const ap = (row.contrib_apellido ?? "").trim();
  const nom = (row.contrib_nombre ?? "").trim();
  const persona = [ap, nom].filter(Boolean).join(" ");
  if (persona) return persona;
  return rubro || "—";
}

/** Etiqueta de estado para UI (no altera el valor persistido). */
export function completarTrabajoEstadoLabel(row: ICompletarTrabajoPendienteRow): string {
  const raw = (row.estado_operativo ?? row.iniciador_estado ?? "").trim();
  if (!raw) return "—";
  if (raw === "EN_PROCESO") return "EN PROCESO";
  return raw;
}

export function completarTrabajoInspectoresNombres(row: ICompletarTrabajoPendienteRow): string[] {
  const texto = row.inspectores_texto?.trim();
  if (texto) return splitCommaList(texto);
  return [row.inspector1, row.inspector2, row.inspector3].filter((s): s is string =>
    Boolean(s?.trim())
  );
}
