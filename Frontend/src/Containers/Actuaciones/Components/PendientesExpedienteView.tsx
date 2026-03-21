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
  Tab,
  Tabs,
  Typography,
} from "@mui/material";
import { MaterialReactTable, useMaterialReactTable, type MRT_ColumnDef } from "material-react-table";

import {
  createExpedienteDesdeActuacion,
  getActuacionesPendientesExpediente,
  type IActuacionesPendientesItem,
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
import { AppButton, AppTextField } from "../../../ui";

const PendientesExpedienteView = () => {
  type SourceTab = "notificacion" | "comprobacion";
  const defaultRange = useMemo(() => getCurrentMonthRange(), []);
  const [desde, setDesde] = useState(defaultRange.desde);
  const [hasta, setHasta] = useState(defaultRange.hasta);

  const [items, setItems] = useState<IActuacionesPendientesItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sourceTab, setSourceTab] = useState<SourceTab>("notificacion");

  const [selected, setSelected] = useState<IActuacionesPendientesItem | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [expNumero, setExpNumero] = useState("");
  const [expFecha, setExpFecha] = useState(defaultRange.hasta);
  const [prorrogaDias, setProrrogaDias] = useState("0");
  const [saving, setSaving] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await getActuacionesPendientesExpediente(desde, hasta, sourceTab);
      setItems(resp.items);
      setTotal(resp.meta.total);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Error al cargar pendientes");
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [desde, hasta, sourceTab]);

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

  const openModal = (row: IActuacionesPendientesItem) => {
    setSelected(row);
    setExpNumero("");
    setExpFecha(defaultRange.hasta);
    setProrrogaDias("0");
    setModalOpen(true);
  };

  const closeModal = () => {
    if (saving) return;
    setModalOpen(false);
    setSelected(null);
  };

  const handleSave = async () => {
    if (!selected) return;
    if (!expNumero.trim() || !expFecha) {
      setError("Completá número y fecha del expediente");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await createExpedienteDesdeActuacion(selected.id, {
        numero_expediente: expNumero.trim(),
        fecha_expediente: expFecha,
        prorroga_dias: Number(prorrogaDias) || 0,
        source_type: selected.source_type,
      });
      closeModal();
      await loadData();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "No se pudo crear el expediente");
    } finally {
      setSaving(false);
    }
  };

  const actionColumn: MRT_ColumnDef<IActuacionesPendientesItem> = {
    id: "acciones",
    header: "Acciones",
    size: 160,
    Cell: ({ row }) => (
      <AppButton dsVariant="primary" dsSize="sm" onClick={() => openModal(row.original)}>
        Crear expediente
      </AppButton>
    ),
  };

  const columns = useMemo<MRT_ColumnDef<IActuacionesPendientesItem>[]>(
    () => [
      { accessorKey: "fecha_actuacion", header: "Fecha", size: 120 },
      { accessorKey: "orden_trabajo_numero", header: "OT", size: 100 },
      { accessorKey: "acta_numero", header: "Acta", size: 140 },
      { accessorKey: "motivo", header: "Motivo", size: 220 },
      { accessorKey: "rubro_nombre", header: "Rubro", size: 180 },
      { accessorKey: "calle", header: "Calle", size: 200 },
      { accessorKey: "numero", header: "Número", size: 100 },
      actionColumn,
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
        Total pendientes: {total}
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

          <Tabs
            value={sourceTab}
            onChange={(_, value: SourceTab) => setSourceTab(value)}
            sx={{ marginTop: -0.5 }}
          >
            <Tab value="notificacion" label="Notificación" />
            <Tab value="comprobacion" label="Comprobación" />
          </Tabs>

          {error && <Alert severity="error" sx={alertBaseStyles}>{error}</Alert>}

          {loading ? (
            <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
              <CircularProgress sx={{ color: COLORS.primary }} />
            </Box>
          ) : (
            <MaterialReactTable table={table} />
          )}

          <Dialog open={modalOpen} onClose={closeModal} fullWidth maxWidth="sm">
            <DialogTitle>Completar expediente</DialogTitle>
            <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
              <AppTextField
                appearance="dense"
                label="Número de expediente"
                value={expNumero}
                onChange={(e) => setExpNumero(e.target.value)}
                fullWidth
                required
              />
              <AppTextField
                appearance="dense"
                label="Fecha de expediente"
                type="date"
                value={expFecha}
                onChange={(e) => setExpFecha(e.target.value)}
                InputLabelProps={{ shrink: true }}
                fullWidth
                required
              />
              {selected?.source_type === "NOTIFICACION" && (
                <AppTextField
                  appearance="dense"
                  label="Prórroga (días)"
                  type="number"
                  value={prorrogaDias}
                  onChange={(e) => setProrrogaDias(e.target.value)}
                  fullWidth
                  required
                  helperText="Se suma al plazo base de 5 días de la notificación."
                />
              )}
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

export default PendientesExpedienteView;
