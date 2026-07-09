import { Chip, FormControl, InputLabel, MenuItem, Select, Stack, TextField, Typography } from "@mui/material";
import type { GestionDomiciliosStatusOperativo, GestionDomiciliosSummary } from "../../../api/gestionDomiciliosApi";
import { moduleFiltersSurfaceSx } from "../../../styles/GlassStyles";
import { GESTION_DOMICILIOS_FILTROS } from "../gestionDomiciliosOperativoFilters";

type Props = {
  statusOperativo: GestionDomiciliosStatusOperativo;
  onStatusChange: (value: GestionDomiciliosStatusOperativo) => void;
  searchQ: string;
  onSearchChange: (value: string) => void;
  summary: GestionDomiciliosSummary | null;
  loading?: boolean;
};

export function GestionDomiciliosFiltro({
  statusOperativo,
  onStatusChange,
  searchQ,
  onSearchChange,
  summary,
  loading = false,
}: Props) {
  return (
    <Stack
      direction={{ xs: "column", md: "row" }}
      spacing={1.5}
      alignItems={{ xs: "stretch", md: "center" }}
      sx={{ ...moduleFiltersSurfaceSx, p: 1.5, borderRadius: 2 }}
    >
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

      <TextField
        size="small"
        label="Buscar domicilio"
        value={searchQ}
        onChange={(e) => onSearchChange(e.target.value)}
        sx={{ minWidth: { md: 220 }, flex: 1 }}
        disabled={loading}
      />

      {summary ? (
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap alignItems="center">
          <Typography variant="caption" color="text.secondary">
            {summary.requieren_accion} requieren acción
          </Typography>
          <Chip size="small" label={`${summary.sin_punto} sin punto`} variant="outlined" />
          <Chip size="small" label={`${summary.geolocalizados} en mapa`} variant="outlined" />
        </Stack>
      ) : null}
    </Stack>
  );
}
