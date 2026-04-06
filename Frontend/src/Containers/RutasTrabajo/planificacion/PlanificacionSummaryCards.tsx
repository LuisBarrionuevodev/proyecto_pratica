import { Box, Grid, Paper, Typography } from "@mui/material";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import type { IPlanificacionMetricas, PlanificacionCardKey } from "./types/planificacion.types";

const tactic = '"Tactic Sans", sans-serif' as const;

type CardDef = {
  key: PlanificacionCardKey;
  label: string;
  valueKey: keyof IPlanificacionMetricas;
};

const CARDS: CardDef[] = [
  { key: null, label: "Total pendientes", valueKey: "total" },
  { key: "ALTA_PRIORIDAD", label: "Alta prioridad", valueKey: "alta" },
  { key: "OFICIOS_URGENTES", label: "Oficios urgentes", valueKey: "oficios_urgentes" },
  { key: "DENUNCIAS", label: "Denuncias", valueKey: "denuncias" },
  { key: "NOTIFICACIONES", label: "Notificaciones", valueKey: "notificaciones" },
  { key: "RELEVAMIENTOS", label: "Relevamientos", valueKey: "relevamientos" },
];

export type PlanificacionSummaryCardsProps = {
  metricas: IPlanificacionMetricas | null;
  cardActiva: PlanificacionCardKey;
  onCardChange: (card: PlanificacionCardKey) => void;
  loading?: boolean;
};

/**
 * Cards KPI interactivas: refinan contexto de la columna izquierda (vía controller + M4), sin autoload al entrar.
 */
export function PlanificacionSummaryCards({
  metricas,
  cardActiva,
  onCardChange,
  loading,
}: PlanificacionSummaryCardsProps) {
  return (
    <Grid container spacing={1.5} sx={{ mb: 2 }}>
      {CARDS.map((c, idx) => {
        const active = cardActiva === c.key;
        const val = metricas ? metricas[c.valueKey] : "—";
        return (
          <Grid size={{ xs: 6, sm: 4, md: 2 }} key={idx}>
            <Paper
              elevation={0}
              onClick={() => onCardChange(c.key)}
              sx={{
                p: 1.5,
                cursor: "pointer",
                borderRadius: "12px",
                border: `1px solid ${active ? GLASS_COLORS.primary : GLASS_COLORS.borderMedium}`,
                backgroundColor: active ? "rgba(1, 102, 255, 0.08)" : GLASS_COLORS.cardBg,
                backdropFilter: "blur(12px)",
                transition: "border-color 0.15s ease, background-color 0.15s ease",
                "&:hover": {
                  borderColor: GLASS_COLORS.borderActive,
                },
              }}
            >
              <Typography
                sx={{
                  fontFamily: tactic,
                  fontSize: "0.65rem",
                  letterSpacing: "0.06em",
                  textTransform: "uppercase",
                  color: GLASS_COLORS.textMuted,
                  mb: 0.5,
                }}
              >
                {c.label}
              </Typography>
              <Typography sx={{ fontFamily: tactic, fontWeight: 800, fontSize: "1.25rem", color: GLASS_COLORS.textPrimary }}>
                {loading ? "…" : val}
              </Typography>
            </Paper>
          </Grid>
        );
      })}
    </Grid>
  );
}
