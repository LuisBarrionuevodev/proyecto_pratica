import { useCallback, useEffect, useMemo, useRef, useState, type Dispatch, type SetStateAction } from "react";
import { Box } from "@mui/material";
import type { CatalogItem } from "../../api/gridApi";
import { useAppFeedback } from "../../components/feedback/useAppFeedback";
import { fetchInspectoresCatalogItemsCached } from "../../utils/inspectoresCatalogCache";
import {
  assignRutaItems,
  createRutaGrupo,
  createRutaTrabajo,
  deleteRutaGrupo,
  getRutaTrabajoDetail,
  publicarRutaTrabajo,
  replaceRutaGrupoInspectores,
  type IRutaGrupoMin,
  type IRutaIniciadorPendienteRow,
  type IRutaItemMin,
  type IRutaTrabajo,
} from "../../api/rutasTrabajoApi";
import { agregarDesdePoolRuta } from "../../api/rutaPoolDiaApi";
import type { AsignacionPoolFilters } from "./Components/TablaIniciadoresPendientes";
import { ASIGNACION_POOL_FILTROS_VACIOS } from "./Components/TablaIniciadoresPendientes";
import ModalAsignarInspectoresGrupo from "./Components/ModalAsignarInspectoresGrupo";
import ModalCrearGrupoRuta from "./Components/ModalCrearGrupoRuta";
import ModalCrearRutaTrabajo from "./Components/ModalCrearRutaTrabajo";
import {
  clearPersistedRutaId,
  persistRutaId,
  useRutaTrabajoBorradorActions,
  useRutasTrabajoSession,
} from "./hooks";
import { useRutaPoolDiaBackend } from "./hooks/useRutaPoolDiaBackend";
import { type RutaFlowStep } from "./Components/RutasTrabajoFlowStepper";
import { RutaTrabajoCompactHeader } from "./Components/RutaTrabajoCompactHeader";
import { computeAsignacionContinuarMapaFinal } from "./utils/asignacionContinuarMapaFinal";
import { RutasEmptyView } from "./views/RutasEmptyView";
import { RutasPlanificacionView } from "./views/RutasPlanificacionView";
import { RutasMapaOperativoView } from "./views/RutasMapaOperativoView";
import { PlanificacionView } from "./planificacion/PlanificacionView";
import type { PlanificacionPoolControl } from "./planificacion/hooks/usePlanificacionController";
import {
  buildDistritoOptionsFromPool,
  filterAsignacionPoolRows,
} from "./utils/filterAsignacionPool";
import { buildIniciadorByIdMap } from "./utils/iniciadorDetalleOperativo";
import {
  evaluarPublicacionRuta,
  resumenBloqueoPublicacion,
} from "./utils/rutaPublicarReadiness";

const RutasTrabajo = () => {
  /** Flujo secuencial: 1 Planificación → 2 Asignación → 3 Mapa final (desbloqueo solo por CTA). */
  const [flowStep, setFlowStep] = useState<RutaFlowStep>(1);
  const [flowMaxUnlocked, setFlowMaxUnlocked] = useState<RutaFlowStep>(1);
  const [ruta, setRuta] = useState<IRutaTrabajo | null>(null);
  const [grupos, setGrupos] = useState<IRutaGrupoMin[]>([]);
  const [items, setItems] = useState<IRutaItemMin[]>([]);
  const [asignacionFilters, setAsignacionFilters] = useState<AsignacionPoolFilters>({
    ...ASIGNACION_POOL_FILTROS_VACIOS,
  });
  /** Solo carga/refresco completo del detail de ruta (no PATCH sueltos). */
  const [detailLoading, setDetailLoading] = useState(false);
  const feedback = useAppFeedback();
  const notifyError = useCallback<Dispatch<SetStateAction<string | null>>>(
    (msg) => {
      const text = typeof msg === "function" ? msg(null) : msg;
      if (text?.trim()) feedback.error(text.trim());
    },
    [feedback]
  );

  const [openCrearGrupo, setOpenCrearGrupo] = useState(false);
  const [openCrearRuta, setOpenCrearRuta] = useState(false);
  const [crearRutaFechaSugerida, setCrearRutaFechaSugerida] = useState<string | null>(null);
  const [openAsignarInspectores, setOpenAsignarInspectores] = useState(false);
  const [grupoSeleccionado, setGrupoSeleccionado] = useState<IRutaGrupoMin | null>(null);
  const [inspectoresCatalogo, setInspectoresCatalogo] = useState<CatalogItem[]>([]);
  const [publishingRuta, setPublishingRuta] = useState(false);
  const rutaId = ruta?.id ?? null;
  const itemsActivos = useMemo(() => items.filter((it) => !it.deleted_at), [items]);
  const publicarReadiness = useMemo(
    () => evaluarPublicacionRuta(grupos, itemsActivos),
    [grupos, itemsActivos]
  );
  /** Borrador con detalle cargado y condiciones mínimas para publicar sin 409 previsible. */
  const puedeIntentarPublicar = Boolean(
    rutaId && ruta?.estado_ruta === "BORRADOR" && !detailLoading && publicarReadiness.puedePublicar
  );
  const publicarTooltip = resumenBloqueoPublicacion(publicarReadiness.blockers);
  /** Ruta publicada u otro estado no borrador: mapa en preview histórica solo lectura. */
  const vistaHistoricaReadOnly = Boolean(ruta && ruta.estado_ruta !== "BORRADOR");

  const handlePoolBackendError = useCallback(
    (msg: string) => {
      feedback.error(msg);
    },
    [feedback]
  );

  const {
    poolItems: poolBackendItems,
    poolIniciadorIds,
    poolRowsById,
    poolIdByIniciadorId,
    loading: poolLoading,
    agregandoIniciadorIds,
    refreshPool,
    agregarAlPool,
    quitarDelPool,
  } = useRutaPoolDiaBackend({
    fecha: ruta?.fecha,
    rutaTrabajoId: rutaId,
    onError: handlePoolBackendError,
  });

  const loadRutaDetail = useCallback(async (targetRutaId: number, opts?: { showLoading?: boolean }) => {
    const showLoading = opts?.showLoading !== false;
    if (showLoading) setDetailLoading(true);
    try {
      const detail = await getRutaTrabajoDetail(targetRutaId);
      setRuta(detail.ruta);
      setGrupos(detail.grupos);
      // Por grupo, el API devuelve ítems ordenados por id ascendente (sin campo de secuencia de visita en modelo).
      const reconstructedItems = (detail.grupos ?? []).flatMap((g) => g.items ?? []);
      setItems(reconstructedItems);
      setAsignacionFilters({ ...ASIGNACION_POOL_FILTROS_VACIOS });
      persistRutaId(targetRutaId);
      const esBorrador = detail.ruta.estado_ruta === "BORRADOR";
      // Planificación y APIs asociadas exigen BORRADOR; rutas publicadas se abren en mapa (base para preview histórica).
      setFlowStep(esBorrador ? 1 : 3);
      setFlowMaxUnlocked(esBorrador ? 1 : 3);
    } catch (err: any) {
      notifyError(err?.response?.data?.detail || "No se pudo cargar el detalle de la ruta");
      setRuta(null);
      setGrupos([]);
      setItems([]);
      clearPersistedRutaId();
    } finally {
      if (showLoading) setDetailLoading(false);
    }
  }, []);

  /** Actualiza grupos e ítems desde el servidor sin resetear el flujo ni el pool (Asignación). */
  const refreshRutaBorrador = useCallback(async (opts?: { showLoading?: boolean }) => {
    if (!rutaId) return;
    const showLoading = opts?.showLoading !== false;
    if (showLoading) setDetailLoading(true);
    try {
      const detail = await getRutaTrabajoDetail(rutaId);
      setRuta(detail.ruta);
      setGrupos(detail.grupos);
      // Mismo orden por grupo que en loadRutaDetail (ítems por id ascendente en presenter).
      const reconstructedItems = (detail.grupos ?? []).flatMap((g) => g.items ?? []);
      setItems(reconstructedItems);
    } catch (err: any) {
      notifyError(err?.response?.data?.detail || "No se pudo sincronizar el borrador");
    } finally {
      if (showLoading) setDetailLoading(false);
    }
  }, [rutaId]);

  const syncPoolTrasQuitarItem = useCallback(async () => {
    await Promise.all([
      refreshRutaBorrador({ showLoading: false }),
      refreshPool(ruta?.fecha, { silent: true }),
    ]);
  }, [refreshRutaBorrador, refreshPool, ruta?.fecha]);

  const poolControl: PlanificacionPoolControl = useMemo(
    () => ({
      poolIniciadorIds,
      poolRowsById,
      poolBackendItems,
      poolIdByIniciadorId,
      poolLoading,
      agregandoIniciadorIds,
      agregarAlPool,
      quitarDelPool,
      refreshPool,
    }),
    [
      poolIniciadorIds,
      poolRowsById,
      poolBackendItems,
      poolIdByIniciadorId,
      poolLoading,
      agregandoIniciadorIds,
      agregarAlPool,
      quitarDelPool,
      refreshPool,
    ]
  );

  const poolRowsOrdered = useMemo(
    () => poolIniciadorIds.map((id) => poolRowsById[id]).filter(Boolean) as IRutaIniciadorPendienteRow[],
    [poolIniciadorIds, poolRowsById]
  );

  const iniciadoresTablaAsignacion = useMemo(
    () => filterAsignacionPoolRows(poolRowsOrdered, asignacionFilters),
    [poolRowsOrdered, asignacionFilters]
  );

  const distritoFilterOptions = useMemo(() => buildDistritoOptionsFromPool(poolRowsOrdered), [poolRowsOrdered]);

  useRutasTrabajoSession(loadRutaDetail);

  const handleCreateRuta = async (payload: { fecha: string; turno: "MANIANA" | "TARDE"; observaciones?: string }) => {
    try {
      const resp = await createRutaTrabajo({
        fecha: payload.fecha,
        turno: payload.turno,
        observaciones: payload.observaciones || null,
      });
      await loadRutaDetail(resp.item.id);
      setOpenCrearRuta(false);
      setCrearRutaFechaSugerida(null);
      feedback.success(`Ruta ${resp.item.numero} creada en BORRADOR.`);
    } catch (err: any) {
      notifyError(err?.response?.data?.detail || "No se pudo crear la ruta");
    }
  };

  /** No-op: la grilla de Asignación usa solo el pool local; se mantiene la firma para mutaciones de borrador. */
  const loadPendientes = useCallback(async () => {}, []);

  const handleAsignacionFiltersChange = useCallback((next: AsignacionPoolFilters) => {
    setAsignacionFilters(next);
  }, []);

  /** Debe ser estable: `usePlanificacionController` depende de `onError` en load* y efectos M1–M4. */
  const handlePlanificacionError = useCallback(
    (msg: string) => {
      feedback.error(msg);
    },
    [feedback]
  );

  /** Limpia sesión y estado local: vuelve a la pantalla de elegir borrador / crear ruta (también tras publicar). */
  const resetVistaRutaTrabajo = useCallback(() => {
    clearPersistedRutaId();
    setRuta(null);
    setGrupos([]);
    setItems([]);
    setAsignacionFilters({ ...ASIGNACION_POOL_FILTROS_VACIOS });
    setOpenCrearGrupo(false);
    setOpenAsignarInspectores(false);
    setGrupoSeleccionado(null);
    setFlowStep(1);
    setFlowMaxUnlocked(1);
  }, []);

  const handlePublicarRuta = useCallback(async () => {
    if (!rutaId || ruta?.estado_ruta !== "BORRADOR" || publishingRuta) return;

    const readiness = evaluarPublicacionRuta(grupos, itemsActivos);
    if (!readiness.puedePublicar) {
      notifyError(readiness.blockers.join(" "));
      return;
    }

    setPublishingRuta(true);
    try {
      await publicarRutaTrabajo(rutaId);
      await loadRutaDetail(rutaId, { showLoading: true });
      feedback.success(
        "Ruta publicada. Usá «Descargar resumen (PDF)» y «Descargar órdenes de salida y órdenes de trabajo» en esta pantalla para la documentación oficial."
      );
    } catch (err: unknown) {
      const ax = err as { response?: { status?: number; data?: { detail?: unknown } } };
      const status = ax?.response?.status;
      const detail = ax?.response?.data?.detail;
      if (typeof detail === "string") {
        notifyError(detail);
      } else if (status === 409) {
        notifyError(
          "No se cumplen las condiciones para publicar. Revisá inspectores por grupo, ítems activos y OT en cada ítem."
        );
      } else {
        notifyError("No se pudo publicar la ruta. Intentá de nuevo más tarde.");
      }
    } finally {
      setPublishingRuta(false);
    }
  }, [feedback, grupos, itemsActivos, loadRutaDetail, publishingRuta, ruta?.estado_ruta, rutaId]);

  useEffect(() => {
    const loadInspectores = async () => {
      try {
        const items = await fetchInspectoresCatalogItemsCached();
        setInspectoresCatalogo(items);
      } catch {
        setInspectoresCatalogo([]);
      }
    };
    void loadInspectores();
  }, []);

  const { moveItem: handleMoveItem, deleteItem: handleQuitarItem, saveOtItem: handleSaveOt } =
    useRutaTrabajoBorradorActions({
      rutaId,
      setItems,
      setError: notifyError,
      loadPendientes,
      onAfterDeleteItem: syncPoolTrasQuitarItem,
    });

  const handleEliminarDelPoolSeleccion = useCallback(
    async (poolIds: number[]) => {
      for (const poolId of poolIds) {
        await quitarDelPool(poolId);
      }
    },
    [quitarDelPool]
  );

  const handleCreateGrupo = async () => {
    if (!rutaId) return;
    try {
      const resp = await createRutaGrupo(rutaId, {});
      setGrupos((prev) => [...prev, { ...resp.item, items: resp.item.items ?? [] }]);
      setOpenCrearGrupo(false);
      feedback.success("Grupo creado correctamente.");
    } catch (err: any) {
      notifyError(err?.response?.data?.detail || "No se pudo crear el grupo");
    }
  };

  const handleCloseModalInspectores = useCallback(() => {
    setOpenAsignarInspectores(false);
    setGrupoSeleccionado(null);
  }, []);

  const handleReplaceInspectores = useCallback(
    async (inspectorIds: number[]) => {
      if (!rutaId || !grupoSeleccionado) return;
      const grupoActual = grupos.find((g) => g.id === grupoSeleccionado.id);
      if (!grupoActual) {
        notifyError("El grupo seleccionado ya no existe en el borrador actual.");
        await loadRutaDetail(rutaId);
        return;
      }
      const grupoId = grupoSeleccionado.id;
      try {
        const resp = await replaceRutaGrupoInspectores(rutaId, grupoId, {
          inspector_ids: inspectorIds,
        });
        setGrupos((prev) => prev.map((g) => (g.id === grupoId ? { ...g, inspectores: resp.items } : g)));
        setOpenAsignarInspectores(false);
        setGrupoSeleccionado(null);
        feedback.success("Inspectores del grupo actualizados.");
      } catch (err: any) {
        notifyError(err?.response?.data?.detail || "No se pudieron actualizar inspectores");
      }
    },
    [feedback, grupoSeleccionado, grupos, loadRutaDetail, rutaId]
  );

  const assignIniciadoresToGrupo = useCallback(
    async (grupoId: number, iniciadorIds: number[]): Promise<boolean> => {
      if (!rutaId || iniciadorIds.length === 0) return false;
      try {
        const poolIds = iniciadorIds
          .map((id) => poolIdByIniciadorId[id])
          .filter((pid): pid is number => pid != null);

        if (poolIds.length === iniciadorIds.length) {
          const resp = await agregarDesdePoolRuta(rutaId, { pool_ids: poolIds, grupo_id: grupoId });
          setItems((prev) => {
            const map = new Map(prev.map((i) => [i.id, i]));
            resp.items.forEach((i) => map.set(i.id, i));
            return Array.from(map.values());
          });
          await refreshPool(ruta?.fecha);
        } else {
          const resp = await assignRutaItems(rutaId, grupoId, { iniciador_ids: iniciadorIds });
          setItems((prev) => {
            const map = new Map(prev.map((i) => [i.id, i]));
            resp.items.forEach((i) => map.set(i.id, i));
            return Array.from(map.values());
          });
        }
        feedback.success("Iniciadores asignados correctamente.");
        return true;
      } catch (err: any) {
        notifyError(err?.response?.data?.detail || "No se pudo asignar la selección");
        return false;
      }
    },
    [feedback, rutaId, poolIdByIniciadorId, refreshPool, ruta?.fecha]
  );

  const handleDeleteGrupo = useCallback(
    async (grupo: IRutaGrupoMin) => {
      if (!rutaId) return;
      try {
        await deleteRutaGrupo(rutaId, grupo.id);
        setGrupos((prev) => prev.filter((g) => g.id !== grupo.id));
        setItems((prev) => prev.filter((it) => it.ruta_grupo_id !== grupo.id));
        await Promise.all([
          refreshRutaBorrador({ showLoading: false }),
          refreshPool(ruta?.fecha, { silent: true }),
        ]);
      } catch (err: any) {
        notifyError(err?.response?.data?.detail || "No se pudo eliminar el grupo");
      }
    },
    [rutaId, ruta?.fecha, refreshPool, refreshRutaBorrador]
  );

  const handleSincronizarBorradorAsignacion = useCallback(() => {
    void refreshRutaBorrador();
  }, [refreshRutaBorrador]);

  const handleOpenCrearGrupo = useCallback(() => setOpenCrearGrupo(true), []);

  const handleEditarInspectoresAsignacion = useCallback((grupo: IRutaGrupoMin) => {
    setGrupoSeleccionado(grupo);
    setOpenAsignarInspectores(true);
  }, []);

  const handleContinuarMapaFinal = useCallback(() => {
    setFlowMaxUnlocked((m): RutaFlowStep => (m < 3 ? 3 : m));
    setFlowStep(3);
  }, []);

  const handleVolverPlanificacion = useCallback(() => setFlowStep(1), []);

  const canCreateGrupo = useMemo(() => Boolean(rutaId), [rutaId]);
  const assignedIniciadorIds = useMemo(
    () => new Set(itemsActivos.map((i) => i.iniciador_ruta_id)),
    [itemsActivos]
  );
  const iniciadorById = useMemo(
    () => buildIniciadorByIdMap(poolRowsById, itemsActivos),
    [poolRowsById, itemsActivos]
  );

  const continuarMapaFinalState = useMemo(
    () => computeAsignacionContinuarMapaFinal(poolRowsOrdered.length, itemsActivos),
    [poolRowsOrdered.length, itemsActivos]
  );

  const otSinGuardarAvisoRef = useRef<number | null>(null);
  useEffect(() => {
    if (flowStep !== 2) {
      otSinGuardarAvisoRef.current = null;
      return;
    }
    const n = continuarMapaFinalState.itemsSinOtCount;
    if (n <= 0) return;
    if (otSinGuardarAvisoRef.current === n) return;
    otSinGuardarAvisoRef.current = n;
    feedback.warning(`${n} ítem${n === 1 ? "" : "s"} sin OT guardada.`);
  }, [continuarMapaFinalState.itemsSinOtCount, feedback, flowStep]);

  return (
    <Box
      sx={{
        width: "100%",
        minWidth: 0,
        boxSizing: "border-box",
        p: 3,
        display: "flex",
        flexDirection: "column",
        gap: 1.25,
        minHeight: rutaId != null ? "calc(100vh - 200px)" : undefined,
      }}
    >
        {rutaId != null && ruta != null && ruta.estado_ruta === "BORRADOR" && (
          <RutaTrabajoCompactHeader
            ruta={ruta}
            flowStep={flowStep}
            flowMaxUnlocked={flowMaxUnlocked}
            onStepChange={setFlowStep}
            onElegirOtraRuta={resetVistaRutaTrabajo}
            onContinuarAsignacion={() => {
              setFlowMaxUnlocked((m): RutaFlowStep => (m < 2 ? 2 : m));
              setFlowStep(2);
            }}
            onVolverPlanificacion={handleVolverPlanificacion}
            onContinuarMapaFinal={handleContinuarMapaFinal}
            continuarMapaFinalDisabled={!continuarMapaFinalState.puedeContinuar}
            continuarMapaFinalTooltip={continuarMapaFinalState.tooltip}
            onVolverAsignacion={() => setFlowStep(2)}
            onPublicarRuta={flowStep === 3 ? handlePublicarRuta : undefined}
            canPublish={puedeIntentarPublicar}
            publicarTooltip={publicarTooltip}
            publishingRuta={publishingRuta}
          />
        )}

        {rutaId != null && ruta != null && ruta.estado_ruta !== "BORRADOR" && flowStep === 3 && (
          <RutaTrabajoCompactHeader
            ruta={ruta}
            flowStep={3}
            flowMaxUnlocked={3}
            onStepChange={() => {
              /* histórico: sin stepper interactivo */
            }}
            showStepper={false}
            readOnly
            onVolverAlListado={resetVistaRutaTrabajo}
          />
        )}

        {rutaId == null && (
          <RutasEmptyView
            onCrearBorrador={(opts) => {
              setCrearRutaFechaSugerida(opts?.fecha ?? null);
              setOpenCrearRuta(true);
            }}
            onAbrirRuta={(id) => void loadRutaDetail(id)}
          />
        )}

        {flowStep === 1 && rutaId != null && ruta != null && (
          <Box sx={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
            <PlanificacionView
              ruta={ruta}
              rutaId={rutaId}
              grupos={grupos}
              itemsActivos={itemsActivos}
              poolControl={poolControl}
              onError={handlePlanificacionError}
            />
          </Box>
        )}

        {flowStep === 2 && rutaId != null && ruta != null && (
          <RutasPlanificacionView
            ruta={ruta}
            grupos={grupos}
            itemsActivos={itemsActivos}
            itemsCount={itemsActivos.length}
            iniciadoresTabla={iniciadoresTablaAsignacion}
            totalEnPool={poolRowsOrdered.length}
            assignedIniciadorIds={assignedIniciadorIds}
            filters={asignacionFilters}
            detailLoading={detailLoading}
            canCreateGrupo={canCreateGrupo}
            iniciadorById={iniciadorById}
            onChangeFilters={handleAsignacionFiltersChange}
            onSincronizarDetalle={handleSincronizarBorradorAsignacion}
            distritoFilterOptions={distritoFilterOptions}
            onOpenCrearGrupo={handleOpenCrearGrupo}
            onEditarInspectores={handleEditarInspectoresAsignacion}
            onEliminarGrupo={handleDeleteGrupo}
            onMoverItem={handleMoveItem}
            onQuitarItem={handleQuitarItem}
            onGuardarOtItem={handleSaveOt}
            onVolverPlanificacion={handleVolverPlanificacion}
            onAssignIniciadoresToGrupo={assignIniciadoresToGrupo}
            poolIdByIniciadorId={poolIdByIniciadorId}
            onEliminarDelPoolSeleccion={handleEliminarDelPoolSeleccion}
          />
        )}

        {flowStep === 3 && rutaId != null && (
          <RutasMapaOperativoView
            ruta={ruta}
            grupos={grupos}
            itemsActivos={itemsActivos}
            iniciadorById={iniciadorById}
            onPublicarRuta={handlePublicarRuta}
            canPublish={puedeIntentarPublicar}
            publicarTooltip={publicarTooltip}
            publicarBlockers={publicarReadiness.blockers}
            publishingRuta={publishingRuta}
            detailLoading={detailLoading}
            vistaHistoricaReadOnly={vistaHistoricaReadOnly}
            onEditarInspectores={
              vistaHistoricaReadOnly
                ? undefined
                : (grupo) => {
                    setGrupoSeleccionado(grupo);
                    setOpenAsignarInspectores(true);
                  }
            }
            onEliminarGrupo={vistaHistoricaReadOnly ? undefined : handleDeleteGrupo}
            onMoverItem={vistaHistoricaReadOnly ? undefined : handleMoveItem}
            onQuitarItem={vistaHistoricaReadOnly ? undefined : handleQuitarItem}
            onGuardarOtItem={vistaHistoricaReadOnly ? undefined : handleSaveOt}
          />
        )}

        <ModalCrearGrupoRuta open={openCrearGrupo} onClose={() => setOpenCrearGrupo(false)} onSubmit={handleCreateGrupo} disabled={!canCreateGrupo} />
        <ModalCrearRutaTrabajo
          open={openCrearRuta}
          fechaSugeridaAlAbrir={crearRutaFechaSugerida}
          onClose={() => {
            setOpenCrearRuta(false);
            setCrearRutaFechaSugerida(null);
          }}
          onSubmit={handleCreateRuta}
        />

        <ModalAsignarInspectoresGrupo
          open={openAsignarInspectores}
          onClose={handleCloseModalInspectores}
          onSubmit={handleReplaceInspectores}
          grupo={grupoSeleccionado}
          inspectoresCatalogo={inspectoresCatalogo}
          grupos={grupos}
        />

    </Box>
  );
};

export default RutasTrabajo;
