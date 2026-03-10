import { Box, Button, MenuItem, TextField, Typography } from "@mui/material";
import { useMemo, useState } from "react";
import SearchIcon from "@mui/icons-material/Search";
import ClearIcon from "@mui/icons-material/Clear";
import { getCurrentMonthRange } from "../../../utils/dateRange";
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
  onFiltrar: (filters: {
    desde: string | null;
    hasta: string | null;
    estado: "all" | "hechas" | "no_hechas";
  }) => void;
}

const FiltroDenuncias = ({ onFiltrar }: FiltroDenunciasProps) => {
  const defaultRange = useMemo(() => getCurrentMonthRange(), []);
  const [desde, setDesde] = useState<string>(defaultRange.desde);
  const [hasta, setHasta] = useState<string>(defaultRange.hasta);
  const [estado, setEstado] = useState<"all" | "hechas" | "no_hechas">("all");

  const handleFiltrar = () => {
    onFiltrar({
      desde: desde || null,
      hasta: hasta || null,
      estado,
    });
  };

  const handleLimpiar = () => {
    const range = getCurrentMonthRange();
    setDesde(range.desde);
    setHasta(range.hasta);
    setEstado("all");
  };

  return (
    <Box sx={filtroContainerStyles}>
      <Typography sx={filtroTitleStyles}>Filtros de Denuncias</Typography>
      <Box sx={filtroGridStyles}>
        <Box sx={filtroItemStyles}>
          <TextField
            fullWidth
            type="date"
            label="Desde"
            value={desde}
            onChange={(e) => setDesde(e.target.value)}
            InputLabelProps={{ shrink: true }}
          />
        </Box>
        <Box sx={filtroItemStyles}>
          <TextField
            fullWidth
            type="date"
            label="Hasta"
            value={hasta}
            onChange={(e) => setHasta(e.target.value)}
            InputLabelProps={{ shrink: true }}
          />
        </Box>
        <Box sx={filtroItemStyles}>
          <TextField
            fullWidth
            select
            label="Estado"
            value={estado}
            disabled
            helperText="En gestión operativa se muestran solo pendientes."
            onChange={(e) => setEstado(e.target.value as "all" | "hechas" | "no_hechas")}
          >
            <MenuItem value="all">Todas</MenuItem>
            <MenuItem value="hechas">Hechas</MenuItem>
            <MenuItem value="no_hechas">No hechas</MenuItem>
          </TextField>
        </Box>
      </Box>
      <Box sx={filtroButtonsStyles}>
        <Button onClick={handleLimpiar} startIcon={<ClearIcon />} sx={filtroButtonSecondaryStyles}>
          Limpiar
        </Button>
        <Button
          onClick={handleFiltrar}
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

export default FiltroDenuncias;

