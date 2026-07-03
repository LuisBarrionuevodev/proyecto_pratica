import type {
  ICompletarTrabajoCierreBody,
  ICompletarTrabajoPendienteRow,
} from "../../../api/completarTrabajoApi";
import { domicilioCalleCargadaEditable, domicilioCalleParaPayload, domicilioEsquinaParaPayload, domicilioNumeroEditable } from "../../../utils/domicilioCalleUi";
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

export type BuildCierreBodyOptions = {
  includeTipoActuacion?: boolean;
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
};

/**
 * Arma el body POST /cerrar alineado al backend (sin actas si hay contraproducencia).
 * `inspectores` solo se incluye si `options.inspectoresExplicitos` está definido (sustituye herencia del grupo).
 */
export function buildCompletarTrabajoCierreBody(
  f: CompletarTrabajoFormFields,
  options?: BuildCierreBodyOptions
): ICompletarTrabajoCierreBody {
  const includeTipo = options?.includeTipoActuacion === true;
  const body: ICompletarTrabajoCierreBody = {};
  const contra = s(f.contraproducencia);
  const visitaRealizada = !contra;
  const noPermiteInspeccion = contra ? esNoPermiteInspeccionContraproducencia(contra) : false;

  if (includeTipo && s(f.tipo_actuacion)) body.tipo_actuacion = s(f.tipo_actuacion);
  if (contra) body.contraproducencia = contra;
  if (s(f.rubro_nombre)) body.rubro_nombre = s(f.rubro_nombre);
  const callePayload = options?.domicilioRow
    ? domicilioCalleParaPayload(f.calle, options.domicilioRow)
    : s(f.calle);
  if (callePayload) body.calle = callePayload;
  const numeroTipo = (f.numero_tipo || options?.domicilioRow?.numero_tipo || "").toUpperCase();
  if (options?.domicilioRow && numeroTipo === "ESQUINA") {
    const esquinaPayload = domicilioEsquinaParaPayload(f.numero, options.domicilioRow);
    if (esquinaPayload) {
      body.numero = esquinaPayload;
      body.numero_tipo = "ESQUINA";
    }
  } else {
    if (s(f.numero)) body.numero = s(f.numero);
    if (s(f.numero_tipo)) body.numero_tipo = s(f.numero_tipo);
  }
  if (s(f.doc_nro)) body.doc_nro = s(f.doc_nro);
  if (s(f.contrib_apellido)) body.contrib_apellido = s(f.contrib_apellido);
  if (s(f.contrib_nombre)) body.contrib_nombre = s(f.contrib_nombre);
  if (s(f.razon_social)) body.razon_social = s(f.razon_social);
  if (s(f.nombre_local)) body.nombre_local = s(f.nombre_local);
  if (s(f.observaciones_ejecucion)) body.observaciones_ejecucion = s(f.observaciones_ejecucion);

  if (visitaRealizada) {
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

function rowToFormFields(row: ICompletarTrabajoPendienteRow): CompletarTrabajoFormFields {
  const kilos = row.decomiso_kilos_total as unknown;
  const kilosStr =
    kilos == null || kilos === "" ? "" : typeof kilos === "number" ? String(kilos) : String(kilos).trim();
  return {
    tipo_actuacion: row.tipo_actuacion ?? "",
    contraproducencia: row.contraproducencia ?? "",
    rubro_nombre: row.rubro_nombre ?? "",
    calle: domicilioCalleCargadaEditable(row),
    numero: domicilioNumeroEditable(row),
    numero_tipo: row.numero_tipo ?? "",
    doc_nro: row.doc_nro ?? "",
    contrib_apellido: row.contrib_apellido ?? "",
    contrib_nombre: row.contrib_nombre ?? "",
    razon_social: row.razon_social ?? "",
    nombre_local: row.nombre_local ?? "",
    observaciones_ejecucion: row.observaciones_ejecucion ?? "",
    resultado_cumplimiento_oficio: row.resultado_cumplimiento_oficio ?? "",
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
  if (options?.omitPrecargadoPr2 === true) {
    applyOmitPrecargadoPr2(fields);
  }
  return buildCompletarTrabajoCierreBody(fields, { ...options, domicilioRow: merged });
}
