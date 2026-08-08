import type {
  IndicadoresActasPorTipo,
  IndicadoresDistritoPendientesItem,
  IndicadoresEjecutivoResponse,
  IndicadoresNoRealizadasResponse,
  IndicadoresPendientesResponse,
  IndicadoresProductividadResponse,
  IndicadoresRiesgoResponse,
} from "../../../api/indicadoresApi";

export type DashboardExportKpi = { title: string; value: number | string };

export type DashboardExportMeta = {
  periodoLabel: string;
  distritoLabel: string;
  inspectorLabel: string;
};

export type DashboardExportPayload = {
  meta: DashboardExportMeta;
  resumenKpis: DashboardExportKpi[];
  ejecutivo: IndicadoresEjecutivoResponse | null;
  pendientes: IndicadoresPendientesResponse | null;
  actasPorTipo: IndicadoresActasPorTipo | null;
  pendientesDistritos: IndicadoresDistritoPendientesItem[];
  riesgo: IndicadoresRiesgoResponse | null;
  mercaderiaDecomisadaKg: number | null;
  noRealizadas: IndicadoresNoRealizadasResponse | null;
  noRealizadasTotal: number | null;
  productividad: IndicadoresProductividadResponse | null;
};

type BuildArgs = {
  periodoLabel: string;
  distritoLabel: string;
  inspectorLabel: string;
  ejecutivo: IndicadoresEjecutivoResponse | null;
  pendientes: IndicadoresPendientesResponse | null;
  riesgo: IndicadoresRiesgoResponse | null;
  noRealizadas: IndicadoresNoRealizadasResponse | null;
  noRealizadasTotal: number | null;
  productividad: IndicadoresProductividadResponse | null;
};

function pushEjecutivoKpis(
  cards: DashboardExportKpi[],
  ejecutivo: IndicadoresEjecutivoResponse
): void {
  const k = ejecutivo.kpis;
  const a = ejecutivo.actas_por_tipo;
  cards.push(
    { title: "Actuaciones realizadas", value: k.actuaciones_realizadas },
    { title: "Actas labradas (total)", value: k.actas_labradas },
    {
      title: "Reinspecciones por notificación (realizadas)",
      value: k.reinspecciones_notificacion_realizadas,
    }
  );
  cards.push(
    {
      title: "Reinspecciones por oficio (realizadas)",
      value: k.reinspecciones_oficio_realizadas,
    },
    { title: "Mercadería decomisada (kg)", value: k.mercaderia_decomisada_kg },
    {
      title: "Ratificaciones de clausura (realizadas)",
      value: k.ratificaciones_clausura_realizadas,
    },
    {
      title: "Ratificaciones de decomiso (realizadas)",
      value: k.ratificaciones_decomiso_realizadas,
    },
    { title: "Verificar e informar (realizadas)", value: k.verificar_informar_realizadas },
    { title: "Actas inspección", value: a.inspeccion },
    { title: "Actas notificación", value: a.notificacion },
    { title: "Actas comprobación", value: a.comprobacion },
    { title: "Actas clausura", value: a.clausura },
    { title: "Actas decomiso", value: a.decomiso }
  );
}

function pushPendientesKpis(cards: DashboardExportKpi[], pendientes: IndicadoresPendientesResponse): void {
  const p = pendientes.kpis;
  cards.push(
    { title: "Relevamientos pendientes", value: p.relevamientos_pendientes },
    { title: "Reinspecciones oficio pendientes", value: p.reinspecciones_oficio_pendientes },
    {
      title: "Reinspecciones notificación pendientes",
      value: p.reinspecciones_notificacion_pendientes,
    }
  );
}

function pushNoRealizadasKpis(
  cards: DashboardExportKpi[],
  _noRealizadas: IndicadoresNoRealizadasResponse,
  total: number | null
): void {
  if (total != null) {
    cards.push({ title: "No realizadas total", value: total });
  }
}

/**
 * Arma el payload de export Excel alineado a los bloques visibles del dashboard.
 * Solo mapea datos ya cargados en frontend; no recalcula ni consulta backend.
 */
export function buildDashboardExportPayload(args: BuildArgs): DashboardExportPayload {
  const resumenKpis: DashboardExportKpi[] = [];

  if (args.ejecutivo) {
    pushEjecutivoKpis(resumenKpis, args.ejecutivo);
  }
  if (args.noRealizadas) {
    pushNoRealizadasKpis(resumenKpis, args.noRealizadas, args.noRealizadasTotal);
  }
  if (args.pendientes) {
    pushPendientesKpis(resumenKpis, args.pendientes);
  }
  if (args.riesgo) {
    const r = args.riesgo.top_rubros[0];
    const mn = args.riesgo.top_motivos_notificacion[0];
    const mc = args.riesgo.top_motivos_comprobacion[0];
    if (r) resumenKpis.push({ title: "Riesgo: top rubro", value: `${r.rubro} (${r.cantidad})` });
    if (mn) {
      resumenKpis.push({
        title: "Riesgo: top motivo notificación",
        value: `${mn.motivo} (${mn.cantidad})`,
      });
    }
    if (mc) {
      resumenKpis.push({
        title: "Riesgo: top motivo comprobación",
        value: `${mc.motivo} (${mc.cantidad})`,
      });
    }
    if (args.ejecutivo) {
      resumenKpis.push({
        title: "Riesgo: mercadería decomisada total (kg)",
        value: args.ejecutivo.kpis.mercaderia_decomisada_kg,
      });
    }
  }
  if (args.productividad) {
    const topReal = args.productividad.inspectores_realizadas[0];
    const topNoReal = args.productividad.inspectores_no_realizadas[0];
    const topActas = args.productividad.actas_por_inspector[0];
    if (topReal) {
      resumenKpis.push({
        title: "Top inspector por actuaciones realizadas",
        value: `${topReal.inspector} (${topReal.total_realizadas})`,
      });
    }
    if (topNoReal) {
      resumenKpis.push({
        title: "Top inspector por no realizadas",
        value: `${topNoReal.inspector} (${topNoReal.total_no_realizadas})`,
      });
    }
    if (topActas) {
      resumenKpis.push({
        title: "Top inspector por actas labradas",
        value: `${topActas.inspector} (${topActas.total_actas})`,
      });
    }
  }

  return {
    meta: {
      periodoLabel: args.periodoLabel,
      distritoLabel: args.distritoLabel,
      inspectorLabel: args.inspectorLabel,
    },
    resumenKpis,
    ejecutivo: args.ejecutivo,
    pendientes: args.pendientes,
    actasPorTipo: args.ejecutivo?.actas_por_tipo ?? null,
    pendientesDistritos: args.pendientes?.distritos_con_mas_pendientes ?? [],
    riesgo: args.riesgo,
    mercaderiaDecomisadaKg: args.ejecutivo?.kpis.mercaderia_decomisada_kg ?? null,
    noRealizadas: args.noRealizadas,
    noRealizadasTotal: args.noRealizadasTotal,
    productividad: args.productividad,
  };
}
