import { Alert, Box, IconButton, Tooltip } from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
} from "material-react-table";
import type { IRelevamientoListItem } from "../../../api/relevamientosListApi";
import { deleteRelevamiento } from "../../../api/relevamientosApi";
import { startBatch, fetchInspectores } from "../../../api/gridApi";
import {
  fetchRubrosCatalogoCached,
  rubroItemsToNombres,
} from "../../../utils/rubrosCatalogCache";
import { submitRelevamientoRow } from "../utils/submitRelevamientoRow";
import { RelevamientoEditDialog } from "./RelevamientoEditDialog";
import { TablaExportButtons } from "../../Actuaciones/Components/TableButtons";
import {
  BandejaEllipsisCell,
  BANDEJA_MRT_BODY_CELL_PROPS,
  BANDEJA_MRT_READ_ONLY_TABLE_PROPS,
} from "../../Actuaciones/Components/bandejaTableCells";
import { DataTableMrtShell } from "../../../components/dataTable/DataTableMrtShell";
import { mergeMrtBodyCellPropsWithActuacionesPreset } from "../../../styles/mrtGlassDataTablePreset";
import { ConfirmDialog } from "../../../ui";
import { useAppFeedback } from "../../../components/feedback";
import { mergeLegacyRubroNames } from "../../../utils/rubrosCatalogCache";
import { shouldRefreshRelevamientosAfterSaveFailure } from "../utils/refreshOnSavePolicy";
import {
  DARK_TABLE_CONFIG,
  COLORS,
} from "../../Actuaciones/styles/actuacionesTableStyles";

function relevamientoCellText(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

interface TablaRelevamientosProps {
  data?: IRelevamientoListItem[];
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
  extraColumns?: MRT_ColumnDef<IRelevamientoListItem>[];
  onBeforeSave?: (fullRow: IRelevamientoListItem) => Promise<void>;
  onAfterSave?: (fullRow: IRelevamientoListItem) => Promise<void>;
  readOnlyColumns?: string[];
  numeroCallesOptions?: string[];
  numeroAllowFreeSolo?: boolean;
}

const TablaRelevamientos = ({
  data: externalData,
  loading: externalLoading,
  onRefresh,
  initialColumnVisibility,
  enableEditing = true,
  hideRowActions = false,
  hideDeleteAction = false,
  skipValidation = false,
  skipUpdate = false,
  numeroHeader = "Numero",
  numeroEditorLabel = "Número",
  extraColumns = [],
  onBeforeSave,
  onAfterSave,
  readOnlyColumns = [],
  numeroCallesOptions,
  numeroAllowFreeSolo = false,
}: TablaRelevamientosProps) => {
  const feedback = useAppFeedback();
  const [data, setData] = useState<IRelevamientoListItem[]>(externalData || []);
  const loading = externalLoading || false;
  const [rowErrors, setRowErrors] = useState<Record<number, Record<string, string>>>({});
  const [batchId, setBatchId] = useState<string | null>(null);
  const [catalogInspectores, setCatalogInspectores] = useState<string[]>([]);
  const [catalogRubros, setCatalogRubros] = useState<string[]>([]);
  const [editDraft, setEditDraft] = useState<IRelevamientoListItem | null>(null);
  const [editSaving, setEditSaving] = useState(false);
  const [editGlobalError, setEditGlobalError] = useState<string | null>(null);
  const [deleteConfirmRow, setDeleteConfirmRow] = useState<IRelevamientoListItem | null>(null);
  const [deleteInProgress, setDeleteInProgress] = useState(false);
  useEffect(() => {
    if (externalData) setData(externalData);
  }, [externalData]);

  useEffect(() => {
    const ensureBatch = async () => {
      try {
        const resp = await startBatch("relevamientos");
        setBatchId(resp.batch_id);
      } catch (error) {
        console.error("Error iniciando batch:", error);
      }
    };
    ensureBatch();
  }, []);

  useEffect(() => {
    const loadCatalogs = async () => {
      try {
        const [inspectores, rubrosItems] = await Promise.all([fetchInspectores(), fetchRubrosCatalogoCached()]);
        setCatalogInspectores([...new Set(inspectores.items.map((i: any) => i.nombre))]);
        setCatalogRubros(rubroItemsToNombres(rubrosItems));
      } catch (error) {
        console.error("Error cargando catálogos:", error);
      }
    };
    loadCatalogs();
  }, []);

  const requestDeleteRow = useCallback(
    (rowItem: IRelevamientoListItem) => {
      if (rowItem.editable === false) {
        feedback.error("Este relevamiento ya no está operativo y no puede eliminarse.");
        return;
      }
      setDeleteConfirmRow(rowItem);
    },
    [onRefresh, feedback]
  );

  const performDeleteRow = useCallback(async () => {
    if (!deleteConfirmRow) return;
    const id = Number(deleteConfirmRow.id);
    const prev = [...data];
    setDeleteInProgress(true);
    setData((prevData) => prevData.filter((item) => item.id !== id));
    try {
      await deleteRelevamiento(id);
      onRefresh?.();
    } catch (error: unknown) {
      console.error("Error al eliminar:", error);
      const err = error as { response?: { data?: { detail?: string } } };
      const msg =
        err?.response?.data?.detail || "No se pudo eliminar el registro. Se restaurará la lista.";
      feedback.error(msg);
      setData(prev);
      onRefresh?.();
    } finally {
      setDeleteInProgress(false);
      setDeleteConfirmRow(null);
    }
  }, [data, deleteConfirmRow, onRefresh, feedback]);

  const catalogs = useMemo(
    () => ({
      inspectores: catalogInspectores,
      rubros: mergeLegacyRubroNames(catalogRubros, editDraft?.rubro),
    }),
    [catalogInspectores, catalogRubros, editDraft?.rubro]
  );

  const handleDialogSave = useCallback(async () => {
    if (!editDraft) return;
    const id = Number(editDraft.id);
    const fullRow = editDraft;
    if (fullRow.editable === false) {
      feedback.error("Este relevamiento ya no está operativo y no puede editarse.");
      return;
    }

    setEditGlobalError(null);
    setEditSaving(true);
    try {
      const result = await submitRelevamientoRow({
        id,
        fullRow,
        batchId,
        skipValidation,
        skipUpdate,
        onBeforeSave,
        onAfterSave,
        onBeforePersist: () => {
          setRowErrors((prev) => ({ ...prev, [id]: {} }));
        },
      });

      if (!result.ok) {
        if (result.kind === "validation" || result.kind === "backend_fields") {
          setRowErrors((prev) => ({ ...prev, [id]: result.fieldErrors }));
          setEditGlobalError(null);
          return;
        }
        setEditGlobalError(result.message);
        feedback.error(result.message);
        return;
      }

      setEditDraft(null);
      setEditGlobalError(null);
      if (shouldRefreshRelevamientosAfterSaveFailure(result)) {
        onRefresh?.();
      }
    } finally {
      setEditSaving(false);
    }
  }, [
    editDraft,
    batchId,
    onRefresh,
    onBeforeSave,
    onAfterSave,
    skipValidation,
    skipUpdate,
    feedback,
  ]);

  const columns = useMemo<MRT_ColumnDef<IRelevamientoListItem>[]>(() => {
    const baseColumns: MRT_ColumnDef<IRelevamientoListItem>[] = [
      { accessorKey: "id", header: "ID", enableHiding: true, size: 80 },
      {
        accessorKey: "fecha",
        header: "Fecha",
        size: 120,
        Cell: ({ cell }) => <BandejaEllipsisCell value={relevamientoCellText(cell.getValue())} />,
      },
      {
        accessorKey: "inspector",
        header: "Inspector",
        size: 200,
        Cell: ({ cell }) => <BandejaEllipsisCell value={relevamientoCellText(cell.getValue())} />,
      },
      {
        accessorKey: "calle",
        header: "Calle",
        size: 200,
        Cell: ({ row }) => {
          if (row.original.calle_estado === "OK" && row.original.calle_normalizada) {
            return <BandejaEllipsisCell value={row.original.calle_normalizada} />;
          }
          return <BandejaEllipsisCell value={relevamientoCellText(row.original.calle)} />;
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
            return (
              <BandejaEllipsisCell
                value={relevamientoCellText(
                  row.original.numero_esquina || row.original.esquina_normalizada
                )}
              />
            );
          }
          return <BandejaEllipsisCell value={relevamientoCellText(row.original.numero)} />;
        },
      },
      {
        accessorKey: "rubro",
        header: "Rubro",
        size: 180,
        Cell: ({ cell }) => <BandejaEllipsisCell value={relevamientoCellText(cell.getValue())} />,
      },
      {
        accessorKey: "turno",
        header: "Turno",
        size: 130,
        Cell: ({ cell }) => <BandejaEllipsisCell value={relevamientoCellText(cell.getValue())} />,
      },
      {
        accessorKey: "esta_abierto",
        header: "Está abierto",
        size: 130,
        Cell: ({ cell }) => {
          const v = cell.getValue() as boolean | string | null | undefined;
          if (v === true || v === "Sí") return <BandejaEllipsisCell value="Sí" />;
          if (v === false || v === "No") return <BandejaEllipsisCell value="No" />;
          return <BandejaEllipsisCell value="—" />;
        },
      },
    ];
    return [...baseColumns, ...extraColumns];
  }, [extraColumns, numeroHeader]);

  const columnOrder = useMemo(() => ([
    ...(hideRowActions ? [] : ["mrt-row-actions"]),
    ...columns.map((col) => col.accessorKey as string),
  ]), [columns, hideRowActions]);

  const muiTableBodyCellPropsMerged = useMemo(
    () =>
      mergeMrtBodyCellPropsWithActuacionesPreset(BANDEJA_MRT_BODY_CELL_PROPS.muiTableBodyCellProps, ({ row, column }) => {
        const rid = Number((row.original as IRelevamientoListItem).id);
        const err = rowErrors[rid]?.[String(column.id)];
        if (!err) return;
        return { sx: { backgroundColor: "rgba(255, 68, 68, 0.15)" } };
      }),
    [rowErrors]
  );

  const table = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    ...BANDEJA_MRT_READ_ONLY_TABLE_PROPS,
    columns,
    data,
    /** La grilla es solo lectura; la prop `enableEditing` habilita el botón y el diálogo. */
    enableEditing: false,
    enableSorting: true,
    enableColumnFilters: true,
    enableGlobalFilter: true,
    enableRowActions: !hideRowActions,
    positionActionsColumn: "first",
    enableHiding: true,
    muiTableBodyCellProps: muiTableBodyCellPropsMerged,
    initialState: {
      columnOrder,
      density: "compact",
      columnVisibility: {
        id: false,
        rubro: true,
        ...initialColumnVisibility,
      },
    },
    state: {
      isLoading: loading,
      showProgressBars: loading,
    },
    renderRowActions: hideRowActions ? undefined : ({ row }) => (
      <Box sx={{ display: "flex", gap: "0.5rem" }}>
        {enableEditing && (
          <Tooltip title={row.original.editable === false ? "No editable (fuera de gestión operativa)" : "Editar"}>
            <IconButton
              sx={{
                color: COLORS.white,
                transition: "color 0.2s ease, background-color 0.2s ease",
                "&:hover": { color: COLORS.primary, backgroundColor: "rgba(1, 102, 255, 0.15)" },
              }}
              disabled={row.original.editable === false}
              onClick={() => setEditDraft({ ...row.original })}
            >
              <EditIcon />
            </IconButton>
          </Tooltip>
        )}
        {!hideDeleteAction && (
          <Tooltip title={row.original.editable === false ? "No eliminable (fuera de gestión operativa)" : "Eliminar"}>
            <IconButton
              sx={{
                color: COLORS.white,
                transition: "color 0.2s ease, background-color 0.2s ease",
                "&:hover": { color: "#ff4444", backgroundColor: "rgba(255, 68, 68, 0.15)" },
              }}
              disabled={row.original.editable === false}
              onClick={() => requestDeleteRow(row.original)}
            >
              <DeleteIcon />
            </IconButton>
          </Tooltip>
        )}
      </Box>
    ),
    renderTopToolbarCustomActions: ({ table }) => (
      <TablaExportButtons table={table} filePrefix="relevamientos" />
    ),
  });

  return (
    <Box>
      <DataTableMrtShell loading={loading} loadingMode="progress">
        <MaterialReactTable table={table} />
      </DataTableMrtShell>

      {editDraft && (
        <RelevamientoEditDialog
          open
          draft={editDraft}
          fieldErrors={rowErrors[editDraft.id] ?? {}}
          saving={editSaving}
          catalogs={catalogs}
          readOnlyColumns={readOnlyColumns}
          numeroCallesOptions={numeroCallesOptions}
          numeroEditorLabel={numeroEditorLabel}
          numeroAllowFreeSolo={numeroAllowFreeSolo}
          onClose={() => {
            setEditDraft(null);
            setEditGlobalError(null);
          }}
          onDraftChange={(patch) => {
            setEditGlobalError(null);
            setEditDraft((prev) => (prev ? { ...prev, ...patch } : null));
          }}
          globalError={editGlobalError}
          onSave={handleDialogSave}
        />
      )}

      <ConfirmDialog
        open={deleteConfirmRow !== null}
        onClose={() => setDeleteConfirmRow(null)}
        onConfirm={performDeleteRow}
        title="Eliminar relevamiento"
        destructive
        loading={deleteInProgress}
        confirmLabel="Eliminar"
      >
        Esta acción quitará el relevamiento del listado. No se podrá deshacer desde esta vista.
      </ConfirmDialog>
    </Box>
  );
};

export default TablaRelevamientos;
