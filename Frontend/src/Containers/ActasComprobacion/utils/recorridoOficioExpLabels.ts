import type {
  IComprobacionRecorridoDetalle,
  IComprobacionRecorridoRow,
} from "../../../api/actuacionesComprobacionActasApi";
import { formatActuacionListDomicilioLinea } from "../../../utils/formatDomicilioLineaVisible";
import {
  hydrateMotivosComprobacion,
  motivosComprobacionTexto,
  type MotivosComprobacionSource,
} from "../../../utils/motivosComprobacion";
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

/** Campos mínimos para el estado de cierre documental de un oficio. */
export type CierreSeguimientoOficioFuente = {
  resultado_cumplimiento_oficio?: string | null;
  resultado?: string | null;
  ejecucion_reinspeccion?: unknown;
  estado_iniciador?: string | null;
  estado_ejecucion?: string | null;
  iniciador_id?: number | null;
};

function resultadoCumplimientoOficioKey(item: CierreSeguimientoOficioFuente): string {
  return String(item.resultado_cumplimiento_oficio ?? item.resultado ?? "")
    .trim()
    .toUpperCase();
}

function oficioTieneVisitaReinspeccion(item: CierreSeguimientoOficioFuente): boolean {
  const estadoIni = String(item.estado_iniciador ?? "").trim().toUpperCase();
  const estadoEjec = String(item.estado_ejecucion ?? "").trim().toUpperCase();
  const ejec = item.ejecucion_reinspeccion;
  const ejecUtil = ejec != null && typeof ejec === "object" && Object.keys(ejec).length > 0;
  return ejecUtil || estadoIni === "CUMPLIDO" || estadoEjec === "REALIZADO";
}

/**
 * Chip compacto de resultado / seguimiento por oficio.
 * No infiere Cumple/No cumple si no hay resultado persistido.
 */
export function resultadoSeguimientoOficioLabel(item: CierreSeguimientoOficioFuente): string {
  const res = resultadoCumplimientoOficioKey(item);
  if (res === "CUMPLE") return "Cumple";
  if (res === "NO_CUMPLE") return "No cumple";
  if (oficioTieneVisitaReinspeccion(item)) return "Reinspección realizada";
  const estadoIni = String(item.estado_iniciador ?? "").trim().toUpperCase();
  if (item.iniciador_id != null || estadoIni === "PENDIENTE") return "Pendiente de reinspección";
  return "—";
}

/** Columna Recorrido «Resultado / seguimiento»: una línea por oficio, sin mezclar resultados. */
export function recorridoResultadoSeguimientoChips(r: IComprobacionRecorridoRow): string[] {
  const resumen = r.oficios_resumen ?? [];
  if (resumen.length === 0) return ["—"];
  if (resumen.length === 1) return [resultadoSeguimientoOficioLabel(resumen[0])];
  return resumen.map((item) => {
    const of = (item.oficio_texto ?? "").trim();
    const lab = resultadoSeguimientoOficioLabel(item);
    return of ? `${of} · ${lab}` : lab;
  });
}

export function recorridoResultadoSeguimientoSortKey(r: IComprobacionRecorridoRow): string {
  return recorridoResultadoSeguimientoChips(r).join(" | ");
}

export type EstadoTramiteRecorridoFila = { etiqueta: string; valor: string };

function textoOGuion(val: unknown): string {
  const t = val == null ? "" : String(val).trim();
  return t || "—";
}

function inspectoresDesdeEjecucion(ejec: Record<string, unknown> | null | undefined): string {
  if (!ejec) return "";
  const t = String(ejec.inspectores_texto ?? "").trim();
  if (t) return t;
  return [ejec.inspector1, ejec.inspector2, ejec.inspector3]
    .map((s) => String(s ?? "").trim())
    .filter(Boolean)
    .join(" · ");
}

/**
 * Resumen visible «Estado del trámite» (modal historial documental).
 * No mezcla resultados de oficios distintos ni inventa Cumple/No cumple.
 */
export function filasEstadoTramiteRecorrido(
  row: IComprobacionRecorridoRow,
  detalle: {
    oficio?: { numero_oficio?: string | null; anio?: number | null } | null;
    resultado_final?: { estado_recorrido?: string | null; tipo_visita?: string | null } | null;
    oficios_resumen?: IComprobacionRecorridoRow["oficios_resumen"];
    reinspeccion_por_oficio?: Record<string, unknown> | null;
  } | null
): EstadoTramiteRecorridoFila[] {
  const resumen = (detalle?.oficios_resumen ?? row.oficios_resumen ?? []) as OficioRecorridoResumenItem[];
  const estadoActual =
    textoOGuion(detalle?.resultado_final?.estado_recorrido) !== "—"
      ? textoOGuion(detalle?.resultado_final?.estado_recorrido)
      : textoOGuion(row.estado_recorrido);

  const oficiosTexto = resumen
    .map((item) => (item.oficio_texto ?? "").trim())
    .filter(Boolean);
  if (oficiosTexto.length === 0) {
    const n = (detalle?.oficio?.numero_oficio ?? row.oficio_numero ?? "").toString().trim();
    const a = detalle?.oficio?.anio ?? row.oficio_anio;
    const compact = n || a != null ? [n, a != null ? String(a) : ""].filter(Boolean).join("/") : "";
    if (compact) oficiosTexto.push(compact);
  }

  const ejecGlobal = (detalle?.reinspeccion_por_oficio as { ejecucion_reinspeccion?: Record<string, unknown> | null } | null)
    ?.ejecucion_reinspeccion;
  const ejecItem = resumen
    .map((item) => item.ejecucion_reinspeccion as Record<string, unknown> | null | undefined)
    .find((ej) => ej != null && typeof ej === "object" && Object.keys(ej).length > 0);
  const ejec = ejecGlobal ?? ejecItem ?? null;

  const fecha =
    textoOGuion(ejec?.fecha_actuacion) !== "—"
      ? textoOGuion(ejec?.fecha_actuacion)
      : textoOGuion(resumen.find((i) => (i.fecha_conclusion ?? "").toString().trim())?.fecha_conclusion);

  const otVisita =
    textoOGuion(ejec?.orden_trabajo_numero) !== "—"
      ? textoOGuion(ejec?.orden_trabajo_numero)
      : textoOGuion(
          resumen.find((i) => (i.orden_trabajo_numero ?? i.orden_trabajo ?? "").toString().trim())
            ?.orden_trabajo_numero ??
            resumen.find((i) => (i.orden_trabajo ?? "").toString().trim())?.orden_trabajo
        );

  const inspectores = inspectoresDesdeEjecucion(ejec) || "—";

  const tipoVisitaRaw = ejec?.tipo_inspeccion_labrada ?? detalle?.resultado_final?.tipo_visita;
  const tipoVisita = tipoVisitaRaw ? humanizarTipoVisitaRecorrido(tipoVisitaRaw) : "—";
  const tipoVisitaMostrar =
    tipoVisita !== "—" && ejec != null ? tipoVisita : ejec != null ? textoOGuion(tipoVisitaRaw) : "—";

  const labels = resumen.map(resultadoSeguimientoOficioLabel);
  const unicos = [...new Set(labels)];
  let resultadoFinal = "—";
  if (unicos.length === 1 && (unicos[0] === "Cumple" || unicos[0] === "No cumple")) {
    resultadoFinal = unicos[0];
  } else if (unicos.some((l) => l === "Reinspección realizada") && !unicos.some((l) => l === "Cumple" || l === "No cumple")) {
    resultadoFinal = "No informado";
  } else if (unicos.length > 1 && unicos.every((l) => l === "Cumple" || l === "No cumple")) {
    resultadoFinal = "—";
  } else if (unicos.length === 1 && unicos[0] === "Reinspección realizada") {
    resultadoFinal = "No informado";
  }

  return [
    { etiqueta: "Estado actual", valor: estadoActual },
    { etiqueta: "Oficio asociado", valor: oficiosTexto.length ? oficiosTexto.join(" · ") : "—" },
    { etiqueta: "Fecha de reinspección", valor: fecha },
    { etiqueta: "Orden de trabajo de la visita de seguimiento", valor: otVisita },
    { etiqueta: "Inspectores", valor: inspectores },
    { etiqueta: "Tipo de visita labrada", valor: tipoVisitaMostrar === "—" && ejec == null ? "—" : tipoVisitaMostrar },
    { etiqueta: "Resultado final", valor: resultadoFinal },
  ];
}

function ejecucionUtil(raw: unknown): Record<string, unknown> | null {
  if (raw == null || typeof raw !== "object") return null;
  return Object.keys(raw as object).length > 0 ? (raw as Record<string, unknown>) : null;
}

function pushSiValor(filas: EstadoTramiteRecorridoFila[], etiqueta: string, valor: string): void {
  const t = valor.trim();
  if (!t || t === "—") return;
  filas.push({ etiqueta, valor: t });
}

/** Número compacto del oficio para títulos y filas documentales. */
export function oficioRecorridoNumeroTexto(item: OficioRecorridoResumenItem): string {
  return (
    (item.oficio_texto ?? "").trim() ||
    parNumAnio(item.numero_oficio ?? item.numero, item.anio_oficio ?? item.anio)
  );
}

export function oficioRecorridoBloqueTitulo(item: OficioRecorridoResumenItem): string {
  const n = oficioRecorridoNumeroTexto(item);
  return n ? `Oficio ${n}` : "Oficio";
}

/**
 * Ejecución de reinspección propia del oficio.
 * No reutiliza la visita de otro oficio cuando hay varios.
 */
export function ejecucionReinspeccionDeOficio(
  item: OficioRecorridoResumenItem,
  detalle: Pick<IComprobacionRecorridoDetalle, "reinspeccion_por_oficio"> | null,
  totalOficios: number
): Record<string, unknown> | null {
  const propia = ejecucionUtil(item.ejecucion_reinspeccion);
  if (propia) return propia;
  const rein = detalle?.reinspeccion_por_oficio as
    | { iniciador_id?: unknown; ejecucion_reinspeccion?: unknown }
    | null
    | undefined;
  const global = ejecucionUtil(rein?.ejecucion_reinspeccion);
  if (!global) return null;
  const globalIni = Number(rein?.iniciador_id);
  if (item.iniciador_id != null && !Number.isNaN(globalIni) && Number(item.iniciador_id) === globalIni) {
    return global;
  }
  if (totalOficios === 1) return global;
  return null;
}

/** Relato de un oficio: causa/expediente, estado y reinspección propia si existe. */
export function filasOficioRecorridoDocumental(
  item: OficioRecorridoResumenItem,
  detalle: Pick<IComprobacionRecorridoDetalle, "reinspeccion_por_oficio"> | null,
  totalOficios: number
): EstadoTramiteRecorridoFila[] {
  const exp =
    (item.expediente_texto ?? "").trim() || parNumAnio(item.numero_expediente, item.anio_expediente);
  const filas: EstadoTramiteRecorridoFila[] = [
    { etiqueta: "Número de oficio", valor: textoOGuion(oficioRecorridoNumeroTexto(item)) },
    { etiqueta: "Causa", valor: textoOGuion(item.causa) },
    { etiqueta: "Expediente", valor: textoOGuion(exp) },
    { etiqueta: "Estado", valor: resultadoSeguimientoOficioLabel(item) },
  ];
  const ejec = ejecucionReinspeccionDeOficio(item, detalle, totalOficios);
  if (ejec) {
    pushSiValor(filas, "Fecha de reinspección", String(ejec.fecha_actuacion ?? "").trim());
    pushSiValor(
      filas,
      "Orden de trabajo",
      String(ejec.orden_trabajo_numero ?? item.orden_trabajo_numero ?? item.orden_trabajo ?? "").trim()
    );
    pushSiValor(filas, "Inspectores", inspectoresDesdeEjecucion(ejec));
    const tipoRaw = ejec.tipo_inspeccion_labrada;
    if (tipoRaw != null && String(tipoRaw).trim()) {
      const h = humanizarTipoVisitaRecorrido(tipoRaw);
      pushSiValor(filas, "Tipo de visita", h === "—" ? String(tipoRaw).trim() : h);
    }
    pushSiValor(filas, "Acta de inspección", String(ejec.acta_inspeccion_num ?? "").trim());
    pushSiValor(filas, "Acta de comprobación", String(ejec.acta_comprobacion_num ?? "").trim());
    pushSiValor(filas, "Acta de notificación", String(ejec.acta_notificacion_num ?? "").trim());
    pushSiValor(filas, "Acta de clausura", String(ejec.acta_clausura_num ?? "").trim());
    pushSiValor(filas, "Acta de decomiso", String(ejec.acta_decomiso_num ?? "").trim());
    pushSiValor(
      filas,
      "Motivos de comprobación",
      motivosComprobacionTexto(hydrateMotivosComprobacion(ejec as MotivosComprobacionSource))
    );
  } else {
    pushSiValor(
      filas,
      "Orden de trabajo",
      String(item.orden_trabajo_numero ?? item.orden_trabajo ?? "").trim()
    );
    pushSiValor(
      filas,
      "Motivos de comprobación",
      motivosComprobacionTexto(hydrateMotivosComprobacion(item as MotivosComprobacionSource))
    );
  }
  return filas;
}

function inspectoresDesdeRow(row: IComprobacionRecorridoRow): string {
  const t = String(row.inspectores_texto ?? "").trim();
  if (t) return t;
  return [row.inspector1, row.inspector2, row.inspector3]
    .map((s) => String(s ?? "").trim())
    .filter(Boolean)
    .join(" · ");
}

/** Cabecera documental del acta de comprobación (origen del recorrido). */
export function filasActaComprobacionRecorrido(row: IComprobacionRecorridoRow): EstadoTramiteRecorridoFila[] {
  const filas: EstadoTramiteRecorridoFila[] = [
    { etiqueta: "N.º de acta", valor: textoOGuion(row.acta_comprobacion_num) },
    { etiqueta: "Fecha", valor: textoOGuion(row.fecha_actuacion) },
    { etiqueta: "Orden de trabajo", valor: textoOGuion(row.orden_trabajo_numero) },
    {
      etiqueta: "Domicilio",
      valor: textoOGuion(
        formatActuacionListDomicilioLinea({
          calle: row.calle,
          numero: row.numero,
          numero_tipo: typeof row.numero_tipo === "string" ? row.numero_tipo : null,
        })
      ),
    },
    { etiqueta: "Inspectores", valor: textoOGuion(inspectoresDesdeRow(row)) },
  ];
  pushSiValor(
    filas,
    "Motivos de comprobación",
    motivosComprobacionTexto(hydrateMotivosComprobacion(row))
  );
  return filas;
}

/** Referencia de cabecera: acta · fecha · OT. */
export function recorridoHeaderReference(
  row: IComprobacionRecorridoRow,
  detalle: IComprobacionRecorridoDetalle | null
): string | null {
  const n =
    (row.acta_comprobacion_num ?? "").toString().trim() ||
    (detalle ? String(detalle.acta_comprobacion?.numero ?? "").trim() : "");
  const fecha = (row.fecha_actuacion ?? "").trim();
  const ot = (row.orden_trabajo_numero ?? "").toString().trim();
  const parts: string[] = [];
  if (n) parts.push(`Acta N.º ${n}`);
  if (fecha) parts.push(fecha);
  if (ot) parts.push(`OT ${ot}`);
  return parts.length ? parts.join(" · ") : null;
}

/** Oficios a narrar: `oficios_resumen` o, si falta, el oficio único del detalle. */
export function oficiosResumenParaDocumental(
  row: IComprobacionRecorridoRow,
  detalle: IComprobacionRecorridoDetalle | null
): OficioRecorridoResumenItem[] {
  const resumen = (detalle?.oficios_resumen ?? row.oficios_resumen ?? []) as OficioRecorridoResumenItem[];
  if (resumen.length > 0) return resumen;
  const ofi = detalle?.oficio;
  const n = (ofi?.numero_oficio ?? row.oficio_numero ?? "").toString().trim();
  const a = ofi?.anio ?? row.oficio_anio;
  if (!n && a == null) return [];
  const rein = detalle?.reinspeccion_por_oficio as Record<string, unknown> | null | undefined;
  return [
    {
      numero_oficio: n || null,
      anio_oficio: a ?? null,
      oficio_texto: n || a != null ? [n, a != null ? String(a) : ""].filter(Boolean).join("/") : "",
      causa: ofi?.causa ?? null,
      iniciador_id: rein?.iniciador_id != null ? Number(rein.iniciador_id) : null,
      estado_iniciador: rein?.estado_iniciador != null ? String(rein.estado_iniciador) : null,
      tipo_iniciador: rein?.tipo_iniciador != null ? String(rein.tipo_iniciador) : null,
      ejecucion_reinspeccion: ejecucionUtil(rein?.ejecucion_reinspeccion),
      resultado: detalle?.resultado_final?.resultado_cumplimiento_oficio ?? null,
      resultado_cumplimiento_oficio: detalle?.resultado_final?.resultado_cumplimiento_oficio ?? null,
    },
  ];
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
  const inf = motivosComprobacionTexto(hydrateMotivosComprobacion(r));
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
