import { Box, Typography } from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import ClearIcon from "@mui/icons-material/Clear";

import { AppButton, AppTextField } from "../../../ui";

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
          <AppTextField
            appearance="dense"
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
          <AppTextField
            appearance="dense"
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
        <AppButton
          dsVariant="ghost"
          dsSize="sm"
          onClick={onLimpiar}
          startIcon={<ClearIcon />}
          sx={filtroButtonSecondaryStyles}
        >
          Limpiar
        </AppButton>

        <AppButton
          dsVariant="primary"
          dsSize="sm"
          onClick={onFiltrar}
          startIcon={<SearchIcon />}
          sx={filtroButtonPrimaryStyles}
        >
          Filtrar
        </AppButton>
      </Box>
    </Box>
  );
};

export default FiltroPendientes;
