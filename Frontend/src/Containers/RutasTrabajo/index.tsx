import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Grid,
  Paper,
  Stack,
  Tab,
  Tabs,
  ThemeProvider,
  Typography,
} from "@mui/material";

import { darkTheme } from "../../configs/theme";
import { fetchInspectores, type CatalogItem } from "../../api/gridApi";
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
import ModalEditarOrdenTrabajoItem from "./Components/ModalEditarOrdenTrabajoItem";
import PanelGruposRuta from "./Components/PanelGruposRuta";
import ResumenRutaTrabajo from "./Components/ResumenRutaTrabajo";
import TablaIniciadoresPendientes from "./Components/TablaIniciadoresPendientes";

const RutasTrabajo = () => {
  const LAST_RUTA_STORAGE_KEY = "rutas_trabajo_last_ruta_id";
  const [tab, setTab] = useState<"TABLA" | "BOARD" | "MAPA">("TABLA");
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

  const [openCrearRuta, setOpenCrearRuta] = useState(false);
  const [openCrearGrupo, setOpenCrearGrupo] = useState(false);
  const [openAsignarInspectores, setOpenAsignarInspectores] = useState(false);
  const [openAsignarGrupo, setOpenAsignarGrupo] = useState(false);
  const [openEditarOt, setOpenEditarOt] = useState(false);
  const [grupoSeleccionado, setGrupoSeleccionado] = useState<IRutaGrupoMin | null>(null);
  const [itemSeleccionado, setItemSeleccionado] = useState<IRutaItemMin | null>(null);
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
      window.localStorage.setItem(LAST_RUTA_STORAGE_KEY, String(targetRutaId));
    } catch (err: any) {
      setError(err?.response?.data?.detail || "No se pudo cargar el detalle de la ruta");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const saved = window.localStorage.getItem(LAST_RUTA_STORAGE_KEY);
    const rutaIdSaved = Number(saved);
    if (!saved || !Number.isFinite(rutaIdSaved) || rutaIdSaved <= 0) return;
    void loadRutaDetail(rutaIdSaved);
  }, [loadRutaDetail]);

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

  const handleSaveOt = async (numeroOt: string) => {
    if (!rutaId || !itemSeleccionado) return;
    try {
      const resp = await patchRutaItemOrdenTrabajo(rutaId, itemSeleccionado.id, { numero_orden_trabajo: numeroOt });
      setItems((prev) => prev.map((it) => (it.id === resp.item.id ? resp.item : it)));
      await loadRutaDetail(rutaId);
      setOpenEditarOt(false);
      setItemSeleccionado(null);
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
    <ThemeProvider theme={darkTheme}>
      <Box sx={{ p: 3, display: "flex", flexDirection: "column", gap: 2.2 }}>
        <Paper
          sx={{
            p: 2.2,
            border: "1px solid rgba(104, 129, 171, 0.35)",
            background:
              "linear-gradient(180deg, rgba(18,27,47,0.94) 0%, rgba(10,16,30,0.99) 100%)",
          }}
        >
          <Stack direction="row" justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={2}>
            <Box>
              <Typography variant="h4" sx={{ fontWeight: 800, letterSpacing: 0.2 }}>
                Rutas de trabajo
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Planificacion operativa de iniciadores, grupos e items.
              </Typography>
            </Box>
            <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
              <Chip label={`Fecha: ${ruta?.fecha ?? "-"}`} variant="outlined" />
              <Chip label={`Turno: ${ruta?.turno ?? "-"}`} variant="outlined" />
              <Chip
                label={`Estado: ${ruta?.estado_ruta ?? "SIN_RUTA"}`}
                color={ruta?.estado_ruta === "BORRADOR" ? "primary" : "default"}
                variant="filled"
              />
            </Stack>
          </Stack>
          <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between" sx={{ mt: 1.5 }} flexWrap="wrap">
            <Tabs value={tab} onChange={(_, value) => setTab(value)}>
              <Tab label="TABLA" value="TABLA" />
              <Tab label="BOARD" value="BOARD" />
              <Tab label="MAPA" value="MAPA" />
            </Tabs>
            <Stack direction="row" spacing={1.2} flexWrap="wrap">
              <Button variant="outlined" onClick={() => setOpenCrearRuta(true)}>
                Crear ruta
              </Button>
              <Button variant="contained" disabled={!canCreateGrupo} onClick={() => setOpenCrearGrupo(true)}>
                Crear grupo
              </Button>
              <Button variant="outlined">Guardar borrador</Button>
              <Button variant="contained">Continuar</Button>
            </Stack>
          </Stack>
        </Paper>

        {error && <Alert severity="error">{error}</Alert>}
        {successMessage && <Alert severity="success">{successMessage}</Alert>}

        <ResumenRutaTrabajo ruta={ruta} grupos={grupos} itemsCount={itemsActivos.length} />

        {tab === "TABLA" && (
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 7 }}>
              <Paper
                sx={{
                  p: 2,
                  border: "1px solid rgba(100, 127, 176, 0.3)",
                  background:
                    "linear-gradient(180deg, rgba(17,26,46,0.94) 0%, rgba(10,16,31,0.98) 100%)",
                }}
              >
                <Typography variant="subtitle1" sx={{ mb: 1 }}>
                  Iniciadores pendientes
                </Typography>
                <TablaIniciadoresPendientes
                  rows={iniciadores}
                  total={iniciadoresMeta.total}
                  page={iniciadoresMeta.page}
                  perPage={iniciadoresMeta.perPage}
                  loading={loadingPendientes}
                  selectedIds={selectedIniciadorIds}
                  filters={filters}
                  onChangeFilters={(next) => {
                    setFilters(next);
                    setIniciadoresMeta((prev) => ({ ...prev, page: 1 }));
                  }}
                  onPageChange={(nextPage) => setIniciadoresMeta((prev) => ({ ...prev, page: nextPage }))}
                  onPerPageChange={(nextPerPage) => setIniciadoresMeta((prev) => ({ ...prev, perPage: nextPerPage, page: 1 }))}
                  onSelectionChange={setSelectedIniciadorIds}
                  onAssignSelected={() => setOpenAsignarGrupo(true)}
                />
              </Paper>
            </Grid>
            <Grid size={{ xs: 12, md: 5 }}>
              <Paper
                sx={{
                  p: 2,
                  border: "1px solid rgba(101, 129, 180, 0.33)",
                  background:
                    "linear-gradient(180deg, rgba(18,28,50,0.95) 0%, rgba(10,16,31,0.99) 100%)",
                }}
              >
                <Typography variant="subtitle1" sx={{ mb: 1 }}>
                  Grupos
                </Typography>
                {loading ? (
                  <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
                    <CircularProgress />
                  </Box>
                ) : (
                  <PanelGruposRuta
                    grupos={grupos}
                    items={itemsActivos}
                    iniciadorById={iniciadorById}
                    onEditarInspectores={(grupo) => {
                      setGrupoSeleccionado(grupo);
                      setOpenAsignarInspectores(true);
                    }}
                    onEliminarGrupo={handleDeleteGrupo}
                    onMoverItem={handleMoveItem}
                    onQuitarItem={handleDeleteItem}
                    onEditarOtItem={(item) => {
                      setItemSeleccionado(item);
                      setOpenEditarOt(true);
                    }}
                  />
                )}
              </Paper>
            </Grid>
          </Grid>
        )}

        {tab === "BOARD" && (
          <Paper
            sx={{
              p: 3,
              border: "1px solid rgba(90,117,162,0.28)",
              background: "linear-gradient(180deg, rgba(16,25,45,0.92), rgba(11,17,33,0.98))",
            }}
          >
            <Typography variant="subtitle1">BOARD</Typography>
            <Typography variant="body2" color="text.secondary">
              Vista operativa básica disponible en siguiente etapa.
            </Typography>
          </Paper>
        )}

        {tab === "MAPA" && (
          <Paper
            sx={{
              p: 3,
              border: "1px solid rgba(90,117,162,0.28)",
              background: "linear-gradient(180deg, rgba(16,25,45,0.92), rgba(11,17,33,0.98))",
            }}
          >
            <Typography variant="subtitle1">MAPA</Typography>
            <Typography variant="body2" color="text.secondary">
              Placeholder visual para integración de mapa en etapa posterior.
            </Typography>
          </Paper>
        )}

        <ModalCrearRutaTrabajo open={openCrearRuta} onClose={() => setOpenCrearRuta(false)} onSubmit={handleCreateRuta} />

        <ModalCrearGrupoRuta open={openCrearGrupo} onClose={() => setOpenCrearGrupo(false)} onSubmit={handleCreateGrupo} disabled={!canCreateGrupo} />

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

        <ModalEditarOrdenTrabajoItem
          open={openEditarOt}
          onClose={() => {
            setOpenEditarOt(false);
            setItemSeleccionado(null);
          }}
          item={itemSeleccionado}
          onConfirm={handleSaveOt}
        />
      </Box>
    </ThemeProvider>
  );
};

export default RutasTrabajo;
