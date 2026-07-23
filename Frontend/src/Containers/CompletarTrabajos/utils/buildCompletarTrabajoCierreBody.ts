import type {
  ICompletarTrabajoCierreBody,
  ICompletarTrabajoPendienteRow,
} from "../../../api/completarTrabajoApi";
import {
  domicilioCalleCargadaEditable,
  domicilioCalleEfectiva,
  domicilioCalleEsClaveTecnica,
  domicilioCalleParaPayload,
  domicilioEsquinaEsClaveTecnica,
  domicilioEsquinaParaPayload,
  domicilioNumeroEditable,
  domicilioNumeroEfectivo,
  domicilioNumeroParaPayload,
  domicilioRowParaHidratacionCompletarTrabajo,
} from "../../../utils/domicilioCalleUi";
import { esNoPermiteInspeccionContraproducencia } from "./completarTrabajoContraproducencia";

export type CompletarTrabajoFormFields = {
  tipo_actuacion: string;
  contraproducencia: string;
  rubro_nombre: string;
  calle: string;
  numero: string;
  numero_tipo: string;
  doc_nro: string;
  contrib_apellido: string;
  contrib_nombre: string;
  razon_social: string;
  nombre_local: string;
  observaciones_ejecucion: string;
  /** Vacío salvo flujo REINSPECCION_OFICIO. */
  resultado_cumplimiento_oficio: string;
  /** Verificar e informar: true = inspección normal; false = cierre sin actas normales. */
  realizo_nueva_inspeccion: string;
  acta_inspeccion_num: string;
  acta_notificacion_num: string;
  notificacion_motivo_1: string;
  notificacion_motivo_2: string;
  notificacion_motivo_3: string;
  acta_comprobacion_num: string;
  comprobacion_motivo: string;
  acta_clausura_num: string;
  acta_decomiso_num: string;
  decomiso_kilos_total: string;
};

function s(v: string): string | undefined {
  const t = v.trim();
  return t === "" ? undefined : t;
}

function domicilioBaselineEfectivo(
  row: ICompletarTrabajoPendienteRow | undefined
): ICompletarTrabajoPendienteRow | undefined {
  if (!row) return undefined;
  const h = domicilioRowParaHidratacionCompletarTrabajo(row);
  return { ...row, calle: h.calle, numero: h.numero, numero_tipo: h.numero_tipo };
}

export type BuildCierreBodyOptions = {
  includeTipoActuacion?: boolean;
  /**
   * Si es false, no incluye actas ni datos de inspección normal (Verificar e informar sin nueva inspección).
   */
  incluirInspeccionNormal?: boolean;
  /**
   * No reenvía `tipo_actuacion` del merge (ya fijado al publicar la ruta).
   * Sí conserva rubro/calle/número: el cierre con contrib/domicilio los necesita en el body.
   */
  omitPrecargadoPr2?: boolean;
  /**
   * Si está definido, envía `inspectores` tal cual (sustituye la herencia del grupo en backend).
   * Lista vacía = sin inspectores en el cierre. Si se omite la opción, el backend sigue usando el grupo.
   */
  inspectoresExplicitos?: string[];
  /** Fila origen para omitir calle del body cuando no hubo edición o sería calle_key. */
  domicilioRow?: ICompletarTrabajoPendienteRow;
  /**
   * Fila origen sin merge del formulario (detecta ESQUINA→NUMERO aunque values ya traiga numero_tipo).
   */
  domicilioRowBaseline?: ICompletarTrabajoPendienteRow;
  /**
   * Claves presentes en el submit del modal (``values``).
   * Si está definido, solo se envían domicilio/rubro/titular cuando el operador los editó explícitamente
   * o hubo cambio geográfico real vs la fila baseline (reinspección sin edición no manda domicilio).
   */
  explicitUserFields?: Set<string>;
};

function fieldExplicit(key: string, options?: BuildCierreBodyOptions): boolean {
  if (!options?.explicitUserFields) return true;
  return options.explicitUserFields.has(key);
}

function rubroCambioReal(
  editedRubro: string,
  baselineRow?: ICompletarTrabajoPendienteRow
): boolean {
  const t = s(editedRubro);
  if (!t) return false;
  const baseline = (baselineRow?.rubro_nombre ?? "").trim();
  return !baseline || t !== baseline;
}

function rubroEfectivo(
  editedRubro: string,
  baselineRow?: ICompletarTrabajoPendienteRow
): string | undefined {
  return s(editedRubro) || s(baselineRow?.rubro_nombre ?? "");
}

function geoHayCambioReal(
  f: CompletarTrabajoFormFields,
  options: BuildCierreBodyOptions | undefined,
  baselineRow: ICompletarTrabajoPendienteRow | undefined,
  corrigeEsquinaANumero: boolean
): boolean {
  if (corrigeEsquinaANumero) return true;
  if (!options?.domicilioRow || !baselineRow) {
    return Boolean(s(f.calle) || s(f.numero) || s(f.numero_tipo));
  }
  const formNumeroTipo = (f.numero_tipo || "").trim().toUpperCase();
  const baselineNumeroTipo = (baselineRow.numero_tipo || "").trim().toUpperCase();
  const calleCambio = Boolean(
    domicilioCalleParaPayload(f.calle, options.domicilioRow, { baselineRow })
  );
  const tipoCambio = Boolean(formNumeroTipo && formNumeroTipo !== baselineNumeroTipo);
  const numeroTipoEfectivo = formNumeroTipo || baselineNumeroTipo;
  const numeroCambio =
    numeroTipoEfectivo === "ESQUINA"
      ? Boolean(domicilioEsquinaParaPayload(f.numero, options.domicilioRow, { baselineRow }))
      : Boolean(domicilioNumeroParaPayload(f.numero, options.domicilioRow, { baselineRow }));
  return calleCambio || numeroCambio || tipoCambio;
}

/**
 * Arma el body POST /cerrar alineado al backend (sin actas si hay contraproducencia).
 * `inspectores` solo se incluye si `options.inspectoresExplicitos` está definido (sustituye herencia del grupo).
 */
export function buildCompletarTrabajoCierreBody(
  f: CompletarTrabajoFormFields,
  options?: BuildCierreBodyOptions
): ICompletarTrabajoCierreBody {
  const includeTipo = options?.includeTipoActuacion === true;
  const incluirInspeccion = options?.incluirInspeccionNormal !== false;
  const body: ICompletarTrabajoCierreBody = {};
  const contra = s(f.contraproducencia);
  const visitaRealizada = !contra;
  const noPermiteInspeccion = contra ? esNoPermiteInspeccionContraproducencia(contra) : false;

  if (includeTipo && s(f.tipo_actuacion)) body.tipo_actuacion = s(f.tipo_actuacion);
  if (contra) body.contraproducencia = contra;

  const baselineRow = options?.domicilioRowBaseline ?? options?.domicilioRow;
  const baselineDomicilio = domicilioBaselineEfectivo(baselineRow);

  const formNumeroTipo = (f.numero_tipo || "").trim().toUpperCase();
  const baselineNumeroTipo = (baselineDomicilio?.numero_tipo || "").trim().toUpperCase();
  const rowNumeroTipo = (options?.domicilioRow?.numero_tipo || "").trim().toUpperCase();
  /** Corrección ESQUINA→NUMERO: usar baseline (fila API), no la fila ya mergeada. */
  const corrigeEsquinaANumero = formNumeroTipo === "NUMERO" && baselineNumeroTipo === "ESQUINA";
  const geoExplicitRequested =
    fieldExplicit("calle", options) ||
    fieldExplicit("numero", options) ||
    fieldExplicit("numero_tipo", options);
  const domicilioCambioReal = geoHayCambioReal(f, options, baselineDomicilio, corrigeEsquinaANumero);
  const includeGeoBlock =
    corrigeEsquinaANumero || (geoExplicitRequested && domicilioCambioReal);

  if (
    fieldExplicit("rubro_nombre", options) &&
    rubroEfectivo(f.rubro_nombre, baselineRow) &&
    (rubroCambioReal(f.rubro_nombre, baselineRow) || domicilioCambioReal)
  ) {
    body.rubro_nombre = rubroEfectivo(f.rubro_nombre, baselineRow);
  }

  if (includeGeoBlock) {
    const calleVisible = s(f.calle);
    let callePayload: string | undefined;
    if (corrigeEsquinaANumero) {
      callePayload =
        calleVisible ||
        (options?.domicilioRow ? domicilioCalleCargadaEditable(baselineDomicilio ?? options.domicilioRow) : undefined);
    } else if (options?.domicilioRow) {
      callePayload = domicilioCalleEfectiva(f.calle, options.domicilioRow, { baselineRow: baselineDomicilio });
    } else {
      callePayload = calleVisible;
    }
    if (callePayload) body.calle = callePayload;

    const numeroTipo = corrigeEsquinaANumero ? "NUMERO" : formNumeroTipo || rowNumeroTipo;
    if (options?.domicilioRow && numeroTipo === "ESQUINA" && !corrigeEsquinaANumero) {
      const esquinaPayload = domicilioNumeroEfectivo(f.numero, options.domicilioRow, {
        baselineRow: baselineDomicilio,
        numeroTipo: "ESQUINA",
      });
      if (esquinaPayload) {
        body.numero = esquinaPayload;
        body.numero_tipo = "ESQUINA";
      }
    } else {
      let numeroPayload: string | undefined;
      if (corrigeEsquinaANumero) {
        numeroPayload = s(f.numero);
      } else if (options?.domicilioRow) {
        numeroPayload = domicilioNumeroEfectivo(f.numero, options.domicilioRow, {
          baselineRow: baselineDomicilio,
          numeroTipo: numeroTipo || "NUMERO",
        });
      } else if (s(f.numero)) {
        numeroPayload = s(f.numero);
      }
      if (numeroPayload) body.numero = numeroPayload;
      if (corrigeEsquinaANumero) {
        body.numero_tipo = "NUMERO";
      } else if (s(f.numero_tipo) && (callePayload || numeroPayload)) {
        body.numero_tipo = s(f.numero_tipo);
      } else if (numeroPayload && numeroTipo) {
        body.numero_tipo = numeroTipo;
      }
    }
  }

  if (fieldExplicit("doc_nro", options) && s(f.doc_nro)) body.doc_nro = s(f.doc_nro);
  if (fieldExplicit("contrib_apellido", options) && s(f.contrib_apellido)) {
    body.contrib_apellido = s(f.contrib_apellido);
  }
  if (fieldExplicit("contrib_nombre", options) && s(f.contrib_nombre)) {
    body.contrib_nombre = s(f.contrib_nombre);
  }
  if (fieldExplicit("razon_social", options) && s(f.razon_social)) {
    body.razon_social = s(f.razon_social);
  }
  if (fieldExplicit("nombre_local", options) && s(f.nombre_local)) {
    body.nombre_local = s(f.nombre_local);
  }
  if (s(f.observaciones_ejecucion)) body.observaciones_ejecucion = s(f.observaciones_ejecucion);

  const rni = s(f.realizo_nueva_inspeccion);
  if (rni === "si") body.realizo_nueva_inspeccion = true;
  if (rni === "no") body.realizo_nueva_inspeccion = false;

  if (visitaRealizada && incluirInspeccion) {
    const rc = s(f.resultado_cumplimiento_oficio);
    if (rc === "CUMPLE" || rc === "NO_CUMPLE") {
      body.resultado_cumplimiento_oficio = rc;
    }
    if (s(f.acta_inspeccion_num)) body.acta_inspeccion_num = s(f.acta_inspeccion_num);
    if (s(f.acta_notificacion_num)) body.acta_notificacion_num = s(f.acta_notificacion_num);
    if (s(f.notificacion_motivo_1)) body.notificacion_motivo_1 = s(f.notificacion_motivo_1);
    if (s(f.notificacion_motivo_2)) body.notificacion_motivo_2 = s(f.notificacion_motivo_2);
    if (s(f.notificacion_motivo_3)) body.notificacion_motivo_3 = s(f.notificacion_motivo_3);
    if (s(f.acta_comprobacion_num)) body.acta_comprobacion_num = s(f.acta_comprobacion_num);
    if (s(f.comprobacion_motivo)) body.comprobacion_motivo = s(f.comprobacion_motivo);
    if (s(f.acta_clausura_num)) body.acta_clausura_num = s(f.acta_clausura_num);
    if (s(f.acta_decomiso_num)) body.acta_decomiso_num = s(f.acta_decomiso_num);
    const kilos = parseFloat(f.decomiso_kilos_total.replace(",", "."));
    if (!Number.isNaN(kilos)) body.decomiso_kilos_total = kilos;
  } else if (noPermiteInspeccion) {
    if (s(f.acta_comprobacion_num)) body.acta_comprobacion_num = s(f.acta_comprobacion_num);
    if (s(f.comprobacion_motivo)) body.comprobacion_motivo = s(f.comprobacion_motivo);
    if (s(f.acta_clausura_num)) body.acta_clausura_num = s(f.acta_clausura_num);
  }

  if (options?.inspectoresExplicitos !== undefined) {
    body.inspectores = options.inspectoresExplicitos.map((n) => String(n).trim()).filter(Boolean);
  }

  return body;
}

export const EMPTY_COMPLETAR_FORM: CompletarTrabajoFormFields = {
  tipo_actuacion: "",
  contraproducencia: "",
  rubro_nombre: "",
  calle: "",
  numero: "",
  numero_tipo: "",
  doc_nro: "",
  contrib_apellido: "",
  contrib_nombre: "",
  razon_social: "",
  nombre_local: "",
  observaciones_ejecucion: "",
  resultado_cumplimiento_oficio: "",
  realizo_nueva_inspeccion: "",
  acta_inspeccion_num: "",
  acta_notificacion_num: "",
  notificacion_motivo_1: "",
  notificacion_motivo_2: "",
  notificacion_motivo_3: "",
  acta_comprobacion_num: "",
  comprobacion_motivo: "",
  acta_clausura_num: "",
  acta_decomiso_num: "",
  decomiso_kilos_total: "",
};

function strFromUnknown(v: unknown): string {
  if (v == null || v === "") return "";
  return String(v).trim();
}

function mergeRow(
  original: ICompletarTrabajoPendienteRow,
  values: Record<string, unknown>
): ICompletarTrabajoPendienteRow {
  const out = { ...original } as Record<string, unknown>;
  for (const [k, v] of Object.entries(values)) {
    if (v !== undefined) out[k] = v;
  }
  return out as ICompletarTrabajoPendienteRow;
}

function trimStr(v: string | null | undefined): string {
  return (v ?? "").trim();
}

function rowToFormFields(row: ICompletarTrabajoPendienteRow): CompletarTrabajoFormFields {
  const kilos = row.decomiso_kilos_total as unknown;
  const kilosStr =
    kilos == null || kilos === "" ? "" : typeof kilos === "number" ? String(kilos) : String(kilos).trim();
  const hydrated = domicilioRowParaHidratacionCompletarTrabajo(row);
  const calleMerged = trimStr(row.calle);
  const numeroMerged = trimStr(row.numero);
  const numeroTipo = trimStr(row.numero_tipo).toUpperCase() || hydrated.numero_tipo;
  const calle =
    calleMerged && !domicilioCalleEsClaveTecnica(calleMerged, row) ? calleMerged : hydrated.calle ?? "";
  const numero =
    numeroMerged && !(numeroTipo === "ESQUINA" && domicilioEsquinaEsClaveTecnica(numeroMerged, row))
      ? numeroMerged
      : hydrated.numero ?? "";
  return {
    tipo_actuacion: row.tipo_actuacion ?? "",
    contraproducencia: row.contraproducencia ?? "",
    rubro_nombre: row.rubro_nombre ?? "",
    calle,
    numero,
    numero_tipo: numeroTipo,
    doc_nro: row.doc_nro ?? "",
    contrib_apellido: row.contrib_apellido ?? "",
    contrib_nombre: row.contrib_nombre ?? "",
    razon_social: row.razon_social ?? "",
    nombre_local: row.nombre_local ?? "",
    observaciones_ejecucion: row.observaciones_ejecucion ?? "",
    resultado_cumplimiento_oficio: row.resultado_cumplimiento_oficio ?? "",
    realizo_nueva_inspeccion: "",
    acta_inspeccion_num: row.acta_inspeccion_num ?? "",
    acta_notificacion_num: row.acta_notificacion_num ?? "",
    notificacion_motivo_1: row.notificacion_motivo_1 ?? "",
    notificacion_motivo_2: row.notificacion_motivo_2 ?? "",
    notificacion_motivo_3: row.notificacion_motivo_3 ?? "",
    acta_comprobacion_num: row.acta_comprobacion_num ?? "",
    comprobacion_motivo: row.comprobacion_motivo ?? "",
    acta_clausura_num: row.acta_clausura_num ?? "",
    acta_decomiso_num: row.acta_decomiso_num ?? "",
    decomiso_kilos_total: kilosStr,
  };
}

function applyOmitPrecargadoPr2(fields: CompletarTrabajoFormFields): void {
  fields.tipo_actuacion = "";
}

export function buildCompletarTrabajoCierreBodyFromInline(
  original: ICompletarTrabajoPendienteRow,
  values: Record<string, unknown>,
  options?: BuildCierreBodyOptions
): ICompletarTrabajoCierreBody {
  const merged = mergeRow(original, values);
  const fields = rowToFormFields(merged);
  if ("decomiso_kilos_total" in values) {
    fields.decomiso_kilos_total = strFromUnknown(values.decomiso_kilos_total);
  }
  if ("realizo_nueva_inspeccion" in values) {
    fields.realizo_nueva_inspeccion = strFromUnknown(values.realizo_nueva_inspeccion);
  }
  if ("resultado_cumplimiento_oficio" in values) {
    fields.resultado_cumplimiento_oficio = strFromUnknown(values.resultado_cumplimiento_oficio);
  }
  if (options?.omitPrecargadoPr2 === true) {
    applyOmitPrecargadoPr2(fields);
  }
  return buildCompletarTrabajoCierreBody(fields, {
    ...options,
    domicilioRow: merged,
    domicilioRowBaseline: original,
    explicitUserFields: new Set(Object.keys(values)),
  });
}
