import { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, Box, Paper, Snackbar, Stack, Tab, Tabs, Tooltip, Typography } from "@mui/material";
import { fetchInspectores, type CatalogItem } from "../../api/gridApi";
import { GLASS_COLORS } from "../../styles/GlassStyles";
import {
  assignRutaItems,
  createRutaGrupo,
  createRutaTrabajo,
  deleteRutaGrupo,
  getRutaIniciadoresPendientes,
  getRutaTrabajoDetail,
  publicarRutaTrabajo,
  replaceRutaGrupoInspectores,
  type IRutaGrupoMin,
  type IRutaIniciadorPendienteRow,
  type IRutaItemMin,
  type IRutaTrabajo,
} from "../../api/rutasTrabajoApi";
import type { IniciadoresPendientesFilters } from "./Components/TablaIniciadoresPendientes";
import ModalAsignarInspectoresGrupo from "./Components/ModalAsignarInspectoresGrupo";
import ModalAsignarSeleccionAGrupo from "./Components/ModalAsignarSeleccionAGrupo";
import ModalCrearGrupoRuta from "./Components/ModalCrearGrupoRuta";
import ModalCrearRutaTrabajo from "./Components/ModalCrearRutaTrabajo";
import {
  clearPersistedRutaId,
  persistRutaId,
  useRutaTrabajoBorradorActions,
  useRutasTrabajoSession,
} from "./hooks";
import { rutasInstitutionalHeaderPaperSx } from "./styles/institutionalVisual";
import { RutasEmptyView } from "./views/RutasEmptyView";
import { RutasPlanificacionView } from "./views/RutasPlanificacionView";
import { RutasMapaOperativoView } from "./views/RutasMapaOperativoView";
import { AppButton } from "../../ui";

const rutasAlertSx = {
  fontFamily: '"Tactic Sans", sans-serif',
  border: `1px solid ${GLASS_COLORS.borderMedium}`,
  borderRadius: "10px",
  backgroundColor: GLASS_COLORS.cardBg,
  color: "#FFFFFF",
  "& .MuiAlert-icon": { color: "#FFFFFF" },
  "& .MuiAlert-message": { fontFamily: '"Tactic Sans", sans-serif' },
} as const;

const FILTROS_INICIADORES_VACIOS: IniciadoresPendientesFilters = {
  tipo: "",
  prioridad_categoria: "",
  distrito: "",
  calle_catalogo_id: null,
  turno_sugerido: "",
};

const RutasTrabajo = () => {
  const [tab, setTab] = useState<"TABLA" | "MAPA">("TABLA");
  const [ruta, setRuta] = useState<IRutaTrabajo | null>(null);
  const [grupos, setGrupos] = useState<IRutaGrupoMin[]>([]);
  const [items, setItems] = useState<IRutaItemMin[]>([]);
  const [iniciadores, setIniciadores] = useState<IRutaIniciadorPendienteRow[]>([]);
  const [iniciadoresMeta, setIniciadoresMeta] = useState({ total: 0, page: 1, perPage: 25 });
  const [selectedIniciadorIds, setSelectedIniciadorIds] = useState<number[]>([]);
  const [filters, setFilters] = useState<IniciadoresPendientesFilters>({ ...FILTROS_INICIADORES_VACIOS });
  const [pendientesTablaVisible, setPendientesTablaVisible] = useState(false);
  /** Solo carga/refresco completo del detail de ruta (no PATCH sueltos). */
  const [detailLoading, setDetailLoading] = useState(false);
  const [loadingPendientes, setLoadingPendientes] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const [openCrearGrupo, setOpenCrearGrupo] = useState(false);
  const [openCrearRuta, setOpenCrearRuta] = useState(false);
  const [openAsignarInspectores, setOpenAsignarInspectores] = useState(false);
  const [openAsignarGrupo, setOpenAsignarGrupo] = useState(false);
  const [grupoSeleccionado, setGrupoSeleccionado] = useState<IRutaGrupoMin | null>(null);
  const [inspectoresCatalogo, setInspectoresCatalogo] = useState<CatalogItem[]>([]);
  const [publishingRuta, setPublishingRuta] = useState(false);

  const rutaId = ruta?.id ?? null;
  /** Borrador con detalle cargado: habilita la acción (el botón se deshabilita además mientras `publishingRuta`). */
  const puedeIntentarPublicar = Boolean(rutaId && ruta?.estado_ruta === "BORRADOR" && !detailLoading);

  const loadRutaDetail = useCallback(async (targetRutaId: number, opts?: { showLoading?: boolean }) => {
    const showLoading = opts?.showLoading !== false;
    if (showLoading) setDetailLoading(true);
    setError(null);
    try {
      const detail = await getRutaTrabajoDetail(targetRutaId);
      setRuta(detail.ruta);
      setGrupos(detail.grupos);
      const reconstructedItems = (detail.grupos ?? []).flatMap((g) => g.items ?? []);
      setItems(reconstructedItems);
      setPendientesTablaVisible(false);
      setFilters({ ...FILTROS_INICIADORES_VACIOS });
      setIniciadores([]);
      setIniciadoresMeta((prev) => ({ ...prev, total: 0, page: 1 }));
      persistRutaId(targetRutaId);
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
      setSuccessMessage(`Ruta ${resp.item.numero} creada en BORRADOR.`);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "No se pudo crear la ruta");
    }
  };

  const loadPendientes = useCallback(async () => {
    if (!rutaId || !pendientesTablaVisible) return;
    setLoadingPendientes(true);
    try {
      const resp = await getRutaIniciadoresPendientes(rutaId, {
        tipo: filters.tipo || undefined,
        prioridad_categoria: filters.prioridad_categoria
          ? (filters.prioridad_categoria as "BAJA" | "MEDIA" | "ALTA")
          : undefined,
        distrito: filters.distrito ? Number(filters.distrito) : undefined,
        calle_catalogo_id: filters.calle_catalogo_id ?? undefined,
        turno_sugerido: (filters.turno_sugerido || undefined) as "MANIANA" | "TARDE" | undefined,
        page: iniciadoresMeta.page,
        per_page: iniciadoresMeta.perPage,
      });
      setIniciadores(resp.items);
      setIniciadoresMeta((prev) => ({ ...prev, total: resp.meta.total }));
    } catch (err: any) {
      setError(err?.response?.data?.detail || "No se pudieron cargar los iniciadores pendientes");
    } finally {
      setLoadingPendientes(false);
    }
  }, [filters, iniciadoresMeta.page, iniciadoresMeta.perPage, pendientesTablaVisible, rutaId]);

  const handleFiltrosPendientesChange = useCallback((next: IniciadoresPendientesFilters) => {
    setFilters(next);
    setPendientesTablaVisible(true);
    setSelectedIniciadorIds([]);
    setIniciadoresMeta((prev) => ({ ...prev, page: 1 }));
  }, []);

  const handleRefrescarPendientes = useCallback(() => {
    setPendientesTablaVisible(false);
    setFilters({ ...FILTROS_INICIADORES_VACIOS });
    setIniciadores([]);
    setIniciadoresMeta((prev) => ({ ...prev, total: 0, page: 1 }));
    setSelectedIniciadorIds([]);
  }, []);

  /** Limpia sesión y estado local: vuelve al flujo de “crear ruta” (p. ej. tras publicar). */
  const resetVistaRutaTrabajo = useCallback(() => {
    clearPersistedRutaId();
    setRuta(null);
    setGrupos([]);
    setItems([]);
    setIniciadores([]);
    setIniciadoresMeta((prev) => ({ ...prev, total: 0, page: 1 }));
    setFilters({ ...FILTROS_INICIADORES_VACIOS });
    setPendientesTablaVisible(false);
    setSelectedIniciadorIds([]);
    setOpenCrearGrupo(false);
    setOpenAsignarInspectores(false);
    setOpenAsignarGrupo(false);
    setGrupoSeleccionado(null);
    setTab("TABLA");
  }, []);

  const handlePublicarRuta = useCallback(async () => {
    if (!rutaId || ruta?.estado_ruta !== "BORRADOR" || publishingRuta) return;
    setPublishingRuta(true);
    setError(null);
    setSuccessMessage(null);
    try {
      await publicarRutaTrabajo(rutaId);
      resetVistaRutaTrabajo();
      setSuccessMessage(
        "Ruta publicada correctamente. Los trabajos pasaron a ejecución y podés registrarlos en Completar trabajo."
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
        const resp = await fetchInspectores();
        setInspectoresCatalogo(resp.items ?? []);
      } catch {
        setInspectoresCatalogo([]);
      }
    };
    void loadInspectores();
  }, []);

  useEffect(() => {
    void loadPendientes();
  }, [loadPendientes]);

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

  const handleReplaceInspectores = async (inspectorIds: number[]) => {
    if (!rutaId || !grupoSeleccionado) return;
    const grupoActual = grupos.find((g) => g.id === grupoSeleccionado.id);
    if (!grupoActual) {
      setError("El grupo seleccionado ya no existe en el borrador actual.");
      await loadRutaDetail(rutaId);
      return;
    }
    setError(null);
    setSuccessMessage(null);
    try {
      const resp = await replaceRutaGrupoInspectores(rutaId, grupoSeleccionado.id, {
        inspector_ids: inspectorIds,
      });
      setGrupos((prev) =>
        prev.map((g) => (g.id === grupoSeleccionado.id ? { ...g, inspectores: resp.items } : g))
      );
      setOpenAsignarInspectores(false);
      setGrupoSeleccionado(null);
      setSuccessMessage("Inspectores del grupo actualizados.");
    } catch (err: any) {
      setError(err?.response?.data?.detail || "No se pudieron actualizar inspectores");
    }
  };

  const handleAssignSelected = async (grupoId: number) => {
    if (!rutaId || selectedIniciadorIds.length === 0) return;
    setError(null);
    setSuccessMessage(null);
    try {
      const resp = await assignRutaItems(rutaId, grupoId, { iniciador_ids: selectedIniciadorIds });
      setItems((prev) => {
        const map = new Map(prev.map((i) => [i.id, i]));
        resp.items.forEach((i) => map.set(i.id, i));
        return Array.from(map.values());
      });
      setSelectedIniciadorIds([]);
      setOpenAsignarGrupo(false);
      await loadPendientes();
      setSuccessMessage("Iniciadores asignados correctamente.");
    } catch (err: any) {
      setError(err?.response?.data?.detail || "No se pudo asignar la selección");
    }
  };

  const handleDeleteGrupo = async (grupo: IRutaGrupoMin) => {
    if (!rutaId) return;
    try {
      await deleteRutaGrupo(rutaId, grupo.id);
      setGrupos((prev) => prev.filter((g) => g.id !== grupo.id));
      setItems((prev) => prev.filter((it) => it.ruta_grupo_id !== grupo.id));
      await loadPendientes();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "No se pudo eliminar el grupo");
    }
  };

  const canCreateGrupo = useMemo(() => Boolean(rutaId), [rutaId]);
  const itemsActivos = useMemo(() => items.filter((i) => !i.deleted_at), [items]);
  const iniciadorById = useMemo(
    () =>
      iniciadores.reduce<Record<number, IRutaIniciadorPendienteRow>>((acc, row) => {
        acc[row.id] = row;
        return acc;
      }, {}),
    [iniciadores]
  );

  return (
    <Box sx={{ p: 3, display: "flex", flexDirection: "column", gap: 2.2 }}>
        <Paper elevation={0} sx={rutasInstitutionalHeaderPaperSx}>
          <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between" flexWrap="wrap">
            <Tabs value={tab} onChange={(_, value) => setTab(value)}>
              <Tab label="TABLA" value="TABLA" />
              <Tab label="MAPA" value="MAPA" />
            </Tabs>
            <Stack direction="row" spacing={1.2} flexWrap="wrap" alignItems="center">
              {rutaId != null && ruta?.estado_ruta === "BORRADOR" && (
                <Tooltip
                  title={
                    publishingRuta
                      ? "Publicando…"
                      : "Valida inspectores por grupo, ítems con OT y genera actuaciones mínimas."
                  }
                >
                  <span>
                    <AppButton
                      dsVariant="primary"
                      dsSize="sm"
                      disabled={!puedeIntentarPublicar || publishingRuta}
                      onClick={() => void handlePublicarRuta()}
                    >
                      {publishingRuta ? "Publicando…" : "Publicar ruta"}
                    </AppButton>
                  </span>
                </Tooltip>
              )}
            </Stack>
          </Stack>
        </Paper>

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

        {tab === "TABLA" && rutaId == null && (
          <RutasEmptyView onCrearBorrador={() => setOpenCrearRuta(true)} />
        )}

        {tab === "TABLA" && rutaId != null && ruta != null && (
          <RutasPlanificacionView
            ruta={ruta}
            grupos={grupos}
            itemsActivos={itemsActivos}
            itemsCount={itemsActivos.length}
            iniciadores={iniciadores}
            iniciadoresMeta={iniciadoresMeta}
            selectedIniciadorIds={selectedIniciadorIds}
            filters={filters}
            detailLoading={detailLoading}
            loadingPendientes={loadingPendientes}
            canCreateGrupo={canCreateGrupo}
            iniciadorById={iniciadorById}
            pendientesTablaVisible={pendientesTablaVisible}
            onChangeFilters={handleFiltrosPendientesChange}
            onRefrescarPendientes={handleRefrescarPendientes}
            onPageChange={(nextPage) => setIniciadoresMeta((prev) => ({ ...prev, page: nextPage }))}
            onPerPageChange={(nextPerPage) =>
              setIniciadoresMeta((prev) => ({ ...prev, perPage: nextPerPage, page: 1 }))
            }
            onSelectionChange={setSelectedIniciadorIds}
            onAssignSelected={() => setOpenAsignarGrupo(true)}
            onOpenCrearGrupo={() => setOpenCrearGrupo(true)}
            onEditarInspectores={(grupo) => {
              setGrupoSeleccionado(grupo);
              setOpenAsignarInspectores(true);
            }}
            onEliminarGrupo={handleDeleteGrupo}
            onMoverItem={handleMoveItem}
            onQuitarItem={handleDeleteItem}
            onGuardarOtItem={handleSaveOt}
          />
        )}

        {tab === "MAPA" && (
          <RutasMapaOperativoView
            ruta={ruta}
            grupos={grupos}
            itemsActivos={itemsActivos}
            iniciadorById={iniciadorById}
            onVolverPlanificacion={() => setTab("TABLA")}
            onPublicarRuta={handlePublicarRuta}
            canPublish={puedeIntentarPublicar}
            publishingRuta={publishingRuta}
            detailLoading={detailLoading}
            onEditarInspectores={(grupo) => {
              setGrupoSeleccionado(grupo);
              setOpenAsignarInspectores(true);
            }}
            onEliminarGrupo={handleDeleteGrupo}
            onMoverItem={handleMoveItem}
            onQuitarItem={handleDeleteItem}
            onGuardarOtItem={handleSaveOt}
          />
        )}

        <ModalCrearGrupoRuta open={openCrearGrupo} onClose={() => setOpenCrearGrupo(false)} onSubmit={handleCreateGrupo} disabled={!canCreateGrupo} />
        <ModalCrearRutaTrabajo open={openCrearRuta} onClose={() => setOpenCrearRuta(false)} onSubmit={handleCreateRuta} />

        <ModalAsignarInspectoresGrupo
          open={openAsignarInspectores}
          onClose={() => {
            setOpenAsignarInspectores(false);
            setGrupoSeleccionado(null);
          }}
          onSubmit={handleReplaceInspectores}
          grupo={grupoSeleccionado}
          inspectoresCatalogo={inspectoresCatalogo}
          grupos={grupos}
        />

        <ModalAsignarSeleccionAGrupo
          open={openAsignarGrupo}
          onClose={() => setOpenAsignarGrupo(false)}
          grupos={grupos}
          selectedCount={selectedIniciadorIds.length}
          onConfirm={handleAssignSelected}
        />

    </Box>
  );
};

export default RutasTrabajo;
