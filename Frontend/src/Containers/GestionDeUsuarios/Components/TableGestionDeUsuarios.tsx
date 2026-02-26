import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
} from "material-react-table";
import { useMemo, useEffect, useState } from "react";
import { Box, Button, Chip, Typography } from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import AddIcon from "@mui/icons-material/Add";
import axios from "axios";
import { TablaGestionUsuariosStyle } from "../../../styles/GestionDeUsuarioStyles";

type Usuario = {
  id: number;
  nombre: string;
  rol: "Administrador" | "Usuario" | "Viewer";
  contraseña: string;
};

const TableGestionDeUsuarios = () => {
  const [data, setData] = useState<Usuario[]>([]);
  const [loading, setLoading] = useState(false);

  // 🔹 Obtener usuarios
  const fetchUsuarios = async () => {
    try {
      setLoading(true);
      const response = await axios.get<Usuario[]>(
        "http://localhost:3000/api/usuarios"
      );
      setData(response.data);
    } catch (error) {
      console.error("Error al obtener usuarios:", error);
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
      await axios.delete(`http://localhost:3000/api/usuarios/${id}`);
      setData((prev) => prev.filter((user) => user.id !== id));
    } catch (error) {
      console.error("Error al eliminar usuario:", error);
    }
  };

  const columns = useMemo<MRT_ColumnDef<Usuario>[]>(
    () => [
      { accessorKey: "id", header: "ID", size: 60 },
      { accessorKey: "nombre", header: "Nombre" },
      { accessorKey: "rol", header: "Rol" },
      { accessorKey: "contraseña", header: "Contraseña" },
      {
        id: "acciones",
        header: "Acciones",
        enableSorting: false,
        Cell: ({ row }) => (
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
              onClick={() => console.log("Editar", row.original)}
            >
              Modificar
            </Button>
          </Box>
        ),
      },
    ],
    []
  );

  const table = useMaterialReactTable({
    ...TablaGestionUsuariosStyle,
    columns,
    data,
    state: { isLoading: loading },
    renderTopToolbarCustomActions: () => (
      <Button
        variant="contained"
        color="success"
        startIcon={<AddIcon />}
        onClick={() => console.log("Abrir dialog para crear")}
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