import { Chip, Stack } from "@mui/material";

import { GLASS_COLORS } from "../../../../styles/GlassStyles";
import { planificacionActiveFiltersRowSx } from "../planificacionMyMapsLayout";
import type {
  PlanificacionCardKey,
  PlanificacionFiltrosLista,
  UrgentesFiltrosAplicados,
} from "../types/planificacion.types";

const tactic = '"Tactic Sans", sans-serif' as const;

const CARD_LABELS: Record<Exclude<PlanificacionCardKey, null>, string> = {
  ALTA_PRIORIDAD: "Alta prioridad",
  OFICIOS_URGENTES: "Oficios urgentes",
  DENUNCIAS: "Denuncias",
  NOTIFICACIONES: "Notificaciones",
  RELEVAMIENTOS: "Relevamientos",
};

const TIPO_URGENTE_LABELS: Record<Exclude<UrgentesFiltrosAplicados["tipo_urgente"], "">, string> = {
  DENUNCIA: "Denuncia",
  NOTIFICACION: "Notificación",
  OFICIO: "Oficio",
};

export type PlanificacionActiveFiltersChipsProps = {
  distritoNombre?: string | null;
  distritoActivoId: number | null;
  cardActiva: PlanificacionCardKey;
  filtrosCandidatos: PlanificacionFiltrosLista;
  rubroNombre?: string | null;
  urgentesFiltros?: UrgentesFiltrosAplicados;
  showUrgentesFilters?: boolean;
};

/**
 * Resumen visual de filtros activos (distrito, tipo, rubro, búsqueda, urgentes).
 */
export function PlanificacionActiveFiltersChips({
  distritoNombre,
  distritoActivoId,
  cardActiva,
  filtrosCandidatos,
  rubroNombre,
  urgentesFiltros,
  showUrgentesFilters,
}: PlanificacionActiveFiltersChipsProps) {
  const chips: { key: string; label: string; color?: "primary" | "warning" | "default" }[] = [];

  if (distritoActivoId != null) {
    chips.push({
      key: "distrito",
      label: `Distrito: ${distritoNombre ?? distritoActivoId}`,
      color: "primary",
    });
  } else {
    chips.push({ key: "distrito-empty", label: "Sin distrito (elegí en el mapa)" });
  }

  if (cardActiva != null) {
    chips.push({ key: "tipo", label: CARD_LABELS[cardActiva], color: "primary" });
  }

  if (filtrosCandidatos.rubro_id != null) {
    chips.push({
      key: "rubro",
      label: `Rubro: ${rubroNombre ?? filtrosCandidatos.rubro_id}`,
      color: "primary",
    });
  }

  if (filtrosCandidatos.q.trim()) {
    chips.push({ key: "q", label: `Buscar: ${filtrosCandidatos.q.trim()}`, color: "primary" });
  }

  if (showUrgentesFilters && urgentesFiltros) {
    if (urgentesFiltros.tipo_urgente) {
      chips.push({
        key: "urg-tipo",
        label: `Urgente: ${TIPO_URGENTE_LABELS[urgentesFiltros.tipo_urgente]}`,
        color: "warning",
      });
    }
    if (urgentesFiltros.q_domicilio.trim()) {
      chips.push({
        key: "urg-dom",
        label: `Urg. domicilio: ${urgentesFiltros.q_domicilio.trim()}`,
        color: "warning",
      });
    }
  }

  return (
    <Stack direction="row" flexWrap="wrap" useFlexGap spacing={0.5} sx={planificacionActiveFiltersRowSx}>
      {chips.map((c) => (
        <Chip
          key={c.key}
          size="small"
          label={c.label}
          color={c.color ?? "default"}
          variant="outlined"
          sx={{
            height: 22,
            fontFamily: tactic,
            fontSize: "0.625rem",
            fontWeight: 600,
            borderColor: GLASS_COLORS.borderMedium,
            color: GLASS_COLORS.textSecondary,
            "&.MuiChip-colorPrimary": {
              borderColor: GLASS_COLORS.primary,
              color: GLASS_COLORS.textPrimary,
            },
            "&.MuiChip-colorWarning": {
              borderColor: "rgba(255, 193, 7, 0.55)",
              color: "#ffe082",
            },
          }}
        />
      ))}
    </Stack>
  );
}
