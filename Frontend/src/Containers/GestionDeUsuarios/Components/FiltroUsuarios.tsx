import { Box, Typography } from "@mui/material";
import { useState } from "react";
import SearchIcon from "@mui/icons-material/Search";
import ClearIcon from "@mui/icons-material/Clear";

import { AppButton, AppSelect, AppTextField } from "../../../ui";
import {
  filtroContainerStyles,
  filtroTitleStyles,
  filtroGridStyles,
  filtroItemStyles,
  filtroButtonsStyles,
  filtroButtonPrimaryStyles,
  filtroButtonSecondaryStyles,
} from "../../Actuaciones/styles/filtroStyles";

export type UsuariosFiltroAplicado = {
  texto: string;
  rol: "" | "admin" | "usuario" | "relevador";
};

interface FiltroUsuariosProps {
  onFiltrar: (filtros: UsuariosFiltroAplicado) => void;
  onLimpiar: () => void;
}

/**
 * Filtros de gestión de usuarios (mismo patrón visual que Relevamientos/Denuncias).
 */
const FiltroUsuarios = ({ onFiltrar, onLimpiar }: FiltroUsuariosProps) => {
  const [texto, setTexto] = useState("");
  const [rol, setRol] = useState<"" | "admin" | "usuario" | "relevador">("");

  const handleFiltrar = () => {
    onFiltrar({ texto: texto.trim(), rol });
  };

  const handleLimpiar = () => {
    setTexto("");
    setRol("");
    onLimpiar();
  };

  return (
    <Box sx={filtroContainerStyles}>
      <Typography sx={filtroTitleStyles}>Filtros de Usuarios</Typography>

      <Box sx={filtroGridStyles}>
        <Box sx={filtroItemStyles}>
          <AppTextField
            appearance="dense"
            fullWidth
            label="Texto (usuario o email)"
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            placeholder="nombre, apellido, email…"
            variant="outlined"
          />
        </Box>

        <Box sx={filtroItemStyles}>
          <AppSelect
            appearance="dense"
            fullWidth
            label="Rol"
            value={rol}
            onChange={(e) => setRol(e.target.value as "" | "admin" | "usuario" | "relevador")}
            variant="outlined"
            options={[
              { value: "", label: "Todos" },
              { value: "admin", label: "Admin" },
              { value: "usuario", label: "Usuario" },
              { value: "relevador", label: "Relevador" },
            ]}
          />
        </Box>
      </Box>

      <Box sx={filtroButtonsStyles}>
        <AppButton
          dsVariant="ghost"
          dsSize="sm"
          onClick={handleLimpiar}
          startIcon={<ClearIcon />}
          sx={filtroButtonSecondaryStyles}
        >
          Limpiar
        </AppButton>

        <AppButton
          dsVariant="primary"
          dsSize="sm"
          onClick={handleFiltrar}
          startIcon={<SearchIcon />}
          sx={filtroButtonPrimaryStyles}
        >
          Buscar
        </AppButton>
      </Box>
    </Box>
  );
};

export default FiltroUsuarios;
