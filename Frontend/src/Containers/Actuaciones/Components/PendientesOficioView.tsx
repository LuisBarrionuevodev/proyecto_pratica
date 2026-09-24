import { useCallback, useEffect, useMemo, useState } from "react";
import ClearIcon from "@mui/icons-material/Clear";
import SearchIcon from "@mui/icons-material/Search";
import { Alert, Box, CircularProgress, Typography } from "@mui/material";
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
import { DARK_TABLE_CONFIG, MRT_READ_ONLY_BANDEJA } from "../styles/actuacionesTableStyles";
import { formDialogContentStackSx } from "../../../styles/formDialogStyles";
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
import { AppButton, AppDialog, AppSelect, AppTextField } from "../../../ui";
import {
  applyOficioPendientesErrorsFromApi,
  validateOficioAltaPayloadClient,
  OFICIO_PENDIENTES_FIELD_ALIASES,
} from "../../../utils/oficioFormErrors";

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
  const [saving, setSaving] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [modalApiError, setModalApiError] = useState<string | null>(null);

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
    setFieldErrors({});
    setModalApiError(null);
    setModalOpen(true);
  };

  const closeModal = () => {
    if (saving) return;
    setModalOpen(false);
    setSelected(null);
    setFieldErrors({});
    setModalApiError(null);
  };

  const handleSave = async () => {
    if (!selected) return;
    const payload = {
      numero_oficio: numeroOficio.trim(),
      fecha_oficio: fechaOficio,
      juzgado_id: Number(juzgadoId),
      causa: causa.trim() || null,
      numero_expediente_oficio: expNumero.trim(),
      fecha_expediente_oficio: fechaOficio,
    };
    const next = validateOficioAltaPayloadClient(payload, OFICIO_PENDIENTES_FIELD_ALIASES);
    setFieldErrors(next);
    if (Object.keys(next).length > 0) {
      setModalApiError(null);
      return;
    }

    setSaving(true);
    setModalApiError(null);
    setFieldErrors({});
    try {
      await createOficioDesdeActuacion(selected.id, payload);
      closeModal();
      await loadData();
    } catch (err: unknown) {
      const parsed = applyOficioPendientesErrorsFromApi(err);
      setFieldErrors(parsed.fieldErrors);
      setModalApiError(parsed.globalMessage);
    } finally {
      setSaving(false);
    }
  };

  const columns = useMemo<MRT_ColumnDef<IPendientesOficioItem>[]>(
    () => [
      { accessorKey: "fecha_actuacion", header: "Fecha", size: 120 },
      { accessorKey: "orden_trabajo_numero", header: "Orden de trabajo", size: 130 },
      { accessorKey: "acta_comprobacion_num", header: "Número de acta", size: 140 },
      { accessorKey: "rubro_nombre", header: "Rubro", size: 160 },
      { accessorKey: "calle", header: "Calle", size: 200 },
      { accessorKey: "numero", header: "Número", size: 100 },
      { accessorKey: "comprobacion_motivo", header: "Motivo", size: 220 },
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
    ...MRT_READ_ONLY_BANDEJA,
    columns,
    data: items,
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

          <AppDialog
            open={modalOpen}
            onClose={closeModal}
            title="Cargar oficio"
            appearance="glass"
            maxWidth="sm"
            fullWidth
            showCloseButton
            onCloseButtonClick={closeModal}
            contentSx={formDialogContentStackSx}
            actions={
              <>
                <AppButton dsVariant="ghost" dsSize="sm" onClick={closeModal} disabled={saving}>
                  Cancelar
                </AppButton>
                <AppButton dsVariant="primary" dsSize="sm" onClick={() => void handleSave()} disabled={saving}>
                  {saving ? "Guardando..." : "Guardar"}
                </AppButton>
              </>
            }
          >
            {modalApiError && Object.keys(fieldErrors).length === 0 ? (
              <Alert severity="error" sx={{ mb: 0 }}>
                {modalApiError}
              </Alert>
            ) : Object.keys(fieldErrors).length > 0 ? (
              <Alert severity="error" sx={{ mb: 0 }}>
                Revisá los campos marcados abajo.
              </Alert>
            ) : null}
            <AppTextField
              appearance="glass"
              label="Expediente original"
              value={`${selected?.expediente_original_numero ?? "-"} / ${selected?.expediente_original_anio ?? "-"}`}
              fullWidth
              InputProps={{ readOnly: true }}
            />
            <AppTextField
              appearance="glass"
              label="Contexto"
              value={`Acta comp: ${selected?.acta_comprobacion_num ?? "-"} | OT: ${selected?.orden_trabajo_numero ?? "-"}`}
              fullWidth
              InputProps={{ readOnly: true }}
            />
            <AppTextField
              appearance="glass"
              label="Número de oficio"
              value={numeroOficio}
              onChange={(e) => {
                setNumeroOficio(e.target.value);
                setFieldErrors((f) => {
                  const n = { ...f };
                  delete n.numeroOficio;
                  return n;
                });
              }}
              fullWidth
              required
              error={Boolean(fieldErrors.numeroOficio)}
              helperText={fieldErrors.numeroOficio || undefined}
            />
            <AppTextField
              appearance="glass"
              label="Fecha de oficio y expediente de respuesta"
              type="date"
              value={fechaOficio}
              onChange={(e) => {
                setFechaOficio(e.target.value);
                setFieldErrors((f) => {
                  const n = { ...f };
                  delete n.fechaOficio;
                  return n;
                });
              }}
              InputLabelProps={{ shrink: true }}
              fullWidth
              required
              error={Boolean(fieldErrors.fechaOficio)}
              helperText={fieldErrors.fechaOficio || "Misma fecha para oficio y expediente de respuesta."}
            />
            <AppSelect
              appearance="glass"
              label="Juzgado"
              value={String(juzgadoId)}
              onChange={(e) => {
                setJuzgadoId(Number(e.target.value));
                setFieldErrors((f) => {
                  const n = { ...f };
                  delete n.juzgadoId;
                  return n;
                });
              }}
              fullWidth
              required
              variant="outlined"
              error={Boolean(fieldErrors.juzgadoId)}
              helperText={fieldErrors.juzgadoId || undefined}
              options={[{ value: "", label: "Seleccionar…" }, ...juzgados.map((j) => ({ value: String(j.id), label: j.nombre }))]}
            />
            <AppTextField
              appearance="glass"
              label="Causa"
              value={causa}
              onChange={(e) => {
                setCausa(e.target.value);
                setFieldErrors((f) => {
                  const n = { ...f };
                  delete n.causa;
                  return n;
                });
              }}
              fullWidth
              error={Boolean(fieldErrors.causa)}
              helperText={fieldErrors.causa || undefined}
            />
            <AppTextField
              appearance="glass"
              label="Número expediente oficio"
              value={expNumero}
              onChange={(e) => {
                setExpNumero(e.target.value);
                setFieldErrors((f) => {
                  const n = { ...f };
                  delete n.expNumero;
                  return n;
                });
              }}
              fullWidth
              required
              error={Boolean(fieldErrors.expNumero)}
              helperText={fieldErrors.expNumero || undefined}
            />
          </AppDialog>
        </Box>
      </Box>
    </Box>
  );
};

export default PendientesOficioView;
