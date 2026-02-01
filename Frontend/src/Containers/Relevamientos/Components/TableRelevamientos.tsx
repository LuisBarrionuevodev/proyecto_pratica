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
  extraColumns?: MRT_ColumnDef<IRelevamientoListItem>[];
  onBeforeSave?: (fullRow: IRelevamientoListItem) => Promise<void>;
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
  extraColumns = [],
  onBeforeSave,
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

  const handleDeleteRow = useCallback(async (id: number) => {
    if (!window.confirm("¿Estás seguro de eliminar este registro?")) return;
    const prev = [...data];
    setData((prevData) => prevData.filter((item) => item.id !== id));
    try {
      await deleteRelevamiento(id);
      onRefresh?.();
    } catch (error) {
      console.error("Error al eliminar:", error);
      alert("No se pudo eliminar el registro. Se restaurará la lista.");
      setData(prev);
    }
  }, [data, onRefresh]);

  const handleSaveRow = useCallback(
    async ({ exitEditingMode, row, values }: any) => {
      const id = Number(row.original.id);
      const fullRow = { ...row.original, ...values };

      if (batchId) {
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
        await updateRelevamiento(id, fullRow as IRelevamientoListItem);
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
      }
    },
    [batchId, onRefresh, onBeforeSave]
  );

  const columns = useMemo<MRT_ColumnDef<IRelevamientoListItem>[]>(() => {
    const baseColumns: MRT_ColumnDef<IRelevamientoListItem>[] = [
      { accessorKey: "id", header: "ID", enableHiding: true, enableEditing: false, size: 80 },
    {
      accessorKey: "fecha",
      header: "Fecha",
      size: 120,
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
      muiEditTextFieldProps: ({ row }) => {
        const rid = Number(row.original.id);
        const err = rowErrors[rid]?.["calle"];
        return { required: true, error: !!err, helperText: err ?? "" };
      },
    },
    {
      accessorKey: "numero",
      header: "Numero",
      size: 100,
      muiEditTextFieldProps: ({ row }) => {
        const rid = Number(row.original.id);
        const err = rowErrors[rid]?.["numero"];
        return { required: true, error: !!err, helperText: err ?? "" };
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
  }, [rowErrors, catalogInspectores, catalogRubros, catalogContras, extraColumns]);

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
        <Tooltip title="Editar">
          <IconButton
            sx={{
              color: COLORS.white,
              transition: "color 0.2s ease, background-color 0.2s ease",
              "&:hover": { color: COLORS.primary, backgroundColor: "rgba(1, 102, 255, 0.15)" },
            }}
            onClick={() => table.setEditingRow(row)}
          >
            <EditIcon />
          </IconButton>
        </Tooltip>
        <Tooltip title="Eliminar">
          <IconButton
            sx={{
              color: COLORS.white,
              transition: "color 0.2s ease, background-color 0.2s ease",
              "&:hover": { color: "#ff4444", backgroundColor: "rgba(255, 68, 68, 0.15)" },
            }}
            onClick={() => handleDeleteRow(Number(row.original.id))}
          >
            <DeleteIcon />
          </IconButton>
        </Tooltip>
      </Box>
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
