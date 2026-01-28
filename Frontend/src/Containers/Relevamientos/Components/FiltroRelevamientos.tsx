import { Box, TextField, Button, MenuItem, Typography } from "@mui/material";
import { useEffect, useState } from "react";
import SearchIcon from "@mui/icons-material/Search";
import ClearIcon from "@mui/icons-material/Clear";

import { fetchInspectores } from "../../../api/gridApi";
import {
  filtroContainerStyles,
  filtroTitleStyles,
  filtroGridStyles,
  filtroItemStyles,
  filtroButtonsStyles,
  filtroButtonPrimaryStyles,
  filtroButtonSecondaryStyles,
} from "../../Actuaciones/styles/filtroStyles";

interface FiltroRelevamientosProps {
  onFiltrar: (filtros: {
    desde: string | null;
    hasta: string | null;
    inspector: string | null;
    calle: string | null;
    numero: string | null;
  }) => void;
}

const FiltroRelevamientos = ({ onFiltrar }: FiltroRelevamientosProps) => {
  const [desde, setDesde] = useState<string>("");
  const [hasta, setHasta] = useState<string>("");
  const [inspector, setInspector] = useState<string>("");
  const [calle, setCalle] = useState<string>("");
  const [numero, setNumero] = useState<string>("");
  const [catalogInspectores, setCatalogInspectores] = useState<string[]>([]);

  useEffect(() => {
    const loadCatalogs = async () => {
      try {
        const resp = await fetchInspectores();
        setCatalogInspectores([...new Set(resp.items.map((i: any) => i.nombre))]);
      } catch (error) {
        console.error("Error cargando inspectores:", error);
      }
    };
    loadCatalogs();
  }, []);

  const handleFiltrar = () => {
    onFiltrar({
      desde: desde || null,
      hasta: hasta || null,
      inspector: inspector || null,
      calle: calle || null,
      numero: numero || null,
    });
  };

  const handleLimpiar = () => {
    setDesde("");
    setHasta("");
    setInspector("");
    setCalle("");
    setNumero("");
  };

  return (
    <Box sx={filtroContainerStyles}>
      <Typography sx={filtroTitleStyles}>Filtros de Relevamientos</Typography>
      <Box sx={filtroGridStyles}>
        <Box sx={filtroItemStyles}>
          <TextField
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
          <TextField
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
          <TextField
            fullWidth
            select
            label="Inspector"
            value={inspector}
            onChange={(e) => setInspector(e.target.value)}
            variant="outlined"
          >
            <MenuItem value="">Todos</MenuItem>
            {catalogInspectores.map((i) => (
              <MenuItem key={i} value={i}>{i}</MenuItem>
            ))}
          </TextField>
        </Box>

        <Box sx={filtroItemStyles}>
          <TextField
            fullWidth
            label="Calle"
            value={calle}
            onChange={(e) => setCalle(e.target.value)}
            variant="outlined"
          />
        </Box>

        <Box sx={filtroItemStyles}>
          <TextField
            fullWidth
            label="Numero"
            value={numero}
            onChange={(e) => setNumero(e.target.value)}
            variant="outlined"
          />
        </Box>
      </Box>

      <Box sx={filtroButtonsStyles}>
        <Button
          onClick={handleLimpiar}
          startIcon={<ClearIcon />}
          sx={filtroButtonSecondaryStyles}
        >
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

export default FiltroRelevamientos;
