import type { IComprobacionRecorridoRow } from "../../../api/actuacionesComprobacionActasApi";
import { humanizarCumplimientoOficio, humanizarTipoVisitaRecorrido } from "./documentalLabelFormat";

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

const MOTIVO_NO_REALIZADO_LABEL: Record<string, string> = {
  LOCAL_CERRADO: "Local cerrado",
  INCLEMENCIA_TIEMPO: "Inclemencia tiempo",
  NO_EXISTE_LOCAL: "No existe local",
  OTRO: "Otro",
};

function motivoNoRealizadoLabel(raw: string | null | undefined): string {
  const key = (raw ?? "").toString().trim().toUpperCase();
  if (!key) return "";
  return MOTIVO_NO_REALIZADO_LABEL[key] ?? key.replace(/_/g, " ").toLowerCase();
}
export function recorridoVisitaResumenLinea(item: OficioRecorridoResumenItem): string {
  const texto = (item.visita_resumen_texto ?? "").toString().trim();
  if (texto) return texto;

  const head = oficioSoloTexto(item) || "Oficio —";
  const estadoIni = (item.estado_iniciador ?? "").toString().trim().toUpperCase();
  const estadoEjec = (item.estado_ejecucion ?? "").toString().trim().toUpperCase();
  const ejec = item.ejecucion_reinspeccion as { tipo_inspeccion_labrada?: string | null } | null | undefined;
  const tipo =
    humanizarTipoVisitaRecorrido(ejec?.tipo_inspeccion_labrada) !== "—"
      ? humanizarTipoVisitaRecorrido(ejec?.tipo_inspeccion_labrada)
      : humanizarTipoVisitaRecorrido(item.tipo_iniciador);

  if (!item.iniciador_id && !estadoIni) {
    return `${head} · Sin inspección programada`;
  }
  if (estadoEjec === "NO_REALIZADO") {
    const motivo = motivoNoRealizadoLabel(item.motivo_no_realizado);
    return motivo ? `${head} · No realizada · ${motivo}` : `${head} · No realizada`;
  }
  if (estadoIni === "CUMPLIDO" || estadoEjec === "REALIZADO" || item.conclusion) {
    return tipo !== "—" ? `${head} · ${tipo} · Realizada` : `${head} · Realizada`;
  }
  if (estadoIni === "PENDIENTE") {
    return `${head} · Pendiente reinspección`;
  }
  const conc = textoConclusion(item);
  if (conc) return `${head} · ${conc}`;
  return head;
}

/** Chips para columna Recorrido: una línea por oficio/visita. */
export function recorridoColumnChips(r: IComprobacionRecorridoRow): string[] {
  const resumen = r.oficios_resumen ?? [];
  if (resumen.length > 0) {
    return resumen.map(recorridoVisitaResumenLinea).filter(Boolean);
  }
  const fallback = (r.estado_recorrido ?? "").toString().trim();
  return fallback ? [fallback] : ["Sin inspección programada"];
}

export function recorridoColumnSortKey(r: IComprobacionRecorridoRow): string {
  return recorridoColumnChips(r).join(" | ");
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

function oficioNumeroCompacto(item: OficioRecorridoResumenItem): string {
  return (
    (item.oficio_texto ?? "").trim() ||
    parNumAnio(item.numero_oficio ?? item.numero, item.anio_oficio ?? item.anio)
  );
}

function expedienteNumeroCompacto(item: OficioRecorridoResumenItem): string {
  return (
    (item.expediente_texto ?? "").trim() ||
    parNumAnio(item.numero_expediente, item.anio_expediente)
  );
}

function joinUnique(parts: string[]): string {
  return [...new Set(parts.map((p) => p.trim()).filter(Boolean))].join(" · ");
}

/** Expediente de envío de acta (único): `66234/2026`. */
export function recorridoExpedienteEnvioTexto(r: IComprobacionRecorridoRow): string {
  return parNumAnio(r.expediente_numero, r.expediente_anio);
}

/** Números de oficio agregados: `432/2026 · 1989/2026`. */
export function recorridoOficiosNumerosTexto(r: IComprobacionRecorridoRow): string {
  const resumen = r.oficios_resumen ?? [];
  if (resumen.length > 0) {
    return joinUnique(resumen.map(oficioNumeroCompacto));
  }
  return parNumAnio(r.oficio_numero, r.oficio_anio);
}

/** Expedientes vinculados a cada oficio. */
export function recorridoExpedientesOficioNumerosTexto(r: IComprobacionRecorridoRow): string {
  const resumen = r.oficios_resumen ?? [];
  if (resumen.length > 0) {
    return joinUnique(resumen.map(expedienteNumeroCompacto));
  }
  return "";
}

/** Expedientes de respuesta agregados. */
export function recorridoExpedientesRespuestaNumerosTexto(r: IComprobacionRecorridoRow): string {
  const resumen = r.oficios_resumen ?? [];
  const fromResumen = resumen.map(expedienteNumeroCompacto).filter(Boolean);
  const rowFallback = parNumAnio(
    r.expediente_respuesta_numero != null ? String(r.expediente_respuesta_numero) : null,
    r.expediente_respuesta_anio
  );
  return joinUnique([...fromResumen, rowFallback]);
}

/** Oficios con expediente de respuesta asociado. */
export function recorridoOficiosConRespuestaTexto(r: IComprobacionRecorridoRow): string {
  const resumen = r.oficios_resumen ?? [];
  if (resumen.length > 0) {
    return joinUnique(
      resumen
        .filter((item) => expedienteNumeroCompacto(item))
        .map(oficioNumeroCompacto)
    );
  }
  return "";
}

export function recorridoCausasExportTexto(r: IComprobacionRecorridoRow): string {
  const resumen = r.oficios_resumen ?? [];
  const fromResumen = resumen
    .map((item) => (item.causa ?? "").toString().trim())
    .filter(Boolean);
  const legacy = ((r as { oficio_causa?: string | null }).oficio_causa ?? "").toString().trim();
  return joinUnique([...fromResumen, legacy]);
}

export function recorridoJuzgadosExportTexto(r: IComprobacionRecorridoRow): string {
  const resumen = r.oficios_resumen ?? [];
  const fromResumen = resumen
    .map((item) => (item.juzgado_nombre ?? "").toString().trim())
    .filter(Boolean);
  const legacy = ((r as { juzgado_nombre?: string | null }).juzgado_nombre ?? "").toString().trim();
  return joinUnique([...fromResumen, legacy]);
}

/** Estado por visita/oficio para export. */
export function recorridoEstadoVisitasExportTexto(r: IComprobacionRecorridoRow): string {
  return recorridoColumnChips(r).join(" / ");
}

function oficioSoloTexto(item: OficioRecorridoResumenItem): string {
  const ot =
    (item.oficio_texto ?? "").trim() ||
    parNumAnio(item.numero_oficio ?? item.numero, item.anio_oficio ?? item.anio);
  return ot ? `Oficio ${ot}` : "";
}

function expedienteSoloTexto(item: OficioRecorridoResumenItem): string {
  const et =
    (item.expediente_texto ?? "").trim() ||
    parNumAnio(item.numero_expediente, item.anio_expediente);
  return et ? `Exp. ${et}` : "";
}

/**
 * Texto agregado de oficios para export Excel/PDF (recorrido).
 */
export function recorridoOficiosExportTexto(r: IComprobacionRecorridoRow): string {
  const resumen = r.oficios_resumen ?? [];
  if (resumen.length > 0) {
    return resumen.map(oficioSoloTexto).filter(Boolean).join(" · ");
  }
  const texto = (r.oficios_texto ?? "").toString().trim();
  if (texto) return texto.toLowerCase().startsWith("oficio") ? texto : `Oficio ${texto}`;
  const on = parNumAnio(r.oficio_numero, r.oficio_anio);
  return on ? `Oficio ${on}` : "";
}

/**
 * Texto agregado de expedientes para export Excel/PDF (recorrido).
 */
export function recorridoExpedientesExportTexto(r: IComprobacionRecorridoRow): string {
  const resumen = r.oficios_resumen ?? [];
  if (resumen.length > 0) {
    const parts = resumen.map(expedienteSoloTexto).filter(Boolean);
    return [...new Set(parts)].join(" · ");
  }
  const parts: string[] = [];
  const envio = parNumAnio(r.expediente_numero, r.expediente_anio);
  if (envio) parts.push(`Exp. envío ${envio}`);
  const resp = parNumAnio(
    r.expediente_respuesta_numero != null ? String(r.expediente_respuesta_numero) : null,
    r.expediente_respuesta_anio
  );
  if (resp) parts.push(`Exp. resp. ${resp}`);
  return parts.join(" · ");
}
