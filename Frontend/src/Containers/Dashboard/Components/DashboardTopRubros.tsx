import { Box, LinearProgress, Typography } from "@mui/material";

import type { IndicadoresRubroTopItem } from "../../../api/indicadoresApi";
import { dashboardEmptyStateSx } from "../../../styles/DashboardStyles";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

const MAX_LABEL = 36;

function truncateLabel(nombre: string): string {
  const t = nombre.trim();
  if (t.length <= MAX_LABEL) return t;
  return `${t.slice(0, MAX_LABEL - 1)}…`;
}

interface Props {
  items: IndicadoresRubroTopItem[];
}

/**
 * Ranking compacto de rubros con barras proporcionales (altura dinámica según cantidad).
 */
const TopRubrosChart = ({ items }: Props) => {
  if (!items.length) {
    return (
      <Box sx={dashboardEmptyStateSx}>
        <Typography variant="body2" textAlign="center">
          Sin actuaciones con rubro asignado en el periodo.
        </Typography>
      </Box>
    );
  }

  const maxCount = Math.max(...items.map((r) => r.count), 1);

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 0.75,
        py: 0.5,
      }}
    >
      {items.map((r, idx) => (
        <Box
          key={r.rubro_id}
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", sm: "minmax(0, 1fr) 48px" },
            alignItems: "center",
            gap: 1,
            minHeight: 28,
          }}
        >
          <Box sx={{ minWidth: 0 }}>
            <Typography
              variant="caption"
              sx={{
                display: "block",
                color: GLASS_COLORS.textSecondary,
                lineHeight: 1.2,
                mb: 0.25,
              }}
            >
              {idx + 1}. {truncateLabel(r.nombre)}
            </Typography>
            <LinearProgress
              variant="determinate"
              value={(r.count / maxCount) * 100}
              sx={{
                height: 6,
                borderRadius: 1,
                bgcolor: "rgba(255,255,255,0.08)",
                "& .MuiLinearProgress-bar": {
                  borderRadius: 1,
                  bgcolor: GLASS_COLORS.primary,
                },
              }}
            />
          </Box>
          <Typography
            variant="body2"
            sx={{
              fontWeight: 600,
              textAlign: { xs: "left", sm: "right" },
              color: GLASS_COLORS.textPrimary,
            }}
          >
            {r.count}
          </Typography>
        </Box>
      ))}
    </Box>
  );
};

export default TopRubrosChart;
