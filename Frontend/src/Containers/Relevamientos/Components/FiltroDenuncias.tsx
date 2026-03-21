import { Box, Typography } from "@mui/material";
import { useMemo, useState } from "react";
import SearchIcon from "@mui/icons-material/Search";
import ClearIcon from "@mui/icons-material/Clear";
import { getCurrentMonthRange } from "../../../utils/dateRange";
import { AppButton, AppSelect, AppTextField } from "../../../ui";
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
    onFiltrar({
      desde: range.desde,
      hasta: range.hasta,
      estado: "all",
    });
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
        <Box sx={filtroItemStyles}>
          <AppSelect
            appearance="dense"
            fullWidth
            label="Estado"
            value={estado}
            disabled
            helperText="En gestión operativa se muestran solo pendientes."
            onChange={(e) => setEstado(e.target.value as "all" | "hechas" | "no_hechas")}
            variant="outlined"
            options={[
              { value: "all", label: "Todas" },
              { value: "hechas", label: "Hechas" },
              { value: "no_hechas", label: "No hechas" },
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
          Filtrar
        </AppButton>
      </Box>
    </Box>
  );
};

export default FiltroDenuncias;
