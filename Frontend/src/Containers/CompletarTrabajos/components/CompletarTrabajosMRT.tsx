import { useCallback, useMemo, useState } from "react";
import {
  Box,
  Chip,
  CircularProgress,
  IconButton,
  Tooltip,
  Typography,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
  type MRT_TableOptions,
} from "material-react-table";

import type { ICompletarTrabajoPendienteRow } from "../../../api/completarTrabajoApi";
import { postCompletarTrabajoCerrar } from "../../../api/completarTrabajoApi";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { COLORS, DARK_TABLE_CONFIG } from "../../Actuaciones/styles/actuacionesTableStyles";
import type { CompletarTrabajoCatalogs } from "../hooks/useCompletarTrabajoCatalogs";
import { buildCompletarTrabajoCierreBodyFromInline } from "../utils/buildCompletarTrabajoCierreBody";
import {
  formatCompletarTrabajoApiError,
  parseCompletarTrabajoFieldErrors,
} from "../utils/completarTrabajoErrors";

const NUMERO_TIPO_OPTS = ["", "NUMERO", "ESQUINA", "OTRO"];

function dashIfEmpty(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

function mergeCatalogWithRowValues(catalog: string[], fromRows: (string | null | undefined)[]): string[] {
  const s = new Set<string>(catalog);
  for (const v of fromRows) {
    const t = (v ?? "").trim();
    if (t) s.add(t);
  }
  return ["", ...s];
}

function estadoChipColor(v: string | null | undefined): "default" | "success" | "warning" | "info" {
  const u = (v ?? "").toUpperCase();
  if (u.includes("FINAL")) return "success";
  if (u.includes("PROCESO") || u.includes("EN_")) return "info";
  if (u.includes("PEND")) return "warning";
  return "default";
}

export type CompletarTrabajosMRTProps = {
  rows: ICompletarTrabajoPendienteRow[];
  loading: boolean;
  total: number;
  page: number;
  perPage: number;
  onPageChange: (nextPage: number) => void;
  onPerPageChange: (nextPerPage: number) => void;
  catalogs: CompletarTrabajoCatalogs | null;
  onCierreExitoso: () => void;
};

/**
 * Completar trabajo: edición en fila (MRT row) + selects desde catálogos DB.
 * `tipo_actuacion` es solo lectura (el envío de tipo va en otro flujo).
 */
export function CompletarTrabajosMRT({
  rows,
  loading,
  total,
  page,
  perPage,
  onPageChange,
  onPerPageChange,
  catalogs,
  onCierreExitoso,
}: CompletarTrabajosMRTProps) {
  const pagination = useMemo(() => ({ pageIndex: page - 1, pageSize: perPage }), [page, perPage]);
  const [bannerError, setBannerError] = useState<string | null>(null);
  const [cellErrorsByRow, setCellErrorsByRow] = useState<Record<string, Record<string, string>>>({});
  const [saving, setSaving] = useState(false);

  const contraOpts = useMemo(
    () =>
      mergeCatalogWithRowValues(
        catalogs?.contraproducencias ?? [],
        rows.flatMap((r) => [r.contraproducencia])
      ),
    [catalogs?.contraproducencias, rows]
  );
  const motivoNotifOpts = useMemo(
    () =>
      mergeCatalogWithRowValues(
        catalogs?.motivos ?? [],
        rows.flatMap((r) => [r.notificacion_motivo_1, r.notificacion_motivo_2, r.notificacion_motivo_3])
      ),
    [catalogs?.motivos, rows]
  );
  const motivoCompOpts = useMemo(
    () =>
      mergeCatalogWithRowValues(
        catalogs?.motivosComprobacion ?? [],
        rows.flatMap((r) => [r.comprobacion_motivo])
      ),
    [catalogs?.motivosComprobacion, rows]
  );
  const rubroOpts = useMemo(
    () => mergeCatalogWithRowValues(catalogs?.rubros ?? [], rows.flatMap((r) => [r.rubro_nombre])),
    [catalogs?.rubros, rows]
  );

  const errFor = useCallback(
    (rutaItemId: number, key: string) => cellErrorsByRow[String(rutaItemId)]?.[key],
    [cellErrorsByRow]
  );

  const columns = useMemo<MRT_ColumnDef<ICompletarTrabajoPendienteRow>[]>(
    () => [
      {
        accessorKey: "fecha_actuacion",
        header: "Fecha",
        size: 108,
        enableEditing: false,
        Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
      },
      {
        accessorKey: "tipo_iniciador",
        header: "Iniciador",
        size: 140,
        enableEditing: false,
        Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
      },
      {
        accessorKey: "orden_trabajo_numero",
        header: "OT",
        size: 92,
        enableEditing: false,
        Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
      },
      {
        accessorKey: "tipo_actuacion",
        header: "Tipo actuación",
        size: 160,
        enableEditing: false,
        Cell: ({ row }) => (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 0.25 }}>
            <Typography variant="body2" sx={{ color: COLORS.white, fontSize: "11px" }}>
              {dashIfEmpty(row.original.tipo_actuacion)}
            </Typography>
            {row.original.tipo_actuacion_esperado ? (
              <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.45)", fontSize: "10px" }}>
                Ref. iniciador: {row.original.tipo_actuacion_esperado}
              </Typography>
            ) : null}
          </Box>
        ),
      },
      {
        accessorKey: "contraproducencia",
        header: "Contraproducencia",
        size: 200,
        editVariant: "select",
        editSelectOptions: contraOpts,
        muiEditTextFieldProps: ({ row }) => {
          const rid = row.original.ruta_item_id;
          const err = errFor(rid, "contraproducencia");
          return {
            select: true,
            error: !!err,
            helperText: err ?? "Vacío = visita realizada",
          };
        },
        Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
      },
      {
        accessorKey: "calle",
        header: "Calle",
        size: 150,
        muiEditTextFieldProps: ({ row }) => {
          const rid = row.original.ruta_item_id;
          const err = errFor(rid, "calle");
          return { error: !!err, helperText: err ?? "" };
        },
      },
      {
        accessorKey: "numero",
        header: "Número",
        size: 90,
        muiEditTextFieldProps: ({ row }) => {
          const rid = row.original.ruta_item_id;
          const err = errFor(rid, "numero");
          return { error: !!err, helperText: err ?? "" };
        },
      },
      {
        accessorKey: "numero_tipo",
        header: "Tipo núm.",
        size: 110,
        editVariant: "select",
        editSelectOptions: NUMERO_TIPO_OPTS,
        muiEditTextFieldProps: ({ row }) => {
          const rid = row.original.ruta_item_id;
          const err = errFor(rid, "numero_tipo");
          return { select: true, error: !!err, helperText: err ?? "" };
        },
        Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
      },
      {
        accessorKey: "rubro_nombre",
        header: "Rubro",
        size: 140,
        editVariant: "select",
        editSelectOptions: rubroOpts,
        muiEditTextFieldProps: ({ row }) => {
          const rid = row.original.ruta_item_id;
          const err = errFor(rid, "rubro_nombre");
          return { select: true, error: !!err, helperText: err ?? "" };
        },
        Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
      },
      {
        accessorKey: "doc_nro",
        header: "Documento",
        size: 110,
        muiEditTextFieldProps: ({ row }) => {
          const rid = row.original.ruta_item_id;
          const err = errFor(rid, "doc_nro");
          return { error: !!err, helperText: err ?? "" };
        },
        Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
      },
      {
        accessorKey: "contrib_apellido",
        header: "Apellido",
        size: 120,
        muiEditTextFieldProps: ({ row }) => {
          const rid = row.original.ruta_item_id;
          const err = errFor(rid, "contrib_apellido");
          return { error: !!err, helperText: err ?? "" };
        },
        Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
      },
      {
        accessorKey: "contrib_nombre",
        header: "Nombre",
        size: 120,
        muiEditTextFieldProps: ({ row }) => {
          const rid = row.original.ruta_item_id;
          const err = errFor(rid, "contrib_nombre");
          return { error: !!err, helperText: err ?? "" };
        },
        Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
      },
      {
        accessorKey: "acta_inspeccion_num",
        header: "Acta insp.",
        size: 100,
        muiEditTextFieldProps: ({ row }) => {
          const rid = row.original.ruta_item_id;
          const err = errFor(rid, "acta_inspeccion_num");
          return { error: !!err, helperText: err ?? "" };
        },
        Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
      },
      {
        accessorKey: "acta_notificacion_num",
        header: "Acta notif.",
        size: 100,
        muiEditTextFieldProps: ({ row }) => {
          const rid = row.original.ruta_item_id;
          const err = errFor(rid, "acta_notificacion_num");
          return { error: !!err, helperText: err ?? "" };
        },
        Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
      },
      {
        accessorKey: "notificacion_motivo_1",
        header: "Motivo notif. 1",
        size: 150,
        editVariant: "select",
        editSelectOptions: motivoNotifOpts,
        muiEditTextFieldProps: ({ row }) => {
          const rid = row.original.ruta_item_id;
          const err = errFor(rid, "notificacion_motivo_1");
          return { select: true, error: !!err, helperText: err ?? "" };
        },
        Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
      },
      {
        accessorKey: "notificacion_motivo_2",
        header: "Motivo notif. 2",
        size: 150,
        editVariant: "select",
        editSelectOptions: motivoNotifOpts,
        muiEditTextFieldProps: ({ row }) => {
          const rid = row.original.ruta_item_id;
          const err = errFor(rid, "notificacion_motivo_2");
          return { select: true, error: !!err, helperText: err ?? "" };
        },
        Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
      },
      {
        accessorKey: "notificacion_motivo_3",
        header: "Motivo notif. 3",
        size: 150,
        editVariant: "select",
        editSelectOptions: motivoNotifOpts,
        muiEditTextFieldProps: ({ row }) => {
          const rid = row.original.ruta_item_id;
          const err = errFor(rid, "notificacion_motivo_3");
          return { select: true, error: !!err, helperText: err ?? "" };
        },
        Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
      },
      {
        accessorKey: "acta_comprobacion_num",
        header: "Acta comp.",
        size: 100,
        muiEditTextFieldProps: ({ row }) => {
          const rid = row.original.ruta_item_id;
          const err = errFor(rid, "acta_comprobacion_num");
          return { error: !!err, helperText: err ?? "" };
        },
        Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
      },
      {
        accessorKey: "comprobacion_motivo",
        header: "Motivo comp.",
        size: 150,
        editVariant: "select",
        editSelectOptions: motivoCompOpts,
        muiEditTextFieldProps: ({ row }) => {
          const rid = row.original.ruta_item_id;
          const err = errFor(rid, "comprobacion_motivo");
          return { select: true, error: !!err, helperText: err ?? "" };
        },
        Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
      },
      {
        accessorKey: "acta_clausura_num",
        header: "Acta clausura",
        size: 110,
        muiEditTextFieldProps: ({ row }) => {
          const rid = row.original.ruta_item_id;
          const err = errFor(rid, "acta_clausura_num");
          return { error: !!err, helperText: err ?? "" };
        },
        Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
      },
      {
        accessorKey: "acta_decomiso_num",
        header: "Acta decomiso",
        size: 110,
        muiEditTextFieldProps: ({ row }) => {
          const rid = row.original.ruta_item_id;
          const err = errFor(rid, "acta_decomiso_num");
          return { error: !!err, helperText: err ?? "" };
        },
        Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
      },
      {
        accessorKey: "decomiso_kilos_total",
        header: "Kilos decomiso",
        size: 110,
        muiEditTextFieldProps: ({ row }) => {
          const rid = row.original.ruta_item_id;
          const err = errFor(rid, "decomiso_kilos_total");
          return { error: !!err, helperText: err ?? "" };
        },
        Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
      },
      {
        accessorKey: "observaciones_ejecucion",
        header: "Observaciones",
        size: 200,
        muiEditTextFieldProps: ({ row }) => {
          const rid = row.original.ruta_item_id;
          const err = errFor(rid, "observaciones_ejecucion");
          return { error: !!err, helperText: err ?? "", multiline: true, minRows: 2 };
        },
        Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
      },
      {
        accessorKey: "inspectores_texto",
        header: "Inspectores",
        size: 160,
        enableEditing: false,
        Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
      },
      {
        accessorKey: "grupo_nombre",
        header: "Grupo",
        size: 110,
        enableEditing: false,
        Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
      },
      {
        accessorKey: "estado_operativo",
        header: "Estado ítem",
        size: 120,
        enableEditing: false,
        Cell: ({ cell }) => (
          <Chip
            size="small"
            label={dashIfEmpty(cell.getValue())}
            color={estadoChipColor(cell.getValue() as string)}
            variant="outlined"
            sx={{ borderColor: "rgba(255,255,255,0.25)", color: COLORS.white, fontSize: "10px" }}
          />
        ),
      },
      {
        accessorKey: "iniciador_estado",
        header: "Estado iniciador",
        size: 130,
        enableEditing: false,
        Cell: ({ cell }) => (
          <Chip
            size="small"
            label={dashIfEmpty(cell.getValue())}
            color={estadoChipColor(cell.getValue() as string)}
            variant="outlined"
            sx={{ borderColor: "rgba(255,255,255,0.25)", color: COLORS.white, fontSize: "10px" }}
          />
        ),
      },
    ],
    [contraOpts, motivoNotifOpts, motivoCompOpts, rubroOpts, errFor]
  );

  const handleSave: MRT_TableOptions<ICompletarTrabajoPendienteRow>["onEditingRowSave"] = useCallback(
    async ({ values, row, table }) => {
      const rid = row.original.ruta_item_id;
      const key = String(rid);
      setBannerError(null);
      setCellErrorsByRow((prev) => ({ ...prev, [key]: {} }));
      setSaving(true);
      try {
        const body = buildCompletarTrabajoCierreBodyFromInline(
          row.original,
          values as Record<string, unknown>,
          { includeTipoActuacion: false }
        );
        await postCompletarTrabajoCerrar(rid, body);
        table.setEditingRow(null);
        onCierreExitoso();
      } catch (err) {
        const fieldMap = parseCompletarTrabajoFieldErrors(err);
        if (fieldMap && Object.keys(fieldMap).length > 0) {
          setCellErrorsByRow((prev) => ({ ...prev, [key]: fieldMap }));
        } else {
          setBannerError(formatCompletarTrabajoApiError(err));
        }
      } finally {
        setSaving(false);
      }
    },
    [onCierreExitoso]
  );

  const table = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    editDisplayMode: "row",
    enableRowSelection: false,
    enableColumnFilters: false,
    enableGlobalFilter: false,
    enableEditing: Boolean(catalogs),
    muiTablePaperProps: {
      sx: {
        backgroundColor: "transparent",
        boxShadow: "none",
        border: "none",
        borderRadius: 0,
        overflow: "visible",
      },
    },
    muiTableContainerProps: {
      sx: {
        ...((DARK_TABLE_CONFIG.muiTableContainerProps as { sx?: object })?.sx ?? {}),
        maxHeight: "calc(100vh - 280px)",
      },
    },
    muiTableHeadCellProps: {
      sx: {
        ...((DARK_TABLE_CONFIG.muiTableHeadCellProps as { sx?: object })?.sx ?? {}),
        textTransform: "uppercase",
        fontSize: "10px",
        letterSpacing: "0.06em",
        color: "rgba(255,255,255,0.6)",
      },
    },
    columns,
    data: rows,
    getRowId: (r) => String(r.ruta_item_id),
    enableRowActions: true,
    positionActionsColumn: "first",
    manualPagination: true,
    rowCount: total,
    onEditingRowSave: handleSave,
    onEditingRowCancel: ({ row }) => {
      setBannerError(null);
      setCellErrorsByRow((prev) => {
        const next = { ...prev };
        delete next[String(row.original.ruta_item_id)];
        return next;
      });
    },
    state: {
      pagination,
      isLoading: loading,
      isSaving: saving,
      showAlertBanner: Boolean(bannerError),
    },
    muiToolbarAlertBannerProps: bannerError
      ? {
          color: "error",
          children: bannerError,
        }
      : undefined,
    onPaginationChange: (updaterOrValue) => {
      const next =
        typeof updaterOrValue === "function" ? updaterOrValue(pagination) : updaterOrValue;
      if (next.pageIndex !== pagination.pageIndex) onPageChange(next.pageIndex + 1);
      if (next.pageSize !== pagination.pageSize) onPerPageChange(next.pageSize);
    },
    initialState: {
      density: "compact",
    },
    renderRowActions: ({ row, table }) => (
      <Box sx={{ display: "flex", gap: "0.35rem", alignItems: "center" }}>
        <Tooltip title="Editar fila y guardar cierre">
          <IconButton
            size="small"
            disabled={loading || !catalogs}
            sx={{
              color: COLORS.white,
              "&:hover": { color: GLASS_COLORS.primary, backgroundColor: "rgba(1, 102, 255, 0.15)" },
              "&.Mui-disabled": { color: "#555" },
            }}
            onClick={() => {
              setBannerError(null);
              table.setEditingRow(row);
            }}
            aria-label="Editar"
          >
            <EditIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>
    ),
  });

  return (
    <Box sx={{ position: "relative", display: "flex", flexDirection: "column", gap: 1 }}>
      <Box sx={{ position: "relative" }}>
        {loading && (
          <Box
            sx={{
              position: "absolute",
              inset: 0,
              zIndex: 2,
              bgcolor: "rgba(0, 0, 0, 0.45)",
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
              alignItems: "center",
              gap: 1,
              borderRadius: "12px",
            }}
          >
            <CircularProgress size={28} sx={{ color: COLORS.primary }} />
            <Typography
              variant="body2"
              sx={{ fontFamily: '"Tactic Sans", sans-serif', color: "rgba(255,255,255,0.75)" }}
            >
              Cargando trabajos…
            </Typography>
          </Box>
        )}
        <MaterialReactTable table={table} />
      </Box>
      <Typography
        variant="caption"
        sx={{
          fontFamily: '"Tactic Sans", sans-serif',
          color: "rgba(255,255,255,0.55)",
          display: "block",
        }}
      >
        Editá la fila con el lápiz: contraproducencia vacía = visita realizada (permitís actas). Con contraproducencia no se
        envían actas. El tipo de actuación se confirma aparte (formulario de tipo).
      </Typography>
    </Box>
  );
}
