import { Box, Typography, IconButton, Tooltip } from "@mui/material";
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
import { startBatch, fetchInspectores, fetchRubros } from "../../../api/gridApi";
import { submitRelevamientoRow } from "../utils/submitRelevamientoRow";
import { RelevamientoEditDialog } from "./RelevamientoEditDialog";
import { TablaExportButtons } from "../../Actuaciones/Components/TableButtons";
import {
  loadingStyles,
  DARK_TABLE_CONFIG,
  COLORS,
} from "../../Actuaciones/styles/actuacionesTableStyles";

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
  const [data, setData] = useState<IRelevamientoListItem[]>(externalData || []);
  const loading = externalLoading || false;
  const [rowErrors, setRowErrors] = useState<Record<number, Record<string, string>>>({});
  const [batchId, setBatchId] = useState<string | null>(null);
  const [catalogInspectores, setCatalogInspectores] = useState<string[]>([]);
  const [catalogRubros, setCatalogRubros] = useState<string[]>([]);
  const [editDraft, setEditDraft] = useState<IRelevamientoListItem | null>(null);
  const [editSaving, setEditSaving] = useState(false);
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
        const [inspectores, rubros] = await Promise.all([fetchInspectores(), fetchRubros()]);
        setCatalogInspectores([...new Set(inspectores.items.map((i: any) => i.nombre))]);
        setCatalogRubros([...new Set(rubros.items.map((r: any) => r.nombre))]);
      } catch (error) {
        console.error("Error cargando catálogos:", error);
      }
    };
    loadCatalogs();
  }, []);

  const handleDeleteRow = useCallback(async (rowItem: IRelevamientoListItem) => {
    const id = Number(rowItem.id);
    if (rowItem.editable === false) {
      alert("Este relevamiento ya no está operativo y no puede eliminarse.");
      onRefresh?.();
      return;
    }
    if (!window.confirm("¿Estás seguro de eliminar este registro?")) return;
    const prev = [...data];
    setData((prevData) => prevData.filter((item) => item.id !== id));
    try {
      await deleteRelevamiento(id);
      onRefresh?.();
    } catch (error: any) {
      console.error("Error al eliminar:", error);
      const msg = error?.response?.data?.detail || "No se pudo eliminar el registro. Se restaurará la lista.";
      alert(msg);
      setData(prev);
      onRefresh?.();
    }
  }, [data, onRefresh]);

  const catalogs = useMemo(
    () => ({ inspectores: catalogInspectores, rubros: catalogRubros }),
    [catalogInspectores, catalogRubros]
  );

  const handleDialogSave = useCallback(async () => {
    if (!editDraft) return;
    const id = Number(editDraft.id);
    const fullRow = editDraft;
    if (fullRow.editable === false) {
      alert("Este relevamiento ya no está operativo y no puede editarse.");
      onRefresh?.();
      return;
    }

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
          return;
        }
        alert(result.message);
        onRefresh?.();
        return;
      }

      setEditDraft(null);
      onRefresh?.();
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
  ]);

  const columns = useMemo<MRT_ColumnDef<IRelevamientoListItem>[]>(() => {
    const baseColumns: MRT_ColumnDef<IRelevamientoListItem>[] = [
      { accessorKey: "id", header: "ID", enableHiding: true, size: 80 },
      { accessorKey: "fecha", header: "Fecha", size: 120 },
      { accessorKey: "inspector", header: "Inspector", size: 200 },
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
      { accessorKey: "rubro", header: "Rubro", size: 180 },
      {
        accessorKey: "turno",
        header: "Turno",
        size: 130,
        Cell: ({ cell }) => {
          const v = cell.getValue() as string | null | undefined;
          return v || "—";
        },
      },
      {
        accessorKey: "esta_abierto",
        header: "Está abierto",
        size: 130,
        Cell: ({ cell }) => {
          const v = cell.getValue() as boolean | string | null | undefined;
          if (v === true || v === "Sí") return "Sí";
          if (v === false || v === "No") return "No";
          return "—";
        },
      },
    ];
    return [...baseColumns, ...extraColumns];
  }, [extraColumns, numeroHeader]);

  const columnOrder = useMemo(() => ([
    ...(hideRowActions ? [] : ["mrt-row-actions"]),
    ...columns.map((col) => col.accessorKey as string),
  ]), [columns, hideRowActions]);

  const table = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
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
    muiTableBodyCellProps: ({ row, column }) => {
      const rid = Number(row.original.id);
      const err = rowErrors[rid]?.[column.id];
      return err ? { sx: { backgroundColor: "rgba(255, 68, 68, 0.15)" } } : {};
    },
    initialState: {
      columnOrder,
      density: "compact",
      columnVisibility: {
        id: false,
        rubro: true,
        ...initialColumnVisibility,
      },
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
              onClick={() => handleDeleteRow(row.original)}
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

  if (loading) {
    return (
      <Box sx={{ padding: "40px", textAlign: "center" }}>
        <Typography sx={loadingStyles}>Cargando relevamientos...</Typography>
      </Box>
    );
  }

  return (
    <Box>
      <MaterialReactTable table={table} />

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
          onClose={() => setEditDraft(null)}
          onDraftChange={(patch) =>
            setEditDraft((prev) => (prev ? { ...prev, ...patch } : null))
          }
          onSave={handleDialogSave}
        />
      )}
    </Box>
  );
};

export default TablaRelevamientos;
