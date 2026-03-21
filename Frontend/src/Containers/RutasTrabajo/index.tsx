import { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, Box, Button, Paper, Stack, Tab, Tabs, Typography } from "@mui/material";
import { fetchInspectores, type CatalogItem } from "../../api/gridApi";
import { GLASS_COLORS } from "../../styles/GlassStyles";
import {
  assignRutaItems,
  createRutaGrupo,
  createRutaTrabajo,
  deleteRutaGrupo,
  deleteRutaItem,
  getRutaIniciadoresPendientes,
  getRutaTrabajoDetail,
  moveRutaItem,
  patchRutaItemOrdenTrabajo,
  replaceRutaGrupoInspectores,
  type IRutaGrupoMin,
  type IRutaIniciadorPendienteRow,
  type IRutaItemMin,
  type IRutaTrabajo,
} from "../../api/rutasTrabajoApi";
import ModalAsignarInspectoresGrupo from "./Components/ModalAsignarInspectoresGrupo";
import ModalAsignarSeleccionAGrupo from "./Components/ModalAsignarSeleccionAGrupo";
import ModalCrearGrupoRuta from "./Components/ModalCrearGrupoRuta";
import ModalCrearRutaTrabajo from "./Components/ModalCrearRutaTrabajo";
import { clearPersistedRutaId, persistRutaId, useRutasTrabajoSession } from "./hooks";
import { rutasInstitutionalHeaderPaperSx } from "./styles/institutionalVisual";
import { RutasEmptyView } from "./views/RutasEmptyView";
import { RutasPlanificacionView } from "./views/RutasPlanificacionView";
import { RutasMapaOperativoView } from "./views/RutasMapaOperativoView";

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
  const [tab, setTab] = useState<"TABLA" | "MAPA">("TABLA");
  const [ruta, setRuta] = useState<IRutaTrabajo | null>(null);
  const [grupos, setGrupos] = useState<IRutaGrupoMin[]>([]);
  const [items, setItems] = useState<IRutaItemMin[]>([]);
  const [iniciadores, setIniciadores] = useState<IRutaIniciadorPendienteRow[]>([]);
  const [iniciadoresMeta, setIniciadoresMeta] = useState({ total: 0, page: 1, perPage: 25 });
  const [selectedIniciadorIds, setSelectedIniciadorIds] = useState<number[]>([]);
  const [filters, setFilters] = useState({
    q: "",
    tipo: "",
    prioridad: "",
    distrito: "",
    turno_sugerido: "",
  });
  const [loading, setLoading] = useState(false);
  const [loadingPendientes, setLoadingPendientes] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const [openCrearGrupo, setOpenCrearGrupo] = useState(false);
  const [openCrearRuta, setOpenCrearRuta] = useState(false);
  const [openAsignarInspectores, setOpenAsignarInspectores] = useState(false);
  const [openAsignarGrupo, setOpenAsignarGrupo] = useState(false);
  const [grupoSeleccionado, setGrupoSeleccionado] = useState<IRutaGrupoMin | null>(null);
  const [inspectoresCatalogo, setInspectoresCatalogo] = useState<CatalogItem[]>([]);

  const rutaId = ruta?.id ?? null;

  const loadRutaDetail = useCallback(async (targetRutaId: number) => {
    setLoading(true);
    setError(null);
    try {
      const detail = await getRutaTrabajoDetail(targetRutaId);
      setRuta(detail.ruta);
      setGrupos(detail.grupos);
      const reconstructedItems = (detail.grupos ?? []).flatMap((g) => g.items ?? []);
      setItems(reconstructedItems);
      persistRutaId(targetRutaId);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "No se pudo cargar el detalle de la ruta");
      setRuta(null);
      setGrupos([]);
      setItems([]);
      clearPersistedRutaId();
    } finally {
      setLoading(false);
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
    if (!rutaId) return;
    setLoadingPendientes(true);
    try {
      const resp = await getRutaIniciadoresPendientes(rutaId, {
        q: filters.q || undefined,
        tipo: filters.tipo || undefined,
        prioridad: filters.prioridad ? Number(filters.prioridad) : undefined,
        distrito: filters.distrito ? Number(filters.distrito) : undefined,
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
  }, [filters, iniciadoresMeta.page, iniciadoresMeta.perPage, rutaId]);

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

  const handleCreateGrupo = async () => {
    if (!rutaId) return;
    setError(null);
    setSuccessMessage(null);
    try {
      await createRutaGrupo(rutaId, {});
      await loadRutaDetail(rutaId);
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
      await replaceRutaGrupoInspectores(rutaId, grupoSeleccionado.id, {
        inspector_ids: inspectorIds,
      });
      await loadRutaDetail(rutaId);
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
      await loadRutaDetail(rutaId);
      setSuccessMessage("Iniciadores asignados correctamente.");
    } catch (err: any) {
      setError(err?.response?.data?.detail || "No se pudo asignar la selección");
    }
  };

  const handleMoveItem = async (item: IRutaItemMin, targetGrupoId: number) => {
    if (!rutaId) return;
    try {
      const resp = await moveRutaItem(rutaId, item.id, { target_grupo_id: targetGrupoId });
      setItems((prev) => prev.map((it) => (it.id === item.id ? resp.item : it)));
      await loadRutaDetail(rutaId);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "No se pudo mover el item");
    }
  };

  const handleDeleteItem = async (item: IRutaItemMin) => {
    if (!rutaId) return;
    try {
      await deleteRutaItem(rutaId, item.id);
      setItems((prev) => prev.filter((it) => it.id !== item.id));
      await loadPendientes();
      await loadRutaDetail(rutaId);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "No se pudo quitar el item");
    }
  };

  const handleDeleteGrupo = async (grupo: IRutaGrupoMin) => {
    if (!rutaId) return;
    try {
      await deleteRutaGrupo(rutaId, grupo.id);
      setGrupos((prev) => prev.filter((g) => g.id !== grupo.id));
      setItems((prev) => prev.filter((it) => it.ruta_grupo_id !== grupo.id));
      await loadPendientes();
      await loadRutaDetail(rutaId);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "No se pudo eliminar el grupo");
    }
  };

  const handleSaveOt = async (item: IRutaItemMin, numeroOt: string) => {
    if (!rutaId) return;
    try {
      const resp = await patchRutaItemOrdenTrabajo(rutaId, item.id, { numero_orden_trabajo: numeroOt });
      setItems((prev) => prev.map((it) => (it.id === resp.item.id ? resp.item : it)));
      await loadRutaDetail(rutaId);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "No se pudo guardar la OT");
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
            <Stack direction="row" spacing={1.2} flexWrap="wrap">
              <Button variant="contained">Continuar</Button>
            </Stack>
          </Stack>
        </Paper>

        {error && (
          <Alert severity="error" sx={rutasAlertSx}>
            {error}
          </Alert>
        )}
        {successMessage && (
          <Alert severity="success" sx={rutasAlertSx}>
            {successMessage}
          </Alert>
        )}

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
            loading={loading}
            loadingPendientes={loadingPendientes}
            canCreateGrupo={canCreateGrupo}
            iniciadorById={iniciadorById}
            onChangeFilters={(next) => {
              setFilters(next);
              setIniciadoresMeta((prev) => ({ ...prev, page: 1 }));
            }}
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
            canPublish={false}
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
