import { Chip, Stack, Typography } from "@mui/material";

import { GLASS_COLORS } from "../../../../styles/GlassStyles";
import type { IPlanificacionMetricas, PlanificacionCardKey } from "../types/planificacion.types";

const tactic = '"Tactic Sans", sans-serif' as const;

type ChipDef = {
  key: PlanificacionCardKey;
  label: string;
  valueKey: keyof IPlanificacionMetricas;
};

const CHIPS: ChipDef[] = [
  { key: null, label: "Todos", valueKey: "total" },
  { key: "ALTA_PRIORIDAD", label: "Alta", valueKey: "alta" },
  { key: "OFICIOS_URGENTES", label: "Oficios", valueKey: "oficios_urgentes" },
  { key: "DENUNCIAS", label: "Denuncias", valueKey: "denuncias" },
  { key: "NOTIFICACIONES", label: "Notif.", valueKey: "notificaciones" },
  { key: "RELEVAMIENTOS", label: "Relev.", valueKey: "relevamientos" },
];

export type PlanificacionTipoFilterChipsProps = {
  metricas: IPlanificacionMetricas | null;
  cardActiva: PlanificacionCardKey;
  onCardChange: (card: PlanificacionCardKey) => void;
  loading?: boolean;
  disabled?: boolean;
};

/**
 * Filtro compacto por tipo/categoría (chips horizontales sobre dataset visible en mapa).
 */
export function PlanificacionTipoFilterChips({
  metricas,
  cardActiva,
  onCardChange,
  loading,
  disabled,
}: PlanificacionTipoFilterChipsProps) {
  return (
    <Stack spacing={0.5} sx={{ minWidth: 0 }}>
      <Typography
        sx={{
          fontFamily: tactic,
          fontSize: "0.65rem",
          fontWeight: 700,
          letterSpacing: "0.06em",
          textTransform: "uppercase",
          color: GLASS_COLORS.textMuted,
        }}
      >
        Tipo
      </Typography>
      <Stack
        direction="row"
        spacing={0.5}
        useFlexGap
        flexWrap="wrap"
        sx={{ maxHeight: 72, overflowY: "auto", pr: 0.25 }}
      >
        {CHIPS.map((c) => {
          const active = cardActiva === c.key;
          const val = metricas ? metricas[c.valueKey] : "—";
          return (
            <Chip
              key={c.label}
              size="small"
              clickable
              disabled={disabled}
              onClick={() => onCardChange(c.key)}
              label={`${c.label} ${loading ? "…" : val}`}
              sx={{
                height: 24,
                fontFamily: tactic,
                fontSize: "0.6875rem",
                fontWeight: active ? 700 : 600,
                borderRadius: "8px",
                border: `1px solid ${active ? GLASS_COLORS.primary : GLASS_COLORS.borderMedium}`,
                backgroundColor: active ? "rgba(1, 102, 255, 0.14)" : "rgba(255,255,255,0.04)",
                color: active ? GLASS_COLORS.textPrimary : GLASS_COLORS.textSecondary,
                "&:hover": {
                  backgroundColor: active ? "rgba(1, 102, 255, 0.2)" : "rgba(255,255,255,0.08)",
                },
              }}
            />
          );
        })}
      </Stack>
    </Stack>
  );
}
