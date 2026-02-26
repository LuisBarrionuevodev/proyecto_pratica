import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
} from "material-react-table";
import { useMemo, useEffect, useState } from "react";
import { Alert, Box, Button, Chip, Typography } from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import AddIcon from "@mui/icons-material/Add";
import { apiClient } from "../../../api/apiClient";
import { TablaGestionUsuariosStyle } from "../../../styles/GestionDeUsuarioStyles";

type Usuario = {
  id: number;
  username: string;
  email: string;
  role: "admin" | "usuario";
  is_active?: boolean;
};

const TableGestionDeUsuarios = () => {
  const [data, setData] = useState<Usuario[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>(
    {}
  );
  const [serverError, setServerError] = useState("");

  // 🔹 Obtener usuarios
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

  // 🔹 Eliminar usuario
  const handleDelete = async (id: number) => {
    try {
      await apiClient.delete(`/api/admin/users/${id}`);
      setData((prev) => prev.filter((user) => user.id !== id));
      setServerError("");
    } catch (error) {
      console.error("Error al eliminar usuario:", error);
      setServerError("No se pudo eliminar el usuario.");
    }
  };

  const handleCreate = async (values: Record<string, unknown>) => {
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
    } catch (error) {
      console.error("Error al crear usuario:", error);
      setServerError("No se pudo crear el usuario. Revisá username/email/rol.");
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = async (userId: number, values: Record<string, unknown>) => {
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
    } catch (error) {
      console.error("Error al editar usuario:", error);
      setServerError("No se pudo actualizar el usuario.");
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

  const columns = useMemo<MRT_ColumnDef<Usuario>[]>(
    () => [
      {
        id: "acciones",
        header: "Acciones",
        enableSorting: false,
        enableEditing: false,
        Cell: ({ row, table }) => (
          <Box display="flex" gap={1}>
            <Button
              variant="contained"
              color="error"
              size="small"
              startIcon={<DeleteIcon />}
              onClick={() => handleDelete(row.original.id)}
            >
              Borrar
            </Button>

            <Button
              variant="contained"
              size="small"
              startIcon={<EditIcon />}
              sx={{
                backgroundColor: "#f0ad4e",
                "&:hover": { backgroundColor: "#ec971f" },
              }}
              onClick={() => table.setEditingRow(row)}
            >
              Modificar
            </Button>
          </Box>
        ),
      },
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

  const validateCreate = (values: Record<string, unknown>) => {
    const errors: Record<string, string> = {};
    if (!String(values.username ?? "").trim()) errors.username = "Usuario requerido";
    if (!String(values.email ?? "").trim()) errors.email = "Email requerido";
    if (!String(values.password ?? "").trim()) errors.password = "Contraseña requerida";
    if (!String(values.role ?? "").trim()) errors.role = "Rol requerido";
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const validateEdit = (values: Record<string, unknown>) => {
    const errors: Record<string, string> = {};
    if (!String(values.username ?? "").trim()) errors.username = "Usuario requerido";
    if (!String(values.email ?? "").trim()) errors.email = "Email requerido";
    if (!String(values.role ?? "").trim()) errors.role = "Rol requerido";
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const table = useMaterialReactTable({
    ...TablaGestionUsuariosStyle,
    columns,
    data,
    enableEditing: true,
    createDisplayMode: "row",
    editDisplayMode: "row",
    enableRowActions: false,
    getRowId: (row) => String(row.id),
    state: { isLoading: loading, isSaving: saving },
    onCreatingRowCancel: () => {
      setSaving(false);
      setValidationErrors({});
      setServerError("");
    },
    onCreatingRowSave: async ({ values, table }) => {
      if (!validateCreate(values)) {
        return;
      }
      await handleCreate(values);
      setValidationErrors({});
      table.setCreatingRow(null);
    },
    onEditingRowCancel: () => {
      setSaving(false);
      setValidationErrors({});
      setServerError("");
    },
    onEditingRowSave: async ({ row, values, table }) => {
      if (!validateEdit(values)) {
        return;
      }
      await handleEdit(row.original.id, values);
      setValidationErrors({});
      table.setEditingRow(null);
    },
    renderTopToolbarCustomActions: ({ table }) => (
      <Button
        variant="contained"
        color="success"
        startIcon={<AddIcon />}
        onClick={() => table.setCreatingRow(true)}
      >
        Agregar
      </Button>
    ),
  });

  return (
    <Box
      sx={{
        m: { xs: 1, sm: 0 },
        minHeight: "90vh",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        flexDirection:"column",
        gap:2
      }}
    >

      <Box width={{xs: 300, sm: 600,md:1200}}>
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
          <Typography variant="h6" sx={{ color:"white", mb: 2, fontWeight: 700 }}>
            CÓMO USAR
          </Typography>

          <Typography sx={{ mb: 1, color:"white",  }}>
            1. Usa <b>Agregar</b> para crear un nuevo usuario.
          </Typography>
          <Typography sx={{ mb: 1, color:"white",  }}>
            2. Usa <b>Modificar</b> para editar los datos de un usuario.
          </Typography>
          <Typography sx={{ mb: 1, color:"white",  }}>
            3. Usa <b>Borrar</b> para eliminar un usuario del sistema.
          </Typography>
          <Typography sx={{ mb: 2, color:"white",  }}>
            4. Los datos se cargan automáticamente desde el servidor.
          </Typography>

          <Box display="flex" gap={1} flexWrap="wrap">
            <Chip label="CARGANDO" sx={{ background: "#1976d2", color: "#fff" }} />
            <Chip label="ERROR" sx={{ background: "#d32f2f", color: "#fff" }} />
            <Chip label="ACTUALIZADO" sx={{ background: "#2e7d32", color: "#fff" }} />
          </Box>
        </Box>

    </Box>
  );

};

export default TableGestionDeUsuarios;