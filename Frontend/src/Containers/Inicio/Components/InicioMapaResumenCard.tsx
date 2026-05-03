import { Box, Typography } from "@mui/material";
import { useMemo } from "react";
import { useNavigate } from "react-router-dom";

import mapaFondo from "../../../assets/mapa.jpg";
import { periodoToDateRange } from "../../Dashboard/utils/periodoDateRange";
import { useIndicadoresResumen } from "../../Dashboard/hooks/useIndicadoresResumen";
import { StyleTextCard, StyleTextCardSecondary } from "../../../styles/InicioStyles";
import { GLASS_COLORS, glassCard } from "../../../styles/GlassStyles";

type KpiFooterItemProps = { label: string; value: string | number; valueColor?: string };

function KpiFooterItem({ label, value, valueColor }: KpiFooterItemProps) {
  return (
    <Box
      sx={{
        textAlign: "center",
        px: 1,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minWidth: 0,
      }}
    >
      <Typography
        sx={{
          fontFamily: '"Tactic Sans", sans-serif',
          fontWeight: 700,
          fontSize: { xs: "1.05rem", sm: "1.2rem" },
          color: valueColor ?? GLASS_COLORS.textPrimary,
          lineHeight: 1.2,
        }}
      >
        {value}
      </Typography>
      <Typography
        sx={{
          ...StyleTextCardSecondary,
          fontSize: "10px",
          mt: 0.5,
          textTransform: "uppercase",
          letterSpacing: "0.04em",
        }}
      >
        {label}
      </Typography>
    </Box>
  );
}

function fmtKpi(n: number | undefined, loading: boolean): string | number {
  if (loading) return "…";
  if (n === undefined) return "—";
  return n;
}

/**
 * Card ancha: cabecera, mapa y tres KPIs del mes (resumen API, alineados al mapa operativo); clic abre `/mapa`.
 */
export default function InicioMapaResumenCard() {
  const navigate = useNavigate();
  const goMapa = () => navigate("/mapa");

  const resumenParams = useMemo(() => periodoToDateRange("Mensual"), []);
  const { data, loading } = useIndicadoresResumen(resumenParams);

  return (
    <Box
      onClick={goMapa}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          goMapa();
        }
      }}
      role="link"
      tabIndex={0}
      sx={[
        glassCard,
        {
          p: 0,
          overflow: "hidden",
          cursor: "pointer",
          borderRadius: "16px",
        },
      ]}
    >
      <Box
        sx={{
          position: "relative",
          minHeight: { xs: 200, sm: 240, md: 260 },
          overflow: "hidden",
        }}
      >
        <Box
          sx={{
            position: "absolute",
            inset: 0,
            backgroundImage: `url(${mapaFondo})`,
            backgroundSize: "cover",
            backgroundPosition: "center",
          }}
        />
        <Box
          sx={{
            position: "absolute",
            inset: 0,
            background: "linear-gradient(105deg, rgba(0,0,0,0.78) 0%, rgba(0,0,0,0.45) 55%, rgba(0,0,0,0.72) 100%)",
          }}
        />
        <Box
          sx={{
            position: "relative",
            zIndex: 1,
            p: { xs: 2, sm: 2.5, md: 3 },
            display: "flex",
            flexDirection: "column",
            gap: 1.5,
            minHeight: { xs: 200, sm: 240, md: 260 },
          }}
        >
          <Box
            sx={{
              display: "flex",
              flexDirection: { xs: "column", sm: "row" },
              alignItems: { xs: "flex-start", sm: "flex-start" },
              justifyContent: "space-between",
              gap: 1,
            }}
          >
            <Box sx={{ minWidth: 0 }}>
              <Typography sx={{ ...StyleTextCard, fontSize: { xs: "16px", sm: "18px" }, mb: 0.5 }}>
                Operación territorial
              </Typography>
              <Typography sx={{ ...StyleTextCardSecondary, fontSize: { xs: "12px", sm: "13px" }, maxWidth: "560px" }}>
                Mapa operativo: ubicaciones y seguimiento.
              </Typography>
            </Box>
            <Typography
              component="span"
              onClick={(e) => {
                e.stopPropagation();
                goMapa();
              }}
              sx={{
                fontFamily: '"Tactic Sans", sans-serif',
                fontWeight: 600,
                fontSize: "12px",
                color: GLASS_COLORS.primary,
                textTransform: "uppercase",
                letterSpacing: "0.06em",
                flexShrink: 0,
                alignSelf: { xs: "flex-start", sm: "flex-start" },
                pt: { sm: 0.25 },
              }}
            >
              Abrir mapa
            </Typography>
          </Box>
        </Box>
      </Box>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          alignItems: "stretch",
          px: { xs: 1.5, sm: 3 },
          py: 2,
          borderTop: `1px solid ${GLASS_COLORS.borderLight}`,
          backgroundColor: "rgba(0, 0, 0, 0.45)",
        }}
      >
        <KpiFooterItem label="Actuaciones del mes" value={fmtKpi(data?.actuaciones.total, loading)} />
        <KpiFooterItem
          label="Pendientes (mapa)"
          value={fmtKpi(data?.mapa_operativo.pendientes_total, loading)}
        />
        <KpiFooterItem
          label="Realizados visita (mapa)"
          value={fmtKpi(data?.mapa_operativo.realizados_visita, loading)}
        />
      </Box>
    </Box>
  );
}
