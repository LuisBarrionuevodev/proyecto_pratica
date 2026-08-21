import { useEffect, useState } from "react";
import { Chip, Stack, TextField, Typography } from "@mui/material";
import MapOutlinedIcon from "@mui/icons-material/MapOutlined";

import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { AppButton } from "../../../ui";
import {
  filterCompactActionsSx,
  filterCompactPrimaryButtonSx,
  filterCompactSecondaryButtonSx,
} from "../../Actuaciones/styles/filtroStyles";
import { planificacionTextFieldSx } from "../styles/institutionalVisual";
import { PlanificacionActiveFiltersChips } from "./components/PlanificacionActiveFiltersChips";
import { PlanificacionRubroSelect } from "./components/PlanificacionRubroSelect";
import { PlanificacionTipoFilterChips } from "./components/PlanificacionTipoFilterChips";
import { planificacionFiltrosBarSx } from "./planificacionMyMapsLayout";
import type {
  IPlanificacionMetricas,
  PlanificacionCardKey,
  PlanificacionFiltrosLista,
  UrgentesFiltrosAplicados,
} from "./types/planificacion.types";
import { UrgentesFiltroPanel } from "./UrgentesFiltroPanel";

const tactic = '"Tactic Sans", sans-serif' as const;

export type PlanificacionFiltrosBarProps = {
  distritoActivoId: number | null;
  distritoNombre?: string | null;
  metricas: IPlanificacionMetricas | null;
  cardActiva: PlanificacionCardKey;
  onCardChange: (card: PlanificacionCardKey) => void;
  metricasLoading?: boolean;
  filtrosAplicados: PlanificacionFiltrosLista;
  onFiltrarCandidatos: (filtros: PlanificacionFiltrosLista) => void;
  onLimpiarCandidatos: () => void;
  candidatosLoading?: boolean;
  rubroNombre?: string | null;
  sidebarTab: "candidatos" | "urgentes" | "pool" | "resumen";
  urgentesFiltros?: UrgentesFiltrosAplicados;
  onFiltrarUrgentes?: (filtros: UrgentesFiltrosAplicados) => void;
  onLimpiarUrgentes?: () => void;
  urgentesLoading?: boolean;
};

/**
 * Barra de filtros visible del panel lateral (distrito, tipo, rubro, búsqueda).
 */
export function PlanificacionFiltrosBar({
  distritoActivoId,
  distritoNombre,
  metricas,
  cardActiva,
  onCardChange,
  metricasLoading,
  filtrosAplicados,
  onFiltrarCandidatos,
  onLimpiarCandidatos,
  candidatosLoading,
  rubroNombre,
  sidebarTab,
  urgentesFiltros,
  onFiltrarUrgentes,
  onLimpiarUrgentes,
  urgentesLoading,
}: PlanificacionFiltrosBarProps) {
  const [q, setQ] = useState(filtrosAplicados.q);
  const [rubroId, setRubroId] = useState<number | null>(filtrosAplicados.rubro_id);

  useEffect(() => {
    setQ(filtrosAplicados.q);
    setRubroId(filtrosAplicados.rubro_id);
  }, [filtrosAplicados.q, filtrosAplicados.rubro_id, distritoActivoId]);

  const handleFiltrarCandidatos = () => {
    onFiltrarCandidatos({ q: q.trim(), rubro_id: rubroId });
  };

  const handleLimpiarCandidatos = () => {
    setQ("");
    setRubroId(null);
    onLimpiarCandidatos();
  };

  return (
    <Stack sx={planificacionFiltrosBarSx} spacing={0.75}>
      <Stack direction="row" alignItems="center" spacing={0.75} flexWrap="wrap" useFlexGap>
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
          Distrito
        </Typography>
        <Chip
          size="small"
          icon={<MapOutlinedIcon sx={{ fontSize: "0.9rem !important" }} />}
          label={
            distritoActivoId != null
              ? distritoNombre ?? `Distrito ${distritoActivoId}`
              : "Elegí en el mapa →"
          }
          color={distritoActivoId != null ? "primary" : "default"}
          variant={distritoActivoId != null ? "filled" : "outlined"}
          sx={{
            height: 26,
            fontFamily: tactic,
            fontSize: "0.72rem",
            fontWeight: 700,
            maxWidth: "100%",
          }}
        />
      </Stack>

      <PlanificacionTipoFilterChips
        metricas={metricas}
        cardActiva={cardActiva}
        onCardChange={onCardChange}
        loading={metricasLoading}
        disabled={distritoActivoId == null && metricas == null}
      />

      <Stack spacing={0.75}>
        <PlanificacionRubroSelect
          value={rubroId}
          onChange={setRubroId}
          disabled={candidatosLoading || distritoActivoId == null}
        />
        <TextField
          size="small"
          fullWidth
          label="Buscar domicilio"
          placeholder="Calle o número"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleFiltrarCandidatos()}
          disabled={distritoActivoId == null}
          sx={planificacionTextFieldSx}
        />
        <Stack direction="row" spacing={1} alignItems="center" sx={filterCompactActionsSx}>
          <AppButton
            dsVariant="ghost"
            dsSize="sm"
            onClick={handleLimpiarCandidatos}
            disabled={candidatosLoading}
            sx={filterCompactSecondaryButtonSx}
          >
            Limpiar
          </AppButton>
          <AppButton
            dsVariant="primary"
            dsSize="sm"
            onClick={handleFiltrarCandidatos}
            disabled={candidatosLoading || distritoActivoId == null}
            sx={filterCompactPrimaryButtonSx}
          >
            Buscar
          </AppButton>
        </Stack>
      </Stack>

      {sidebarTab === "urgentes" && onFiltrarUrgentes && onLimpiarUrgentes ? (
        <UrgentesFiltroPanel
          onFiltrar={onFiltrarUrgentes}
          onLimpiar={onLimpiarUrgentes}
          loading={urgentesLoading}
        />
      ) : null}

      <PlanificacionActiveFiltersChips
        distritoActivoId={distritoActivoId}
        distritoNombre={distritoNombre}
        cardActiva={cardActiva}
        filtrosCandidatos={filtrosAplicados}
        rubroNombre={rubroNombre}
        urgentesFiltros={urgentesFiltros}
        showUrgentesFilters={sidebarTab === "urgentes"}
      />
    </Stack>
  );
}
