import type { DashboardExportPayload } from "./buildDashboardExportPayload";
import {
  buildContraproducenciasResumen,
  formatPorcentajeNoRealizadas,
} from "./noRealizadasContraproducencias";

export const DASHBOARD_PDF_EMPTY_MESSAGE = "Sin datos en el período seleccionado.";

const RIESGO_TOP_N = 5;
const PRODUCTIVIDAD_TOP_N = 10;

export type DashboardPdfKpiRow = { label: string; value: string };

export type DashboardPdfTableRow = {
  label: string;
  value: string;
  value2?: string;
  extraValues?: string[];
};

export type DashboardPdfTableSection = {
  title: string;
  headers: string[];
  rows: DashboardPdfTableRow[];
};

export type DashboardPdfModel = {
  title: string;
  periodoLine: string;
  distritoLabel: string;
  inspectorLabel: string;
  generadoEl: string;
  desde: string;
  hasta: string;
  ejecutivoKpis: DashboardPdfKpiRow[];
  pendientesKpis: DashboardPdfKpiRow[];
  actasPorTipo: DashboardPdfTableSection;
  riesgoRubros: DashboardPdfTableSection;
  riesgoMotivosNotificacion: DashboardPdfTableSection;
  riesgoMotivosComprobacion: DashboardPdfTableSection;
  riesgoDecomisoKg: DashboardPdfTableSection;
  noRealizadasTotal: string | null;
  noRealizadasContraproducencias: DashboardPdfTableSection;
  noRealizadasDistritos: DashboardPdfTableSection;
  productividadRealizadas: DashboardPdfTableSection;
  productividadNoRealizadas: DashboardPdfTableSection;
  productividadActas: DashboardPdfTableSection;
  productividadTruncatedNote: string | null;
};

function fmtNum(n: number | null | undefined): string {
  if (n == null) return "—";
  return String(n);
}

function fmtKg(n: number | null | undefined): string {
  if (n == null) return "—";
  return n.toLocaleString("es-AR", { maximumFractionDigits: 2 });
}

function buildTableSection(
  title: string,
  headers: string[],
  rows: DashboardPdfTableRow[]
): DashboardPdfTableSection {
  return { title, headers: headers as DashboardPdfTableSection["headers"], rows };
}

function limitRows<T>(rows: T[], max: number): { rows: T[]; truncated: boolean } {
  if (rows.length <= max) return { rows, truncated: false };
  return { rows: rows.slice(0, max), truncated: true };
}

/**
 * Mapea el payload unificado del dashboard a secciones del PDF institucional.
 * No recalcula ni consulta backend: solo transforma datos ya cargados.
 */
export function buildDashboardPdfModel(
  payload: DashboardExportPayload,
  desde: string,
  hasta: string,
  generadoEl: string,
  periodoLine: string
): DashboardPdfModel {
  const k = payload.ejecutivo?.kpis;
  const ejecutivoKpis: DashboardPdfKpiRow[] = k
    ? [
        { label: "Actuaciones realizadas", value: fmtNum(k.actuaciones_realizadas) },
        { label: "Actas labradas", value: fmtNum(k.actas_labradas) },
        {
          label: "Reins. notificación realizadas",
          value: fmtNum(k.reinspecciones_notificacion_realizadas),
        },
        {
          label: "Reins. oficio realizadas",
          value: fmtNum(k.reinspecciones_oficio_realizadas),
        },
        {
          label: "Ratificaciones de clausura",
          value: fmtNum(k.ratificaciones_clausura_realizadas),
        },
        {
          label: "Ratificaciones de decomiso",
          value: fmtNum(k.ratificaciones_decomiso_realizadas),
        },
        {
          label: "Verificar e informar",
          value: fmtNum(k.verificar_informar_realizadas),
        },
        { label: "Mercadería decomisada (kg)", value: fmtKg(k.mercaderia_decomisada_kg) },
      ]
    : [];

  const p = payload.pendientes?.kpis;
  const pendientesKpis: DashboardPdfKpiRow[] = p
    ? [
        { label: "Relevamientos pendientes", value: fmtNum(p.relevamientos_pendientes) },
        { label: "Reins. oficio pendientes", value: fmtNum(p.reinspecciones_oficio_pendientes) },
        {
          label: "Reins. notificación pendientes",
          value: fmtNum(p.reinspecciones_notificacion_pendientes),
        },
      ]
    : [];

  const actas = payload.actasPorTipo;
  const actasRows: DashboardPdfTableRow[] = actas
    ? [
        { label: "Inspección", value: fmtNum(actas.inspeccion) },
        { label: "Notificación", value: fmtNum(actas.notificacion) },
        { label: "Comprobación", value: fmtNum(actas.comprobacion) },
        { label: "Clausura", value: fmtNum(actas.clausura) },
        { label: "Decomiso", value: fmtNum(actas.decomiso) },
      ]
    : [];

  const riesgo = payload.riesgo;
  const riesgoRubros = buildTableSection(
    "Top rubros intervenidos",
    ["Rubro", "Cantidad"],
    (riesgo?.top_rubros ?? []).slice(0, RIESGO_TOP_N).map((r) => ({
      label: r.rubro,
      value: fmtNum(r.cantidad),
    }))
  );
  const riesgoMotivosNotificacion = buildTableSection(
    "Motivos de notificación",
    ["Motivo", "Cantidad"],
    (riesgo?.top_motivos_notificacion ?? []).slice(0, RIESGO_TOP_N).map((m) => ({
      label: m.motivo,
      value: fmtNum(m.cantidad),
    }))
  );
  const riesgoMotivosComprobacion = buildTableSection(
    "Motivos de comprobación",
    ["Motivo", "Cantidad"],
    (riesgo?.top_motivos_comprobacion ?? []).slice(0, RIESGO_TOP_N).map((m) => ({
      label: m.motivo,
      value: fmtNum(m.cantidad),
    }))
  );
  const riesgoDecomisoKg = buildTableSection(
    "Decomiso kg por rubro",
    ["Rubro", "Kg"],
    (riesgo?.decomiso_kg_por_rubro ?? []).slice(0, RIESGO_TOP_N).map((r) => ({
      label: r.rubro,
      value: fmtKg(r.kg),
    }))
  );

  const nr = payload.noRealizadas;
  const contraproducenciasResumen = buildContraproducenciasResumen(nr);
  const noRealizadasContraproducencias = buildTableSection(
    "Principales contraproducencias",
    ["Contraproducencia", "Cantidad", "%"],
    contraproducenciasResumen.rows.map((c) => ({
      label: c.contraproducencia,
      value: fmtNum(c.cantidad),
      value2: formatPorcentajeNoRealizadas(c.porcentaje),
    }))
  );

  const noRealizadasDistritos = buildTableSection(
    "Distritos con más no realizadas",
    ["Distrito", "Cantidad"],
    (nr?.distritos_con_mas_no_realizadas ?? []).slice(0, RIESGO_TOP_N).map((d) => ({
      label: d.distrito_nombre,
      value: fmtNum(d.cantidad),
    }))
  );

  const prod = payload.productividad;
  let productividadTruncated = false;

  const realizadasLimited = limitRows(prod?.inspectores_realizadas ?? [], PRODUCTIVIDAD_TOP_N);
  productividadTruncated = productividadTruncated || realizadasLimited.truncated;

  const noRealLimited = limitRows(prod?.inspectores_no_realizadas ?? [], PRODUCTIVIDAD_TOP_N);
  productividadTruncated = productividadTruncated || noRealLimited.truncated;

  const actasLimited = limitRows(prod?.actas_por_inspector ?? [], PRODUCTIVIDAD_TOP_N);
  productividadTruncated = productividadTruncated || actasLimited.truncated;

  const productividadRealizadas = buildTableSection(
    "Actuaciones realizadas por inspector",
    ["Inspector", "Total", "Inspecc.", "R.of.", "R.not.", "Otras"],
    realizadasLimited.rows.map((r) => ({
      label: r.inspector,
      value: fmtNum(r.total_realizadas),
      value2: fmtNum(r.inspecciones),
      extraValues: [
        fmtNum(r.reinspecciones_oficio),
        fmtNum(r.reinspecciones_notificacion),
        fmtNum(r.otras ?? 0),
      ],
    }))
  );

  const productividadNoRealizadas = buildTableSection(
    "Actuaciones no realizadas por inspector",
    ["Inspector", "Total", "L.cerr.", "No ex.", "No rat.", "Clima", "Otras"],
    noRealLimited.rows.map((r) => ({
      label: r.inspector,
      value: fmtNum(r.total_no_realizadas),
      value2: fmtNum(r.local_cerrado ?? 0),
      extraValues: [
        fmtNum(r.no_existe ?? 0),
        fmtNum(r.no_se_ratifico ?? 0),
        fmtNum(r.clima ?? 0),
        fmtNum(r.otras ?? 0),
      ],
    }))
  );

  const productividadActas = buildTableSection(
    "Actas labradas por inspector",
    ["Inspector", "Total actas"],
    actasLimited.rows.map((r) => ({
      label: r.inspector,
      value: fmtNum(r.total_actas),
    }))
  );

  return {
    title: "Informe de Indicadores Operativos",
    periodoLine,
    distritoLabel: payload.meta.distritoLabel,
    inspectorLabel: payload.meta.inspectorLabel,
    generadoEl,
    desde,
    hasta,
    ejecutivoKpis,
    pendientesKpis,
    actasPorTipo: buildTableSection("Actas por tipo", ["Tipo", "Cantidad"], actasRows),
    riesgoRubros,
    riesgoMotivosNotificacion,
    riesgoMotivosComprobacion,
    riesgoDecomisoKg,
    noRealizadasTotal:
      payload.noRealizadasTotal != null ? fmtNum(payload.noRealizadasTotal) : null,
    noRealizadasContraproducencias,
    noRealizadasDistritos,
    productividadRealizadas,
    productividadNoRealizadas,
    productividadActas,
    productividadTruncatedNote: productividadTruncated
      ? "Se muestran los principales registros. El detalle completo se encuentra en el Excel."
      : null,
  };
}
