import { Box, LinearProgress, Typography } from "@mui/material";

import { dashboardEmptyStateCompactSx } from "../../../styles/DashboardStyles";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { DashboardAnalyticsChartCard } from "./DashboardAnalyticsChartCard";

type Props = {
  kg: number | null | undefined;
  loading?: boolean;
};

function formatKg(kg: number): string {
  if (Number.isInteger(kg)) return String(kg);
  return kg.toLocaleString("es-AR", { maximumFractionDigits: 2 });
}

/**
 * Total de mercadería decomisada (kg) — card analytics con acento visual neutro.
 */
export function DashboardMercaderiaDecomisadaCard({ kg, loading = false }: Props) {
  const hasValue = kg != null && !loading;
  const active = hasValue && kg > 0;

  return (
    <Box sx={{ width: "100%", display: "flex", flex: 1 }}>
    <DashboardAnalyticsChartCard title="Mercadería decomisada" loading={loading} fillHeight>
      {!hasValue ? (
        <Box sx={dashboardEmptyStateCompactSx}>
          <Typography variant="body2">{loading ? "Cargando…" : "Sin datos."}</Typography>
        </Box>
      ) : (
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            minHeight: 140,
            gap: 1.5,
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
            <Box
              sx={{
                position: "relative",
                width: 64,
                height: 64,
                flexShrink: 0,
              }}
            >
              <Box
                sx={{
                  position: "absolute",
                  inset: 0,
                  borderRadius: "50%",
                  border: `2px solid rgba(255,255,255,0.1)`,
                }}
              />
              <Box
                sx={{
                  position: "absolute",
                  inset: 4,
                  borderRadius: "50%",
                  border: `3px solid ${GLASS_COLORS.primary}`,
                  opacity: active ? 1 : 0.3,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Typography
                  sx={{
                    fontFamily: '"Tactic Sans", sans-serif',
                    fontWeight: 700,
                    fontSize: "0.65rem",
                    color: GLASS_COLORS.textMuted,
                  }}
                >
                  kg
                </Typography>
              </Box>
            </Box>
            <Box>
              <Typography
                sx={{
                  fontFamily: '"Tactic Sans", sans-serif',
                  fontWeight: 700,
                  fontSize: "2rem",
                  lineHeight: 1.05,
                  color: GLASS_COLORS.textPrimary,
                }}
              >
                {formatKg(kg)}
              </Typography>
              <Typography
                variant="caption"
                sx={{
                  display: "block",
                  mt: 0.35,
                  color: GLASS_COLORS.textMuted,
                  fontFamily: '"Tactic Sans", sans-serif',
                  fontSize: "0.7rem",
                }}
              >
                Total del período
              </Typography>
            </Box>
          </Box>
          <Box sx={{ px: 0.25 }}>
            <LinearProgress
              variant="determinate"
              value={active ? 100 : 0}
              sx={{
                height: 6,
                borderRadius: 1,
                bgcolor: "rgba(255,255,255,0.08)",
                "& .MuiLinearProgress-bar": {
                  borderRadius: 1,
                  bgcolor: GLASS_COLORS.primary,
                  opacity: active ? 0.85 : 0.25,
                },
              }}
            />
          </Box>
        </Box>
      )}
    </DashboardAnalyticsChartCard>
    </Box>
  );
}
