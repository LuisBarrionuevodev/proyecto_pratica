import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
} from "material-react-table";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, Box, Chip, IconButton, Paper, Tab, Tabs, Tooltip } from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import VisibilityIcon from "@mui/icons-material/Visibility";
import PersonOffIcon from "@mui/icons-material/PersonOff";
import HowToRegIcon from "@mui/icons-material/HowToReg";
import { apiClient } from "../../../api/apiClient";
import { DataTableMrtShell } from "../../../components/dataTable/DataTableMrtShell";
import { BANDEJA_MRT_SPINNER_LOADING_STATE } from "../../../components/dataTable/bandejaTableLoading";
import { useAppFeedback } from "../../../components/feedback/useAppFeedback";
import { moduleSlicesPanelPaperSx, moduleSlicesTabsSx } from "../../../styles/GlassStyles";
import {
  bandejaOutlinedChipSx,
  BANDEJA_MRT_READ_ONLY_TABLE_PROPS,
} from "../../Actuaciones/Components/bandejaTableCells";
import { COLORS, DARK_TABLE_CONFIG } from "../../Actuaciones/styles/actuacionesTableStyles";
import { wrapperStyles } from "../../Actuaciones/styles/filtroStyles";
import { AppButton, ConfirmDialog } from "../../../ui";
import FiltroUsuarios, { type UsuariosFiltroAplicado } from "./FiltroUsuarios";
import { GestionUsuarioCrudDialog } from "./GestionUsuarioCrudDialog";
import {
  buildCreateUsuarioPayload,
  buildUpdateUsuarioPayload,
  type GestionUsuarioFormValues,
  usuarioRoleLabel,
  validateGestionUsuarioForm,
} from "../utils/gestionUsuarioForm";
import { mapGestionUsuarioApiErrors } from "../utils/gestionUsuarioFormErrors";

type UsuarioSlice = "activos" | "inactivos";

type Usuario = {
  id: number;
  username: string;
  email: string;
  role: "admin" | "usuario" | "relevador";
  is_active?: boolean;
  password?: string;
};

type ConfirmAction =
  | { kind: "inactivar"; userId: number }
  | { kind: "reactivar"; userId: number }
  | null;

type CrudMode = "create" | "view" | "edit" | null;

function extractApiDetail(error: unknown, fallback: string): string {
  const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail.trim();
  }
  return fallback;
}

const TableGestionDeUsuarios = () => {
  const feedback = useAppFeedback();
  const [slice, setSlice] = useState<UsuarioSlice>("activos");
  const [data, setData] = useState<Usuario[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [listServerError, setListServerError] = useState("");
  const [confirmAction, setConfirmAction] = useState<ConfirmAction>(null);
  const [appliedFiltros, setAppliedFiltros] = useState<UsuariosFiltroAplicado>({
    texto: "",
    rol: "",
  });

  const [crudMode, setCrudMode] = useState<CrudMode>(null);
  const [selectedUser, setSelectedUser] = useState<Usuario | null>(null);
  const [crudFieldErrors, setCrudFieldErrors] = useState<Record<string, string>>({});
  const [crudGlobalError, setCrudGlobalError] = useState<string | null>(null);

  const fetchUsuarios = useCallback(async (estado: UsuarioSlice) => {
    try {
      setLoading(true);
      const response = await apiClient.get<Usuario[]>(`/api/admin/users?estado=${estado}`);
      setData(response.data);
      setListServerError("");
    } catch (error) {
      console.error("Error al obtener usuarios:", error);
      setListServerError(extractApiDetail(error, "No se pudieron cargar los usuarios."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchUsuarios(slice);
  }, [slice, fetchUsuarios]);

  const filteredData = useMemo(() => {
    const q = appliedFiltros.texto.trim().toLowerCase();
    return data.filter((u) => {
      if (appliedFiltros.rol && u.role !== appliedFiltros.rol) return false;
      if (!q) return true;
      return (
        u.username.toLowerCase().includes(q) ||
        u.email.toLowerCase().includes(q) ||
        String(u.role).toLowerCase().includes(q) ||
        usuarioRoleLabel(u.role).toLowerCase().includes(q)
      );
    });
  }, [data, appliedFiltros]);

  const resetCrudErrors = useCallback(() => {
    setCrudFieldErrors({});
    setCrudGlobalError(null);
  }, []);

  const closeCrudDialog = useCallback(() => {
    if (saving) return;
    setCrudMode(null);
    setSelectedUser(null);
    resetCrudErrors();
  }, [saving, resetCrudErrors]);

  const openCreateDialog = useCallback(() => {
    resetCrudErrors();
    setSelectedUser(null);
    setCrudMode("create");
  }, [resetCrudErrors]);

  const openViewDialog = useCallback(
    (user: Usuario) => {
      resetCrudErrors();
      setSelectedUser(user);
      setCrudMode("view");
    },
    [resetCrudErrors]
  );

  const clearCrudFieldError = useCallback((field: string) => {
    setCrudFieldErrors((prev) => {
      if (!prev[field]) return prev;
      const next = { ...prev };
      delete next[field];
      return next;
    });
  }, []);

  const handleInactivar = async (id: number) => {
    try {
      setSaving(true);
      await apiClient.patch(`/api/admin/users/${id}/inactivar`);
      await fetchUsuarios(slice);
      setListServerError("");
      feedback.success("Usuario inactivado correctamente.");
    } catch (error) {
      console.error("Error al inactivar usuario:", error);
      setListServerError(extractApiDetail(error, "No se pudo inactivar el usuario."));
    } finally {
      setSaving(false);
    }
  };

  const handleReactivar = async (id: number) => {
    try {
      setSaving(true);
      await apiClient.patch(`/api/admin/users/${id}/reactivar`);
      await fetchUsuarios(slice);
      setListServerError("");
      feedback.success("Usuario reactivado correctamente.");
    } catch (error) {
      console.error("Error al reactivar usuario:", error);
      setListServerError(extractApiDetail(error, "No se pudo reactivar el usuario."));
    } finally {
      setSaving(false);
    }
  };

  const handleCreate = useCallback(
    async (values: GestionUsuarioFormValues): Promise<boolean> => {
      try {
        setSaving(true);
        setCrudGlobalError(null);
        await apiClient.post("/api/admin/users", buildCreateUsuarioPayload(values));
        await fetchUsuarios(slice);
        feedback.success("Usuario creado correctamente.");
        return true;
      } catch (error) {
        console.error("Error al crear usuario:", error);
        const { fieldErrors, globalMessage } = mapGestionUsuarioApiErrors(
          error,
          "No se pudo crear el usuario. Revisá username/email/rol."
        );
        if (Object.keys(fieldErrors).length > 0) {
          setCrudFieldErrors(fieldErrors);
          setCrudGlobalError(globalMessage);
        } else {
          setCrudGlobalError(globalMessage);
        }
        return false;
      } finally {
        setSaving(false);
      }
    },
    [fetchUsuarios, slice, feedback]
  );

  const handleEdit = useCallback(
    async (userId: number, values: GestionUsuarioFormValues): Promise<boolean> => {
      try {
        setSaving(true);
        setCrudGlobalError(null);
        await apiClient.put(`/api/admin/users/${userId}`, buildUpdateUsuarioPayload(values));
        await fetchUsuarios(slice);
        feedback.success("Usuario actualizado correctamente.");
        return true;
      } catch (error) {
        console.error("Error al editar usuario:", error);
        const { fieldErrors, globalMessage } = mapGestionUsuarioApiErrors(
          error,
          "No se pudo actualizar el usuario."
        );
        if (Object.keys(fieldErrors).length > 0) {
          setCrudFieldErrors(fieldErrors);
          setCrudGlobalError(globalMessage);
        } else {
          setCrudGlobalError(globalMessage);
        }
        return false;
      } finally {
        setSaving(false);
      }
    },
    [fetchUsuarios, slice, feedback]
  );

  const handleCrudSave = useCallback(
    async (values: GestionUsuarioFormValues) => {
      const isCreate = crudMode === "create";
      const clientErrors = validateGestionUsuarioForm(values, isCreate);
      if (Object.keys(clientErrors).length > 0) {
        setCrudFieldErrors(clientErrors);
        setCrudGlobalError(null);
        return;
      }

      const ok = isCreate
        ? await handleCreate(values)
        : selectedUser
          ? await handleEdit(selectedUser.id, values)
          : false;

      if (ok) {
        closeCrudDialog();
      }
    },
    [crudMode, selectedUser, closeCrudDialog, handleCreate, handleEdit]
  );

  const columns = useMemo<MRT_ColumnDef<Usuario>[]>(
    () => [
      {
        accessorKey: "id",
        header: "ID",
        size: 60,
      },
      {
        accessorKey: "username",
        header: "Usuario",
      },
      {
        accessorKey: "email",
        header: "Email",
      },
      {
        id: "password_masked",
        header: "Contraseña",
        accessorFn: () => "********",
        enableSorting: false,
      },
      {
        accessorKey: "role",
        header: "Rol",
        Cell: ({ cell }) => (
          <Chip
            size="small"
            variant="outlined"
            label={usuarioRoleLabel(String(cell.getValue() ?? ""))}
            sx={bandejaOutlinedChipSx}
          />
        ),
      },
      {
        id: "estado",
        header: "Estado",
        accessorFn: (row) => (row.is_active !== false ? "Activo" : "Inactivo"),
        size: 100,
        Cell: ({ row }) => {
          const active = row.original.is_active !== false;
          return (
            <Chip
              size="small"
              variant="outlined"
              label={active ? "Activo" : "Inactivo"}
              color={active ? "success" : "default"}
              sx={bandejaOutlinedChipSx}
            />
          );
        },
      },
    ],
    []
  );

  const isActivosSlice = slice === "activos";

  const table = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    ...BANDEJA_MRT_READ_ONLY_TABLE_PROPS,
    columns,
    data: filteredData,
    enableColumnFilters: false,
    enableGlobalFilter: false,
    enableEditing: false,
    enableRowActions: true,
    positionActionsColumn: "first",
    getRowId: (row) => String(row.id),
    state: {
      ...BANDEJA_MRT_SPINNER_LOADING_STATE,
    },
    renderRowActions: ({ row }) => (
      <Box sx={{ display: "flex", gap: "0.5rem", flexWrap: "nowrap" }}>
        {isActivosSlice ? (
          <>
            <Tooltip title="Ver">
              <IconButton
                sx={{
                  color: COLORS.white,
                  transition: "color 0.2s ease, background-color 0.2s ease",
                  "&:hover": { color: COLORS.primary, backgroundColor: "rgba(1, 102, 255, 0.15)" },
                }}
                onClick={() => openViewDialog(row.original)}
              >
                <VisibilityIcon fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title="Inactivar usuario">
              <IconButton
                sx={{
                  color: COLORS.white,
                  transition: "color 0.2s ease, background-color 0.2s ease",
                  "&:hover": { color: "#ff9800", backgroundColor: "rgba(255, 152, 0, 0.15)" },
                }}
                onClick={() => setConfirmAction({ kind: "inactivar", userId: row.original.id })}
              >
                <PersonOffIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </>
        ) : (
          <Tooltip title="Reactivar usuario">
            <IconButton
              sx={{
                color: COLORS.white,
                transition: "color 0.2s ease, background-color 0.2s ease",
                "&:hover": { color: "#2e7d32", backgroundColor: "rgba(46, 125, 50, 0.15)" },
              }}
              onClick={() => setConfirmAction({ kind: "reactivar", userId: row.original.id })}
            >
              <HowToRegIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        )}
      </Box>
    ),
    renderTopToolbarCustomActions: () =>
      isActivosSlice ? (
        <AppButton dsVariant="primary" dsSize="sm" startIcon={<AddIcon />} onClick={openCreateDialog}>
          Crear nuevo user
        </AppButton>
      ) : null,
  });

  const tabIndex = slice === "activos" ? 0 : 1;

  return (
    <>
      <Box sx={wrapperStyles}>
        <FiltroUsuarios
          onFiltrar={setAppliedFiltros}
          onLimpiar={() => setAppliedFiltros({ texto: "", rol: "" })}
        />

        <Paper elevation={0} sx={{ ...moduleSlicesPanelPaperSx, mb: 2 }}>
          <Tabs
            value={tabIndex}
            onChange={(_, v) => setSlice(v === 0 ? "activos" : "inactivos")}
            variant="scrollable"
            allowScrollButtonsMobile
            sx={moduleSlicesTabsSx}
          >
            <Tab label={`Usuarios activos${slice === "activos" && loading ? " · …" : ""}`} />
            <Tab label={`Usuarios inactivos${slice === "inactivos" && loading ? " · …" : ""}`} />
          </Tabs>
        </Paper>

        {listServerError ? (
          <Alert severity="error" sx={{ mb: 2 }}>
            {listServerError}
          </Alert>
        ) : null}

        <DataTableMrtShell loading={loading} loadingMode="overlay">
          <MaterialReactTable table={table} />
        </DataTableMrtShell>
      </Box>

      <GestionUsuarioCrudDialog
        open={crudMode !== null}
        mode={crudMode === "create" ? "create" : crudMode === "edit" ? "edit" : "view"}
        user={selectedUser}
        saving={saving}
        fieldErrors={crudFieldErrors}
        globalError={crudGlobalError}
        onClose={closeCrudDialog}
        onModeChange={(nextMode) => {
          resetCrudErrors();
          setCrudMode(nextMode);
        }}
        onSave={(values) => void handleCrudSave(values)}
        onClearFieldError={clearCrudFieldError}
      />

      <ConfirmDialog
        open={confirmAction?.kind === "inactivar"}
        onClose={() => setConfirmAction(null)}
        onConfirm={async () => {
          if (confirmAction?.kind !== "inactivar") return;
          const id = confirmAction.userId;
          try {
            await handleInactivar(id);
          } finally {
            setConfirmAction(null);
          }
        }}
        title="Inactivar usuario"
        destructive
        loading={saving}
        confirmLabel="Inactivar usuario"
      >
        Este usuario dejará de poder ingresar al sistema. No se eliminará su historial.
      </ConfirmDialog>

      <ConfirmDialog
        open={confirmAction?.kind === "reactivar"}
        onClose={() => setConfirmAction(null)}
        onConfirm={async () => {
          if (confirmAction?.kind !== "reactivar") return;
          const id = confirmAction.userId;
          try {
            await handleReactivar(id);
          } finally {
            setConfirmAction(null);
          }
        }}
        title="Reactivar usuario"
        loading={saving}
        confirmLabel="Reactivar usuario"
      >
        El usuario podrá volver a ingresar al sistema.
      </ConfirmDialog>
    </>
  );
};

export default TableGestionDeUsuarios;
