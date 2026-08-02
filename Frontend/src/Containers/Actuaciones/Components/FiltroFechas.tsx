import { Box, Divider, FormControlLabel, Switch, Typography } from "@mui/material";
import { useEffect, useState } from "react";
import SearchIcon from "@mui/icons-material/Search";
import ClearIcon from "@mui/icons-material/Clear";

import { fetchTiposActuacion, fetchContraproducencias } from "../../../api/gridApi";
import { AppButton, AppSelect, AppTextField } from "../../../ui";

import {
    filtroContainerStyles,
    filtroTitleStyles,
    filtroGridStyles,
    filtroItemStyles,
    filtroButtonsStyles,
    filtroButtonPrimaryStyles,
    filtroButtonSecondaryStyles,
    filtroSectionTitleStyles,
} from "../styles/filtroStyles";
import type { IActuacionesListFilters } from "../../../api/actuacionesListApi";
import {
  ACTUACIONES_BUSQUEDA_ESPECIFICA_MIN_CHARS,
  actuacionesBusquedaEspecificaValida,
  buildActuacionesFiltroPayload,
} from "../utils/buildActuacionesFiltroPayload";

export type ActuacionesFiltroPayload = IActuacionesListFilters;

interface FiltroFechasProps {
  onFiltrar: (filtros: IActuacionesListFilters) => void;
  initialDesde?: string;
  initialHasta?: string;
  onLimpiarLista?: () => void;
}

/**
 * Filtros de Actuaciones: búsqueda específica (acta/global) separada del rango de fechas.
 */
const FiltroFechas = ({
  onFiltrar,
  initialDesde = "",
  initialHasta = "",
  onLimpiarLista,
}: FiltroFechasProps) => {
  const [desde, setDesde] = useState<string>(initialDesde);
  const [hasta, setHasta] = useState<string>(initialHasta);
  const [tipo, setTipo] = useState<string>("");
  const [contraproducencia, setContraproducencia] = useState<string>("");
  const [busquedaEspecifica, setBusquedaEspecifica] = useState<string>("");
  const [combinarConRango, setCombinarConRango] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [catalogTipos, setCatalogTipos] = useState<string[]>([]);
  const [catalogContras, setCatalogContras] = useState<string[]>([]);

  useEffect(() => {
    const loadCatalogs = async () => {
      try {
        const [tipos, contras] = await Promise.all([fetchTiposActuacion(), fetchContraproducencias()]);
        setCatalogTipos([...new Set(tipos.items.map((t: { nombre: string }) => t.nombre))]);
        setCatalogContras([...new Set(contras.items.map((c: { nombre: string }) => c.nombre))]);
      } catch (error) {
        console.error("Error cargando catálogos de filtros:", error);
      }
    };
    loadCatalogs();
  }, []);

  const hasSpecificDraft = busquedaEspecifica.trim().length > 0;
  const hasRangeDraft = Boolean(desde || hasta || tipo || contraproducencia);

  const handleFiltrar = () => {
    const trimmed = busquedaEspecifica.trim();
    if (trimmed.length > 0 && !actuacionesBusquedaEspecificaValida(trimmed)) {
      setValidationError(
        `Ingresá al menos ${ACTUACIONES_BUSQUEDA_ESPECIFICA_MIN_CHARS} caracteres para la búsqueda específica.`
      );
      return;
    }
    if (!trimmed && !hasRangeDraft) {
      setValidationError("Completá la búsqueda específica o el rango de fechas y filtros.");
      return;
    }
    setValidationError(null);
    onFiltrar(
      buildActuacionesFiltroPayload({
        desde,
        hasta,
        tipo,
        contraproducencia,
        busquedaEspecifica,
        combinarConRango,
      })
    );
  };

  const handleLimpiar = () => {
    setDesde(initialDesde);
    setHasta(initialHasta);
    setTipo("");
    setContraproducencia("");
    setBusquedaEspecifica("");
    setCombinarConRango(false);
    setValidationError(null);
    onLimpiarLista?.();
  };

  const tipoOptions = [{ value: "", label: "Todos" }, ...catalogTipos.map((t) => ({ value: t, label: t }))];
  const contraproducenciaOptions = [
    { value: "", label: "Todas" },
    ...catalogContras.map((c) => ({ value: c, label: c })),
  ];

  return (
    <Box sx={filtroContainerStyles}>
      <Typography sx={filtroTitleStyles}>Filtros de búsqueda</Typography>

      <Typography sx={filtroSectionTitleStyles}>Búsqueda específica</Typography>

      <Box sx={{ ...filtroGridStyles, gridTemplateColumns: { xs: "1fr", md: "1fr" }, mb: 1 }}>
        <Box sx={filtroItemStyles}>
          <AppTextField
            appearance="dense"
            fullWidth
            label="Buscar por acta o texto"
            value={busquedaEspecifica}
            onChange={(e) => {
              setBusquedaEspecifica(e.target.value);
              if (validationError) setValidationError(null);
            }}
            placeholder="Nº de acta, calle, expediente, oficio…"
            variant="outlined"
            onKeyDown={(e) => {
              if (e.key === "Enter") handleFiltrar();
            }}
          />
        </Box>
      </Box>

      {hasSpecificDraft && (
        <FormControlLabel
          sx={{
            mb: 1.5,
            ml: 0,
            "& .MuiFormControlLabel-label": {
              color: "rgba(255,255,255,0.85)",
              fontFamily: '"Tactic Sans", sans-serif',
              fontSize: "0.85rem",
            },
          }}
          control={
            <Switch
              size="small"
              checked={combinarConRango}
              onChange={(e) => setCombinarConRango(e.target.checked)}
              color="primary"
            />
          }
          label="Combinar también con rango de fechas y filtros"
        />
      )}

      <Divider sx={{ borderColor: "rgba(255,255,255,0.12)", my: 2 }} />

      <Typography sx={filtroSectionTitleStyles}>Rango de fechas</Typography>

      <Box sx={filtroGridStyles}>
        <Box sx={filtroItemStyles}>
          <AppTextField
            appearance="dense"
            fullWidth
            type="date"
            label="Desde (opcional)"
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
            label="Hasta (opcional)"
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
            label="Tipo de Actuación"
            value={tipo}
            onChange={(e) => setTipo(e.target.value)}
            variant="outlined"
            options={tipoOptions}
          />
        </Box>

        <Box sx={filtroItemStyles}>
          <AppSelect
            appearance="dense"
            fullWidth
            label="Contraproducencia"
            value={contraproducencia}
            onChange={(e) => setContraproducencia(e.target.value)}
            variant="outlined"
            options={contraproducenciaOptions}
          />
        </Box>
      </Box>

      {validationError && (
        <Typography sx={{ color: "#E53935", fontSize: "0.85rem", mb: 1.5 }}>{validationError}</Typography>
      )}

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

export default FiltroFechas;
