import type { IComprobacionRecorridoRow } from "../../../api/actuacionesComprobacionActasApi";
import { humanizarCumplimientoOficio } from "./documentalLabelFormat";

export type OficioRecorridoResumenItem = NonNullable<IComprobacionRecorridoRow["oficios_resumen"]>[number];

function parNumAnio(num: string | null | undefined, anio: number | string | null | undefined): string {
  const n = (num ?? "").toString().trim();
  const a = anio != null ? String(anio) : "";
  if (!n && !a) return "";
  return [n, a].filter(Boolean).join("/");
}

function textoOt(item: OficioRecorridoResumenItem): string {
  const ot = (item.orden_trabajo_numero ?? item.orden_trabajo ?? "").toString().trim();
  return ot || "";
}

function textoConclusion(item: OficioRecorridoResumenItem): string {
  const conc = (item.conclusion ?? "").toString().trim();
  if (conc) return conc;
  const res = humanizarCumplimientoOficio(item.resultado_cumplimiento_oficio ?? item.resultado);
  return res !== "—" ? res : "";
}

/** Etiqueta compacta: ``Oficio 3489/2026 · Exp. 012388/2026``. */
export function recOficioExpItemLabel(item: OficioRecorridoResumenItem): string {
  const ot = (item.oficio_texto ?? "").trim() || parNumAnio(item.numero_oficio ?? item.numero, item.anio_oficio ?? item.anio);
  const et =
    (item.expediente_texto ?? "").trim() ||
    parNumAnio(item.numero_expediente, item.anio_expediente);
  if (ot && et) return `Oficio ${ot} · Exp. ${et}`;
  if (ot) return `Oficio ${ot}`;
  return "";
}

/** Chips por oficio: cabecera + OT + conclusión (mismo formato para todos). */
export function recOficioExpDetalleChips(item: OficioRecorridoResumenItem): string[] {
  const chips: string[] = [];
  const head = recOficioExpItemLabel(item);
  if (head) chips.push(head);
  const ot = textoOt(item);
  chips.push(ot ? `OT: ${ot}` : "OT: Sin OT");
  const conc = textoConclusion(item);
  chips.push(conc ? `Conclusión: ${conc}` : "Conclusión: Sin conclusión");
  return chips;
}

function recOficioNumCompact(r: IComprobacionRecorridoRow): string {
  const n = (r.oficio_numero ?? "").toString().trim();
  const a = r.oficio_anio != null ? String(r.oficio_anio) : "";
  if (!n && !a) return "—";
  return [n, a].filter(Boolean).join("/");
}

/** Chips de oficio(s) con expediente, OT y conclusión para columna Recorrido. */
export function recOficiosExpChips(r: IComprobacionRecorridoRow): string[] {
  const resumen = r.oficios_resumen ?? [];
  if (resumen.length > 0) {
    return resumen.flatMap(recOficioExpDetalleChips);
  }
  const texto = (r.oficios_texto ?? "").toString().trim();
  if (texto) return [`Oficios: ${texto}`];
  const on = recOficioNumCompact(r);
  if (on !== "—") return [`Oficio ${on}`];
  return ["Oficio —"];
}

/** Chips: acta, oficios+expedientes+OT+conclusión, motivo. */
export function recCompOficioExpMotivoChips(r: IComprobacionRecorridoRow): string[] {
  const n = (r.acta_comprobacion_num ?? "").toString().trim();
  const comp = n ? `Comp. ${n}` : "Comp. —";
  const oficioExp = recOficiosExpChips(r);
  const inf = (r.comprobacion_motivo ?? "").toString().trim();
  return [comp, ...oficioExp, inf || "Sin infracción o motivo cargado"];
}

export function recCompOficioExpMotivoSortKey(r: IComprobacionRecorridoRow): string {
  return recCompOficioExpMotivoChips(r).join(" | ");
}
