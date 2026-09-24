import { Box, Typography } from "@mui/material";
import { useEffect, useState } from "react";
import SearchIcon from "@mui/icons-material/Search";
import ClearIcon from "@mui/icons-material/Clear";

import { fetchRelevadores, type CatalogItem } from "../../../api/gridApi";
import { fetchDistritosCatalogo, type DistritoCatalogoItem } from "../../../api/geolocalizacionApi";
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

export type RelevamientosFiltrosForm = {
  desde: string | null;
  hasta: string | null;
  relevador: string | null;
  calle: string | null;
  numero: string | null;
  esta_abierto: boolean | null;
  distrito_id: number | null;
};

interface FiltroRelevamientosProps {
  onFiltrar: (filtros: RelevamientosFiltrosForm) => void;
  onLimpiarLista?: () => void;
}

const FiltroRelevamientos = ({ onFiltrar, onLimpiarLista }: FiltroRelevamientosProps) => {
  const [desde, setDesde] = useState<string>("");
  const [hasta, setHasta] = useState<string>("");
  const [relevador, setRelevador] = useState<string>("");
  const [calle, setCalle] = useState<string>("");
  const [numero, setNumero] = useState<string>("");
  const [estaAbierto, setEstaAbierto] = useState<string>("");
  const [distritoId, setDistritoId] = useState<string>("");
  const [catalogRelevadores, setCatalogRelevadores] = useState<string[]>([]);
  const [catalogDistritos, setCatalogDistritos] = useState<DistritoCatalogoItem[]>([]);

  useEffect(() => {
    const loadCatalogs = async () => {
      try {
        const [relevadoresResp, distritosResp] = await Promise.all([
          fetchRelevadores(),
          fetchDistritosCatalogo(),
        ]);
        setCatalogRelevadores([...new Set(relevadoresResp.items.map((i: CatalogItem) => i.nombre))]);
        setCatalogDistritos(distritosResp.items);
      } catch (error) {
        console.error("Error cargando catálogos de filtros:", error);
      }
    };
    loadCatalogs();
  }, []);

  const buildPayload = (desdeVal: string | null, hastaVal: string | null): RelevamientosFiltrosForm => {
    const estaAbiertoParsed =
      estaAbierto === "true" ? true : estaAbierto === "false" ? false : null;
    const distritoParsed =
      distritoId && Number(distritoId) > 0 ? Number(distritoId) : null;
    return {
      desde: desdeVal,
      hasta: hastaVal,
      relevador: relevador || null,
      calle: calle || null,
      numero: numero || null,
      esta_abierto: estaAbiertoParsed,
      distrito_id: distritoParsed,
    };
  };

  const handleFiltrar = () => {
    if (!desde && !hasta) {
      const range = getCurrentMonthRange();
      setDesde(range.desde);
      setHasta(range.hasta);
      onFiltrar(buildPayload(range.desde, range.hasta));
      return;
    }
    onFiltrar(buildPayload(desde || null, hasta || null));
  };

  const handleLimpiar = () => {
    setDesde("");
    setHasta("");
    setRelevador("");
    setCalle("");
    setNumero("");
    setEstaAbierto("");
    setDistritoId("");
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
            label="Relevador"
            value={relevador}
            onChange={(e) => setRelevador(e.target.value)}
            variant="outlined"
            options={[
              { value: "", label: "Todos" },
              ...catalogRelevadores.map((i) => ({ value: i, label: i })),
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
            label="Número / esquina"
            value={numero}
            onChange={(e) => setNumero(e.target.value)}
            variant="outlined"
          />
        </Box>

        <Box sx={filtroItemStyles}>
          <AppSelect
            appearance="dense"
            fullWidth
            label="Está abierto"
            value={estaAbierto}
            onChange={(e) => setEstaAbierto(e.target.value)}
            variant="outlined"
            options={[
              { value: "", label: "Todos" },
              { value: "true", label: "Sí" },
              { value: "false", label: "No" },
            ]}
          />
        </Box>

        <Box sx={filtroItemStyles}>
          <AppSelect
            appearance="dense"
            fullWidth
            label="Distrito"
            value={distritoId}
            onChange={(e) => setDistritoId(e.target.value)}
            variant="outlined"
            options={[
              { value: "", label: "Todos" },
              ...catalogDistritos.map((d) => ({ value: String(d.id), label: d.nombre })),
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

export default FiltroRelevamientos;
