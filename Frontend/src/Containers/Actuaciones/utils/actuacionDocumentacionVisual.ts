import type { IActuacionListItem } from "../../../api/actuacionesListApi";

/** Subconjunto tipado del presenter F2.2 (`documentacion_contexto.propia`). */
export type DocumentacionPropia = {
  expediente_numero?: string | null;
  expediente_anio?: string | number | null;
  notificacion_plazo_dias?: number | null;
  notificacion_prorroga_dias?: number | null;
  notificacion_fecha_vencimiento?: string | null;
};

export type DocumentacionContexto = {
  circuito:
    | "COMUN_NOTIFICACION"
    | "COMUN_COMPROBACION"
    | "REINSPECCION_OFICIO"
    | "REINSPECCION_NOTIFICACION"
    | "DESCONOCIDO";
  propia: DocumentacionPropia;
};

export type OrigenReinspeccionOficio = {
  comprobacion_acta_numero?: string | null;
  comprobacion_acta_anio?: number | null;
  expediente_numero?: string | null;
  expediente_anio?: string | number | null;
  oficio_numero?: string | null;
  oficio_anio?: number | null;
  oficio_causa?: string | null;
};

export type OrigenReinspeccionNotificacion = {
  notificacion_acta_numero?: string | null;
  notificacion_acta_anio?: number | null;
  expediente_numero?: string | null;
  expediente_anio?: string | number | null;
  plazo_dias?: number | null;
  prorroga_dias?: number | null;
  fecha_vencimiento?: string | null;
};

/**
 * Solo chips de actas operativas (Inspección, Notificación, etc.).
 * Decomiso unifica N.º y kilos cuando hay ambos (F2.4).
 */
export function actuacionActaChipsOnly(r: IActuacionListItem): string[] {
  const out: string[] = [];
  if (r.acta_inspeccion_num?.trim()) out.push(`Inspección ${r.acta_inspeccion_num.trim()}`);
  if (r.acta_notificacion_num?.trim()) out.push(`Notificación ${r.acta_notificacion_num.trim()}`);
  if (r.acta_comprobacion_num?.trim()) out.push(`Comprobación ${r.acta_comprobacion_num.trim()}`);
  if (r.acta_clausura_num?.trim()) out.push(`Clausura ${r.acta_clausura_num.trim()}`);
  const decomNum = r.acta_decomiso_num?.trim();
  if (decomNum) {
    const k = r.decomiso_kilos_total;
    const kg = k != null && !Number.isNaN(Number(k)) && Number(k) > 0 ? Number(k) : null;
    if (kg != null) {
      out.push(`Decomiso N.º ${decomNum} — ${kg} kg`);
    } else {
      out.push(`Decomiso N.º ${decomNum}`);
    }
  }
  return out;
}

function _hasPropiaExpediente(p: DocumentacionPropia): boolean {
  return p.expediente_numero != null && String(p.expediente_numero).trim() !== "";
}

function _propiaNotificacionTramiteHints(p: DocumentacionPropia): boolean {
  return (
    p.notificacion_plazo_dias != null ||
    (p.notificacion_prorroga_dias != null && p.notificacion_prorroga_dias > 0) ||
    Boolean(p.notificacion_fecha_vencimiento?.trim())
  );
}

function _resultadoCumplimientoSegments(r: IActuacionListItem): string[] {
  if (r.resultado_cumplimiento_oficio?.trim()) {
    return [`Cumpl. oficio: ${r.resultado_cumplimiento_oficio.trim()}`];
  }
  return [];
}

/**
 * Trámite / expediente propio de la actuación (sin origen de reinspección ni «Cumpl. oficio»).
 * Para el modal F2.4: combinar con `actuacionDocumentacionOrigenReinspeccionSegments`.
 */
export function actuacionDocumentacionPropiaTramiteSegments(r: IActuacionListItem): string[] {
  const out: string[] = [];
  const ctx = r.documentacion_contexto as DocumentacionContexto | undefined;
  const circuit = ctx?.circuito;

  if (ctx?.propia) {
    const p = ctx.propia;
    if (_hasPropiaExpediente(p)) {
      const num = `${String(p.expediente_numero).trim()}/${p.expediente_anio ?? "—"}`;
      const notifTramite =
        circuit === "COMUN_NOTIFICACION" ||
        (circuit === "REINSPECCION_NOTIFICACION" && _propiaNotificacionTramiteHints(p));
      if (notifTramite) {
        out.push(`Expediente N.º ${num}`);
      } else if (circuit === "COMUN_COMPROBACION" || circuit === "REINSPECCION_OFICIO") {
        out.push(`Expediente envío N.º ${num}`);
      } else if (circuit === "REINSPECCION_NOTIFICACION") {
        out.push(`Expediente envío N.º ${num}`);
      } else {
        out.push(`Expediente N.º ${num}`);
      }
    }
    if (circuit === "COMUN_NOTIFICACION" || circuit === "REINSPECCION_NOTIFICACION") {
      if (p.notificacion_plazo_dias != null) {
        out.push(`Plazo ${p.notificacion_plazo_dias} días`);
      }
      if (p.notificacion_prorroga_dias != null && p.notificacion_prorroga_dias > 0) {
        out.push(`Prórroga +${p.notificacion_prorroga_dias} d`);
      }
      if (p.notificacion_fecha_vencimiento?.trim()) {
        out.push(`Vencimiento: ${p.notificacion_fecha_vencimiento.trim()}`);
      }
    }
  } else {
    if (r.expediente_numero != null && String(r.expediente_numero).trim()) {
      const an = r.expediente_anio != null ? `/${r.expediente_anio}` : "";
      out.push(`Expediente N.º ${String(r.expediente_numero).trim()}${an}`);
    }
    if (r.oficio_numero != null && String(r.oficio_numero).trim()) {
      const oa = r.oficio_anio != null ? `/${r.oficio_anio}` : "";
      out.push(`Oficio N.º ${String(r.oficio_numero).trim()}${oa}`);
      if (r.oficio_causa?.trim()) {
        out.push(`Causa: ${r.oficio_causa.trim()}`);
      }
    }
  }

  return out;
}

/** Solo datos de actas anteriores / origen de reinspección (oficio o notificación). */
export function actuacionDocumentacionOrigenReinspeccionSegments(r: IActuacionListItem): string[] {
  const out: string[] = [];

  const oo = r.origen_reinspeccion_oficio as OrigenReinspeccionOficio | null | undefined;
  if (oo && (oo.comprobacion_acta_numero || oo.oficio_numero || oo.expediente_numero)) {
    out.push("Origen: Reinspección por oficio");
    const cnum = oo.comprobacion_acta_numero?.trim();
    if (cnum) {
      const can = oo.comprobacion_acta_anio != null ? `/${oo.comprobacion_acta_anio}` : "";
      out.push(`Comp. origen N.º ${cnum}${can}`);
    }
    if (oo.expediente_numero != null && String(oo.expediente_numero).trim()) {
      const ea = oo.expediente_anio != null ? `/${oo.expediente_anio}` : "";
      out.push(`Exp. oficio N.º ${String(oo.expediente_numero).trim()}${ea}`);
    }
    if (oo.oficio_numero != null && String(oo.oficio_numero).trim()) {
      const oa = oo.oficio_anio != null ? `/${oo.oficio_anio}` : "";
      out.push(`Oficio N.º ${String(oo.oficio_numero).trim()}${oa}`);
    }
    if (oo.oficio_causa?.trim()) {
      out.push(`Causa: ${oo.oficio_causa.trim()}`);
    }
  }

  const on = r.origen_reinspeccion_notificacion as OrigenReinspeccionNotificacion | null | undefined;
  if (
    on &&
    (on.notificacion_acta_numero ||
      on.expediente_numero ||
      on.fecha_vencimiento?.trim() ||
      on.plazo_dias != null ||
      (on.prorroga_dias != null && on.prorroga_dias > 0))
  ) {
    out.push("Origen: Reinspección por notificación");
    const nn = on.notificacion_acta_numero?.trim();
    if (nn) {
      const na = on.notificacion_acta_anio != null ? `/${on.notificacion_acta_anio}` : "";
      out.push(`Notificación origen N.º ${nn}${na}`);
    }
    if (on.expediente_numero != null && String(on.expediente_numero).trim()) {
      const ea = on.expediente_anio != null ? `/${on.expediente_anio}` : "";
      out.push(`Exp. notificación N.º ${String(on.expediente_numero).trim()}${ea}`);
    }
    if (on.plazo_dias != null) {
      out.push(`Plazo origen ${on.plazo_dias} días`);
    }
    if (on.prorroga_dias != null && on.prorroga_dias > 0) {
      out.push(`Prórroga origen +${on.prorroga_dias} d`);
    }
    if (on.fecha_vencimiento?.trim()) {
      out.push(`Vencimiento: ${on.fecha_vencimiento.trim()}`);
    }
  }

  return out;
}

/**
 * Chips de documentación propia + origen de reinspección + cumplimiento oficio (F2.3 / F2.4).
 * Alineado al presenter F2.2; sin oficio/causa en común comprobación salvo origen explícito.
 */
export function actuacionDocumentacionTramiteSegments(
  r: IActuacionListItem,
  opts?: { includeResultadoCumplimiento?: boolean },
): string[] {
  const includeRes = opts?.includeResultadoCumplimiento !== false;
  const base = [
    ...actuacionDocumentacionPropiaTramiteSegments(r),
    ...actuacionDocumentacionOrigenReinspeccionSegments(r),
  ];
  if (!includeRes) {
    return base;
  }
  return [...base, ..._resultadoCumplimientoSegments(r)];
}

export function actuacionActasYTramiteAccessor(r: IActuacionListItem): string {
  return [...actuacionActaChipsOnly(r), ...actuacionDocumentacionTramiteSegments(r)].join(" | ");
}
