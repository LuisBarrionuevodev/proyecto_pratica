import { Box, Typography } from "@mui/material";

import type { IndicadoresActasPorTipo } from "../../../api/indicadoresApi";
import { dashboardEmptyStateCompactSx } from "../../../styles/DashboardStyles";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

const ACTA_ITEMS: { key: keyof IndicadoresActasPorTipo; label: string }[] = [
  { key: "inspeccion", label: "Inspección" },
  { key: "notificacion", label: "Notificación" },
  { key: "comprobacion", label: "Comprobación" },
  { key: "clausura", label: "Clausura" },
  { key: "decomiso", label: "Decomiso" },
];

type Props = {
  actas: IndicadoresActasPorTipo;
  loading?: boolean;
};

function totalActasLabradas(actas: IndicadoresActasPorTipo): number {
  return (
    actas.inspeccion +
    actas.notificacion +
    actas.comprobacion +
    actas.clausura +
    actas.decomiso
  );
}

/**
 * Desglose compacto de actas labradas por tipo (mini cards en fila).
 */
export function DashboardActasPorTipoMini({ actas, loading }: Props) {
  const total = totalActasLabradas(actas);

  if (loading) {
    return <Box sx={dashboardEmptyStateCompactSx}>Cargando actas…</Box>;
  }

  if (total === 0) {
    return <Box sx={dashboardEmptyStateCompactSx}>Sin actas labradas en el período.</Box>;
  }

  return (
    <Box>
      <Typography
        variant="caption"
        sx={{
          display: "block",
          mb: 0.75,
          fontFamily: '"Tactic Sans", sans-serif',
          fontWeight: 600,
          color: GLASS_COLORS.textMuted,
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          fontSize: "0.65rem",
        }}
      >
        Actas por tipo · {total} total
      </Typography>
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          gap: 0.75,
        }}
      >
        {ACTA_ITEMS.map(({ key, label }) => (
          <Box
            key={key}
            sx={{
              flex: "1 1 88px",
              minWidth: 88,
              px: 1,
              py: 0.75,
              borderRadius: 1,
              border: `1px solid ${GLASS_COLORS.borderLight}`,
              backgroundColor: "rgba(255,255,255,0.04)",
              textAlign: "center",
            }}
          >
            <Typography
              variant="caption"
              sx={{
                display: "block",
                color: GLASS_COLORS.textMuted,
                fontSize: "0.65rem",
                lineHeight: 1.2,
                fontFamily: '"Tactic Sans", sans-serif',
              }}
            >
              {label}
            </Typography>
            <Typography
              sx={{
                fontFamily: '"Tactic Sans", sans-serif',
                fontWeight: 700,
                fontSize: "1rem",
                color: GLASS_COLORS.textPrimary,
                lineHeight: 1.2,
              }}
            >
              {actas[key]}
            </Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
}

/** @deprecated Use DashboardActasPorTipoMini */
export const DashboardActasPorTipoChips = DashboardActasPorTipoMini;

export { totalActasLabradas };
