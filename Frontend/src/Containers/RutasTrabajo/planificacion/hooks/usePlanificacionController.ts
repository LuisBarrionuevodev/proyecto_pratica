import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { IRutaIniciadorPendienteRow } from "../../../../api/rutasTrabajoApi";
import { fetchDistritosCatalogo, type DistritoCatalogoItem } from "../../../../api/geolocalizacionApi";
import {
  getPlanificacionCargaDistritos,
  getPlanificacionMetricas,
  getPlanificacionPendientesContexto,
  getPlanificacionUrgentes,
} from "../api/planificacionApi";
import {
  aplicarCardContextoLista,
  sinPool,
  toPoolSet,
} from "../selectors/planificacionSelectors";
import type {
  ICargaDistritoRow,
  IPlanificacionMetricas,
  PlanificacionCardKey,
  PlanificacionFiltrosLista,
} from "../types/planificacion.types";

const FILTROS_VACIOS: PlanificacionFiltrosLista = {
  tipo: "",
  prioridad_categoria: "",
  q: "",
  orden: "prioridad",
};

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

  const [metricas, setMetricas] = useState<IPlanificacionMetricas | null>(null);
  const [cargaPorDistrito, setCargaPorDistrito] = useState<ICargaDistritoRow[]>([]);
  const [urgentesRaw, setUrgentesRaw] = useState<IRutaIniciadorPendienteRow[]>([]);
  const [urgentesMeta, setUrgentesMeta] = useState({ total: 0, page: 1, perPage: 25 });
  const [pendientesRaw, setPendientesRaw] = useState<IRutaIniciadorPendienteRow[]>([]);
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
    async (page = 1, perPage = 25) => {
      setLoading((s) => ({ ...s, urgentes: true }));
      try {
        const { items, meta } = await getPlanificacionUrgentes(rutaId, { page, per_page: perPage });
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
    [rutaId]
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

  /** Montaje: M2, M3; M1 vía efecto de distrito. */
  useEffect(() => {
    void loadCargaDistritos();
    void loadUrgentes(1, 25);
  }, [loadCargaDistritos, loadUrgentes]);

  /** M1 según distrito activo (null = global). */
  useEffect(() => {
    void loadMetricas(distritoActivoId);
  }, [distritoActivoId, loadMetricas]);

  const pendientesReqSeq = useRef(0);

  /** M4: distrito + card + filtros (página 1). */
  useEffect(() => {
    if (distritoActivoId == null) {
      setPendientesRaw([]);
      setPendientesMeta({ total: 0, page: 1, perPage: 25 });
      return;
    }
    const seq = ++pendientesReqSeq.current;
    const run = async () => {
      setLoading((s) => ({ ...s, pendientesContexto: true }));
      try {
        const cardParams = mapCardToM4Params(cardActiva);
        const { items, meta } = await getPlanificacionPendientesContexto(rutaId, {
          distrito_id: distritoActivoId,
          page: 1,
          per_page: 25,
          q: filtros.q.trim() || undefined,
          tipo: filtros.tipo || cardParams.tipo || undefined,
          prioridad_categoria:
            filtros.prioridad_categoria || cardParams.prioridad_categoria || undefined,
          orden: filtros.orden,
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
  ]);

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
        const cardParams = mapCardToM4Params(cardActiva);
        const { items, meta } = await getPlanificacionPendientesContexto(rutaId, {
          distrito_id: distritoActivoId,
          page,
          per_page: pendientesMeta.perPage,
          q: filtros.q.trim() || undefined,
          tipo: filtros.tipo || cardParams.tipo || undefined,
          prioridad_categoria:
            filtros.prioridad_categoria || cardParams.prioridad_categoria || undefined,
          orden: filtros.orden,
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
    poolIniciadorIds,
    poolItemsOrdenados,
    agregarAlPool,
    quitarDelPool,
    metricas,
    cargaPorDistrito,
    urgentesVisibles,
    urgentesMeta,
    loadUrgentes,
    pendientesContextoVisibles,
    pendientesMeta,
    loadPendientesContextoPage,
    loading,
    distritoCatalogo,
    loadingDistritoCatalogo,
  };
}
