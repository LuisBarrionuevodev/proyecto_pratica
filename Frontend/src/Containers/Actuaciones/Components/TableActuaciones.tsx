import { Alert, Box, Typography, IconButton, Tooltip } from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import VisibilityIcon from "@mui/icons-material/Visibility";
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
  type MRT_Row,
} from "material-react-table";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import { deleteActuacion } from "../../../api/actuacionesApi";
import {
  fetchInspectores,
  fetchMotivos,
  fetchRubros,
  fetchTiposActuacion,
  fetchContraproducencias,
  fetchMotivosComprobacion,
} from "../../../api/gridApi";
import { TablaExportButtons } from "./TableButtons";
import { GridLegend } from "./GridLegend";
import { AnimatedTable, useTableRefresh } from "../../../animations";
import { ActuacionDetalleDialog } from "./ActuacionDetalleDialog";

import {
  loadingStyles,
  DARK_TABLE_CONFIG,
  COLORS,
} from "../styles/actuacionesTableStyles";

import { ConfirmDialog } from "../../../ui";
import { submitActuacionRow } from "../utils/submitActuacionRow";

/** Referencia estable: `= []` en props default crea un array nuevo cada render y rompe el memo de columnas / MRT. */
const EMPTY_EXTRA_COLUMNS: MRT_ColumnDef<IActuacionListItem>[] = [];
const EMPTY_READ_ONLY_COLUMNS: string[] = [];

interface TablaActuacionesProps {
  data?: IActuacionListItem[];
  loading?: boolean;
  onRefresh?: () => void;
  initialColumnVisibility?: Record<string, boolean>;
  enableEditing?: boolean;
  hideRowActions?: boolean;
  hideDeleteAction?: boolean;
  skipValidation?: boolean;
  skipUpdate?: boolean;
  numeroHeader?: string;
  numeroEditorLabel?: string;
  extraColumns?: MRT_ColumnDef<IActuacionListItem>[];
  onBeforeSave?: (fullRow: IActuacionListItem) => Promise<void>;
  onAfterSave?: (fullRow: IActuacionListItem) => Promise<void>;
  readOnlyColumns?: string[];
  numeroCallesOptions?: string[];
  numeroAllowFreeSolo?: boolean;
}

const TablaActuaciones = ({
  data: externalData,
  loading: externalLoading,
  onRefresh,
  initialColumnVisibility,
  enableEditing = true,
  hideRowActions = false,
  hideDeleteAction = false,
  skipValidation = false,
  skipUpdate = false,
  numeroHeader = "Número",
  numeroEditorLabel = "Número",
  extraColumns = EMPTY_EXTRA_COLUMNS,
  onBeforeSave,
  onAfterSave,
  readOnlyColumns = EMPTY_READ_ONLY_COLUMNS,
  numeroCallesOptions,
  numeroAllowFreeSolo = false,
}: TablaActuacionesProps) => {
  const [data, setData] = useState<IActuacionListItem[]>(externalData || []);
  const loading = externalLoading || false;

  const { isRefreshing, triggerRefresh } = useTableRefresh();

  /** Un solo setState tras cargar catálogos evita 6 re-renders en serie al montar. */
  const [catalogBundle, setCatalogBundle] = useState<{
    inspectores: string[];
    motivos: string[];
    rubros: string[];
    tipos: string[];
    contras: string[];
    motivosComprobacion: string[];
  } | null>(null);
  // ✅ errores por celda por idActuacion
  const [rowErrors, setRowErrors] = useState<Record<number, Record<string, string>>>({});
  /** Actuación pendiente de confirmar borrado en `ConfirmDialog` (solo si no `hideDeleteAction`). */
  const [deleteConfirmActuacionId, setDeleteConfirmActuacionId] = useState<number | null>(null);
  const [deleteInProgress, setDeleteInProgress] = useState(false);
  /** Fila abierta en modal de detalle/edición; la tabla es solo lectura. */
  const [editDraft, setEditDraft] = useState<IActuacionListItem | null>(null);
  const [editSaving, setEditSaving] = useState(false);

  useEffect(() => {
    if (externalData) setData(externalData);
  }, [externalData]);

  useEffect(() => {
    let cancelled = false;
    const loadCatalogs = async () => {
      try {
        const [inspectores, motivos, rubros, tipos, contras, motivosComp] = await Promise.all([
          fetchInspectores(),
          fetchMotivos(),
          fetchRubros(),
          fetchTiposActuacion(),
          fetchContraproducencias(),
          fetchMotivosComprobacion(),
        ]);
        if (cancelled) return;
        setCatalogBundle({
          inspectores: [...new Set(inspectores.items.map((i: any) => i.nombre))],
          motivos: [...new Set(motivos.items.map((m: any) => m.nombre))],
          rubros: [...new Set(rubros.items.map((r: any) => r.nombre))],
          tipos: [...new Set(tipos.items.map((t: any) => t.nombre))],
          contras: [...new Set(contras.items.map((c: any) => c.nombre))],
          motivosComprobacion: [...new Set(motivosComp.items.map((m: any) => m.nombre))],
        });
      } catch (error) {
        console.error("Error cargando catálogos:", error);
      }
    };
    void loadCatalogs();
    return () => {
      cancelled = true;
    };
  }, []);

  // Catálogos combinados (reusa helper del grid)
  const hasBloqueoExpediente = useMemo(
    () =>
      data.some(
        (r) => r.notificacion_editable === false || r.comprobacion_editable === false
      ),
    [data]
  );

  const catalogs = useMemo(
    () => ({
      inspectores: catalogBundle?.inspectores ?? [],
      motivos: catalogBundle?.motivos ?? [],
      rubros: catalogBundle?.rubros ?? [],
      tipos: catalogBundle?.tipos ?? [],
      contraproducencias: catalogBundle?.contras ?? [],
      motivosComprobacion: catalogBundle?.motivosComprobacion ?? [],
    }),
    [catalogBundle]
  );

  const performDeleteRow = useCallback(
    async (id: number) => {
      const prev = [...data];
      setDeleteInProgress(true);
      setData((prevData) => prevData.filter((item) => item.id !== id));

      try {
        await deleteActuacion(id);
        onRefresh?.();
      } catch (error) {
        console.error("Error al eliminar:", error);
        alert("No se pudo eliminar el registro. Se restaurará la lista.");
        setData(prev);
      } finally {
        setDeleteInProgress(false);
      }
    },
    [data, onRefresh]
  );

  const handleEditDraftChange = useCallback((patch: Partial<IActuacionListItem>) => {
    setEditDraft((prev) => (prev ? { ...prev, ...patch } : null));
  }, []);

  const handleCloseEditDialog = useCallback(() => {
    setEditDraft(null);
  }, []);

  const handleDialogSave = useCallback(async () => {
    if (!editDraft) return;
    const id = Number(editDraft.id);
    setEditSaving(true);
    try {
      const result = await submitActuacionRow({
        id,
        fullRow: editDraft,
        skipValidation,
        skipUpdate,
        onBeforeSave,
        onAfterSave,
        onValidationPassed: () => {
          setRowErrors((prev) => ({ ...prev, [id]: {} }));
        },
      });

      if (!result.ok) {
        if (result.kind === "validation" || result.kind === "backend_fields") {
          setRowErrors((prev) => ({ ...prev, [id]: result.fieldErrors }));
          return;
        }
        alert(result.message);
        return;
      }

      setEditDraft(null);
      triggerRefresh();
      setTimeout(() => onRefresh?.(), 100);
    } finally {
      setEditSaving(false);
    }
  }, [
    editDraft,
    onRefresh,
    triggerRefresh,
    onBeforeSave,
    onAfterSave,
    skipValidation,
    skipUpdate,
  ]);

  const columns = useMemo<MRT_ColumnDef<IActuacionListItem>[]>(() => {
    const baseColumns: MRT_ColumnDef<IActuacionListItem>[] = [
      { accessorKey: "id", header: "ID", enableHiding: true, size: 80 },

      { accessorKey: "orden_trabajo_numero", header: "OT", size: 100 },
      { accessorKey: "fecha_actuacion", header: "Fecha", size: 120 },
      { accessorKey: "tipo_actuacion", header: "Tipo", size: 180 },
      { accessorKey: "contraproducencia", header: "Contraproducencia", size: 180 },
      { accessorKey: "rubro_nombre", header: "Rubro", size: 200 },

      { accessorKey: "inspector1", header: "Inspector 1", size: 150 },
      { accessorKey: "inspector2", header: "Inspector 2", size: 150 },
      { accessorKey: "inspector3", header: "Inspector 3", size: 150 },

      {
        accessorKey: "calle",
        header: "Calle",
        size: 200,
        Cell: ({ row }) => {
          if (row.original.calle_estado === "OK" && row.original.calle_normalizada) {
            return row.original.calle_normalizada;
          }
          return row.original.calle ?? "";
        },
      },
      {
        accessorKey: "numero",
        header: numeroHeader,
        size: 400,
        Cell: ({ row }) => {
          if (
            row.original.numero_tipo === "ESQUINA" &&
            (row.original.numero_esquina || row.original.esquina_normalizada)
          ) {
            return row.original.numero_esquina || row.original.esquina_normalizada || "";
          }
          return row.original.numero ?? "";
        },
      },

      { accessorKey: "doc_nro", header: "Doc. Nro", size: 120 },
      { accessorKey: "contrib_apellido", header: "Contribuyente Apellido", size: 180 },
      { accessorKey: "contrib_nombre", header: "Contribuyente Nombre", size: 180 },

      { accessorKey: "acta_inspeccion_num", header: "Acta Inspección", size: 150 },
      { accessorKey: "acta_notificacion_num", header: "Acta Notificación", size: 150 },
      { accessorKey: "notificacion_motivo_1", header: "Motivo Notif. 1", size: 180 },
      { accessorKey: "notificacion_motivo_2", header: "Motivo Notif. 2", size: 180 },
      { accessorKey: "notificacion_motivo_3", header: "Motivo Notif. 3", size: 180 },

      { accessorKey: "acta_comprobacion_num", header: "Acta Comprobación", size: 150 },
      { accessorKey: "comprobacion_motivo", header: "Motivo Comprob.", size: 180 },

      { accessorKey: "acta_clausura_num", header: "Acta Clausura", size: 150 },
      { accessorKey: "acta_decomiso_num", header: "Acta Decomiso", size: 150 },
      { accessorKey: "decomiso_kilos_total", header: "Kilos Decomisados", size: 150 },

      { accessorKey: "expediente_numero", header: "Expediente Nro", size: 150 },
      { accessorKey: "expediente_anio", header: "Expediente Año", size: 120 },

      { accessorKey: "oficio_numero", header: "Oficio Nro", size: 120 },
      { accessorKey: "oficio_anio", header: "Oficio Año", size: 120 },
      { accessorKey: "oficio_causa", header: "Oficio Causa", size: 180 },
    ];
    return [...baseColumns, ...extraColumns];
  }, [extraColumns, numeroHeader]);

  const columnOrder = useMemo(() => ([
    "mrt-row-select",
    ...(hideRowActions ? [] : ["mrt-row-actions"]),
    ...columns.map((col) => col.accessorKey as string),
  ]), [columns, hideRowActions]);

  /** Objeto estable: un `initialState` nuevo cada render puede hacer que MRT re-sincronice estado interno sin fin. */
  const tableInitialState = useMemo(
    () => ({
      columnOrder,
      columnVisibility: {
        id: false,
        inspector2: false,
        inspector3: false,
        doc_nro: false,
        contrib_apellido: false,
        contrib_nombre: false,
        notificacion_motivo_2: false,
        notificacion_motivo_3: false,
        comprobacion_motivo: false,
        acta_clausura_num: false,
        acta_decomiso_num: false,
        decomiso_kilos_total: false,
        expediente_numero: false,
        expediente_anio: false,
        oficio_numero: false,
        oficio_anio: false,
        oficio_causa: false,
        ...initialColumnVisibility,
      },
      density: "compact" as const,
    }),
    [columnOrder, initialColumnVisibility]
  );

  /**
   * El override de `muiTableBodyCellProps` debe componerse con el de `DARK_TABLE_CONFIG`;
   * si no, las celdas sin error pierden zebra, bordes y tipografía (layout “roto”).
   */
  const baseMuiTableBodyCellProps = DARK_TABLE_CONFIG.muiTableBodyCellProps;

  const muiTableBodyCellPropsMerged = useCallback(
    ({ row, column }: { row: MRT_Row<IActuacionListItem>; column: { id?: string } }) => {
      const base =
        typeof baseMuiTableBodyCellProps === "function"
          ? baseMuiTableBodyCellProps({ row } as Parameters<typeof baseMuiTableBodyCellProps>[0])
          : {};
      const rid = Number(row.original.id);
      const err = rowErrors[rid]?.[String(column.id)];
      if (!err) return base;
      const prev = base as { sx?: Record<string, unknown> };
      const sx = prev.sx;
      const mergedSx =
        sx && typeof sx === "object" && !Array.isArray(sx)
          ? { ...sx, backgroundColor: "rgba(255, 68, 68, 0.15)" }
          : { backgroundColor: "rgba(255, 68, 68, 0.15)" };
      return { ...base, sx: mergedSx };
    },
    [rowErrors]
  );

  const renderRowActionsCb = useCallback(
    ({ row }: { row: MRT_Row<IActuacionListItem> }) => (
      <Box sx={{ display: "flex", gap: "0.5rem" }}>
        <Tooltip title="Ver detalle">
          <IconButton
            sx={{
              color: COLORS.white,
              transition: "color 0.2s ease, background-color 0.2s ease",
              "&:hover": { color: COLORS.primary, backgroundColor: "rgba(1, 102, 255, 0.15)" },
            }}
            onClick={() => setEditDraft({ ...row.original })}
          >
            <VisibilityIcon />
          </IconButton>
        </Tooltip>

        {!hideDeleteAction && (
          <Tooltip title="Eliminar">
            <IconButton
              sx={{
                color: COLORS.white,
                transition: "color 0.2s ease, background-color 0.2s ease",
                "&:hover": { color: "#ff4444", backgroundColor: "rgba(255, 68, 68, 0.15)" },
              }}
              onClick={() => setDeleteConfirmActuacionId(Number(row.original.id))}
            >
              <DeleteIcon />
            </IconButton>
          </Tooltip>
        )}
      </Box>
    ),
    [hideDeleteAction]
  );

  const renderTopToolbarCustomActionsCb = useCallback(
    ({ table }: { table: Parameters<typeof TablaExportButtons>[0]["table"] }) => (
      <TablaExportButtons table={table} filePrefix="actuaciones" />
    ),
    []
  );

  const table = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    columns,
    data,
    /** La grilla es solo lectura; `enableEditing` (prop) solo habilita el botón y el diálogo. */
    enableEditing: false,
    enableSorting: true,
    enableColumnFilters: true,
    enableGlobalFilter: true,
    enableRowActions: !hideRowActions,
    // Acciones al inicio (después del checkbox de selección)
    positionActionsColumn: "first",
    enableHiding: true,

    muiTableBodyCellProps: muiTableBodyCellPropsMerged,

    initialState: tableInitialState,

    renderRowActions: hideRowActions ? undefined : renderRowActionsCb,

    renderTopToolbarCustomActions: renderTopToolbarCustomActionsCb,
  });

  if (loading) {
    return (
      <Box sx={{ padding: "40px", textAlign: "center" }}>
        <Typography sx={loadingStyles}>Cargando actuaciones...</Typography>
      </Box>
    );
  }

  return (
    <Box>
      {hasBloqueoExpediente && (
        <Alert severity="info" sx={{ mb: 1.5 }} variant="outlined">
          Hay actuaciones con notificación o comprobación bloqueadas: ya tienen expediente asociado.
          Esos campos no se pueden editar desde esta vista (el servidor también rechaza el cambio).
        </Alert>
      )}
      <AnimatedTable isRefreshing={isRefreshing}>
        <MaterialReactTable table={table} />
      </AnimatedTable>
      <GridLegend />

      {editDraft && (
        <ActuacionDetalleDialog
          open
          draft={editDraft}
          fieldErrors={rowErrors[editDraft.id] ?? {}}
          saving={editSaving}
          catalogs={catalogs}
          readOnlyColumns={readOnlyColumns}
          numeroCallesOptions={numeroCallesOptions}
          numeroEditorLabel={numeroEditorLabel}
          numeroAllowFreeSolo={numeroAllowFreeSolo}
          canEdit={enableEditing}
          onClose={handleCloseEditDialog}
          onDraftChange={handleEditDraftChange}
          onSave={handleDialogSave}
        />
      )}

      <ConfirmDialog
        open={deleteConfirmActuacionId !== null}
        onClose={() => setDeleteConfirmActuacionId(null)}
        onConfirm={async () => {
          if (deleteConfirmActuacionId == null) return;
          const id = deleteConfirmActuacionId;
          try {
            await performDeleteRow(id);
          } finally {
            setDeleteConfirmActuacionId(null);
          }
        }}
        title="Eliminar actuación"
        destructive
        loading={deleteInProgress}
        confirmLabel="Eliminar"
      >
        ¿Estás seguro de eliminar este registro? Esta acción no se puede deshacer desde esta vista.
      </ConfirmDialog>
    </Box>
  );
};

export default TablaActuaciones;
