import { Box, Typography } from "@mui/material";
import { useState } from "react";
import SearchIcon from "@mui/icons-material/Search";
import ClearIcon from "@mui/icons-material/Clear";
import { AppButton, AppTextField } from "../../../ui";
import {
  filtroButtonPrimaryStyles,
  filtroButtonSecondaryStyles,
  filtroButtonsStyles,
  filtroContainerStyles,
  filtroGridStyles,
  filtroItemStyles,
  filtroTitleStyles,
} from "../../Actuaciones/styles/filtroStyles";

interface FiltroDenunciasProps {
  variant?: "pendientes" | "procesados";
  onFiltrar: (filters: { desde: string | null; hasta: string | null }) => void;
  onLimpiarLista?: () => void;
}

const FiltroDenuncias = ({ onFiltrar, onLimpiarLista }: FiltroDenunciasProps) => {
  const [desde, setDesde] = useState<string>("");
  const [hasta, setHasta] = useState<string>("");
  const handleFiltrar = () => {
    onFiltrar({
      desde: desde || null,
      hasta: hasta || null,
    });
  };

  const handleLimpiar = () => {
    setDesde("");
    setHasta("");
    onLimpiarLista?.();
  };

  return (
    <Box sx={filtroContainerStyles}>
      <Typography sx={filtroTitleStyles}>Filtros de Denuncias</Typography>
      <Box sx={filtroGridStyles}>
        <Box sx={filtroItemStyles}>
          <AppTextField
            appearance="dense"
            fullWidth
            type="date"
            label="Desde"
            value={desde}
            onChange={(e) => setDesde(e.target.value)}
            InputLabelProps={{ shrink: true }}
            variant="outlined"
          />
        </Box>
        <Box sx={filtroItemStyles}>
          <AppTextField
            appearance="dense"
            fullWidth
            type="date"
            label="Hasta"
            value={hasta}
            onChange={(e) => setHasta(e.target.value)}
            InputLabelProps={{ shrink: true }}
            variant="outlined"
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
          Filtrar
        </AppButton>
      </Box>
    </Box>
  );
};

export default FiltroDenuncias;
