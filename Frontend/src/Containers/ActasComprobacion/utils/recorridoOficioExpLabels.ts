import type { IComprobacionRecorridoRow } from "../../../api/actuacionesComprobacionActasApi";

export type OficioRecorridoResumenItem = NonNullable<IComprobacionRecorridoRow["oficios_resumen"]>[number];

function parNumAnio(num: string | null | undefined, anio: number | string | null | undefined): string {
  const n = (num ?? "").toString().trim();
  const a = anio != null ? String(anio) : "";
  if (!n && !a) return "";
  return [n, a].filter(Boolean).join("/");
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

function recOficioNumCompact(r: IComprobacionRecorridoRow): string {
  const n = (r.oficio_numero ?? "").toString().trim();
  const a = r.oficio_anio != null ? String(r.oficio_anio) : "";
  if (!n && !a) return "—";
  return [n, a].filter(Boolean).join("/");
}

/** Chips de oficio(s) con expediente asociado para columna Recorrido. */
export function recOficiosExpChips(r: IComprobacionRecorridoRow): string[] {
  const resumen = r.oficios_resumen ?? [];
  if (resumen.length > 0) {
    const chips = resumen.map(recOficioExpItemLabel).filter((s) => s.length > 0);
    if (chips.length > 0) return chips;
  }
  const texto = (r.oficios_texto ?? "").toString().trim();
  if (texto) return [`Oficios: ${texto}`];
  const on = recOficioNumCompact(r);
  if (on !== "—") return [`Oficio ${on}`];
  return ["Oficio —"];
}

/** Chips: acta, oficios+expedientes, motivo. */
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
