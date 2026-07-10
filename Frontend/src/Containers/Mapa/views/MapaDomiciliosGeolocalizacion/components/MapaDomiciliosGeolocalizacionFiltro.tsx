import ClearIcon from "@mui/icons-material/Clear";
import SearchIcon from "@mui/icons-material/Search";
import {
  Box,
  Chip,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";

import type { GestionDomiciliosStatusOperativo, GestionDomiciliosSummary } from "../../../../../api/gestionDomiciliosApi";
import { AppButton, AppTextField } from "../../../../../ui";
import {
  filtroButtonPrimaryStyles,
  filtroButtonSecondaryStyles,
  filtroButtonsStyles,
  filtroContainerStyles,
  filtroGridStyles,
  filtroItemStyles,
  filtroTitleStyles,
} from "../../../../Actuaciones/styles/filtroStyles";
import {
  glassSecondaryTabsSx,
  glassTabsSecondaryPanelBarSx,
  moduleFiltersSurfaceSx,
} from "../../../../../styles/GlassStyles";
import {
  formatGestionDomiciliosSummaryLine,
  GESTION_DOMICILIOS_FILTROS,
  MAPA_DOMICILIOS_SUBTABS,
} from "../mapaDomiciliosOperativoFilters";

export type MapaDomiciliosGeolocalizacionFilterVariant = "dropdown" | "chips" | "mapa";

type Props = {
  statusOperativo: GestionDomiciliosStatusOperativo;
  onStatusChange: (value: GestionDomiciliosStatusOperativo) => void;
  searchQ: string;
  onSearchChange: (value: string) => void;
  onFiltrar?: () => void;
  onLimpiar?: () => void;
  summary: GestionDomiciliosSummary | null;
  loading?: boolean;
  filterVariant?: MapaDomiciliosGeolocalizacionFilterVariant;
};

export function MapaDomiciliosGeolocalizacionFiltro({
  statusOperativo,
  onStatusChange,
  searchQ,
  onSearchChange,
  onFiltrar,
  onLimpiar,
  summary,
  loading = false,
  filterVariant = "dropdown",
}: Props) {
  if (filterVariant === "mapa") {
    return (
      <Stack spacing={2} sx={{ width: "100%", minWidth: 0 }}>
        <Box sx={filtroContainerStyles}>
          <Typography sx={filtroTitleStyles}>Buscar domicilio</Typography>
          <Box sx={filtroGridStyles}>
            <Box sx={filtroItemStyles}>
              <AppTextField
                appearance="dense"
                fullWidth
                label="Buscar domicilio"
                value={searchQ}
                onChange={(e) => onSearchChange(e.target.value)}
                disabled={loading}
                onKeyDown={(e) => {
                  if (e.key === "Enter") onFiltrar?.();
                }}
              />
            </Box>
          </Box>
          <Box sx={filtroButtonsStyles}>
            <AppButton
              dsVariant="ghost"
              dsSize="sm"
              onClick={onLimpiar}
              disabled={loading}
              startIcon={<ClearIcon />}
              sx={filtroButtonSecondaryStyles}
            >
              Limpiar
            </AppButton>
            <AppButton
              dsVariant="primary"
              dsSize="sm"
              onClick={onFiltrar}
              disabled={loading}
              startIcon={<SearchIcon />}
              sx={filtroButtonPrimaryStyles}
            >
              Filtrar
            </AppButton>
          </Box>
        </Box>

        <Paper elevation={0} sx={{ ...glassTabsSecondaryPanelBarSx, width: "100%" }}>
          <Tabs
            value={statusOperativo}
            onChange={(_, value) => onStatusChange(value as GestionDomiciliosStatusOperativo)}
            variant="scrollable"
            allowScrollButtonsMobile
            sx={glassSecondaryTabsSx}
          >
            {MAPA_DOMICILIOS_SUBTABS.map(({ value, label }) => (
              <Tab key={value} label={label} value={value} disabled={loading} />
            ))}
          </Tabs>
        </Paper>
      </Stack>
    );
  }

  return (
    <Stack spacing={1} sx={{ ...moduleFiltersSurfaceSx, p: 1.5, borderRadius: 2 }}>
      <Stack
        direction={{ xs: "column", md: "row" }}
        spacing={1.5}
        alignItems={{ xs: "stretch", md: "center" }}
      >
        {filterVariant === "chips" ? (
          <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap sx={{ flex: 1 }}>
            {GESTION_DOMICILIOS_FILTROS.map(({ value, label }) => (
              <Chip
                key={value}
                label={label}
                size="small"
                clickable
                color={statusOperativo === value ? "primary" : "default"}
                variant={statusOperativo === value ? "filled" : "outlined"}
                onClick={() => onStatusChange(value)}
                disabled={loading}
              />
            ))}
          </Stack>
        ) : (
          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel id="gestion-domicilios-filtro-label">Estado</InputLabel>
            <Select
              labelId="gestion-domicilios-filtro-label"
              label="Estado"
              value={statusOperativo}
              onChange={(e) => onStatusChange(e.target.value as GestionDomiciliosStatusOperativo)}
              disabled={loading}
            >
              {GESTION_DOMICILIOS_FILTROS.map(({ value, label }) => (
                <MenuItem key={value} value={value}>
                  {label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        )}

        <TextField
          size="small"
          label="Buscar domicilio"
          value={searchQ}
          onChange={(e) => onSearchChange(e.target.value)}
          sx={{ minWidth: { md: 260 }, flex: filterVariant === "chips" ? { md: "0 0 280px" } : 1 }}
          disabled={loading}
        />
      </Stack>

      {summary ? (
        <Typography variant="caption" color="text.secondary" sx={{ pl: 0.25 }}>
          {formatGestionDomiciliosSummaryLine(summary)}
        </Typography>
      ) : null}
    </Stack>
  );
}
