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
import { updateRelevamiento, deleteRelevamiento } from "../../../api/relevamientosApi";
import { validateRow, startBatch, fetchInspectores, fetchRubros, fetchContraproducencias } from "../../../api/gridApi";
import NumeroEsquinaEditor from "../../../components/shared/NumeroEsquinaEditor";
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

const ERROR_KEY_MAP: Record<string, string> = {
  Fecha: "fecha",
  Inspector: "inspector",
  Calle: "calle",
  Numero: "numero",
  Rubro: "rubro",
  Contraproducencia: "contraproducencia",
};

const normalizeErrors = (errors?: Record<string, string>) => {
  if (!errors) return {};
  const mapped: Record<string, string> = {};
  Object.entries(errors).forEach(([key, msg]) => {
    const targetKey = ERROR_KEY_MAP[key] || key;
    mapped[targetKey] = msg;
  });
  return mapped;
};

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
  const [catalogContras, setCatalogContras] = useState<string[]>([]);
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
        const [inspectores, rubros, contras] = await Promise.all([
          fetchInspectores(),
          fetchRubros(),
          fetchContraproducencias(),
        ]);
        setCatalogInspectores([...new Set(inspectores.items.map((i: any) => i.nombre))]);
        setCatalogRubros([...new Set(rubros.items.map((r: any) => r.nombre))]);
        setCatalogContras([...new Set(contras.items.map((c: any) => c.nombre))]);
      } catch (error) {
        console.error("Error cargando catálogos:", error);
      }
    };
    loadCatalogs();
  }, []);

  const buildGridRow = (row: IRelevamientoListItem) => ({
    ID: row.id,
    Fecha: row.fecha,
    Inspector: row.inspector,
    Calle: row.calle,
    Numero: row.numero,
    Rubro: row.rubro,
    Contraproducencia: row.contraproducencia,
  });

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

  const handleSaveRow = useCallback(
    async ({ exitEditingMode, row, values }: any) => {
      const id = Number(row.original.id);
      const fullRow = { ...row.original, ...values };
      if ((fullRow as IRelevamientoListItem).editable === false) {
        alert("Este relevamiento ya no está operativo y no puede editarse.");
        onRefresh?.();
        return;
      }

      if (batchId && !skipValidation) {
        const v = await validateRow({
          batch_id: batchId,
          row_id: `rel_${id}`,
          row: buildGridRow(fullRow as IRelevamientoListItem) as any,
        });

        if (!v.ok) {
          setRowErrors((prev) => ({ ...prev, [id]: normalizeErrors(v.errors || {}) }));
          return;
        }
      }

      setRowErrors((prev) => ({ ...prev, [id]: {} }));

      try {
        if (onBeforeSave) {
          await onBeforeSave(fullRow as IRelevamientoListItem);
        }
        if (!skipUpdate) {
          await updateRelevamiento(id, fullRow as IRelevamientoListItem);
        }

        if (onAfterSave) {
          await onAfterSave(fullRow as IRelevamientoListItem);
        }

        exitEditingMode();
        onRefresh?.();
      } catch (error: any) {
        console.error("Error al actualizar:", error);
        const backendErrors = error?.response?.data?.errors;
        if (backendErrors && typeof backendErrors === "object") {
          setRowErrors((prev) => ({ ...prev, [id]: normalizeErrors(backendErrors) }));
          return;
        }
        const msg = error?.response?.data?.detail || "No se pudo actualizar el registro.";
        alert(msg);
        onRefresh?.();
      }
    },
    [batchId, onRefresh, onBeforeSave, onAfterSave, skipValidation, skipUpdate]
  );

  const columns = useMemo<MRT_ColumnDef<IRelevamientoListItem>[]>(() => {
    const baseColumns: MRT_ColumnDef<IRelevamientoListItem>[] = [
      { accessorKey: "id", header: "ID", enableHiding: true, enableEditing: false, size: 80 },
    {
      accessorKey: "fecha",
      header: "Fecha",
      size: 120,
      enableEditing: !readOnlyColumns.includes("fecha"),
      muiEditTextFieldProps: ({ row }) => {
        const rid = Number(row.original.id);
        const err = rowErrors[rid]?.["fecha"];
        return { type: "date", required: true, error: !!err, helperText: err ?? "" };
      },
    },
    {
      accessorKey: "inspector",
      header: "Inspector",
      size: 200,
      editVariant: "select",
      editSelectOptions: ["", ...catalogInspectores],
      muiEditTextFieldProps: ({ row }) => {
        const rid = Number(row.original.id);
        const err = rowErrors[rid]?.["inspector"];
        return { select: true, required: true, error: !!err, helperText: err ?? "" };
      },
    },
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
      muiEditTextFieldProps: ({ row }) => {
        const rid = Number(row.original.id);
        const err = rowErrors[rid]?.["calle"];
        return { required: true, error: !!err, helperText: err ?? "" };
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
      Edit: ({ row }) => {
        const rid = Number(row.original.id);
        const err = rowErrors[rid]?.["numero"];
        const currentValue =
          (row as any)?._valuesCache?.numero ?? row.original.numero ?? null;

        return (
          <NumeroEsquinaEditor
            value={currentValue}
            onChange={(newValue) => {
              (row as any)._valuesCache = {
                ...(row as any)._valuesCache,
                numero: newValue,
              };
            }}
            onModeChange={(mode) => {
              (row as any)._valuesCache = {
                ...(row as any)._valuesCache,
                numero_tipo: mode,
              };
            }}
            extraCalles={numeroCallesOptions}
            label={numeroEditorLabel}
            error={!!err}
            helperText={err ?? ""}
            allowFreeSolo={numeroAllowFreeSolo}
            initialMode={(row.original as any).numero_tipo || undefined}
          />
        );
      },
    },
    {
      accessorKey: "rubro",
      header: "Rubro",
      size: 180,
      editVariant: "select",
      editSelectOptions: ["", ...catalogRubros],
      muiEditTextFieldProps: ({ row }) => {
        const rid = Number(row.original.id);
        const err = rowErrors[rid]?.["rubro"];
        return { select: true, error: !!err, helperText: err ?? "" };
      },
    },
      {
      accessorKey: "contraproducencia",
      header: "Contraproducencia",
      size: 200,
      editVariant: "select",
      editSelectOptions: ["", ...catalogContras],
      muiEditTextFieldProps: ({ row }) => {
        const rid = Number(row.original.id);
        const err = rowErrors[rid]?.["contraproducencia"];
        return { select: true, error: !!err, helperText: err ?? "" };
      },
      },
    ];
    return [...baseColumns, ...extraColumns];
  }, [rowErrors, catalogInspectores, catalogRubros, catalogContras, extraColumns, numeroCallesOptions, numeroHeader, numeroEditorLabel]);

  const columnOrder = useMemo(() => ([
    ...(hideRowActions ? [] : ["mrt-row-actions"]),
    ...columns.map((col) => col.accessorKey as string),
  ]), [columns, hideRowActions]);

  const table = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    columns,
    data,
    enableEditing,
    editDisplayMode: "row",
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
        rubro: false,
        contraproducencia: false,
        ...initialColumnVisibility,
      },
    },
    onEditingRowSave: handleSaveRow,
    renderRowActions: hideRowActions ? undefined : ({ row, table }) => (
      <Box sx={{ display: "flex", gap: "0.5rem" }}>
        <Tooltip title={row.original.editable === false ? "No editable (fuera de gestión operativa)" : "Editar"}>
          <IconButton
            sx={{
              color: COLORS.white,
              transition: "color 0.2s ease, background-color 0.2s ease",
              "&:hover": { color: COLORS.primary, backgroundColor: "rgba(1, 102, 255, 0.15)" },
            }}
            disabled={row.original.editable === false}
            onClick={() => table.setEditingRow(row)}
          >
            <EditIcon />
          </IconButton>
        </Tooltip>
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
    </Box>
  );
};

export default TablaRelevamientos;
