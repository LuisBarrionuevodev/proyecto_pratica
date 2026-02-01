import { Box, TextField, Button, Typography } from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import ClearIcon from "@mui/icons-material/Clear";

import {
  filtroContainerStyles,
  filtroTitleStyles,
  filtroGridStyles,
  filtroItemStyles,
  filtroButtonsStyles,
  filtroButtonPrimaryStyles,
  filtroButtonSecondaryStyles,
} from "../styles/filtroStyles";

interface FiltroPendientesProps {
  desde: string;
  hasta: string;
  onChangeDesde: (value: string) => void;
  onChangeHasta: (value: string) => void;
  onFiltrar: () => void;
  onLimpiar: () => void;
  title?: string;
}

const FiltroPendientes = ({
  desde,
  hasta,
  onChangeDesde,
  onChangeHasta,
  onFiltrar,
  onLimpiar,
  title = "Filtros de Pendientes",
}: FiltroPendientesProps) => {
  return (
    <Box sx={filtroContainerStyles}>
      <Typography sx={filtroTitleStyles}>{title}</Typography>

      <Box sx={filtroGridStyles}>
        <Box sx={filtroItemStyles}>
          <TextField
            fullWidth
            type="date"
            label="Desde"
            value={desde}
            onChange={(e) => onChangeDesde(e.target.value)}
            InputLabelProps={{ shrink: true }}
            variant="outlined"
          />
        </Box>

        <Box sx={filtroItemStyles}>
          <TextField
            fullWidth
            type="date"
            label="Hasta"
            value={hasta}
            onChange={(e) => onChangeHasta(e.target.value)}
            InputLabelProps={{ shrink: true }}
            variant="outlined"
          />
        </Box>
      </Box>

      <Box sx={filtroButtonsStyles}>
        <Button
          onClick={onLimpiar}
          startIcon={<ClearIcon />}
          sx={filtroButtonSecondaryStyles}
        >
          Limpiar
        </Button>

        <Button
          onClick={onFiltrar}
          startIcon={<SearchIcon />}
          sx={filtroButtonPrimaryStyles}
          variant="contained"
        >
          Filtrar
        </Button>
      </Box>
    </Box>
  );
};

export default FiltroPendientes;
