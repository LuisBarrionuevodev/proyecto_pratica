import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
} from "material-react-table";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, Box, Chip, IconButton, Paper, Tab, Tabs, Tooltip, Typography } from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import PersonOffIcon from "@mui/icons-material/PersonOff";
import HowToRegIcon from "@mui/icons-material/HowToReg";
import { apiClient } from "../../../api/apiClient";
import { DataTableMrtShell } from "../../../components/dataTable/DataTableMrtShell";
import { useAppFeedback } from "../../../components/feedback/useAppFeedback";
import { moduleSlicesPanelPaperSx, moduleSlicesTabsSx } from "../../../styles/GlassStyles";
import {
  bandejaOutlinedChipSx,
  BANDEJA_MRT_READ_ONLY_TABLE_PROPS,
} from "../../Actuaciones/Components/bandejaTableCells";
import { COLORS, DARK_TABLE_CONFIG } from "../../Actuaciones/styles/actuacionesTableStyles";
import { AppButton, ConfirmDialog } from "../../../ui";

type UsuarioSlice = "activos" | "inactivos";

type Usuario = {
  id: number;
  username: string;
  email: string;
  role: "admin" | "usuario";
  is_active?: boolean;
  password?: string;
};

type ConfirmAction =
  | { kind: "inactivar"; userId: number }
  | { kind: "reactivar"; userId: number }
  | null;

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

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
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState("");
  const [confirmAction, setConfirmAction] = useState<ConfirmAction>(null);

  const fetchUsuarios = useCallback(async (estado: UsuarioSlice) => {
    try {
      setLoading(true);
      const response = await apiClient.get<Usuario[]>(`/api/admin/users?estado=${estado}`);
      setData(response.data);
      setServerError("");
    } catch (error) {
      console.error("Error al obtener usuarios:", error);
      setServerError(extractApiDetail(error, "No se pudieron cargar los usuarios."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchUsuarios(slice);
  }, [slice, fetchUsuarios]);

  const handleInactivar = async (id: number) => {
    try {
      setSaving(true);
      await apiClient.patch(`/api/admin/users/${id}/inactivar`);
      await fetchUsuarios(slice);
      setServerError("");
      feedback.success("Usuario inactivado correctamente.");
    } catch (error) {
      console.error("Error al inactivar usuario:", error);
      setServerError(extractApiDetail(error, "No se pudo inactivar el usuario."));
    } finally {
      setSaving(false);
    }
  };

  const handleReactivar = async (id: number) => {
    try {
      setSaving(true);
      await apiClient.patch(`/api/admin/users/${id}/reactivar`);
      await fetchUsuarios(slice);
      setServerError("");
      feedback.success("Usuario reactivado correctamente.");
    } catch (error) {
      console.error("Error al reactivar usuario:", error);
      setServerError(extractApiDetail(error, "No se pudo reactivar el usuario."));
    } finally {
      setSaving(false);
    }
  };

  const mapServerErrors = (error: unknown) => {
    const mapped: Record<string, string> = {};
    const fieldErrors = (error as { response?: { data?: { errors?: Record<string, string> } } })
      ?.response?.data?.errors;
    const detail = extractApiDetail(error, "");

    if (fieldErrors && typeof fieldErrors === "object") {
      Object.entries(fieldErrors).forEach(([key, message]) => {
        mapped[key] = message;
      });
      return mapped;
    }

    const detailLower = detail.toLowerCase();
    if (detailLower.includes("email")) {
      mapped.email = detail || "Email ya está en uso.";
    }
    if (detailLower.includes("username") || detailLower.includes("usuario")) {
      mapped.username = detail || "Username ya está en uso.";
    }
    if (detailLower.includes("rol") || detailLower.includes("role")) {
      mapped.role = detail || "Rol inválido.";
    }
    return mapped;
  };

  const handleCreate = async (values: Record<string, unknown>): Promise<boolean> => {
    try {
      setSaving(true);
      setServerError("");
      await apiClient.post("/api/admin/users", {
        username: String(values.username ?? ""),
        email: String(values.email ?? ""),
        password: String(values.password ?? ""),
        role: values.role === "admin" ? "admin" : "usuario",
      });
      await fetchUsuarios(slice);
      feedback.success("Usuario creado correctamente.");
      return true;
    } catch (error) {
      console.error("Error al crear usuario:", error);
      const mappedErrors = mapServerErrors(error);
      if (Object.keys(mappedErrors).length > 0) {
        setValidationErrors((prev) => ({ ...prev, ...mappedErrors }));
      } else {
        setServerError(extractApiDetail(error, "No se pudo crear el usuario. Revisá username/email/rol."));
      }
      return false;
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = async (userId: number, values: Record<string, unknown>): Promise<boolean> => {
    try {
      setSaving(true);
      setServerError("");
      await apiClient.put(`/api/admin/users/${userId}`, {
        username: String(values.username ?? ""),
        email: String(values.email ?? ""),
        password: String(values.password ?? "").trim() || undefined,
        role: values.role === "admin" ? "admin" : "usuario",
      });
      await fetchUsuarios(slice);
      feedback.success("Usuario actualizado correctamente.");
      return true;
    } catch (error) {
      console.error("Error al editar usuario:", error);
      const mappedErrors = mapServerErrors(error);
      if (Object.keys(mappedErrors).length > 0) {
        setValidationErrors((prev) => ({ ...prev, ...mappedErrors }));
      } else {
        setServerError(extractApiDetail(error, "No se pudo actualizar el usuario."));
      }
      return false;
    } finally {
      setSaving(false);
    }
  };

  const clearFieldError = (field: string) => {
    setValidationErrors((prev) => {
      if (!prev[field]) return prev;
      const next = { ...prev };
      delete next[field];
      return next;
    });
  };

  const validateUser = (values: Record<string, unknown>, isCreate: boolean) => {
    const errors: Record<string, string> = {};
    const username = String(values.username ?? "").trim();
    const email = String(values.email ?? "").trim();
    const password = String(values.password ?? "").trim();
    const role = String(values.role ?? "").trim();

    if (!username) {
      errors.username = "Username is required";
    } else if (username.length < 3) {
      errors.username = "Username must be at least 3 characters";
    }

    if (!email) {
      errors.email = "Email is required";
    } else if (!EMAIL_REGEX.test(email)) {
      errors.email = "Incorrect Email Format";
    }

    if (isCreate && !password) {
      errors.password = "Password is required";
    }

    if (!role) {
      errors.role = "Role is required";
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const columns = useMemo<MRT_ColumnDef<Usuario>[]>(
    () => [
      {
        accessorKey: "id",
        header: "ID",
        size: 60,
        enableEditing: false,
      },
      {
        accessorKey: "username",
        header: "Usuario",
        muiEditTextFieldProps: {
          required: true,
          error: !!validationErrors.username,
          helperText: validationErrors.username,
          onFocus: () => clearFieldError("username"),
        },
      },
      {
        accessorKey: "email",
        header: "Email",
        muiEditTextFieldProps: {
          required: true,
          error: !!validationErrors.email,
          helperText: validationErrors.email,
          onFocus: () => clearFieldError("email"),
        },
      },
      {
        accessorKey: "password",
        header: "Contraseña",
        Cell: () => "********",
        muiEditTextFieldProps: {
          type: "password",
          placeholder: "Dejar vacío para mantener la actual",
          error: !!validationErrors.password,
          helperText: validationErrors.password,
          onFocus: () => clearFieldError("password"),
        },
      },
      {
        accessorKey: "role",
        header: "Rol",
        editVariant: "select",
        editSelectOptions: [
          { value: "admin", label: "admin" },
          { value: "usuario", label: "usuario" },
        ],
        Cell: ({ cell }) => (
          <Chip size="small" variant="outlined" label={String(cell.getValue() ?? "—")} sx={bandejaOutlinedChipSx} />
        ),
        muiEditTextFieldProps: {
          required: true,
          error: !!validationErrors.role,
          helperText: validationErrors.role,
          onFocus: () => clearFieldError("role"),
        },
      },
      {
        id: "estado",
        header: "Estado",
        accessorFn: (row) => (row.is_active !== false ? "Activo" : "Inactivo"),
        enableEditing: false,
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
    [validationErrors]
  );

  const isActivosSlice = slice === "activos";

  const table = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    ...BANDEJA_MRT_READ_ONLY_TABLE_PROPS,
    columns,
    data,
    enableColumnFilters: false,
    enableRowSelection: false,
    positionGlobalFilter: "right",
    enableEditing: isActivosSlice,
    createDisplayMode: "modal",
    editDisplayMode: "modal",
    enableRowActions: true,
    positionActionsColumn: "first",
    getRowId: (row) => String(row.id),
    state: {
      isLoading: loading,
      isSaving: saving,
      showAlertBanner: !!serverError,
      showProgressBars: loading || saving,
    },
    muiToolbarAlertBannerProps: serverError
      ? {
          color: "error",
          children: serverError,
        }
      : undefined,
    onCreatingRowCancel: () => {
      setSaving(false);
      setValidationErrors({});
      setServerError("");
    },
    onCreatingRowSave: async ({ values, table: mrtTable }) => {
      if (!validateUser(values, true)) {
        return;
      }
      const ok = await handleCreate(values);
      if (ok) {
        setValidationErrors({});
        mrtTable.setCreatingRow(null);
      }
    },
    onEditingRowCancel: () => {
      setSaving(false);
      setValidationErrors({});
      setServerError("");
    },
    onEditingRowSave: async ({ row, values, table: mrtTable }) => {
      if (!validateUser(values, false)) {
        return;
      }
      const ok = await handleEdit(row.original.id, values);
      if (ok) {
        setValidationErrors({});
        mrtTable.setEditingRow(null);
      }
    },
    renderRowActions: ({ row, table: mrtTable }) => (
      <Box sx={{ display: "flex", gap: "0.5rem", flexWrap: "nowrap" }}>
        {isActivosSlice ? (
          <>
            <Tooltip title="Editar">
              <IconButton
                sx={{
                  color: COLORS.white,
                  transition: "color 0.2s ease, background-color 0.2s ease",
                  "&:hover": { color: COLORS.primary, backgroundColor: "rgba(1, 102, 255, 0.15)" },
                }}
                onClick={() => mrtTable.setEditingRow(row)}
              >
                <EditIcon fontSize="small" />
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
    renderTopToolbarCustomActions: ({ table: mrtTable }) =>
      isActivosSlice ? (
        <AppButton dsVariant="primary" dsSize="sm" startIcon={<AddIcon />} onClick={() => mrtTable.setCreatingRow(true)}>
          Crear nuevo user
        </AppButton>
      ) : null,
  });

  const tabIndex = slice === "activos" ? 0 : 1;

  return (
    <>
      <Box
        sx={{
          m: { xs: 1, sm: 0 },
          minHeight: "90vh",
          display: "flex",
          justifyContent: "center",
          alignItems: "flex-start",
          flexDirection: "column",
          gap: 2,
          width: "100%",
        }}
      >
        <Box width={{ xs: "100%", sm: 600, md: 1200 }} sx={{ maxWidth: "100%" }}>
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

          {serverError ? (
            <Alert severity="error" sx={{ mb: 2 }}>
              {serverError}
            </Alert>
          ) : null}

          <DataTableMrtShell loading={loading} loadingMode="progress">
            <MaterialReactTable table={table} />
          </DataTableMrtShell>
        </Box>

        <Box
          sx={{
            backgroundColor: "#1E2127",
            borderRadius: "16px",
            border: "1px solid #2c2f36",
            p: 3,
            mb: 3,
            width: { xs: "100%", sm: 600, md: 1200 },
            maxWidth: "100%",
          }}
        >
          <Typography variant="h6" sx={{ color: "white", mb: 2, fontWeight: 700 }}>
            CÓMO USAR
          </Typography>

          <Typography sx={{ mb: 1, color: "white" }}>
            1. En <b>Usuarios activos</b>, usá <b>Crear nuevo user</b> para dar de alta un usuario.
          </Typography>
          <Typography sx={{ mb: 1, color: "white" }}>
            2. Usá el ícono <b>Editar</b> para modificar datos de un usuario activo.
          </Typography>
          <Typography sx={{ mb: 1, color: "white" }}>
            3. Usá el ícono <b>Inactivar</b> para impedir el ingreso sin borrar el historial.
          </Typography>
          <Typography sx={{ mb: 2, color: "white" }}>
            4. En <b>Usuarios inactivos</b>, usá <b>Reactivar</b> para volver a habilitar el acceso.
          </Typography>

          <Box display="flex" gap={1} flexWrap="wrap">
            <Chip label="CARGANDO" sx={{ background: "#1976d2", color: "#fff" }} />
            <Chip label="ERROR" sx={{ background: "#d32f2f", color: "#fff" }} />
            <Chip label="ACTUALIZADO" sx={{ background: "#2e7d32", color: "#fff" }} />
          </Box>
        </Box>
      </Box>

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
