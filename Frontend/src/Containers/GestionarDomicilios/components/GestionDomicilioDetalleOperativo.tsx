import { Box, Button, Chip, Stack, Typography } from "@mui/material";
import type { GestionDomiciliosRow } from "../../../api/gestionDomiciliosApi";
import { labelGeoChip } from "../gestionDomiciliosOperativoFilters";

type Props = {
  row: GestionDomiciliosRow | null;
  onClose?: () => void;
  onGeolocalizar?: (row: GestionDomiciliosRow) => void;
  onReubicar?: (row: GestionDomiciliosRow) => void;
};

/** Panel de detalle operativo simplificado (PR6C.6). */
export function GestionDomicilioDetalleOperativo({
  row,
  onClose,
  onGeolocalizar,
  onReubicar,
}: Props) {
  if (!row) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography variant="body2" color="text.secondary">
          Seleccioná un domicilio de la lista o un punto del mapa.
        </Typography>
      </Box>
    );
  }

  const isEnMapa = row.geo_chip === "EN_MAPA";

  return (
    <Box sx={{ p: 2, minWidth: 0 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" gap={1}>
        <Typography variant="subtitle1" fontWeight={600}>
          #{row.domicilio_id}
        </Typography>
        {onClose ? (
          <Button size="small" onClick={onClose}>
            Cerrar
          </Button>
        ) : null}
      </Stack>

      <Typography variant="body2" sx={{ mt: 0.5, mb: 1 }}>
        {row.domicilio_linea}
      </Typography>

      <Stack direction="row" spacing={1} sx={{ mb: 1.5 }} flexWrap="wrap" useFlexGap>
        <Chip
          size="small"
          label={labelGeoChip(row.geo_chip)}
          color={isEnMapa ? "primary" : "warning"}
          variant={isEnMapa ? "filled" : "outlined"}
        />
        <Chip size="small" label={row.status_operativo_label} variant="outlined" />
      </Stack>

      {row.calle_sugerida ? (
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1.5 }}>
          Calle sugerida: {row.calle_sugerida}
        </Typography>
      ) : null}

      <Stack direction="row" flexWrap="wrap" gap={1} useFlexGap>
        {isEnMapa && onReubicar ? (
          <Button size="small" variant="contained" onClick={() => onReubicar(row)}>
            Reubicar
          </Button>
        ) : null}
        {!isEnMapa && onGeolocalizar ? (
          <Button size="small" variant="contained" onClick={() => onGeolocalizar(row)}>
            Geolocalizar
          </Button>
        ) : null}
      </Stack>
    </Box>
  );
}
