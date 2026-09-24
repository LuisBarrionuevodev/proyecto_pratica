import { Box, Card, CardContent, LinearProgress, Typography } from "@mui/material";
import type { ReactNode } from "react";

import {
  dashboardCardTitleSx,
  dashboardGlassCardSx,
} from "../../../styles/DashboardStyles";
import { DashboardDemoBadge } from "./DashboardDemoBadge";

interface ChartCardProps {
  title: string;
  children: ReactNode;
  /** Muestra badge «Demo» — datos no conectados al backend. */
  demo?: boolean;
  loading?: boolean;
  /** Padding y título reducidos (dashboard compacto). */
  compact?: boolean;
}

const ChartCard = ({ title, children, demo = false, loading = false, compact = false }: ChartCardProps) => (
  <Card
    sx={{
      ...dashboardGlassCardSx,
      p: compact ? { xs: 1.25, sm: 1.5 } : { xs: 2, sm: 2.5 },
      position: "relative",
      overflow: "hidden",
      minWidth: compact ? 0 : 260,
    }}
  >
    {loading ? (
      <LinearProgress
        sx={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: 3,
          borderRadius: 0,
        }}
      />
    ) : null}
    <Box
      sx={{
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "space-between",
        gap: 1,
        mb: compact ? 1 : 2,
        flexWrap: "wrap",
      }}
    >
      <Typography
        component="h3"
        sx={{ ...dashboardCardTitleSx, fontSize: compact ? "0.9rem" : undefined }}
      >
        {title}
      </Typography>
      {demo ? <DashboardDemoBadge /> : null}
    </Box>
    <CardContent sx={{ p: 0, "&:last-child": { pb: 0 }, opacity: loading ? 0.72 : 1, transition: "opacity 0.2s" }}>
      {children}
    </CardContent>
  </Card>
);

export default ChartCard;
