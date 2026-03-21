import ClearIcon from "@mui/icons-material/Clear";
import SearchIcon from "@mui/icons-material/Search";
import { Box, Typography } from "@mui/material";

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
import type { DomiciliosFilters } from "../types";

interface DomiciliosFiltersBarProps {
  filters: DomiciliosFilters;
  onChange: (next: DomiciliosFilters) => void;
  onFiltrar: () => void;
  onLimpiar: () => void;
}

/**
 * Bloque Desde / Hasta / Alcance con el mismo lenguaje visual que filtros de relevamientos.
 */
const DomiciliosFiltersBar = ({
  filters,
  onChange,
  onFiltrar,
  onLimpiar,
}: DomiciliosFiltersBarProps) => {
  return (
    <Box sx={filtroContainerStyles}>
      <Typography sx={filtroTitleStyles}>Filtros</Typography>
      <Box sx={filtroGridStyles}>
        <Box sx={filtroItemStyles}>
          <AppTextField
            appearance="dense"
            fullWidth
            type="date"
            label="Desde"
            value={filters.desde}
            onChange={(e) => onChange({ ...filters, desde: e.target.value })}
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
            value={filters.hasta}
            onChange={(e) => onChange({ ...filters, hasta: e.target.value })}
            InputLabelProps={{ shrink: true }}
            variant="outlined"
          />
        </Box>
        <Box sx={filtroItemStyles}>
          <AppSelect
            appearance="dense"
            fullWidth
            label="Estado"
            value={filters.scope}
            onChange={(e) =>
              onChange({
                ...filters,
                scope: e.target.value as DomiciliosFilters["scope"],
              })
            }
            variant="outlined"
            options={[
              { value: "all", label: "Todos" },
              { value: "actuaciones", label: "Actuaciones" },
              { value: "relevamientos", label: "Relevamientos" },
            ]}
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

export default DomiciliosFiltersBar;
