import { useCallback, useEffect, useMemo, useState } from "react";
import ClearIcon from "@mui/icons-material/Clear";
import SearchIcon from "@mui/icons-material/Search";
import {
  Alert,
  Box,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Typography,
} from "@mui/material";
import { MaterialReactTable, useMaterialReactTable, type MRT_ColumnDef } from "material-react-table";

import {
  createOficioDesdeActuacion,
  getActuacionesPendientesOficio,
  getJuzgadosCatalogo,
  type IJuzgadoCatalogItem,
  type IPendientesOficioItem,
} from "../../../api/actuacionesPendientesApi";
import { containerStyles, wrapperStyles } from "../../CargarActuaciones/styles/cargarActuacionesStyles";
import { getCurrentMonthRange } from "../../../utils/dateRange";
import { DARK_TABLE_CONFIG } from "../styles/actuacionesTableStyles";
import {
  alertBaseStyles,
  COLORS,
  filtroButtonPrimaryStyles,
  filtroButtonSecondaryStyles,
  filtroButtonsStyles,
  filtroContainerStyles,
  filtroGridStyles,
  filtroItemStyles,
  filtroTitleStyles,
} from "../styles/filtroStyles";
import { AppButton, AppSelect, AppTextField } from "../../../ui";

const PendientesOficioView = () => {
  const defaultRange = useMemo(() => getCurrentMonthRange(), []);
  const [desde, setDesde] = useState(defaultRange.desde);
  const [hasta, setHasta] = useState(defaultRange.hasta);

  const [items, setItems] = useState<IPendientesOficioItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [juzgados, setJuzgados] = useState<IJuzgadoCatalogItem[]>([]);

  const [selected, setSelected] = useState<IPendientesOficioItem | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [numeroOficio, setNumeroOficio] = useState("");
  const [fechaOficio, setFechaOficio] = useState(defaultRange.hasta);
  const [juzgadoId, setJuzgadoId] = useState<number | "">("");
  const [causa, setCausa] = useState("");
  const [expNumero, setExpNumero] = useState("");
  const [expFecha, setExpFecha] = useState(defaultRange.hasta);
  const [saving, setSaving] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [resp, juzgadosResp] = await Promise.all([
        getActuacionesPendientesOficio(desde, hasta),
        getJuzgadosCatalogo(),
      ]);
      setItems(resp.items);
      setTotal(resp.meta.total);
      setJuzgados(juzgadosResp);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Error al cargar pendientes de oficio");
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [desde, hasta]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleFiltrar = useCallback(() => {
    void loadData();
  }, [loadData]);

  const handleLimpiar = useCallback(() => {
    const range = getCurrentMonthRange();
    setDesde(range.desde);
    setHasta(range.hasta);
  }, []);

  const openModal = (row: IPendientesOficioItem) => {
    setSelected(row);
    setNumeroOficio("");
    setFechaOficio(defaultRange.hasta);
    setJuzgadoId("");
    setCausa("");
    setExpNumero("");
    setExpFecha(defaultRange.hasta);
    setModalOpen(true);
  };

  const closeModal = () => {
    if (saving) return;
    setModalOpen(false);
    setSelected(null);
  };

  const handleSave = async () => {
    if (!selected) return;
    if (!numeroOficio.trim() || !fechaOficio || !juzgadoId || !expNumero.trim() || !expFecha) {
      setError("Completá número/fecha/juzgado y datos del expediente de oficio");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await createOficioDesdeActuacion(selected.id, {
        numero_oficio: numeroOficio.trim(),
        fecha_oficio: fechaOficio,
        juzgado_id: Number(juzgadoId),
        causa: causa.trim() || null,
        numero_expediente_oficio: expNumero.trim(),
        fecha_expediente_oficio: expFecha,
      });
      closeModal();
      await loadData();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "No se pudo cargar el oficio");
    } finally {
      setSaving(false);
    }
  };

  const columns = useMemo<MRT_ColumnDef<IPendientesOficioItem>[]>(
    () => [
      { accessorKey: "fecha_actuacion", header: "Fecha", size: 120 },
      { accessorKey: "orden_trabajo_numero", header: "OT", size: 100 },
      { accessorKey: "acta_comprobacion_num", header: "Acta comprobación", size: 180 },
      { accessorKey: "comprobacion_motivo", header: "Motivo", size: 220 },
      { accessorKey: "rubro_nombre", header: "Rubro", size: 180 },
      { accessorKey: "calle", header: "Calle", size: 200 },
      { accessorKey: "numero", header: "Número", size: 100 },
      { accessorKey: "expediente_original_numero", header: "Expediente original", size: 180 },
      { accessorKey: "expediente_original_anio", header: "Año exp. original", size: 140 },
      {
        id: "acciones",
        header: "Acciones",
        size: 160,
        Cell: ({ row }) => (
          <AppButton dsVariant="primary" dsSize="sm" onClick={() => openModal(row.original)}>
            Cargar oficio
          </AppButton>
        ),
      },
    ],
    []
  );

  const table = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    columns,
    data: items,
    enableEditing: false,
    enableRowSelection: false,
    renderTopToolbarCustomActions: () => (
      <Typography variant="body2" sx={{ pl: 1 }}>
        Total esperando oficio: {total}
      </Typography>
    ),
  });

  return (
    <Box sx={containerStyles}>
      <Box sx={wrapperStyles}>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <Box sx={filtroContainerStyles}>
            <Typography sx={filtroTitleStyles}>Rango de fechas</Typography>
            <Box sx={filtroGridStyles}>
              <Box sx={filtroItemStyles}>
                <AppTextField
                  appearance="dense"
                  fullWidth
                  type="date"
                  label="Desde"
                  value={desde}
                  onChange={(e) => setDesde(e.target.value)}
                  InputLabelProps={{ shrink: true }}
                  variant="outlined"
                />
              </Box>
              <Box sx={filtroItemStyles}>
                <AppTextField
                  appearance="dense"
                  fullWidth
                  type="date"
                  label="Hasta"
                  value={hasta}
                  onChange={(e) => setHasta(e.target.value)}
                  InputLabelProps={{ shrink: true }}
                  variant="outlined"
                />
              </Box>
            </Box>
            <Box sx={filtroButtonsStyles}>
              <AppButton
                dsVariant="ghost"
                dsSize="sm"
                onClick={handleLimpiar}
                startIcon={<ClearIcon />}
                sx={filtroButtonSecondaryStyles}
              >
                Limpiar
              </AppButton>
              <AppButton
                dsVariant="primary"
                dsSize="sm"
                onClick={handleFiltrar}
                startIcon={<SearchIcon />}
                sx={filtroButtonPrimaryStyles}
              >
                Filtrar
              </AppButton>
            </Box>
          </Box>

          {error && <Alert severity="error" sx={alertBaseStyles}>{error}</Alert>}

          {loading ? (
            <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
              <CircularProgress sx={{ color: COLORS.primary }} />
            </Box>
          ) : (
            <MaterialReactTable table={table} />
          )}

          <Dialog open={modalOpen} onClose={closeModal} fullWidth maxWidth="sm">
            <DialogTitle>Cargar oficio</DialogTitle>
            <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
              <AppTextField
                appearance="dense"
                label="Expediente original"
                value={`${selected?.expediente_original_numero ?? "-"} / ${selected?.expediente_original_anio ?? "-"}`}
                fullWidth
                InputProps={{ readOnly: true }}
              />
              <AppTextField
                appearance="dense"
                label="Contexto"
                value={`Acta comp: ${selected?.acta_comprobacion_num ?? "-"} | OT: ${selected?.orden_trabajo_numero ?? "-"}`}
                fullWidth
                InputProps={{ readOnly: true }}
              />
              <AppTextField
                appearance="dense"
                label="Número de oficio"
                value={numeroOficio}
                onChange={(e) => setNumeroOficio(e.target.value)}
                fullWidth
                required
              />
              <AppTextField
                appearance="dense"
                label="Fecha de oficio"
                type="date"
                value={fechaOficio}
                onChange={(e) => setFechaOficio(e.target.value)}
                InputLabelProps={{ shrink: true }}
                fullWidth
                required
              />
              <AppSelect
                appearance="dense"
                label="Juzgado"
                value={String(juzgadoId)}
                onChange={(e) => setJuzgadoId(Number(e.target.value))}
                fullWidth
                required
                variant="outlined"
                options={juzgados.map((j) => ({ value: String(j.id), label: j.nombre }))}
              />
              <AppTextField
                appearance="dense"
                label="Causa"
                value={causa}
                onChange={(e) => setCausa(e.target.value)}
                fullWidth
              />
              <AppTextField
                appearance="dense"
                label="Número expediente oficio"
                value={expNumero}
                onChange={(e) => setExpNumero(e.target.value)}
                fullWidth
                required
              />
              <AppTextField
                appearance="dense"
                label="Fecha expediente oficio"
                type="date"
                value={expFecha}
                onChange={(e) => setExpFecha(e.target.value)}
                InputLabelProps={{ shrink: true }}
                fullWidth
                required
              />
            </DialogContent>
            <DialogActions>
              <AppButton dsVariant="ghost" dsSize="sm" onClick={closeModal} disabled={saving}>
                Cancelar
              </AppButton>
              <AppButton dsVariant="primary" dsSize="sm" onClick={handleSave} disabled={saving}>
                {saving ? "Guardando..." : "Guardar"}
              </AppButton>
            </DialogActions>
          </Dialog>
        </Box>
      </Box>
    </Box>
  );
};

export default PendientesOficioView;
