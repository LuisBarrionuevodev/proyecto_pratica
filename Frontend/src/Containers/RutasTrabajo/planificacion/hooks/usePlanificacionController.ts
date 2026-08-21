import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { IRutaIniciadorPendienteRow } from "../../../../api/rutasTrabajoApi";
import type { IRutaPoolDiaRow } from "../../../../api/rutaPoolDiaApi";
import type { IRubroCatalogItem } from "../../../../api/rubrosCatalogApi";
import { fetchDistritosCatalogo, type DistritoCatalogoItem } from "../../../../api/geolocalizacionApi";
import { fetchRubrosCatalogoCached } from "../../../../utils/rubrosCatalogCache";
import {
  getPlanificacionCargaDistritos,
  getPlanificacionMetricas,
  getPlanificacionPendientesContexto,
  getPlanificacionUrgentes,
  type IPendientesContextoParams,
} from "../api/planificacionApi";
import {
  aplicarFiltrosPendientesContexto as filtrarPendientesMapaPorFiltros,
  computeMetricasCardsDesdeMapa,
  filasConPinMapa,
  filtrarPendientesMapaPorCard,
  filtrarUrgentesVisibles,
  ordenarPendientes,
  sinPool,
  toPoolSet,
} from "../selectors/planificacionSelectors";
import type {
  ICargaDistritoRow,
  IPlanificacionMetricas,
  PlanificacionCardKey,
  PlanificacionFiltrosLista,
  UrgentesFiltrosAplicados,
} from "../types/planificacion.types";

const FILTROS_VACIOS: PlanificacionFiltrosLista = {
  q: "",
  rubro_id: null,
};

const URGENTES_FILTROS_VACIOS: UrgentesFiltrosAplicados = {
  tipo_urgente: "",
  rubro_id: null,
  q_identificador: "",
  q_domicilio: "",
};

/** Tamaño de página de la lista “Pendientes del contexto”. */
const M4_PAGE_LIST_SIZE = 25;
/** Chunk M4 por request para armar el universo del mapa (tope API típico). */
const M4_PAGE_MAP_CHUNK = 500;
/** Tope de páginas M4 consecutivas para el mapa (evita bucles infinitos). */
const M4_MAP_MAX_PAGES = 40;

/**
 * Parámetros M4 para carga del mapa (solo distrito; filtros panel en cliente — STAB-10d).
 */
function buildM4QueryBase(distritoActivoId: number): Omit<IPendientesContextoParams, "page" | "per_page"> {
  return {
    distrito_id: distritoActivoId,
    orden: "prioridad",
  };
}

/** Pool compartido con el contenedor RutasTrabajo (backend `ruta-pool-dia`). */
export type PlanificacionPoolControl = {
  poolIniciadorIds: number[];
  poolRowsById: Record<number, IRutaIniciadorPendienteRow>;
  poolBackendItems: IRutaPoolDiaRow[];
  poolIdByIniciadorId: Record<number, number>;
  poolLoading?: boolean;
  agregarAlPool: (row: IRutaIniciadorPendienteRow) => void | Promise<void>;
  quitarDelPool: (poolId: number) => void | Promise<void>;
  agregandoIniciadorIds?: ReadonlySet<number>;
  refreshPool?: (fechaOverride?: string | null, opts?: { silent?: boolean }) => Promise<void>;
};

export type UsePlanificacionControllerParams = {
  rutaId: number;
  onError: (msg: string) => void;
  poolControl: PlanificacionPoolControl;
};

export function usePlanificacionController({
  rutaId,
  onError,
  poolControl,
}: UsePlanificacionControllerParams) {
  const { poolIniciadorIds, poolRowsById, poolBackendItems, agregarAlPool, quitarDelPool } = poolControl;

  /** Evita que un `onError` inline del padre invalide load* y dispare efectos M1–M4 en bucle. */
  const onErrorRef = useRef(onError);
  onErrorRef.current = onError;

  const [distritoActivoId, setDistritoActivoId] = useState<number | null>(null);
  const [cardActiva, setCardActivaState] = useState<PlanificacionCardKey>(null);
  const [filtros, setFiltros] = useState<PlanificacionFiltrosLista>({ ...FILTROS_VACIOS });
  const [urgentesFiltrosAplicados, setUrgentesFiltrosAplicados] = useState<UrgentesFiltrosAplicados>({
    ...URGENTES_FILTROS_VACIOS,
  });
  const urgentesFiltrosRef = useRef(urgentesFiltrosAplicados);
  urgentesFiltrosRef.current = urgentesFiltrosAplicados;

  const [metricas, setMetricas] = useState<IPlanificacionMetricas | null>(null);
  const [cargaPorDistrito, setCargaPorDistrito] = useState<ICargaDistritoRow[]>([]);
  const [urgentesRaw, setUrgentesRaw] = useState<IRutaIniciadorPendienteRow[]>([]);
  const [urgentesMeta, setUrgentesMeta] = useState({ total: 0, page: 1, perPage: 25 });
  const [pendientesMapaRaw, setPendientesMapaRaw] = useState<IRutaIniciadorPendienteRow[]>([]);
  const [listaContextoPage, setListaContextoPage] = useState(1);
  const [distritoCatalogo, setDistritoCatalogo] = useState<DistritoCatalogoItem[]>([]);
  const [loadingDistritoCatalogo, setLoadingDistritoCatalogo] = useState(true);
  const [rubrosCatalogo, setRubrosCatalogo] = useState<IRubroCatalogItem[]>([]);

  const [loading, setLoading] = useState({
    metricas: false,
    cargaDistritos: false,
    urgentes: false,
    pendientesContexto: false,
    /** Primer M1 global (montaje). */
    metricasInicial: true,
  });

  const poolSet = useMemo(() => toPoolSet(poolIniciadorIds), [poolIniciadorIds]);

  const rubroNombrePorId = useCallback(
    (id: number) => rubrosCatalogo.find((r) => r.id === id)?.nombre ?? null,
    [rubrosCatalogo]
  );

  /** Pins con geocode, sin pool, sin filtros panel. */
  const pendientesMapaPins = useMemo(() => {
    return filasConPinMapa(sinPool(pendientesMapaRaw, poolSet));
  }, [pendientesMapaRaw, poolSet]);

  /** Universo visible: pins + filtros panel (rubro, domicilio, orden rubro). */
  const pendientesMapaBase = useMemo(() => {
    return filtrarPendientesMapaPorFiltros(pendientesMapaPins, filtros, rubroNombrePorId);
  }, [pendientesMapaPins, filtros, rubroNombrePorId]);

  const pendientesFiltradosPorCard = useMemo(() => {
    return ordenarPendientes(filtrarPendientesMapaPorCard(pendientesMapaBase, cardActiva));
  }, [pendientesMapaBase, cardActiva]);

  const pendientesMeta = useMemo(() => {
    if (distritoActivoId == null) {
      return { total: 0, page: 1, perPage: M4_PAGE_LIST_SIZE };
    }
    return {
      total: pendientesFiltradosPorCard.length,
      page: listaContextoPage,
      perPage: M4_PAGE_LIST_SIZE,
    };
  }, [distritoActivoId, pendientesFiltradosPorCard.length, listaContextoPage]);

  const pendientesContextoVisibles = useMemo(() => {
    if (distritoActivoId == null) return [];
    const start = (listaContextoPage - 1) * M4_PAGE_LIST_SIZE;
    return pendientesFiltradosPorCard.slice(start, start + M4_PAGE_LIST_SIZE);
  }, [distritoActivoId, pendientesFiltradosPorCard, listaContextoPage]);

  /** Mapa y lista comparten filtro por card sobre el mismo universo de pins. */
  const pendientesParaMapa = pendientesFiltradosPorCard;

  /** M3: backend filtra agregables (6J); además ocultar pool local hasta refrescar. */
  const urgentesVisibles = useMemo(
    () => filtrarUrgentesVisibles(urgentesRaw, poolSet),
    [urgentesRaw, poolSet]
  );

  /** KPIs: con distrito, desde pins visibles en mapa; sin distrito, M1 global. */
  const metricasVisibles = useMemo(() => {
    if (distritoActivoId == null) {
      return metricas;
    }
    return computeMetricasCardsDesdeMapa(pendientesMapaBase);
  }, [distritoActivoId, pendientesMapaBase, metricas]);

  const loadMetricas = useCallback(
    async (distritoId: number | null) => {
      setLoading((s) => ({ ...s, metricas: true }));
      try {
        const m = await getPlanificacionMetricas(rutaId, distritoId ?? undefined);
        setMetricas(m);
      } catch (e: unknown) {
        const ax = e as { response?: { data?: { detail?: string } } };
        onErrorRef.current(
          typeof ax?.response?.data?.detail === "string"
            ? ax.response.data.detail
            : "No se pudieron cargar las métricas"
        );
      } finally {
        setLoading((s) => ({ ...s, metricas: false, metricasInicial: false }));
      }
    },
    [rutaId]
  );

  const loadCargaDistritos = useCallback(async () => {
    setLoading((s) => ({ ...s, cargaDistritos: true }));
    try {
      const { items } = await getPlanificacionCargaDistritos(rutaId);
      setCargaPorDistrito(items);
    } catch (e: unknown) {
      const ax = e as { response?: { data?: { detail?: string } } };
      onErrorRef.current(
        typeof ax?.response?.data?.detail === "string"
          ? ax.response.data.detail
          : "No se pudo cargar la carga por distrito"
      );
    } finally {
      setLoading((s) => ({ ...s, cargaDistritos: false }));
    }
  }, [rutaId]);

  const loadUrgentes = useCallback(
    async (page = 1, perPage = 25, filtrosUrg?: UrgentesFiltrosAplicados) => {
      const f = filtrosUrg ?? urgentesFiltrosRef.current;
      setLoading((s) => ({ ...s, urgentes: true }));
      try {
        const { items, meta } = await getPlanificacionUrgentes(rutaId, {
          page,
          per_page: perPage,
          filtros: f,
        });
        setUrgentesRaw(items);
        setUrgentesMeta({ total: meta.total, page: meta.page, perPage: meta.per_page });
      } catch (e: unknown) {
        const ax = e as {
          response?: { status?: number; data?: { detail?: string; errors?: unknown } };
        };
        const status = ax?.response?.status;
        const detail = ax?.response?.data?.detail;
        if (import.meta.env.DEV && status != null) {
          console.warn("[planificacion/urgentes]", status, ax?.response?.data);
        }
        if (status === 422) {
          onErrorRef.current(
            "No se pudieron cargar los urgentes. Revisá los filtros aplicados."
          );
        } else if (typeof detail === "string" && detail.trim()) {
          onErrorRef.current(detail);
        } else {
          onErrorRef.current("No se pudieron cargar los urgentes.");
        }
      } finally {
        setLoading((s) => ({ ...s, urgentes: false }));
      }
    },
    [rutaId]
  );

  const aplicarFiltrosUrgentes = useCallback(
    (filtrosUrg: UrgentesFiltrosAplicados) => {
      setUrgentesFiltrosAplicados(filtrosUrg);
      void loadUrgentes(1, urgentesMeta.perPage, filtrosUrg);
    },
    [loadUrgentes, urgentesMeta.perPage]
  );

  const limpiarFiltrosUrgentes = useCallback(() => {
    setUrgentesFiltrosAplicados({ ...URGENTES_FILTROS_VACIOS });
    void loadUrgentes(1, urgentesMeta.perPage, URGENTES_FILTROS_VACIOS);
  }, [loadUrgentes, urgentesMeta.perPage]);

  const aplicarFiltrosPendientesContexto = useCallback((f: PlanificacionFiltrosLista) => {
    setFiltros(f);
    setListaContextoPage(1);
  }, []);

  const reiniciarFiltrosPendientesContexto = useCallback(() => {
    setFiltros({ ...FILTROS_VACIOS });
    setListaContextoPage(1);
  }, []);

  /** En la página actual de M3, cuántas filas del servicio están en el pool (no se listan en la bandeja). */
  const urgentesOcultosPorPoolEnPagina = useMemo(
    () => urgentesRaw.filter((r) => poolSet.has(r.id)).length,
    [urgentesRaw, poolSet]
  );

  /** Catálogo distritos (IDs reales DB) para mapa — no invasivo, API existente. */
  useEffect(() => {
    let cancel = false;
    setLoadingDistritoCatalogo(true);
    void fetchDistritosCatalogo()
      .then((res) => {
        if (!cancel) setDistritoCatalogo(res.items ?? []);
      })
      .catch(() => {
        if (!cancel) setDistritoCatalogo([]);
      })
      .finally(() => {
        if (!cancel) setLoadingDistritoCatalogo(false);
      });
    return () => {
      cancel = true;
    };
  }, []);

  useEffect(() => {
    let cancel = false;
    void fetchRubrosCatalogoCached()
      .then((items) => {
        if (!cancel) setRubrosCatalogo(items);
      })
      .catch(() => {
        if (!cancel) setRubrosCatalogo([]);
      });
    return () => {
      cancel = true;
    };
  }, []);

  /** Montaje: M2; M3 global al abrir (no depende del distrito del mapa). */
  useEffect(() => {
    void loadCargaDistritos();
  }, [loadCargaDistritos]);

  /** Montaje y cambio de ruta: M3 global (no refetch al mutar pool — ocultar con filtrarUrgentesVisibles). */
  useEffect(() => {
    void loadUrgentes(1, 25);
  }, [rutaId, loadUrgentes]);

  /** M1 solo sin distrito activo; con distrito los KPIs salen de `metricasVisibles` (M4 mapa). */
  useEffect(() => {
    if (distritoActivoId != null) {
      setLoading((s) => ({ ...s, metricasInicial: false }));
      return;
    }
    void loadMetricas(null);
  }, [distritoActivoId, loadMetricas]);

  const pendientesMapaReqSeq = useRef(0);
  const lastDistritoLoadedRef = useRef<number | null>(null);

  const loadPendientesMapa = useCallback(
    async (opts?: { silent?: boolean }) => {
      if (distritoActivoId == null) {
        lastDistritoLoadedRef.current = null;
        setPendientesMapaRaw([]);
        setLoading((s) => ({ ...s, pendientesContexto: false }));
        return;
      }
      if (lastDistritoLoadedRef.current !== distritoActivoId) {
        lastDistritoLoadedRef.current = distritoActivoId;
        setPendientesMapaRaw([]);
      }
      const seq = ++pendientesMapaReqSeq.current;
      if (!opts?.silent) {
        setLoading((s) => ({ ...s, pendientesContexto: true }));
      }
      try {
        const base = buildM4QueryBase(distritoActivoId);
        const merged = new Map<number, IRutaIniciadorPendienteRow>();
        let page = 1;
        let totalReported = 0;
        while (page <= M4_MAP_MAX_PAGES) {
          const { items, meta } = await getPlanificacionPendientesContexto(rutaId, {
            ...base,
            page,
            per_page: M4_PAGE_MAP_CHUNK,
            fields: "minimal",
          });
          if (seq !== pendientesMapaReqSeq.current) return;
          if (page === 1) totalReported = meta.total;
          for (const row of items) {
            merged.set(row.id, row);
          }
          if (items.length === 0) break;
          if (merged.size >= totalReported) break;
          if (items.length < M4_PAGE_MAP_CHUNK) break;
          page += 1;
        }
        if (seq !== pendientesMapaReqSeq.current) return;
        if (page > M4_MAP_MAX_PAGES && totalReported > 0 && merged.size < totalReported) {
          onErrorRef.current(
            `Hay ${totalReported} pendientes en contexto; en el mapa se cargaron ${merged.size} (límite de volumen). Use filtros para acotar o revise la lista paginada.`
          );
        }
        setPendientesMapaRaw(Array.from(merged.values()));
      } catch (e: unknown) {
        if (seq !== pendientesMapaReqSeq.current) return;
        const ax = e as { response?: { data?: { detail?: string; errors?: unknown } } };
        const detail =
          typeof ax?.response?.data?.detail === "string" ? ax.response.data.detail : null;
        onErrorRef.current(detail ?? "No se pudieron cargar los puntos del mapa para este distrito");
      } finally {
        if (seq === pendientesMapaReqSeq.current) {
          setLoading((s) => ({ ...s, pendientesContexto: false }));
        }
      }
    },
    [distritoActivoId, rutaId]
  );

  useEffect(() => {
    setListaContextoPage(1);
    setFiltros({ ...FILTROS_VACIOS });
  }, [distritoActivoId]);

  useEffect(() => {
    setListaContextoPage(1);
  }, [cardActiva, filtros.q, filtros.rubro_id]);

  /**
   * M4 mapa: solo distrito (filtros panel en cliente). Pool oculta candidatos vía sinPool (OPER-RUTA.7F.1).
   */
  useEffect(() => {
    void loadPendientesMapa();
  }, [loadPendientesMapa]);

  const seleccionarDistrito = useCallback((id: number | null) => {
    setDistritoActivoId(id);
    setListaContextoPage(1);
  }, []);

  const setCardActiva = useCallback((card: PlanificacionCardKey) => {
    setCardActivaState(card);
    setListaContextoPage(1);
  }, []);

  const loadPendientesContextoPage = useCallback(
    (page: number) => {
      if (distritoActivoId == null) return;
      setListaContextoPage(page);
    },
    [distritoActivoId]
  );

  const poolItemsOrdenados = useMemo(() => {
    return poolIniciadorIds.map((id) => poolRowsById[id]).filter(Boolean) as IRutaIniciadorPendienteRow[];
  }, [poolIniciadorIds, poolRowsById]);

  return {
    distritoActivoId,
    seleccionarDistrito,
    cardActiva,
    setCardActiva,
    filtros,
    urgentesFiltrosAplicados,
    rubroNombrePorId,
    aplicarFiltrosPendientesContexto,
    reiniciarFiltrosPendientesContexto,
    poolIniciadorIds,
    poolItemsOrdenados,
    poolBackendItems,
    agregarAlPool,
    quitarDelPool,
    metricas,
    metricasVisibles,
    cargaPorDistrito,
    urgentesVisibles,
    urgentesMeta,
    urgentesOcultosPorPoolEnPagina,
    loadUrgentes,
    aplicarFiltrosUrgentes,
    limpiarFiltrosUrgentes,
    pendientesContextoVisibles,
    pendientesParaMapa,
    pendientesMeta,
    loadPendientesContextoPage,
    refreshPendientesMapa: loadPendientesMapa,
    loading,
    distritoCatalogo,
    loadingDistritoCatalogo,
  };
}
