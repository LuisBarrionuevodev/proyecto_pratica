import { Box, Card, LinearProgress, Typography } from "@mui/material";

import {
  dashboardCardTitleSx,
  dashboardEmptyStateCompactSx,
  dashboardGlassCardSx,
} from "../../../styles/DashboardStyles";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

export type DashboardRankingItem = {
  label: string;
  value: number;
};

const MAX_LABEL = 40;
const ROW_HEIGHT = 32;
const MAX_CONTENT_PX = 260;

function truncateLabel(label: string): string {
  const t = label.trim();
  if (t.length <= MAX_LABEL) return t;
  return `${t.slice(0, MAX_LABEL - 1)}…`;
}

type Props = {
  title: string;
  items: DashboardRankingItem[];
  emptyMessage?: string;
  loading?: boolean;
  maxItems?: number;
};

/**
 * Ranking compacto con barras horizontales (rubros, contraproducencias, etc.).
 */
export function DashboardCompactRankingCard({
  title,
  items,
  emptyMessage = "Sin datos en el período.",
  loading = false,
  maxItems = 10,
}: Props) {
  const slice = items.slice(0, maxItems);
  const maxVal = Math.max(...slice.map((i) => i.value), 1);
  const contentHeight =
    slice.length === 0
      ? undefined
      : Math.min(MAX_CONTENT_PX, Math.max(ROW_HEIGHT + 8, slice.length * ROW_HEIGHT + 4));

  return (
    <Card
      sx={{
        ...dashboardGlassCardSx,
        p: { xs: 1.25, sm: 1.5 },
        position: "relative",
        overflow: "hidden",
        minWidth: 0,
      }}
    >
      {loading ? (
        <LinearProgress
          sx={{ position: "absolute", top: 0, left: 0, right: 0, height: 2, borderRadius: 0 }}
        />
      ) : null}
      <Typography component="h3" sx={{ ...dashboardCardTitleSx, fontSize: "0.9rem", mb: 1 }}>
        {title}
      </Typography>

      {loading && slice.length === 0 ? (
        <Box sx={dashboardEmptyStateCompactSx}>Cargando…</Box>
      ) : slice.length === 0 ? (
        <Box sx={dashboardEmptyStateCompactSx}>{emptyMessage}</Box>
      ) : (
        <Box sx={{ maxHeight: MAX_CONTENT_PX, overflowY: "auto", height: contentHeight }}>
          {slice.map((item, idx) => (
            <Box
              key={`${item.label}-${idx}`}
              sx={{
                display: "grid",
                gridTemplateColumns: "22px minmax(0, 1fr) 40px",
                alignItems: "center",
                gap: 0.75,
                minHeight: ROW_HEIGHT,
                py: 0.25,
              }}
            >
              <Typography
                variant="caption"
                sx={{ color: GLASS_COLORS.textMuted, fontWeight: 700, textAlign: "right" }}
              >
                {idx + 1}
              </Typography>
              <Box sx={{ minWidth: 0 }}>
                <Typography
                  variant="caption"
                  sx={{
                    display: "block",
                    color: GLASS_COLORS.textSecondary,
                    lineHeight: 1.15,
                    mb: 0.35,
                    fontSize: "0.7rem",
                  }}
                  title={item.label}
                >
                  {truncateLabel(item.label)}
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={(item.value / maxVal) * 100}
                  sx={{
                    height: 5,
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
                  fontWeight: 700,
                  textAlign: "right",
                  color: GLASS_COLORS.textPrimary,
                  fontSize: "0.8125rem",
                }}
              >
                {item.value}
              </Typography>
            </Box>
          ))}
        </Box>
      )}
    </Card>
  );
}
