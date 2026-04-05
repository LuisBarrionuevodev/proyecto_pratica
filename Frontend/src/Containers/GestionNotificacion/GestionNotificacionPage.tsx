import { useCallback, useEffect, useMemo, useState } from "react";
import FilterAltIcon from "@mui/icons-material/FilterAlt";
import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  Typography,
} from "@mui/material";
import { MaterialReactTable, useMaterialReactTable, type MRT_ColumnDef } from "material-react-table";

import {
  createExpedienteDesdeActuacion,
  getActuacionesPendientesExpediente,
  type IActuacionesPendientesItem,
  type ICreateExpedienteRequest,
} from "../../api/actuacionesPendientesApi";
import { containerStyles, wrapperStyles } from "../CargarActuaciones/styles/cargarActuacionesStyles";
import { getCurrentMonthRange } from "../../utils/dateRange";
import { DARK_TABLE_CONFIG } from "../Actuaciones/styles/actuacionesTableStyles";
import { alertBaseStyles, COLORS, filtroContainerStyles, filtroTitleStyles } from "../Actuaciones/styles/filtroStyles";
import { AppButton, AppTextField } from "../../ui";
import {
  countByPlazoSlice,
  DIAS_EN_PLAZO_MIN,
  matchesPlazoSlice,
  POR_VENCER_MAX,
  POR_VENCER_MIN,
  sliceLabel,
  type PlazoOperativoSlice,
} from "./gestionNotificacionPlazo";

function contribuyenteText(row: IActuacionesPendientesItem): string {
  const a = (row.contrib_apellido ?? "").trim();
  const n = (row.contrib_nombre ?? "").trim();
  const t = [a, n].filter(Boolean).join(", ");
  return t || "—";
}

function domicilioText(row: IActuacionesPendientesItem): string {
  const c = (row.calle ?? "").trim();
  const n = (row.numero ?? "").trim();
  const t = [c, n].filter(Boolean).join(" ");
  return t || "—";
}

function motivosNotif(row: IActuacionesPendientesItem): string {
  const parts = [row.notificacion_motivo_1, row.notificacion_motivo_2, row.notificacion_motivo_3].filter(
    (s): s is string => Boolean(s && String(s).trim())
  );
  return parts.join(", ") || "—";
}

function diasRestantesCell(row: IActuacionesPendientesItem): string {
  if (row.dias_restantes === null || row.dias_restantes === undefined) return "—";
  return String(row.dias_restantes);
}

function plazosOtorgadosCell(row: IActuacionesPendientesItem): string {
  if (row.plazos_otorgados === null || row.plazos_otorgados === undefined) return "—";
  return String(row.plazos_otorgados);
}

/**
 * Bandeja: GET /actuaciones/pendientes/expediente?source_type=notificacion (sin rango en UI; usa default del backend).
 */
const GestionNotificacionPage = () => {
  const defaultRange = useMemo(() => getCurrentMonthRange(), []);

  const [items, setItems] = useState<IActuacionesPendientesItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [plazoSlice, setPlazoSlice] = useState<PlazoOperativoSlice>("total");

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
      const resp = await getActuacionesPendientesExpediente(undefined, undefined, "notificacion");
      setItems(resp.items);
    } catch (err: unknown) {
      const detail = err && typeof err === "object" && "response" in err ? (err as any).response?.data?.detail : null;
      setError(detail || "Error al cargar la bandeja");
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const notificacionRows = useMemo(
    () => items.filter((r) => r.source_type === "NOTIFICACION"),
    [items]
  );

  const sliceCounts = useMemo(() => countByPlazoSlice(notificacionRows), [notificacionRows]);

  const filteredRows = useMemo(
    () => notificacionRows.filter((r) => matchesPlazoSlice(r, plazoSlice)),
    [notificacionRows, plazoSlice]
  );

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
      setError("Completá número y fecha del expediente de plazo");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const payload: ICreateExpedienteRequest = {
        expediente_numero: expNumero.trim(),
        fecha_expediente: expFecha,
        source_type: "NOTIFICACION",
        prorroga_dias: Number(prorrogaDias) || 0,
      };
      await createExpedienteDesdeActuacion(selected.id, payload);
      closeModal();
      await loadData();
    } catch (err: unknown) {
      const detail = err && typeof err === "object" && "response" in err ? (err as any).response?.data?.detail : null;
      setError(detail || "No se pudo añadir el expediente de plazo");
    } finally {
      setSaving(false);
    }
  };

  const actionColumn: MRT_ColumnDef<IActuacionesPendientesItem> = {
    id: "acciones",
    header: "Acción",
    size: 200,
    Cell: ({ row }) => (
      <AppButton dsVariant="primary" dsSize="sm" onClick={() => openModal(row.original)}>
        Añadir expediente de plazo
      </AppButton>
    ),
  };

  const columns = useMemo<MRT_ColumnDef<IActuacionesPendientesItem>[]>(
    () => [
      { accessorKey: "fecha_actuacion", header: "Fecha", size: 120 },
      {
        id: "contribuyente",
        header: "Contribuyente",
        size: 200,
        accessorFn: (row) => contribuyenteText(row),
      },
      {
        id: "domicilio",
        header: "Domicilio",
        size: 220,
        accessorFn: (row) => domicilioText(row),
      },
      {
        id: "acta_notificacion",
        header: "Nº notificación",
        size: 140,
        accessorFn: (row) => row.acta_notificacion_num ?? "—",
      },
      {
        id: "motivos",
        header: "Motivo(s)",
        size: 200,
        accessorFn: (row) => motivosNotif(row),
      },
      {
        id: "dias_restantes",
        header: "Días restantes",
        size: 130,
        accessorFn: (row) => diasRestantesCell(row),
      },
      {
        id: "plazos_otorgados",
        header: "Plazos otorgados",
        size: 130,
        accessorFn: (row) => plazosOtorgadosCell(row),
      },
      actionColumn,
    ],
    []
  );

  const table = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    columns,
    data: filteredRows,
    enableEditing: false,
    enableRowSelection: false,
    enableColumnFilters: false,
    enableGlobalFilter: false,
    renderTopToolbarCustomActions: () => (
      <Typography variant="body2" sx={{ pl: 1, color: "rgba(255,255,255,0.75)" }}>
        {plazoSlice === "total"
          ? `${filteredRows.length} notificación(es) en la bandeja`
          : `Mostrando ${filteredRows.length} fila(s) · ${sliceLabel(plazoSlice)}`}
      </Typography>
    ),
  });

  const sliceChips: { slice: PlazoOperativoSlice; count: number }[] = [
    { slice: "total", count: sliceCounts.total },
    { slice: "en_plazo", count: sliceCounts.en_plazo },
    { slice: "por_vencer", count: sliceCounts.por_vencer },
    { slice: "vencidas_o_hoy", count: sliceCounts.vencidas_o_hoy },
  ];

  return (
    <Box sx={containerStyles}>
      <Box sx={wrapperStyles}>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <Box sx={filtroContainerStyles}>
            <Typography sx={filtroTitleStyles}>Filtros e indicadores</Typography>
            <Grid container spacing={1.5} alignItems="flex-end">
              <Grid size={{ xs: 12 }}>
                <Typography variant="subtitle2" sx={{ color: "rgba(255,255,255,0.85)", mb: 1 }}>
                  Plazo operativo — tocá un indicador para filtrar la tabla
                </Typography>
                <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
                  {sliceChips.map(({ slice, count }) => {
                    const selected = plazoSlice === slice;
                    return (
                      <Chip
                        key={slice}
                        label={`${sliceLabel(slice)} · ${count}`}
                        onClick={() => setPlazoSlice(slice)}
                        variant={selected ? "filled" : "outlined"}
                        sx={{
                          cursor: "pointer",
                          fontWeight: 600,
                          borderColor: "rgba(255,255,255,0.2)",
                          backgroundColor: selected ? "rgba(1, 102, 255, 0.35)" : "rgba(255,255,255,0.04)",
                          color: "#fff",
                          "&:hover": { backgroundColor: selected ? "rgba(1, 102, 255, 0.45)" : "rgba(255,255,255,0.08)" },
                        }}
                      />
                    );
                  })}
                </Box>
              </Grid>
              <Grid size={{ xs: 12, sm: "auto" }}>
                <AppButton
                  dsVariant="primary"
                  dsSize="sm"
                  startIcon={<FilterAltIcon sx={{ fontSize: 18 }} />}
                  onClick={() => void loadData()}
                  sx={{ fontFamily: '"Tactic Sans", sans-serif', fontWeight: 600 }}
                >
                  Actualizar bandeja
                </AppButton>
              </Grid>
            </Grid>
            <Typography variant="caption" sx={{ display: "block", mt: 1.5, color: "rgba(255,255,255,0.45)" }}>
              Total = notificaciones cargadas en esta vista. En plazo: ≥{DIAS_EN_PLAZO_MIN} días (&gt;4). Por vencer:{" "}
              {POR_VENCER_MIN} a {POR_VENCER_MAX} días. Vencidas o hoy: 0 días (criterio API). Los días 3 y 4 solo
              aparecen con Total.
            </Typography>
          </Box>

          {error && (
            <Alert severity="error" sx={alertBaseStyles}>
              {error}
            </Alert>
          )}

          {loading ? (
            <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
              <CircularProgress sx={{ color: COLORS.primary }} />
            </Box>
          ) : (
            <MaterialReactTable table={table} />
          )}

          <Dialog open={modalOpen} onClose={closeModal} fullWidth maxWidth="sm">
            <DialogTitle>Añadir expediente de plazo</DialogTitle>
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
              <AppTextField
                appearance="dense"
                label="Prórroga (días)"
                type="number"
                value={prorrogaDias}
                onChange={(e) => setProrrogaDias(e.target.value)}
                fullWidth
                required
                helperText="Días que se suman al plazo consolidado de la notificación."
              />
            </DialogContent>
            <DialogActions>
              <AppButton dsVariant="ghost" dsSize="sm" onClick={closeModal} disabled={saving}>
                Cancelar
              </AppButton>
              <AppButton dsVariant="primary" dsSize="sm" onClick={() => void handleSave()} disabled={saving}>
                {saving ? "Guardando..." : "Guardar"}
              </AppButton>
            </DialogActions>
          </Dialog>
        </Box>
      </Box>
    </Box>
  );
};

export default GestionNotificacionPage;
