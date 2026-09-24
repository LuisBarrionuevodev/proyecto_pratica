import { Chip, Stack, Typography } from "@mui/material";

import { GLASS_COLORS } from "../../../../styles/GlassStyles";
import type { IPlanificacionMetricas, PlanificacionCardKey, UrgentesFiltrosAplicados } from "../types/planificacion.types";

const tactic = '"Tactic Sans", sans-serif' as const;

type ChipDef = {
  key: PlanificacionCardKey;
  label: string;
  valueKey?: keyof IPlanificacionMetricas;
};

const CHIPS_TOTAL_MAPA: ChipDef[] = [
  { key: null, label: "Todos", valueKey: "total" },
  { key: "RELEVAMIENTOS", label: "Relev.", valueKey: "relevamientos" },
  { key: "NOTIFICACIONES", label: "Notif.", valueKey: "notificaciones" },
  { key: "OFICIOS_URGENTES", label: "Oficios", valueKey: "oficios_urgentes" },
  { key: "DENUNCIAS", label: "Denuncias", valueKey: "denuncias" },
];

const CHIPS_URGENTES: { key: UrgentesFiltrosAplicados["tipo_urgente"]; label: string }[] = [
  { key: "", label: "Todos" },
  { key: "NOTIFICACION", label: "Notif." },
  { key: "OFICIO", label: "Oficios" },
  { key: "DENUNCIA", label: "Denuncias" },
];

type BaseProps = {
  loading?: boolean;
  disabled?: boolean;
};

type TotalMapaProps = BaseProps & {
  variant?: "totalMapa";
  metricas: IPlanificacionMetricas | null;
  cardActiva: PlanificacionCardKey;
  onCardChange: (card: PlanificacionCardKey) => void;
};

type UrgentesProps = BaseProps & {
  variant: "urgentes";
  urgenteTipoActivo: UrgentesFiltrosAplicados["tipo_urgente"];
  onUrgenteTipoChange: (tipo: UrgentesFiltrosAplicados["tipo_urgente"]) => void;
};

export type PlanificacionTipoFilterChipsProps = TotalMapaProps | UrgentesProps;

function chipSx(active: boolean) {
  return {
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
  } as const;
}

/**
 * Filtro compacto por tipo/categoría según tab Total mapa o Urgentes.
 */
export function PlanificacionTipoFilterChips(props: PlanificacionTipoFilterChipsProps) {
  const { loading, disabled } = props;

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
      <Stack direction="row" spacing={0.5} useFlexGap flexWrap="wrap" sx={{ maxHeight: 72, overflowY: "auto", pr: 0.25 }}>
        {props.variant === "urgentes"
          ? CHIPS_URGENTES.map((c) => {
              const active = props.urgenteTipoActivo === c.key;
              return (
                <Chip
                  key={c.label}
                  size="small"
                  clickable
                  disabled={disabled}
                  onClick={() => props.onUrgenteTipoChange(c.key)}
                  label={c.label}
                  sx={chipSx(active)}
                />
              );
            })
          : CHIPS_TOTAL_MAPA.map((c) => {
              const active = props.cardActiva === c.key;
              const val = c.valueKey && props.metricas ? props.metricas[c.valueKey] : "—";
              return (
                <Chip
                  key={c.label}
                  size="small"
                  clickable
                  disabled={disabled}
                  onClick={() => props.onCardChange(c.key)}
                  label={`${c.label} ${loading ? "…" : val}`}
                  sx={chipSx(active)}
                />
              );
            })}
      </Stack>
    </Stack>
  );
}
