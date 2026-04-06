import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
} from "material-react-table";
import { useMemo, useEffect, useState } from "react";
import { Alert, Box, Chip, IconButton, Snackbar, Tooltip, Typography } from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import AddIcon from "@mui/icons-material/Add";
import { apiClient } from "../../../api/apiClient";
import { DARK_TABLE_CONFIG } from "../../Actuaciones/styles/actuacionesTableStyles";
import { AppButton } from "../../../ui";

type Usuario = {
  id: number;
  username: string;
  email: string;
  role: "admin" | "usuario";
  is_active?: boolean;
  password?: string;
};

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const TableGestionDeUsuarios = () => {
  const [data, setData] = useState<Usuario[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const fetchUsuarios = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get<Usuario[]>("/api/admin/users");
      setData(response.data.filter((u) => u.is_active !== false));
      setServerError("");
    } catch (error) {
      console.error("Error al obtener usuarios:", error);
      setServerError("No se pudieron cargar los usuarios.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsuarios();
  }, []);

  const handleDelete = async (id: number) => {
    try {
      setSaving(true);
      await apiClient.delete(`/api/admin/users/${id}`);
      await fetchUsuarios();
      setServerError("");
      setSuccessMessage("Usuario eliminado correctamente.");
    } catch (error) {
      console.error("Error al eliminar usuario:", error);
      setServerError("No se pudo eliminar el usuario.");
    } finally {
      setSaving(false);
    }
  };

  const mapServerErrors = (error: any) => {
    const mapped: Record<string, string> = {};
    const fieldErrors = error?.response?.data?.errors;
    const detail = String(error?.response?.data?.detail ?? "");

    if (fieldErrors && typeof fieldErrors === "object") {
      Object.entries(fieldErrors as Record<string, string>).forEach(([key, message]) => {
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
      await fetchUsuarios();
      setSuccessMessage("Usuario creado correctamente.");
      return true;
    } catch (error) {
      console.error("Error al crear usuario:", error);
      const mappedErrors = mapServerErrors(error);
      if (Object.keys(mappedErrors).length > 0) {
        setValidationErrors((prev) => ({ ...prev, ...mappedErrors }));
      } else {
        setServerError("No se pudo crear el usuario. Revisá username/email/rol.");
      }
      return false;
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = async (
    userId: number,
    values: Record<string, unknown>
  ): Promise<boolean> => {
    try {
      setSaving(true);
      setServerError("");
      await apiClient.put(`/api/admin/users/${userId}`, {
        username: String(values.username ?? ""),
        email: String(values.email ?? ""),
        password: String(values.password ?? "").trim() || undefined,
        role: values.role === "admin" ? "admin" : "usuario",
      });
      await fetchUsuarios();
      setSuccessMessage("Usuario actualizado correctamente.");
      return true;
    } catch (error) {
      console.error("Error al editar usuario:", error);
      const mappedErrors = mapServerErrors(error);
      if (Object.keys(mappedErrors).length > 0) {
        setValidationErrors((prev) => ({ ...prev, ...mappedErrors }));
      } else {
        setServerError("No se pudo actualizar el usuario.");
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
        muiEditTextFieldProps: {
          required: true,
          error: !!validationErrors.role,
          helperText: validationErrors.role,
          onFocus: () => clearFieldError("role"),
        },
      },
    ],
    [validationErrors]
  );

  const table = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    columns,
    data,
    enableColumnFilters: false,
    enableRowSelection: false,
    positionGlobalFilter: "right",
    enableEditing: true,
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
    onCreatingRowSave: async ({ values, table }) => {
      if (!validateUser(values, true)) {
        return;
      }
      const ok = await handleCreate(values);
      if (ok) {
        setValidationErrors({});
        table.setCreatingRow(null);
      }
    },
    onEditingRowCancel: () => {
      setSaving(false);
      setValidationErrors({});
      setServerError("");
    },
    onEditingRowSave: async ({ row, values, table }) => {
      if (!validateUser(values, false)) {
        return;
      }
      const ok = await handleEdit(row.original.id, values);
      if (ok) {
        setValidationErrors({});
        table.setEditingRow(null);
      }
    },
    renderRowActions: ({ row, table }) => (
      <Box sx={{ display: "flex", gap: "0.5rem" }}>
        <Tooltip title="Editar">
          <IconButton onClick={() => table.setEditingRow(row)}>
            <EditIcon />
          </IconButton>
        </Tooltip>
        <Tooltip title="Eliminar">
          <IconButton
            color="error"
            onClick={() => {
              if (!window.confirm("¿Seguro que querés eliminar este usuario?")) return;
              handleDelete(row.original.id);
            }}
          >
            <DeleteIcon />
          </IconButton>
        </Tooltip>
      </Box>
    ),
    renderTopToolbarCustomActions: ({ table }) => (
      <AppButton dsVariant="primary" dsSize="sm" startIcon={<AddIcon />} onClick={() => table.setCreatingRow(true)}>
        Crear nuevo user
      </AppButton>
    ),
  });

  return (
    <>
      <Box
      sx={{
        m: { xs: 1, sm: 0 },
        minHeight: "90vh",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "column",
        gap: 2,
      }}
    >
      <Box width={{ xs: 300, sm: 600, md: 1200 }}>
        {serverError ? (
          <Alert severity="error" sx={{ mb: 2 }}>
            {serverError}
          </Alert>
        ) : null}
        <MaterialReactTable table={table} />
      </Box>

      <Box
        sx={{
          backgroundColor: "#1E2127",
          borderRadius: "16px",
          border: "1px solid #2c2f36",
          p: 3,
          mb: 3,
        }}
      >
        <Typography variant="h6" sx={{ color: "white", mb: 2, fontWeight: 700 }}>
          CÓMO USAR
        </Typography>

        <Typography sx={{ mb: 1, color: "white" }}>
          1. Usa <b>Crear nuevo user</b> para crear un nuevo usuario.
        </Typography>
        <Typography sx={{ mb: 1, color: "white" }}>
          2. Usa el ícono <b>Editar</b> para modificar un usuario.
        </Typography>
        <Typography sx={{ mb: 1, color: "white" }}>
          3. Usa el ícono <b>Eliminar</b> para desactivar un usuario.
        </Typography>
        <Typography sx={{ mb: 2, color: "white" }}>
          4. Los datos se recargan automáticamente tras cada acción.
        </Typography>

        <Box display="flex" gap={1} flexWrap="wrap">
          <Chip label="CARGANDO" sx={{ background: "#1976d2", color: "#fff" }} />
          <Chip label="ERROR" sx={{ background: "#d32f2f", color: "#fff" }} />
          <Chip label="ACTUALIZADO" sx={{ background: "#2e7d32", color: "#fff" }} />
        </Box>
      </Box>
      </Box>
      <Snackbar
        open={!!successMessage}
        autoHideDuration={2500}
        onClose={() => setSuccessMessage("")}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert severity="success" variant="filled" onClose={() => setSuccessMessage("")}>
          {successMessage}
        </Alert>
      </Snackbar>
    </>
  );

};

export default TableGestionDeUsuarios;