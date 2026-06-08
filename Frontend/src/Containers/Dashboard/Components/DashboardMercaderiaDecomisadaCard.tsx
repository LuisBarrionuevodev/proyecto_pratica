import { Box, LinearProgress, Tooltip, Typography } from "@mui/material";

import { PieChart } from "@mui/x-charts/PieChart";

import { useMemo } from "react";



import type { IndicadoresDecomisoKgRubroItem } from "../../../api/indicadoresApi";

import {

  ChartStyle,

  dashboardEmptyStateCompactSx,

  dashboardLegendLabelSx,

} from "../../../styles/DashboardStyles";

import { GLASS_COLORS } from "../../../styles/GlassStyles";

import { formatDashboardKgCompact } from "../utils/formatDashboardNumbers";

import { DashboardAnalyticsChartCard } from "./DashboardAnalyticsChartCard";



const CHART_COLORS = [

  GLASS_COLORS.primary,

  "#22BF75",

  "#4A9FD4",

  "#F5A623",

  "#9B7EDE",

  "#5C6BC0",

];



type Props = {

  kg: number | null | undefined;

  rubroItems?: IndicadoresDecomisoKgRubroItem[];

  loading?: boolean;

};



function formatKgLegend(kg: number): string {

  if (kg >= 1000) {

    return `${(kg / 1000).toLocaleString("es-AR", { maximumFractionDigits: 1 })} mil`;

  }

  return kg.toLocaleString("es-AR", { maximumFractionDigits: kg % 1 === 0 ? 0 : 1 });

}



/**

 * Mercadería decomisada: total protagonista fuera del donut + distribución por rubro.

 */

export function DashboardMercaderiaDecomisadaCard({

  kg,

  rubroItems = [],

  loading = false,

}: Props) {

  const distribution = useMemo(() => {

    const rows = rubroItems.filter((r) => r.kg > 0).slice(0, 5);

    const sumRubros = rows.reduce((s, r) => s + r.kg, 0);

    return { rows, sumRubros };

  }, [rubroItems]);



  const hasValue = kg != null && !loading;

  const hasDonut = distribution.rows.length > 0;

  const totalFormatted = hasValue ? formatDashboardKgCompact(kg) : null;



  return (

    <Box sx={{ width: "100%", display: "flex", flex: 1 }}>

      <DashboardAnalyticsChartCard title="Mercadería decomisada" loading={loading} fillHeight>

        {!hasValue ? (

          <Box sx={dashboardEmptyStateCompactSx}>

            <Typography variant="body2">{loading ? "Cargando…" : "Sin datos."}</Typography>

          </Box>

        ) : (

          <Box>

            {totalFormatted ? (

              <Box sx={{ textAlign: "center", mb: hasDonut ? 1 : 0.5, px: 0.5 }}>

                <Typography

                  component="div"

                  sx={{

                    fontFamily: '"Tactic Sans", sans-serif',

                    fontWeight: 700,

                    fontSize: { xs: "1.5rem", sm: "1.75rem" },

                    lineHeight: 1.15,

                    color: GLASS_COLORS.textPrimary,

                  }}

                >

                  {totalFormatted.main}

                  <Typography

                    component="span"

                    sx={{

                      ml: 0.5,

                      fontFamily: '"Tactic Sans", sans-serif',

                      fontWeight: 700,

                      fontSize: "0.875rem",

                      color: GLASS_COLORS.textPrimary,

                    }}

                  >

                    {totalFormatted.suffix}

                  </Typography>

                </Typography>

              </Box>

            ) : null}



            {hasDonut ? (

              <>

                <Box sx={{ height: 140, display: "flex", justifyContent: "center" }}>

                  <PieChart

                    series={[

                      {

                        data: distribution.rows.map((row, i) => ({

                          id: i,

                          value: row.kg,

                          label: row.rubro,

                          color: CHART_COLORS[i % CHART_COLORS.length],

                        })),

                        innerRadius: 44,

                        outerRadius: 62,

                        paddingAngle: distribution.rows.length === 1 ? 0 : 2,

                        cornerRadius: 3,

                        valueFormatter: (v) => `${formatKgLegend(v ?? 0)} kg`,

                      },

                    ]}

                    height={140}

                    margin={{ top: 4, bottom: 4, left: 4, right: 4 }}

                    slotProps={{ legend: { hidden: true } }}

                    sx={ChartStyle}

                  />

                </Box>



                <Box sx={{ mt: 1, display: "flex", flexDirection: "column", gap: 0.85 }}>

                  {distribution.rows.map((row, i) => {

                    const pct =

                      distribution.sumRubros > 0

                        ? Math.round((row.kg / distribution.sumRubros) * 100)

                        : 0;

                    const rowColor = CHART_COLORS[i % CHART_COLORS.length];

                    return (

                      <Box key={`${row.rubro}-${i}`}>

                        <Box

                          sx={{

                            display: "grid",

                            gridTemplateColumns: "10px minmax(0, 1fr) auto auto",

                            alignItems: "center",

                            gap: 0.75,

                            mb: 0.35,

                          }}

                        >

                          <Box sx={{ width: 8, height: 8, borderRadius: "50%", bgcolor: rowColor }} />

                          <Tooltip title={row.rubro}>

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

                              {row.rubro}

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

                            {formatKgLegend(row.kg)} kg

                          </Typography>

                        </Box>

                        <LinearProgress

                          variant="determinate"

                          value={pct}

                          sx={{

                            height: 4,

                            borderRadius: 1,

                            bgcolor: "rgba(255,255,255,0.06)",

                            "& .MuiLinearProgress-bar": { borderRadius: 1, bgcolor: rowColor },

                          }}

                        />

                      </Box>

                    );

                  })}

                </Box>

              </>

            ) : (

              <Typography

                variant="caption"

                sx={{

                  display: "block",

                  textAlign: "center",

                  mt: 0.5,

                  color: GLASS_COLORS.textSecondary,

                  fontFamily: '"Tactic Sans", sans-serif',

                }}

              >

                {kg === 0 ? "Sin decomisos en el período." : "Total del período (sin desglose por rubro)."}

              </Typography>

            )}

          </Box>

        )}

      </DashboardAnalyticsChartCard>

    </Box>

  );

}


