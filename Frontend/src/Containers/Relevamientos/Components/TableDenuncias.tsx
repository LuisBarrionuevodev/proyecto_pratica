import { Alert, Box, IconButton, Tooltip, Typography } from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import VisibilityIcon from "@mui/icons-material/Visibility";
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
import { ConfirmDialog } from "../../../ui";
import { useAppFeedback } from "../../../components/feedback";
import { applyDenunciaErrorsFromApi } from "../utils/denunciaFormErrors";
import { shouldRefreshDenunciasAfterSaveFailure } from "../utils/refreshOnSavePolicy";
import { DenunciaCrudDialog } from "./DenunciaCrudDialog";
import { TablaExportButtons } from "../../Actuaciones/Components/TableButtons";
import {
  BandejaEllipsisCell,
  BANDEJA_MRT_READ_ONLY_TABLE_PROPS,
} from "../../Actuaciones/Components/bandejaTableCells";
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

function denunciaCellText(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
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
  const [crudDraft, setCrudDraft] = useState<IDenunciaGestionItem | null>(null);
  const [crudMode, setCrudMode] = useState<"view" | "edit" | null>(null);
  const [crudSaving, setCrudSaving] = useState(false);
  const [crudGlobalError, setCrudGlobalError] = useState<string | null>(null);
  const loading = externalLoading || false;

  useEffect(() => {
    if (externalData) setData(externalData);
  }, [externalData]);

  const closeCrudDialog = useCallback(() => {
    setCrudDraft(null);
    setCrudMode(null);
    setCrudGlobalError(null);
  }, []);

  const openCrudView = useCallback((row: IDenunciaGestionItem) => {
    setCrudGlobalError(null);
    setCrudDraft({ ...row });
    setCrudMode("view");
  }, []);

  const requestDeleteRow = useCallback(
    (rowItem: IDenunciaGestionItem) => {
      if (rowItem.editable === false) {
        feedback.error("Esta denuncia ya no está operativa y no puede eliminarse.");
        return;
      }
      setDeleteConfirmRow(rowItem);
    },
    [feedback]
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

  const handleDialogSave = useCallback(async () => {
    if (!crudDraft) return;
    const id = Number(crudDraft.id);
    const fullRow = crudDraft;
    if (fullRow.editable === false) {
      feedback.error("Esta denuncia ya no está operativa y no puede editarse.");
      return;
    }

    setCrudGlobalError(null);
    setCrudSaving(true);
    try {
      setRowErrors((prev) => ({ ...prev, [id]: {} }));
      await updateDenunciaGestion(id, fullRow);
      closeCrudDialog();
      onRefresh?.();
    } catch (error: unknown) {
      const { fieldErrors, globalMessage } = applyDenunciaErrorsFromApi(error);
      if (Object.keys(fieldErrors).length > 0) {
        setRowErrors((prev) => ({ ...prev, [id]: fieldErrors }));
        setCrudGlobalError(null);
        return;
      }
      const msg = globalMessage ?? "No se pudo actualizar la denuncia.";
      setCrudGlobalError(msg);
      feedback.error(msg);
      if (shouldRefreshDenunciasAfterSaveFailure(error, fieldErrors)) {
        onRefresh?.();
      }
    } finally {
      setCrudSaving(false);
    }
  }, [crudDraft, closeCrudDialog, onRefresh, feedback]);

  const columns = useMemo<MRT_ColumnDef<IDenunciaGestionItem>[]>(
    () => [
      { accessorKey: "id", header: "ID", enableHiding: true, size: 80 },
      {
        accessorKey: "fecha",
        header: "Fecha",
        size: 140,
        Cell: ({ cell }) => <BandejaEllipsisCell value={denunciaCellText(cell.getValue())} />,
      },
      {
        accessorKey: "calle",
        header: "Calle",
        size: 220,
        Cell: ({ cell }) => <BandejaEllipsisCell value={denunciaCellText(cell.getValue())} />,
      },
      {
        accessorKey: "numero",
        header: "Número/Esquina",
        size: 380,
        Cell: ({ cell }) => <BandejaEllipsisCell value={denunciaCellText(cell.getValue())} />,
      },
      {
        accessorKey: "motivo",
        header: "Motivo",
        size: 260,
        Cell: ({ cell }) => <BandejaEllipsisCell value={denunciaCellText(cell.getValue())} />,
      },
      {
        accessorKey: "estado",
        header: "Estado",
        size: 160,
        Cell: ({ cell }) => <BandejaEllipsisCell value={denunciaCellText(cell.getValue())} />,
      },
    ],
    []
  );

  const table = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    ...BANDEJA_MRT_READ_ONLY_TABLE_PROPS,
    columns,
    data,
    enableEditing: false,
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
    renderRowActions: readOnly
      ? undefined
      : ({ row }) => (
          <Box sx={{ display: "flex", gap: "0.5rem" }}>
            <Tooltip title="Ver">
              <IconButton
                sx={{
                  color: COLORS.white,
                  transition: "color 0.2s ease, background-color 0.2s ease",
                  "&:hover": { color: COLORS.primary, backgroundColor: "rgba(1, 102, 255, 0.15)" },
                }}
                onClick={() => openCrudView(row.original)}
              >
                <VisibilityIcon fontSize="small" />
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
                <DeleteIcon fontSize="small" />
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

      {crudDraft && crudMode ? (
        <DenunciaCrudDialog
          open
          mode={crudMode}
          draft={crudDraft}
          fieldErrors={rowErrors[crudDraft.id] ?? {}}
          saving={crudSaving}
          globalError={crudGlobalError}
          canEdit={crudDraft.editable !== false && !readOnly}
          showDelete={crudMode === "edit" && !readOnly}
          onClose={closeCrudDialog}
          onModeChange={(nextMode) => {
            setCrudGlobalError(null);
            setCrudMode(nextMode);
          }}
          onDelete={
            crudDraft.editable !== false
              ? () => {
                  requestDeleteRow(crudDraft);
                  closeCrudDialog();
                }
              : undefined
          }
          onDraftChange={(patch) => {
            setCrudGlobalError(null);
            setCrudDraft((prev) => (prev ? { ...prev, ...patch } : null));
          }}
          onSave={handleDialogSave}
        />
      ) : null}

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
