import { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, Box, Paper, Snackbar } from "@mui/material";
import type { CatalogItem } from "../../api/gridApi";
import { fetchInspectoresCatalogItemsCached } from "../../utils/inspectoresCatalogCache";
import { GLASS_COLORS, moduleSlicesPanelPaperSx } from "../../styles/GlassStyles";
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
import { RutasTrabajoFlowStepper, type RutaFlowStep } from "./Components/RutasTrabajoFlowStepper";
import { RutasEmptyView } from "./views/RutasEmptyView";
import { RutasPlanificacionView } from "./views/RutasPlanificacionView";
import { RutasMapaOperativoView } from "./views/RutasMapaOperativoView";
import { PlanificacionView } from "./planificacion/PlanificacionView";
import type { PlanificacionPoolControl } from "./planificacion/hooks/usePlanificacionController";
import {
  buildDistritoOptionsFromPool,
  filterAsignacionPoolRows,
} from "./utils/filterAsignacionPool";

const rutasAlertSx = {
  fontFamily: '"Tactic Sans", sans-serif',
  border: `1px solid ${GLASS_COLORS.borderMedium}`,
  borderRadius: "10px",
  backgroundColor: GLASS_COLORS.cardBg,
  color: "#FFFFFF",
  "& .MuiAlert-icon": { color: "#FFFFFF" },
  "& .MuiAlert-message": { fontFamily: '"Tactic Sans", sans-serif' },
} as const;

const RutasTrabajo = () => {
  /** Flujo secuencial: 1 Planificación → 2 Asignación → 3 Mapa final (desbloqueo solo por CTA). */
  const [flowStep, setFlowStep] = useState<RutaFlowStep>(1);
  const [flowMaxUnlocked, setFlowMaxUnlocked] = useState<RutaFlowStep>(1);
  const [ruta, setRuta] = useState<IRutaTrabajo | null>(null);
  const [grupos, setGrupos] = useState<IRutaGrupoMin[]>([]);
  const [items, setItems] = useState<IRutaItemMin[]>([]);
  /** Pool del día compartido Planificación → Asignación (solo frontend hasta asignar a grupos). */
  const [poolIniciadorIds, setPoolIniciadorIds] = useState<number[]>([]);
  const [poolRowsById, setPoolRowsById] = useState<Record<number, IRutaIniciadorPendienteRow>>({});
  const [asignacionFilters, setAsignacionFilters] = useState<AsignacionPoolFilters>({
    ...ASIGNACION_POOL_FILTROS_VACIOS,
  });
  /** Solo carga/refresco completo del detail de ruta (no PATCH sueltos). */
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const [openCrearGrupo, setOpenCrearGrupo] = useState(false);
  const [openCrearRuta, setOpenCrearRuta] = useState(false);
  const [crearRutaFechaSugerida, setCrearRutaFechaSugerida] = useState<string | null>(null);
  const [openAsignarInspectores, setOpenAsignarInspectores] = useState(false);
  const [grupoSeleccionado, setGrupoSeleccionado] = useState<IRutaGrupoMin | null>(null);
  const [inspectoresCatalogo, setInspectoresCatalogo] = useState<CatalogItem[]>([]);
  const [publishingRuta, setPublishingRuta] = useState(false);
  const rutaId = ruta?.id ?? null;
  /** Borrador con detalle cargado: habilita la acción (el botón se deshabilita además mientras `publishingRuta`). */
  const puedeIntentarPublicar = Boolean(rutaId && ruta?.estado_ruta === "BORRADOR" && !detailLoading);
  /** Ruta publicada u otro estado no borrador: mapa en preview histórica solo lectura. */
  const vistaHistoricaReadOnly = Boolean(ruta && ruta.estado_ruta !== "BORRADOR");

  const loadRutaDetail = useCallback(async (targetRutaId: number, opts?: { showLoading?: boolean }) => {
    const showLoading = opts?.showLoading !== false;
    if (showLoading) setDetailLoading(true);
    setError(null);
    try {
      const detail = await getRutaTrabajoDetail(targetRutaId);
      setRuta(detail.ruta);
      setGrupos(detail.grupos);
      // Por grupo, el API devuelve ítems ordenados por id ascendente (sin campo de secuencia de visita en modelo).
      const reconstructedItems = (detail.grupos ?? []).flatMap((g) => g.items ?? []);
      setItems(reconstructedItems);
      setPoolIniciadorIds([]);
      setPoolRowsById({});
      setAsignacionFilters({ ...ASIGNACION_POOL_FILTROS_VACIOS });
      persistRutaId(targetRutaId);
      const esBorrador = detail.ruta.estado_ruta === "BORRADOR";
      // Planificación y APIs asociadas exigen BORRADOR; rutas publicadas se abren en mapa (base para preview histórica).
      setFlowStep(esBorrador ? 1 : 3);
      setFlowMaxUnlocked(esBorrador ? 1 : 3);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "No se pudo cargar el detalle de la ruta");
      setRuta(null);
      setGrupos([]);
      setItems([]);
      clearPersistedRutaId();
    } finally {
      if (showLoading) setDetailLoading(false);
    }
  }, []);

  /** Actualiza grupos e ítems desde el servidor sin resetear el flujo ni el pool (Asignación). */
  const refreshRutaBorrador = useCallback(async () => {
    if (!rutaId) return;
    setDetailLoading(true);
    setError(null);
    try {
      const detail = await getRutaTrabajoDetail(rutaId);
      setRuta(detail.ruta);
      setGrupos(detail.grupos);
      // Mismo orden por grupo que en loadRutaDetail (ítems por id ascendente en presenter).
      const reconstructedItems = (detail.grupos ?? []).flatMap((g) => g.items ?? []);
      setItems(reconstructedItems);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "No se pudo sincronizar el borrador");
    } finally {
      setDetailLoading(false);
    }
  }, [rutaId]);

  const agregarAlPool = useCallback((row: IRutaIniciadorPendienteRow) => {
    setPoolIniciadorIds((prev) => (prev.includes(row.id) ? prev : [...prev, row.id]));
    setPoolRowsById((prev) => ({ ...prev, [row.id]: row }));
  }, []);

  const quitarDelPool = useCallback((id: number) => {
    setPoolIniciadorIds((prev) => prev.filter((x) => x !== id));
    setPoolRowsById((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
  }, []);

  const poolControl: PlanificacionPoolControl = useMemo(
    () => ({
      poolIniciadorIds,
      poolRowsById,
      agregarAlPool,
      quitarDelPool,
    }),
    [poolIniciadorIds, poolRowsById, agregarAlPool, quitarDelPool]
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
    setError(null);
    setSuccessMessage(null);
    try {
      const resp = await createRutaTrabajo({
        fecha: payload.fecha,
        turno: payload.turno,
        observaciones: payload.observaciones || null,
      });
      await loadRutaDetail(resp.item.id);
      setOpenCrearRuta(false);
      setCrearRutaFechaSugerida(null);
      setSuccessMessage(`Ruta ${resp.item.numero} creada en BORRADOR.`);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "No se pudo crear la ruta");
    }
  };

  /** No-op: la grilla de Asignación usa solo el pool local; se mantiene la firma para mutaciones de borrador. */
  const loadPendientes = useCallback(async () => {}, []);

  const handleAsignacionFiltersChange = useCallback((next: AsignacionPoolFilters) => {
    setAsignacionFilters(next);
  }, []);

  /** Debe ser estable: `usePlanificacionController` depende de `onError` en load* y efectos M1–M4. */
  const handlePlanificacionError = useCallback((msg: string) => {
    setError(msg);
  }, []);

  /** Limpia sesión y estado local: vuelve a la pantalla de elegir borrador / crear ruta (también tras publicar). */
  const resetVistaRutaTrabajo = useCallback(() => {
    clearPersistedRutaId();
    setRuta(null);
    setGrupos([]);
    setItems([]);
    setPoolIniciadorIds([]);
    setPoolRowsById({});
    setAsignacionFilters({ ...ASIGNACION_POOL_FILTROS_VACIOS });
    setOpenCrearGrupo(false);
    setOpenAsignarInspectores(false);
    setGrupoSeleccionado(null);
    setFlowStep(1);
    setFlowMaxUnlocked(1);
    setError(null);
    setSuccessMessage(null);
  }, []);

  const handlePublicarRuta = useCallback(async () => {
    if (!rutaId || ruta?.estado_ruta !== "BORRADOR" || publishingRuta) return;

    setPublishingRuta(true);
    setError(null);
    setSuccessMessage(null);
    try {
      await publicarRutaTrabajo(rutaId);
      await loadRutaDetail(rutaId, { showLoading: true });
      setSuccessMessage(
        "Ruta publicada. Usá «Descargar resumen (PDF)» y «Descargar órdenes de salida (PDF)» en esta pantalla para la documentación oficial."
      );
    } catch (err: unknown) {
      const ax = err as { response?: { status?: number; data?: { detail?: unknown } } };
      const status = ax?.response?.status;
      const detail = ax?.response?.data?.detail;
      if (typeof detail === "string") {
        setError(detail);
      } else if (status === 409) {
        setError(
          "No se cumplen las condiciones para publicar. Revisá inspectores por grupo, ítems activos y OT en cada ítem."
        );
      } else {
        setError("No se pudo publicar la ruta. Intentá de nuevo más tarde.");
      }
    } finally {
      setPublishingRuta(false);
    }
  }, [publishingRuta, resetVistaRutaTrabajo, ruta?.estado_ruta, rutaId]);

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

  const { moveItem: handleMoveItem, deleteItem: handleDeleteItem, saveOtItem: handleSaveOt } =
    useRutaTrabajoBorradorActions({
      rutaId,
      setItems,
      setError,
      loadPendientes,
    });

  const handleCreateGrupo = async () => {
    if (!rutaId) return;
    setError(null);
    setSuccessMessage(null);
    try {
      const resp = await createRutaGrupo(rutaId, {});
      setGrupos((prev) => [...prev, { ...resp.item, items: resp.item.items ?? [] }]);
      setOpenCrearGrupo(false);
      setSuccessMessage("Grupo creado correctamente.");
    } catch (err: any) {
      setError(err?.response?.data?.detail || "No se pudo crear el grupo");
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
        setError("El grupo seleccionado ya no existe en el borrador actual.");
        await loadRutaDetail(rutaId);
        return;
      }
      const grupoId = grupoSeleccionado.id;
      setError(null);
      setSuccessMessage(null);
      try {
        const resp = await replaceRutaGrupoInspectores(rutaId, grupoId, {
          inspector_ids: inspectorIds,
        });
        setGrupos((prev) => prev.map((g) => (g.id === grupoId ? { ...g, inspectores: resp.items } : g)));
        setOpenAsignarInspectores(false);
        setGrupoSeleccionado(null);
        setSuccessMessage("Inspectores del grupo actualizados.");
      } catch (err: any) {
        setError(err?.response?.data?.detail || "No se pudieron actualizar inspectores");
      }
    },
    [grupoSeleccionado, grupos, loadRutaDetail, rutaId]
  );

  const assignIniciadoresToGrupo = useCallback(
    async (grupoId: number, iniciadorIds: number[]): Promise<boolean> => {
      if (!rutaId || iniciadorIds.length === 0) return false;
      setError(null);
      setSuccessMessage(null);
      try {
        const resp = await assignRutaItems(rutaId, grupoId, { iniciador_ids: iniciadorIds });
        setItems((prev) => {
          const map = new Map(prev.map((i) => [i.id, i]));
          resp.items.forEach((i) => map.set(i.id, i));
          return Array.from(map.values());
        });
        setSuccessMessage("Iniciadores asignados correctamente.");
        return true;
      } catch (err: any) {
        setError(err?.response?.data?.detail || "No se pudo asignar la selección");
        return false;
      }
    },
    [rutaId]
  );

  const handleDeleteGrupo = useCallback(
    async (grupo: IRutaGrupoMin) => {
      if (!rutaId) return;
      try {
        await deleteRutaGrupo(rutaId, grupo.id);
        setGrupos((prev) => prev.filter((g) => g.id !== grupo.id));
        setItems((prev) => prev.filter((it) => it.ruta_grupo_id !== grupo.id));
      } catch (err: any) {
        setError(err?.response?.data?.detail || "No se pudo eliminar el grupo");
      }
    },
    [rutaId]
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
  const itemsActivos = useMemo(() => items.filter((i) => !i.deleted_at), [items]);
  const assignedIniciadorIds = useMemo(
    () => new Set(itemsActivos.map((i) => i.iniciador_ruta_id)),
    [itemsActivos]
  );
  const iniciadorById = useMemo(() => ({ ...poolRowsById }), [poolRowsById]);

  return (
    <Box
      sx={{
        width: "100%",
        minWidth: 0,
        boxSizing: "border-box",
        p: 3,
        display: "flex",
        flexDirection: "column",
        gap: 2.2,
      }}
    >
        {rutaId != null && ruta?.estado_ruta === "BORRADOR" && (
          <Paper
            elevation={0}
            sx={{
              ...moduleSlicesPanelPaperSx,
              width: "100%",
              minWidth: 0,
              maxWidth: "100%",
              boxSizing: "border-box",
            }}
          >
            <RutasTrabajoFlowStepper
              flowStep={flowStep}
              flowMaxUnlocked={flowMaxUnlocked}
              onStepChange={setFlowStep}
            />
          </Paper>
        )}

        {error && (
          <Alert severity="error" sx={rutasAlertSx}>
            {error}
          </Alert>
        )}
        <Snackbar
          open={Boolean(successMessage)}
          autoHideDuration={5000}
          onClose={(_, reason) => {
            if (reason === "clickaway") return;
            setSuccessMessage(null);
          }}
          anchorOrigin={{ vertical: "top", horizontal: "center" }}
          sx={{ top: { sm: 88 } }}
        >
          <Alert
            onClose={() => setSuccessMessage(null)}
            severity="success"
            variant="filled"
            sx={{ ...rutasAlertSx, width: "100%" }}
          >
            {successMessage}
          </Alert>
        </Snackbar>

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
          <PlanificacionView
            ruta={ruta}
            rutaId={rutaId}
            poolControl={poolControl}
            onError={handlePlanificacionError}
            onVolverAElegirRuta={resetVistaRutaTrabajo}
            onContinuarAsignacion={() => {
              setFlowMaxUnlocked((m): RutaFlowStep => (m < 2 ? 2 : m));
              setFlowStep(2);
            }}
          />
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
            onQuitarItem={handleDeleteItem}
            onGuardarOtItem={handleSaveOt}
            onContinuarMapaFinal={handleContinuarMapaFinal}
            onVolverPlanificacion={handleVolverPlanificacion}
            onAssignIniciadoresToGrupo={assignIniciadoresToGrupo}
          />
        )}

        {flowStep === 3 && rutaId != null && (
          <RutasMapaOperativoView
            ruta={ruta}
            grupos={grupos}
            itemsActivos={itemsActivos}
            iniciadorById={iniciadorById}
            onVolverAsignacion={() => setFlowStep(2)}
            onPublicarRuta={handlePublicarRuta}
            canPublish={puedeIntentarPublicar}
            publishingRuta={publishingRuta}
            detailLoading={detailLoading}
            vistaHistoricaReadOnly={vistaHistoricaReadOnly}
            onVolverAlListado={resetVistaRutaTrabajo}
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
            onQuitarItem={vistaHistoricaReadOnly ? undefined : handleDeleteItem}
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
