import { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, Box, CircularProgress, Typography } from "@mui/material";
import { MaterialReactTable, useMaterialReactTable, type MRT_ColumnDef } from "material-react-table";

import {
  createExpedienteDesdeActuacion,
  getActuacionesPendientesExpediente,
  postSyncNotificacionesVencidas,
  type IActuacionesPendientesItem,
  type ICreateExpedienteRequest,
  type ISyncNotificacionesVencidasResponse,
} from "../../api/actuacionesPendientesApi";
import { containerStyles, wrapperStyles } from "../CargarActuaciones/styles/cargarActuacionesStyles";
import { getCurrentMonthRange } from "../../utils/dateRange";
import { DARK_TABLE_CONFIG, MRT_READ_ONLY_BANDEJA } from "../Actuaciones/styles/actuacionesTableStyles";
import { alertBaseStyles, COLORS, moduleContentColumnSx } from "../Actuaciones/styles/filtroStyles";
import { formDialogContentStackSx } from "../../styles/formDialogStyles";
import { AppButton, AppDialog, AppTextField, SegmentedFilterChips } from "../../ui";
import {
  countByPlazoSlice,
  matchesPlazoSlice,
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
 * Bandeja: GET /actuaciones/pendientes/expediente?source_type=notificacion&omitir_rango_fecha=true (sin filtro por fecha en UI).
 */
const GestionNotificacionPage = () => {
  const defaultRange = useMemo(() => getCurrentMonthRange(), []);

  const [items, setItems] = useState<IActuacionesPendientesItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [plazoSlice, setPlazoSlice] = useState<PlazoOperativoSlice>("total");
  /** La tabla solo se monta tras elegir un indicador de plazo. */
  const [tablaVisible, setTablaVisible] = useState(false);

  const [selected, setSelected] = useState<IActuacionesPendientesItem | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [expNumero, setExpNumero] = useState("");
  const [expFecha, setExpFecha] = useState(defaultRange.hasta);
  const [prorrogaDias, setProrrogaDias] = useState("0");
  const [saving, setSaving] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [modalApiError, setModalApiError] = useState<string | null>(null);

  const [syncLoading, setSyncLoading] = useState(false);
  const [syncFeedback, setSyncFeedback] = useState<
    | null
    | { kind: "success"; metrics: ISyncNotificacionesVencidasResponse }
    | { kind: "error"; message: string }
  >(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await getActuacionesPendientesExpediente(undefined, undefined, "notificacion", null, {
        omitirRangoFecha: true,
      });
      setItems(resp.items);
    } catch (err: unknown) {
      const detail =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : null;
      setError(detail || "Error al cargar la bandeja");
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleSyncNotificacionesVencidas = useCallback(async () => {
    setSyncLoading(true);
    setSyncFeedback(null);
    try {
      const metrics = await postSyncNotificacionesVencidas();
      setSyncFeedback({ kind: "success", metrics });
      await loadData();
    } catch (err: unknown) {
      const detail =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string }; status?: number } }).response?.data?.detail
          : null;
      const status =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { status?: number } }).response?.status
          : undefined;
      if (status === 429) {
        setSyncFeedback({
          kind: "error",
          message: typeof detail === "string" ? detail : "Demasiadas solicitudes. Probá más tarde.",
        });
      } else {
        setSyncFeedback({
          kind: "error",
          message: typeof detail === "string" ? detail : "No se pudo sincronizar.",
        });
      }
    } finally {
      setSyncLoading(false);
    }
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
    const next: Record<string, string> = {};
    if (!expNumero.trim()) next.expNumero = "Completá el número de expediente.";
    if (!expFecha) next.expFecha = "Completá la fecha de expediente.";
    const pr = Number(prorrogaDias);
    if (prorrogaDias.trim() !== "" && (Number.isNaN(pr) || pr < 0)) {
      next.prorrogaDias = "Indicá un número de días válido (0 o más).";
    }
    setFieldErrors(next);
    if (Object.keys(next).length > 0) return;

    setSaving(true);
    setModalApiError(null);
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
      const detail =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : null;
      setModalApiError(detail || "No se pudo añadir el expediente de plazo");
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
    ...MRT_READ_ONLY_BANDEJA,
    columns,
    data: filteredRows,
    enableColumnFilters: false,
    enableGlobalFilter: false,
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
        <Box sx={{ ...moduleContentColumnSx, gap: 2 }}>
          <Box
            sx={{
              display: "flex",
              flexDirection: { xs: "column", sm: "row" },
              flexWrap: "wrap",
              alignItems: { xs: "stretch", sm: "flex-start" },
              gap: 2,
              pb: 1,
              borderBottom: "1px solid rgba(255,255,255,0.08)",
            }}
          >
            <Box sx={{ flex: "1 1 280px", minWidth: 0 }}>
              <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.78)", mb: 0.75 }}>
                <strong>Sincronizar vencimientos</strong> materializa en el sistema la cola de reinspección por
                notificaciones vencidas (iniciadores para planificación). Esta tabla sigue siendo la bandeja de{" "}
                <strong>expedientes de plazo</strong> y <strong>días restantes</strong>: el resultado del sync{" "}
                <strong>no siempre cambia</strong> las filas visibles.
              </Typography>
              <Typography variant="caption" sx={{ display: "block", color: "rgba(255,255,255,0.55)", mb: 1.25 }}>
                El ícono de actualizar en los indicadores solo <strong>recarga esta bandeja</strong>; no ejecuta el
                proceso operativo de sincronización.
              </Typography>
              <AppButton
                dsVariant="primary"
                dsSize="sm"
                onClick={() => void handleSyncNotificacionesVencidas()}
                disabled={syncLoading || loading}
              >
                {syncLoading ? "Sincronizando…" : "Sincronizar vencimientos"}
              </AppButton>
            </Box>
          </Box>

          {syncFeedback?.kind === "success" && (
            <Alert
              severity="success"
              sx={alertBaseStyles}
              onClose={() => setSyncFeedback(null)}
            >
              Sincronización correcta. Creados: <strong>{syncFeedback.metrics.created}</strong>, elegibles:{" "}
              <strong>{syncFeedback.metrics.eligible_notificaciones}</strong>, omitidos (ya bloqueados):{" "}
              <strong>{syncFeedback.metrics.skipped_already_blocking}</strong>, colisiones idempotentes:{" "}
              <strong>{syncFeedback.metrics.collisions_idempotent}</strong>, tiempo:{" "}
              <strong>{syncFeedback.metrics.elapsed_ms}</strong> ms.
            </Alert>
          )}
          {syncFeedback?.kind === "error" && (
            <Alert severity="error" sx={alertBaseStyles} onClose={() => setSyncFeedback(null)}>
              {syncFeedback.message}
            </Alert>
          )}

          <SegmentedFilterChips<PlazoOperativoSlice>
            options={sliceChips.map(({ slice, count }) => ({
              value: slice,
              label: `${sliceLabel(slice)} · ${loading ? "…" : count}`,
            }))}
            onSelect={(slice) => {
              setPlazoSlice(slice);
              setTablaVisible(true);
            }}
            isSelected={(slice) => tablaVisible && plazoSlice === slice}
            onRefresh={() => void loadData()}
            refreshDisabled={loading}
          />

          {error && (
            <Alert severity="error" sx={alertBaseStyles}>
              {error}
            </Alert>
          )}

          {loading && !tablaVisible && (
            <Box sx={{ display: "flex", justifyContent: "center", py: 2 }}>
              <CircularProgress size={28} sx={{ color: COLORS.primary }} />
            </Box>
          )}

          {tablaVisible && (
            <Box sx={{ position: "relative", opacity: loading ? 0.65 : 1, transition: "opacity 0.2s" }}>
              {loading && (
                <Box
                  sx={{
                    position: "absolute",
                    inset: 0,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    zIndex: 1,
                    pointerEvents: "none",
                  }}
                >
                  <CircularProgress size={32} sx={{ color: COLORS.primary }} />
                </Box>
              )}
              <MaterialReactTable table={table} />
            </Box>
          )}

          <AppDialog
            open={modalOpen}
            onClose={closeModal}
            title="Añadir expediente de plazo"
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
            {modalApiError ? (
              <Alert severity="error" sx={{ mb: 0 }}>
                {modalApiError}
              </Alert>
            ) : null}
            <AppTextField
              appearance="glass"
              label="Número de expediente"
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
            <AppTextField
              appearance="glass"
              label="Fecha de expediente"
              type="date"
              value={expFecha}
              onChange={(e) => {
                setExpFecha(e.target.value);
                setFieldErrors((f) => {
                  const n = { ...f };
                  delete n.expFecha;
                  return n;
                });
              }}
              InputLabelProps={{ shrink: true }}
              fullWidth
              required
              error={Boolean(fieldErrors.expFecha)}
              helperText={fieldErrors.expFecha || undefined}
            />
            <AppTextField
              appearance="glass"
              label="Prórroga (días)"
              type="number"
              value={prorrogaDias}
              onChange={(e) => {
                setProrrogaDias(e.target.value);
                setFieldErrors((f) => {
                  const n = { ...f };
                  delete n.prorrogaDias;
                  return n;
                });
              }}
              fullWidth
              required
              error={Boolean(fieldErrors.prorrogaDias)}
              helperText={fieldErrors.prorrogaDias ?? "Días que se suman al plazo consolidado de la notificación."}
            />
          </AppDialog>
        </Box>
      </Box>
    </Box>
  );
};

export default GestionNotificacionPage;
