import { Alert, Box, IconButton, Tooltip, Typography } from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  MaterialReactTable,
  type MRT_ColumnDef,
  useMaterialReactTable,
} from "material-react-table";
import {
  deleteDenunciaGestion,
  type IDenunciaGestionItem,
  updateDenunciaGestion,
} from "../../../api/denunciasApi";
import NumeroEsquinaEditor from "../../../components/shared/NumeroEsquinaEditor";
import { ConfirmDialog } from "../../../ui";
import { useAppFeedback } from "../../../components/feedback";
import { applyDenunciaErrorsFromApi } from "../utils/denunciaFormErrors";
import { shouldRefreshDenunciasAfterSaveFailure } from "../utils/refreshOnSavePolicy";
import { TablaExportButtons } from "../../Actuaciones/Components/TableButtons";
import {
  COLORS,
  DARK_TABLE_CONFIG,
  loadingStyles,
} from "../../Actuaciones/styles/actuacionesTableStyles";

interface TablaDenunciasProps {
  data?: IDenunciaGestionItem[];
  loading?: boolean;
  onRefresh?: () => void;
  /** En realizados la tabla es solo lectura (sin acciones de edición/borrado). */
  readOnly?: boolean;
}

const TablaDenuncias = ({
  data: externalData,
  loading: externalLoading,
  onRefresh,
  readOnly = false,
}: TablaDenunciasProps) => {
  const feedback = useAppFeedback();
  const [data, setData] = useState<IDenunciaGestionItem[]>(externalData || []);
  const [rowErrors, setRowErrors] = useState<Record<number, Record<string, string>>>({});
  const [tableGlobalError, setTableGlobalError] = useState<string | null>(null);
  const [deleteConfirmRow, setDeleteConfirmRow] = useState<IDenunciaGestionItem | null>(null);
  const [deleteInProgress, setDeleteInProgress] = useState(false);
  const loading = externalLoading || false;

  useEffect(() => {
    if (externalData) setData(externalData);
  }, [externalData]);

  const requestDeleteRow = useCallback(
    (rowItem: IDenunciaGestionItem) => {
      if (rowItem.editable === false) {
        feedback.error("Esta denuncia ya no está operativa y no puede eliminarse.");
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
      await deleteDenunciaGestion(id);
      onRefresh?.();
    } catch (error: unknown) {
      console.error("Error al eliminar denuncia:", error);
      const { globalMessage } = applyDenunciaErrorsFromApi(error);
      const msg = globalMessage ?? "No se pudo eliminar la denuncia. Se restaurará la lista.";
      setTableGlobalError(msg);
      feedback.error(msg);
      setData(prev);
      onRefresh?.();
    } finally {
      setDeleteInProgress(false);
      setDeleteConfirmRow(null);
    }
  }, [data, deleteConfirmRow, onRefresh, feedback]);

  const handleSaveRow = useCallback(
    async ({ exitEditingMode, row, values }: any) => {
      const id = Number(row.original.id);
      const fullRow: IDenunciaGestionItem = { ...row.original, ...values };
      if (fullRow.editable === false) {
        feedback.error("Esta denuncia ya no está operativa y no puede editarse.");
        return;
      }
      try {
        setTableGlobalError(null);
        setRowErrors((prev) => ({ ...prev, [id]: {} }));
        await updateDenunciaGestion(id, fullRow);
        exitEditingMode();
        onRefresh?.();
      } catch (error: unknown) {
        const { fieldErrors, globalMessage } = applyDenunciaErrorsFromApi(error);
        if (Object.keys(fieldErrors).length > 0) {
          setRowErrors((prev) => ({ ...prev, [id]: fieldErrors }));
          setTableGlobalError(null);
          return;
        }
        const msg = globalMessage ?? "No se pudo actualizar la denuncia.";
        setTableGlobalError(msg);
        feedback.error(msg);
        if (shouldRefreshDenunciasAfterSaveFailure(error, fieldErrors)) {
          onRefresh?.();
        }
      }
    },
    [onRefresh, feedback]
  );

  const columns = useMemo<MRT_ColumnDef<IDenunciaGestionItem>[]>(
    () => [
      { accessorKey: "id", header: "ID", enableEditing: false, size: 80 },
      {
        accessorKey: "fecha",
        header: "Fecha",
        size: 140,
        muiEditTextFieldProps: ({ row }) => {
          const rid = Number(row.original.id);
          const err = rowErrors[rid]?.["fecha"];
          return { type: "date", required: true, error: !!err, helperText: err ?? "" };
        },
      },
      {
        accessorKey: "calle",
        header: "Calle",
        size: 220,
        muiEditTextFieldProps: ({ row }) => {
          const rid = Number(row.original.id);
          const err = rowErrors[rid]?.["calle"];
          return { required: true, error: !!err, helperText: err ?? "" };
        },
      },
      {
        accessorKey: "numero",
        header: "Número/Esquina",
        size: 380,
        Edit: ({ row }) => {
          const rid = Number(row.original.id);
          const err = rowErrors[rid]?.["numero"];
          const currentValue = (row as any)?._valuesCache?.numero ?? row.original.numero ?? null;
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
              label="Número/Esquina"
              error={!!err}
              helperText={err ?? ""}
              allowFreeSolo
              initialMode={(row.original as any).numero_tipo || undefined}
            />
          );
        },
      },
      {
        accessorKey: "motivo",
        header: "Motivo",
        size: 260,
        muiEditTextFieldProps: ({ row }) => {
          const rid = Number(row.original.id);
          const err = rowErrors[rid]?.["motivo"];
          return { required: true, error: !!err, helperText: err ?? "" };
        },
      },
      {
        accessorKey: "estado",
        header: "Estado",
        size: 160,
        editVariant: "select",
        editSelectOptions: ["ABIERTA", "CERRADA", "DESCARTADA"],
      },
    ],
    [rowErrors]
  );

  const table = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    columns,
    data,
    enableEditing: !readOnly,
    editDisplayMode: "row",
    enableSorting: true,
    enableColumnFilters: true,
    enableGlobalFilter: true,
    enableRowActions: !readOnly,
    positionActionsColumn: "first",
    initialState: {
      density: "compact",
      columnVisibility: {
        id: false,
      },
    },
    onEditingRowSave: handleSaveRow,
    renderRowActions: readOnly
      ? undefined
      : ({ row, table }) => (
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
      </Box>
    ),
    renderTopToolbarCustomActions: ({ table }) => (
      <TablaExportButtons table={table} filePrefix="denuncias" />
    ),
  });

  if (loading) {
    return (
      <Box sx={{ padding: "40px", textAlign: "center" }}>
        <Typography sx={loadingStyles}>Cargando denuncias...</Typography>
      </Box>
    );
  }

  return (
    <>
      {tableGlobalError ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {tableGlobalError}
        </Alert>
      ) : null}
      <MaterialReactTable table={table} />
      <ConfirmDialog
        open={deleteConfirmRow !== null}
        onClose={() => setDeleteConfirmRow(null)}
        onConfirm={performDeleteRow}
        title="Eliminar denuncia"
        destructive
        loading={deleteInProgress}
        confirmLabel="Eliminar"
      >
        Esta acción quitará la denuncia del listado. No se podrá deshacer desde esta vista.
      </ConfirmDialog>
    </>
  );
};

export default TablaDenuncias;

