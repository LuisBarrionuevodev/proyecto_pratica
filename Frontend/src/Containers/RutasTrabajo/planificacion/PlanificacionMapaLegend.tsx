import { Box, Stack, Typography } from "@mui/material";

import { glassCard, GLASS_COLORS } from "../../../styles/GlassStyles";

const tactic = '"Tactic Sans", sans-serif' as const;

function LegendDot({ color }: { color: string }) {
  return (
    <Box
      sx={{
        width: 10,
        height: 10,
        borderRadius: "50%",
        backgroundColor: color,
        border: "1.5px solid rgba(255,255,255,0.9)",
        flexShrink: 0,
      }}
    />
  );
}

/** Leyenda mínima sobre el mapa de planificación. */
export function PlanificacionMapaLegend() {
  return (
    <Box
      data-testid="planificacion-mapa-legend"
      sx={{
        ...glassCard,
        position: "absolute",
        left: 12,
        bottom: 12,
        zIndex: 1100,
        p: 1,
        pointerEvents: "none",
        border: `1px solid ${GLASS_COLORS.borderMedium}`,
        boxShadow: "0 6px 20px rgba(0,0,0,0.35)",
      }}
    >
      <Stack spacing={0.5}>
        <Stack direction="row" spacing={0.75} alignItems="center">
          <LegendDot color="#0166FF" />
          <Typography sx={{ fontFamily: tactic, fontSize: "0.6875rem", color: GLASS_COLORS.textSecondary }}>
            Candidato libre
          </Typography>
        </Stack>
        <Stack direction="row" spacing={0.75} alignItems="center">
          <LegendDot color="#d32f2f" />
          <Typography sx={{ fontFamily: tactic, fontSize: "0.6875rem", color: GLASS_COLORS.textSecondary }}>
            Ya agregado a esta ruta
          </Typography>
        </Stack>
      </Stack>
    </Box>
  );
}
