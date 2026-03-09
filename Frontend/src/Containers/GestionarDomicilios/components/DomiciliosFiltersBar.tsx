import { Box, Button, MenuItem, Select, TextField } from "@mui/material";
import { filtroItemStyles } from "../../Actuaciones/styles/filtroStyles";
import type { DomiciliosFilters } from "../types";

interface DomiciliosFiltersBarProps {
  filters: DomiciliosFilters;
  onChange: (next: DomiciliosFilters) => void;
  onFiltrar: () => void;
  onLimpiar: () => void;
}

const DomiciliosFiltersBar = ({
  filters,
  onChange,
  onFiltrar,
  onLimpiar,
}: DomiciliosFiltersBarProps) => {
  return (
    <Box
      sx={{
        p: 1,
        bgcolor: "#2B2E34",
        display: "flex",
        gap: 1,
        flexWrap: "wrap",
        mb: 2,
        alignItems: "center",
      }}
    >
      <TextField
        sx={filtroItemStyles}
        size="small"
        type="date"
        label="Desde"
        value={filters.desde}
        onChange={(e) => onChange({ ...filters, desde: e.target.value })}
      />
      <TextField
        sx={filtroItemStyles}
        size="small"
        type="date"
        label="Hasta"
        value={filters.hasta}
        onChange={(e) => onChange({ ...filters, hasta: e.target.value })}
      />
      <Select
        sx={{ color: "white" }}
        size="small"
        value={filters.scope}
        onChange={(e) =>
          onChange({
            ...filters,
            scope: e.target.value as DomiciliosFilters["scope"],
          })
        }
        displayEmpty
      >
        <MenuItem sx={{ color: "black" }} value="all">
          Todos
        </MenuItem>
        <MenuItem sx={{ color: "black" }} value="actuaciones">
          Actuaciones
        </MenuItem>
        <MenuItem sx={{ color: "black" }} value="relevamientos">
          Relevamientos
        </MenuItem>
      </Select>
      <Button variant="contained" onClick={onFiltrar}>
        Filtrar
      </Button>
      <Button variant="outlined" onClick={onLimpiar}>
        Limpiar
      </Button>
    </Box>
  );
};

export default DomiciliosFiltersBar;
