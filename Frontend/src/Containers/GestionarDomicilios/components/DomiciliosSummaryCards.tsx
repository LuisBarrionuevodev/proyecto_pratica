import FormatListBulletedIcon from "@mui/icons-material/FormatListBulleted";
import LayersIcon from "@mui/icons-material/Layers";
import PlaceIcon from "@mui/icons-material/Place";
import { Box, Grid, Typography } from "@mui/material";
import type { ReactNode } from "react";

import { GLASS_COLORS, glassCard } from "../../../styles/GlassStyles";

interface DomiciliosSummaryCardsProps {
  nomenclaturaCount: number;
  geolocalizacionCount: number;
  /** Si aún no se aplicó filtro, se muestran guiones en los totales. */
  pendingQuery?: boolean;
}

const labelSx = {
  fontFamily: '"Tactic Sans", sans-serif',
  fontSize: "11px",
  fontWeight: 600,
  letterSpacing: "1.2px",
  textTransform: "uppercase" as const,
  color: GLASS_COLORS.textMuted,
  mb: 1,
};

const iconShellSx = {
  width: { xs: 52, sm: 64 },
  height: { xs: 52, sm: 64 },
  borderRadius: "12px",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  flexShrink: 0,
  border: `1px solid ${GLASS_COLORS.borderLight}`,
  backgroundColor: "rgba(0, 0, 0, 0.22)",
};

function MetricGlassCard({
  label,
  value,
  valueEmphasis = "default",
  icon,
  iconColor,
}: {
  label: string;
  value: string | number;
  valueEmphasis?: "default" | "primary";
  icon: ReactNode;
  iconColor: string;
}) {
  return (
    <Box
      sx={{
        ...glassCard,
        p: { xs: 2.25, sm: 2.75 },
        minHeight: { xs: 128, sm: 148 },
        display: "flex",
        flexDirection: "row",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 2,
        overflow: "hidden",
      }}
    >
      <Box sx={{ minWidth: 0, flex: 1 }}>
        <Typography component="div" sx={labelSx}>
          {label}
        </Typography>
        <Typography
          variant="h3"
          component="div"
          sx={{
            fontFamily: '"Tactic Sans", sans-serif',
            fontWeight: 800,
            fontSize: { xs: "2rem", sm: "2.35rem" },
            lineHeight: 1.1,
            color:
              valueEmphasis === "primary" ? GLASS_COLORS.primary : GLASS_COLORS.textPrimary,
            letterSpacing: "-0.02em",
          }}
        >
          {value}
        </Typography>
      </Box>
      <Box sx={{ ...iconShellSx, "& .MuiSvgIcon-root": { fontSize: { xs: 28, sm: 32 }, color: iconColor } }}>
        {icon}
      </Box>
    </Box>
  );
}

/**
 * Tres métricas en fila (referencia de layout operativo) con estética glass del sistema.
 */
const DomiciliosSummaryCards = ({
  nomenclaturaCount,
  geolocalizacionCount,
  pendingQuery = false,
}: DomiciliosSummaryCardsProps) => {
  const total = nomenclaturaCount + geolocalizacionCount;
  const display = (n: number) => (pendingQuery ? "—" : n);
  const geoPrimary = !pendingQuery && geolocalizacionCount > 0;

  return (
    <Grid container spacing={2} sx={{ mb: 2 }}>
      <Grid size={{ xs: 12, md: 4 }}>
        <MetricGlassCard
          label="Pendientes nomenclatura"
          value={display(nomenclaturaCount)}
          icon={<FormatListBulletedIcon />}
          iconColor={GLASS_COLORS.textSecondary}
        />
      </Grid>
      <Grid size={{ xs: 12, md: 4 }}>
        <MetricGlassCard
          label="Pendientes geolocalización"
          value={display(geolocalizacionCount)}
          valueEmphasis={geoPrimary ? "primary" : "default"}
          icon={<PlaceIcon />}
          iconColor={geoPrimary ? GLASS_COLORS.primary : GLASS_COLORS.textSecondary}
        />
      </Grid>
      <Grid size={{ xs: 12, md: 4 }}>
        <MetricGlassCard
          label="Total pendientes"
          value={display(total)}
          icon={<LayersIcon />}
          iconColor={GLASS_COLORS.textSecondary}
        />
      </Grid>
    </Grid>
  );
};

export default DomiciliosSummaryCards;
