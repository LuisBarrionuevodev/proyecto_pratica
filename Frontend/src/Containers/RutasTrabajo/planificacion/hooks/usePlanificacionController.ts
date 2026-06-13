import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { IRutaIniciadorPendienteRow } from "../../../../api/rutasTrabajoApi";
import { fetchDistritosCatalogo, type DistritoCatalogoItem } from "../../../../api/geolocalizacionApi";
import {
  getPlanificacionCargaDistritos,
  getPlanificacionMetricas,
  getPlanificacionPendientesContexto,
  getPlanificacionUrgentes,
  type IPendientesContextoParams,
} from "../api/planificacionApi";
import {
  aplicarCardContextoLista,
  computeMetricasDesdeFilas,
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
  tipo: "",
  prioridad_categoria: "",
  q: "",
  orden: "prioridad",
};

const URGENTES_FILTROS_VACIOS: UrgentesFiltrosAplicados = {
  tipo_urgente: "",
  q: "",
};

/** Tamaño de página de la lista “Pendientes del contexto”. */
const M4_PAGE_LIST_SIZE = 25;
/** Chunk M4 por request para armar el universo del mapa (tope API típico). */
const M4_PAGE_MAP_CHUNK = 500;
/** Tope de páginas M4 consecutivas para el mapa (evita bucles infinitos). */
const M4_MAP_MAX_PAGES = 40;

/**
 * Deriva filtros de API M4 según la KPI card activa.
 *
 * Nota: `OFICIOS_URGENTES` no puede expresarse con un solo `tipo` en la API (varios tipos
 * de oficio). Lista y mapa piden M4 sin `tipo` de card y aplican el mismo criterio en
 * cliente con `aplicarCardContextoLista`.
 */
function mapCardToM4Params(card: PlanificacionCardKey): {
  tipo?: string;
  prioridad_categoria?: "BAJA" | "MEDIA" | "ALTA";
} {
  if (card == null || card === "OFICIOS_URGENTES") {
    return {};
  }
  if (card === "ALTA_PRIORIDAD") {
    return { prioridad_categoria: "ALTA" };
  }
  if (card === "DENUNCIAS") {
    return { tipo: "DENUNCIA" };
  }
  if (card === "NOTIFICACIONES") {
    return { tipo: "REINSPECCION_NOTIFICACION" };
  }
  if (card === "RELEVAMIENTOS") {
    return { tipo: "RELEVAMIENTO" };
  }
  return {};
}

/**
 * Parámetros M4 comunes para lista y mapa (mismo criterio backend; sin paginación).
 *
 * Parámetros:
 * - `distritoActivoId`: distrito seleccionado.
 * - `cardActiva`: KPI card (se fusiona con filtros del panel).
 * - `filtros`: búsqueda / tipo / prioridad / orden del panel.
 *
 * Retorno: objeto listo para spread en `getPlanificacionPendientesContexto` junto con `page` y `per_page`.
 */
function buildM4QueryBase(
  distritoActivoId: number,
  cardActiva: PlanificacionCardKey,
  filtros: PlanificacionFiltrosLista
): Omit<IPendientesContextoParams, "page" | "per_page"> {
  const cardParams = mapCardToM4Params(cardActiva);
  return {
    distrito_id: distritoActivoId,
    q: filtros.q.trim() || undefined,
    tipo: filtros.tipo || cardParams.tipo || undefined,
    prioridad_categoria:
      filtros.prioridad_categoria || cardParams.prioridad_categoria || undefined,
    orden: filtros.orden,
  };
}

/** Pool compartido con el contenedor RutasTrabajo (misma etapa Planificación → Asignación). */
export type PlanificacionPoolControl = {
  poolIniciadorIds: number[];
  poolRowsById: Record<number, IRutaIniciadorPendienteRow>;
  agregarAlPool: (row: IRutaIniciadorPendienteRow) => void;
  quitarDelPool: (id: number) => void;
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
  const { poolIniciadorIds, poolRowsById, agregarAlPool, quitarDelPool } = poolControl;

  /** Evita que un `onError` inline del padre invalide load* y dispare efectos M1–M4 en bucle. */
  const onErrorRef = useRef(onError);
  onErrorRef.current = onError;

  const [distritoActivoId, setDistritoActivoId] = useState<number | null>(null);
  const [cardActiva, setCardActivaState] = useState<PlanificacionCardKey>(null);
  const [filtros, setFiltros] = useState<PlanificacionFiltrosLista>({ ...FILTROS_VACIOS });
  const [urgentesFiltrosAplicados, setUrgentesFiltrosAplicados] = useState<UrgentesFiltrosAplicados>({
    ...URGENTES_FILTROS_VACIOS,
  });

  const [metricas, setMetricas] = useState<IPlanificacionMetricas | null>(null);
  const [cargaPorDistrito, setCargaPorDistrito] = useState<ICargaDistritoRow[]>([]);
  const [urgentesRaw, setUrgentesRaw] = useState<IRutaIniciadorPendienteRow[]>([]);
  const [urgentesMeta, setUrgentesMeta] = useState({ total: 0, page: 1, perPage: 25 });
  const [pendientesRaw, setPendientesRaw] = useState<IRutaIniciadorPendienteRow[]>([]);
  /** Misma query M4 con per_page alto: puntos en mapa al elegir distrito (no limitado a la página de la lista). */
  const [pendientesMapaRaw, setPendientesMapaRaw] = useState<IRutaIniciadorPendienteRow[]>([]);
  const [pendientesMeta, setPendientesMeta] = useState({ total: 0, page: 1, perPage: 25 });
  const [distritoCatalogo, setDistritoCatalogo] = useState<DistritoCatalogoItem[]>([]);
  const [loadingDistritoCatalogo, setLoadingDistritoCatalogo] = useState(true);

  const [loading, setLoading] = useState({
    metricas: false,
    cargaDistritos: false,
    urgentes: false,
    pendientesContexto: false,
    /** Primer M1 global (montaje). */
    metricasInicial: true,
  });

  const poolSet = useMemo(() => toPoolSet(poolIniciadorIds), [poolIniciadorIds]);

  /**
   * M3: backend ya filtra tipo≠RELEVAMIENTO y prioridad≥3; alineamos con `elegible_urgente` del presenter si viene.
   * Pool excluye filas en ambas columnas.
   */
  const urgentesVisibles = useMemo(
    () =>
      sinPool(urgentesRaw, poolSet).filter((r) => {
        if (r.tipo_iniciador === "RELEVAMIENTO") return false;
        if (r.elegible_urgente === false) return false;
        return true;
      }),
    [urgentesRaw, poolSet]
  );

  const pendientesContextoVisibles = useMemo(() => {
    const sinP = sinPool(pendientesRaw, poolSet);
    return aplicarCardContextoLista(sinP, cardActiva);
  }, [pendientesRaw, poolSet, cardActiva]);

  /** Mismo universo que la lista respecto a card + pool; datos M4 del mapa ya alineados con `buildM4QueryBase`. */
  const pendientesParaMapa = useMemo(() => {
    const sinP = sinPool(pendientesMapaRaw, poolSet);
    return aplicarCardContextoLista(sinP, cardActiva);
  }, [pendientesMapaRaw, poolSet, cardActiva]);

  /**
   * KPIs alineados al mapa visible: con distrito activo, cuenta el dataset M4 filtrado (panel + pool).
   * Sin distrito, conserva M1 global del backend.
   */
  const metricasVisibles = useMemo(() => {
    if (distritoActivoId == null) {
      return metricas;
    }
    return computeMetricasDesdeFilas(sinPool(pendientesMapaRaw, poolSet));
  }, [distritoActivoId, pendientesMapaRaw, poolSet, metricas]);

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
    async (page = 1, perPage = 25, filtrosUrg = urgentesFiltrosAplicados) => {
      setLoading((s) => ({ ...s, urgentes: true }));
      try {
        const { items, meta } = await getPlanificacionUrgentes(rutaId, {
          page,
          per_page: perPage,
          ...(distritoActivoId != null ? { distrito_id: distritoActivoId } : {}),
          ...(filtrosUrg.tipo_urgente ? { tipo_urgente: filtrosUrg.tipo_urgente } : {}),
          ...(filtrosUrg.q ? { q: filtrosUrg.q } : {}),
        });
        setUrgentesRaw(items);
        setUrgentesMeta({ total: meta.total, page: meta.page, perPage: meta.per_page });
      } catch (e: unknown) {
        const ax = e as { response?: { data?: { detail?: string } } };
        onErrorRef.current(
          typeof ax?.response?.data?.detail === "string"
            ? ax.response.data.detail
            : "No se pudieron cargar urgentes"
        );
      } finally {
        setLoading((s) => ({ ...s, urgentes: false }));
      }
    },
    [rutaId, distritoActivoId, urgentesFiltrosAplicados]
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

  /** Montaje: M2; M3 al abrir y al cambiar distrito (alineado con M1 «alta» territorial). */
  useEffect(() => {
    void loadCargaDistritos();
  }, [loadCargaDistritos]);

  useEffect(() => {
    void loadUrgentes(1, 25);
  }, [loadUrgentes]);

  /** M1 según distrito activo (null = global). */
  useEffect(() => {
    void loadMetricas(distritoActivoId);
  }, [distritoActivoId, loadMetricas]);

  const pendientesReqSeq = useRef(0);
  const pendientesMapaReqSeq = useRef(0);
  /**
   * Evita mostrar pins de un contexto M4 anterior (otro distrito, card o filtros) hasta recibir
   * la nueva carga; la clave debe coincidir con las dependencias del efecto M4 mapa.
   */
  const lastMapContextKeyRef = useRef<string>("");

  /**
   * Se incrementa al reiniciar el panel (botón o equivalente) para forzar nuevo M4 aunque los
   * filtros ya estén vacíos — evita mapa/lista “pegados” tras errores o estados raros.
   */
  const [pendientesContextoRefetchSignal, setPendientesContextoRefetchSignal] = useState(0);

  /** M4: distrito + card + filtros (página 1). */
  useEffect(() => {
    if (distritoActivoId == null) {
      setPendientesRaw([]);
      setPendientesMapaRaw([]);
      setPendientesMeta({ total: 0, page: 1, perPage: 25 });
      return;
    }
    const seq = ++pendientesReqSeq.current;
    const run = async () => {
      setLoading((s) => ({ ...s, pendientesContexto: true }));
      try {
        const base = buildM4QueryBase(distritoActivoId, cardActiva, filtros);
        const { items, meta } = await getPlanificacionPendientesContexto(rutaId, {
          ...base,
          page: 1,
          per_page: M4_PAGE_LIST_SIZE,
        });
        if (seq !== pendientesReqSeq.current) return;
        setPendientesRaw(items);
        setPendientesMeta({ total: meta.total, page: meta.page, perPage: meta.per_page });
      } catch (e: unknown) {
        if (seq !== pendientesReqSeq.current) return;
        const ax = e as { response?: { data?: { detail?: string } } };
        onErrorRef.current(
          typeof ax?.response?.data?.detail === "string"
            ? ax.response.data.detail
            : "No se pudieron cargar pendientes del distrito"
        );
      } finally {
        if (seq === pendientesReqSeq.current) {
          setLoading((s) => ({ ...s, pendientesContexto: false }));
        }
      }
    };
    void run();
  }, [
    distritoActivoId,
    cardActiva,
    filtros.q,
    filtros.tipo,
    filtros.prioridad_categoria,
    filtros.orden,
    rutaId,
    pendientesContextoRefetchSignal,
  ]);

  /**
   * M4 mapa: mismo criterio que la lista (`buildM4QueryBase`), con paginación hasta cubrir `meta.total`
   * o hasta `M4_MAP_MAX_PAGES`. Los pins visibles aplican además `aplicarCardContextoLista` vía
   * `pendientesParaMapa` (alineación con OFICIOS_URGENTES y similares).
   */
  useEffect(() => {
    if (distritoActivoId == null) {
      lastMapContextKeyRef.current = "";
      setPendientesMapaRaw([]);
      return;
    }
    const mapContextKey = JSON.stringify({
      distritoId: distritoActivoId,
      card: cardActiva,
      q: filtros.q.trim(),
      tipo: filtros.tipo,
      prioridad_categoria: filtros.prioridad_categoria,
      orden: filtros.orden,
      refetch: pendientesContextoRefetchSignal,
    });
    if (lastMapContextKeyRef.current !== mapContextKey) {
      lastMapContextKeyRef.current = mapContextKey;
      setPendientesMapaRaw([]);
    }
    const seq = ++pendientesMapaReqSeq.current;
    const run = async () => {
      try {
        const base = buildM4QueryBase(distritoActivoId, cardActiva, filtros);
        const merged = new Map<number, IRutaIniciadorPendienteRow>();
        let page = 1;
        let totalReported = 0;
        while (page <= M4_MAP_MAX_PAGES) {
          const { items, meta } = await getPlanificacionPendientesContexto(rutaId, {
            ...base,
            page,
            per_page: M4_PAGE_MAP_CHUNK,
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
      }
    };
    void run();
  }, [
    distritoActivoId,
    cardActiva,
    filtros.q,
    filtros.tipo,
    filtros.prioridad_categoria,
    filtros.orden,
    rutaId,
    pendientesContextoRefetchSignal,
  ]);

  /** Limpia búsqueda y filtros del panel izquierdo (no cambia distrito ni KPI card) y relanza M4 lista + mapa. */
  const reiniciarFiltrosPendientesContexto = useCallback(() => {
    setFiltros({ ...FILTROS_VACIOS });
    setPendientesContextoRefetchSignal((n) => n + 1);
  }, []);

  const seleccionarDistrito = useCallback((id: number | null) => {
    setDistritoActivoId(id);
  }, []);

  const setCardActiva = useCallback((card: PlanificacionCardKey) => {
    setCardActivaState(card);
  }, []);

  const loadPendientesContextoPage = useCallback(
    async (page: number) => {
      if (distritoActivoId == null) return;
      setLoading((s) => ({ ...s, pendientesContexto: true }));
      try {
        const base = buildM4QueryBase(distritoActivoId, cardActiva, filtros);
        const { items, meta } = await getPlanificacionPendientesContexto(rutaId, {
          ...base,
          page,
          per_page: pendientesMeta.perPage,
        });
        setPendientesRaw(items);
        setPendientesMeta({ total: meta.total, page: meta.page, perPage: meta.per_page });
      } catch (e: unknown) {
        const ax = e as { response?: { data?: { detail?: string } } };
        onErrorRef.current(
          typeof ax?.response?.data?.detail === "string"
            ? ax.response.data.detail
            : "No se pudieron cargar pendientes"
        );
      } finally {
        setLoading((s) => ({ ...s, pendientesContexto: false }));
      }
    },
    [distritoActivoId, rutaId, cardActiva, filtros, pendientesMeta.perPage]
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
    setFiltros,
    reiniciarFiltrosPendientesContexto,
    poolIniciadorIds,
    poolItemsOrdenados,
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
    loading,
    distritoCatalogo,
    loadingDistritoCatalogo,
  };
}
