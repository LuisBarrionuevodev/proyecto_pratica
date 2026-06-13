import { Box, Typography } from "@mui/material";
import { useEffect, useState } from "react";
import SearchIcon from "@mui/icons-material/Search";
import ClearIcon from "@mui/icons-material/Clear";

import { fetchInspectores, type CatalogItem } from "../../../api/gridApi";
import { getCurrentMonthRange } from "../../../utils/dateRange";
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

interface FiltroRelevamientosProps {
  onFiltrar: (filtros: {
    desde: string | null;
    hasta: string | null;
    inspector: string | null;
    calle: string | null;
    numero: string | null;
  }) => void;
  onLimpiarLista?: () => void;
}

const FiltroRelevamientos = ({ onFiltrar, onLimpiarLista }: FiltroRelevamientosProps) => {
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
        setCatalogInspectores([...new Set(resp.items.map((i: CatalogItem) => i.nombre))]);
      } catch (error) {
        console.error("Error cargando inspectores:", error);
      }
    };
    loadCatalogs();
  }, []);

  const handleFiltrar = () => {
    if (!desde && !hasta) {
      const range = getCurrentMonthRange();
      setDesde(range.desde);
      setHasta(range.hasta);
      onFiltrar({
        desde: range.desde,
        hasta: range.hasta,
        inspector: inspector || null,
        calle: calle || null,
        numero: numero || null,
      });
      return;
    }
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
    onLimpiarLista?.();
  };

  return (
    <Box sx={filtroContainerStyles}>
      <Typography sx={filtroTitleStyles}>Filtros de Relevamientos</Typography>
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
            label="Inspector"
            value={inspector}
            onChange={(e) => setInspector(e.target.value)}
            variant="outlined"
            options={[
              { value: "", label: "Todos" },
              ...catalogInspectores.map((i) => ({ value: i, label: i })),
            ]}
          />
        </Box>

        <Box sx={filtroItemStyles}>
          <AppTextField
            appearance="dense"
            fullWidth
            label="Calle"
            value={calle}
            onChange={(e) => setCalle(e.target.value)}
            variant="outlined"
          />
        </Box>

        <Box sx={filtroItemStyles}>
          <AppTextField
            appearance="dense"
            fullWidth
            label="Numero"
            value={numero}
            onChange={(e) => setNumero(e.target.value)}
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

export default FiltroRelevamientos;
