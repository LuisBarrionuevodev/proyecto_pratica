import { Box, LinearProgress, Tooltip, Typography } from "@mui/material";
import { useMemo } from "react";

import { dashboardEmptyStateCompactSx, dashboardLegendLabelSx } from "../../../styles/DashboardStyles";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

export type DashboardRankingBarItem = {
  label: string;
  value: number;
};

const LABEL_MIN = 100;
const ROW_HEIGHT = 36;

function normalizeLabel(label: string): string {
  return label
    .replace(/_/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .trim();
}

type Props = {
  items: DashboardRankingBarItem[];
  emptyMessage?: string;
  maxItems?: number;
  color?: string;
};

/**
 * Ranking legible: etiqueta + barra proporcional + valor (patrón analytics MUI).
 */
export function DashboardRankingBarList({
  items,
  emptyMessage = "Sin datos en el período.",
  maxItems = 7,
  color = GLASS_COLORS.primary,
}: Props) {
  const slice = useMemo(
    () =>
      items
        .slice(0, maxItems)
        .map((i) => ({ label: normalizeLabel(i.label), value: i.value })),
    [items, maxItems],
  );

  const maxVal = useMemo(() => Math.max(...slice.map((i) => i.value), 1), [slice]);

  if (slice.length === 0) {
    return (
      <Box sx={dashboardEmptyStateCompactSx}>
        <Typography variant="body2">{emptyMessage}</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
      {slice.map((item, idx) => (
        <Box
          key={`${item.label}-${idx}`}
          sx={{
            display: "grid",
            gridTemplateColumns: `${LABEL_MIN}px minmax(0, 1fr) 36px`,
            alignItems: "center",
            gap: 1,
            minHeight: ROW_HEIGHT,
          }}
        >
          <Tooltip title={item.label} placement="top-start">
            <Typography
              variant="body2"
              sx={{
                ...dashboardLegendLabelSx,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {item.label}
            </Typography>
          </Tooltip>
          <LinearProgress
            variant="determinate"
            value={(item.value / maxVal) * 100}
            sx={{
              height: 8,
              borderRadius: 1,
              bgcolor: "rgba(255,255,255,0.08)",
              "& .MuiLinearProgress-bar": {
                borderRadius: 1,
                bgcolor: color,
              },
            }}
          />
          <Typography
            variant="body2"
            sx={{
              fontFamily: '"Tactic Sans", sans-serif',
              fontWeight: 700,
              fontSize: "0.8125rem",
              color: GLASS_COLORS.textPrimary,
              textAlign: "right",
            }}
          >
            {item.value}
          </Typography>
        </Box>
      ))}
    </Box>
  );
}
