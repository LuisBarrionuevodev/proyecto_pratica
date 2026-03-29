import { Box, Typography } from "@mui/material";
import { useMemo, useState } from "react";

import { GLASS_COLORS, glassCard } from "../../../styles/GlassStyles";
import { fechaLocalHoyIso } from "../../../utils/dateRange";
import { AppButton, AppTextField } from "../../../ui";
import {
  filtroButtonPrimaryStyles,
  filtroButtonsStyles,
  filtroContainerStyles,
  filtroGridStyles,
  filtroItemStyles,
  filtroTitleStyles,
} from "../../Actuaciones/styles/filtroStyles";
import type { CompletarTrabajosEmptyProps } from "../types";

/** Contenedor de filtro: relevamientos + glass; altura según contenido (compacto). */
const filtroGlassPanelSx = {
  ...filtroContainerStyles,
  ...glassCard,
  width: "100%",
  display: "flex",
  flexDirection: "column" as const,
  boxSizing: "border-box" as const,
};

/**
 * Pantalla inicial: filtro de fecha operativa (glass, ancho completo como el resto de filtros).
 */
export function CompletarEmptyView({ initialFecha, onVerTrabajos }: CompletarTrabajosEmptyProps) {
  const defaultFecha = useMemo(() => initialFecha ?? fechaLocalHoyIso(), [initialFecha]);
  const [fecha, setFecha] = useState(defaultFecha);

  return (
    <Box sx={{ width: "100%" }}>
      <Box sx={filtroGlassPanelSx}>
        <Typography sx={{ ...filtroTitleStyles, marginBottom: "12px" }}>Fecha operativa</Typography>
        <Typography variant="body2" sx={{ color: GLASS_COLORS.textSecondary, mb: 1.75 }}>
          Usá la <strong>misma fecha operativa</strong> que configuraste en la ruta de trabajo (no el día en que creaste el
          borrador). Solo aparecen ítems de rutas <strong>ya publicadas</strong>; hasta publicar no hay actuación ni
          EN_PROCESO.
        </Typography>

        <Box sx={{ ...filtroGridStyles, marginBottom: "12px" }}>
          <Box sx={filtroItemStyles}>
            <AppTextField
              appearance="dense"
              label="Fecha"
              type="date"
              value={fecha}
              onChange={(e) => setFecha(e.target.value)}
              InputLabelProps={{ shrink: true }}
              fullWidth
              variant="outlined"
            />
          </Box>
        </Box>

        <Box sx={filtroButtonsStyles}>
          <AppButton
            dsVariant="primary"
            dsSize="sm"
            onClick={() => onVerTrabajos?.(fecha)}
            disabled={!fecha}
            sx={filtroButtonPrimaryStyles}
          >
            Ver trabajos
          </AppButton>
        </Box>
      </Box>
    </Box>
  );
}
