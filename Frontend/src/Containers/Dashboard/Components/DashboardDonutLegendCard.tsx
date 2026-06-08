import { Box, LinearProgress, Tooltip, Typography } from "@mui/material";

import { PieChart } from "@mui/x-charts/PieChart";

import { useMemo } from "react";



import {

  ChartStyle,

  dashboardEmptyStateCompactSx,

  dashboardLegendLabelSx,

} from "../../../styles/DashboardStyles";

import { GLASS_COLORS } from "../../../styles/GlassStyles";

import { formatDashboardCompactCount } from "../utils/formatDashboardNumbers";

import { DashboardAnalyticsChartCard } from "./DashboardAnalyticsChartCard";



export type DashboardDonutLegendItem = {

  label: string;

  value: number;

};



const CHART_COLORS = [

  GLASS_COLORS.primary,

  "#22BF75",

  "#4A9FD4",

  "#F5A623",

  "#9B7EDE",

  "#5C6BC0",

];



function normalizeLabel(label: string): string {

  return label

    .replace(/_/g, " ")

    .replace(/([a-z])([A-Z])/g, "$1 $2")

    .trim();

}



type Props = {

  title: string;

  items: DashboardDonutLegendItem[];

  loading?: boolean;

  emptyMessage?: string;

  maxItems?: number;

  centerCaption?: string;

};



/**

 * Donut + leyenda estilo MUI «Users by country» (dark analytics).

 * El total va fuera del gráfico para evitar desbordes.

 */

export function DashboardDonutLegendCard({

  title,

  items,

  loading = false,

  emptyMessage = "Sin datos en el período.",

  maxItems = 5,

  centerCaption = "Total",

}: Props) {

  const slice = useMemo(() => {

    const normalized = items

      .filter((i) => i.value > 0)

      .slice(0, maxItems)

      .map((i) => ({ label: normalizeLabel(i.label), value: i.value }));

    const total = normalized.reduce((s, i) => s + i.value, 0);

    return { rows: normalized, total };

  }, [items, maxItems]);



  return (

    <Box sx={{ width: "100%", display: "flex", flex: 1 }}>

      <DashboardAnalyticsChartCard title={title} loading={loading} fillHeight>

        {loading && slice.rows.length === 0 ? (

          <Box sx={dashboardEmptyStateCompactSx}>

            <Typography variant="body2">Cargando…</Typography>

          </Box>

        ) : slice.rows.length === 0 ? (

          <Box sx={dashboardEmptyStateCompactSx}>

            <Typography variant="body2">{emptyMessage}</Typography>

          </Box>

        ) : (

          <Box>

            <Box

              sx={{

                display: "flex",

                alignItems: "baseline",

                justifyContent: "space-between",

                gap: 1,

                mb: 1,

                px: 0.25,

              }}

            >

              <Typography

                variant="caption"

                sx={{

                  ...dashboardLegendLabelSx,

                  fontSize: "0.7rem",

                  color: GLASS_COLORS.textSecondary,

                  fontWeight: 600,

                }}

              >

                {centerCaption}

              </Typography>

              <Typography

                sx={{

                  fontFamily: '"Tactic Sans", sans-serif',

                  fontWeight: 700,

                  fontSize: "1.05rem",

                  color: GLASS_COLORS.textPrimary,

                  lineHeight: 1.2,

                }}

              >

                {formatDashboardCompactCount(slice.total)}

              </Typography>

            </Box>



            <Box sx={{ height: 156, display: "flex", justifyContent: "center" }}>

              <PieChart

                series={[

                  {

                    data: slice.rows.map((row, i) => ({

                      id: i,

                      value: row.value,

                      label: row.label,

                      color: CHART_COLORS[i % CHART_COLORS.length],

                    })),

                    innerRadius: 48,

                    outerRadius: 68,

                    paddingAngle: slice.rows.length === 1 ? 0 : 2,

                    cornerRadius: 3,

                    valueFormatter: (v) => String(v ?? 0),

                  },

                ]}

                height={156}

                margin={{ top: 4, bottom: 4, left: 4, right: 4 }}

                slotProps={{ legend: { hidden: true } }}

                sx={ChartStyle}

              />

            </Box>



            <Box sx={{ mt: 1, display: "flex", flexDirection: "column", gap: 0.85 }}>

              {slice.rows.map((row, i) => {

                const pct = slice.total > 0 ? Math.round((row.value / slice.total) * 100) : 0;

                const rowColor = CHART_COLORS[i % CHART_COLORS.length];

                return (

                  <Box key={`${row.label}-${i}`}>

                    <Box

                      sx={{

                        display: "grid",

                        gridTemplateColumns: "10px minmax(0, 1fr) auto auto",

                        alignItems: "center",

                        gap: 0.75,

                        mb: 0.35,

                      }}

                    >

                      <Box

                        sx={{

                          width: 8,

                          height: 8,

                          borderRadius: "50%",

                          bgcolor: rowColor,

                          flexShrink: 0,

                        }}

                      />

                      <Tooltip title={row.label}>

                        <Typography

                          variant="caption"

                          sx={{

                            ...dashboardLegendLabelSx,

                            fontSize: "0.72rem",

                            overflow: "hidden",

                            textOverflow: "ellipsis",

                            whiteSpace: "nowrap",

                          }}

                        >

                          {row.label}

                        </Typography>

                      </Tooltip>

                      <Typography

                        variant="caption"

                        sx={{

                          fontFamily: '"Tactic Sans", sans-serif',

                          fontWeight: 600,

                          color: GLASS_COLORS.textSecondary,

                          fontSize: "0.68rem",

                        }}

                      >

                        {pct}%

                      </Typography>

                      <Typography

                        variant="caption"

                        sx={{

                          ...dashboardLegendLabelSx,

                          fontSize: "0.72rem",

                        }}

                      >

                        {formatDashboardCompactCount(row.value)}

                      </Typography>

                    </Box>

                    <LinearProgress

                      variant="determinate"

                      value={pct}

                      sx={{

                        height: 4,

                        borderRadius: 1,

                        bgcolor: "rgba(255,255,255,0.06)",

                        "& .MuiLinearProgress-bar": {

                          borderRadius: 1,

                          bgcolor: rowColor,

                        },

                      }}

                    />

                  </Box>

                );

              })}

            </Box>

          </Box>

        )}

      </DashboardAnalyticsChartCard>

    </Box>

  );

}


