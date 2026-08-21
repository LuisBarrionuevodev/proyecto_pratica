import { useEffect, useState } from "react";
import { Stack, TextField, Typography } from "@mui/material";

import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { AppButton } from "../../../ui";
import {
  filterCompactActionsSx,
  filterCompactPrimaryButtonSx,
  filterCompactSecondaryButtonSx,
} from "../../Actuaciones/styles/filtroStyles";
import { planificacionTextFieldSx } from "../styles/institutionalVisual";
import { PlanificacionRubroSelect } from "./components/PlanificacionRubroSelect";
import { PlanificacionTipoFilterChips } from "./components/PlanificacionTipoFilterChips";
import { planificacionFiltrosBarSx } from "./planificacionMyMapsLayout";
import type {
  IPlanificacionMetricas,
  PlanificacionCardKey,
  PlanificacionFiltrosLista,
  UrgentesFiltrosAplicados,
} from "./types/planificacion.types";
import type { PlanificacionSidebarTab } from "./PlanificacionSidebarPanel";

const tactic = '"Tactic Sans", sans-serif' as const;

export type PlanificacionFiltrosBarProps = {
  distritoActivoId: number | null;
  metricas: IPlanificacionMetricas | null;
  cardActiva: PlanificacionCardKey;
  onCardChange: (card: PlanificacionCardKey) => void;
  metricasLoading?: boolean;
  filtrosAplicados: PlanificacionFiltrosLista;
  onFiltrarCandidatos: (filtros: PlanificacionFiltrosLista) => void;
  onLimpiarCandidatos: () => void;
  candidatosLoading?: boolean;
  rubroNombre?: string | null;
  sidebarTab: PlanificacionSidebarTab;
  urgentesFiltros: UrgentesFiltrosAplicados;
  onFiltrarUrgentes: (filtros: UrgentesFiltrosAplicados) => void;
  onLimpiarUrgentes: () => void;
  urgentesLoading?: boolean;
};

/**
 * Filtros compactos del panel lateral (tipo, rubro, búsqueda) según tab activo.
 */
export function PlanificacionFiltrosBar({
  distritoActivoId,
  metricas,
  cardActiva,
  onCardChange,
  metricasLoading,
  filtrosAplicados,
  onFiltrarCandidatos,
  onLimpiarCandidatos,
  candidatosLoading,
  sidebarTab,
  urgentesFiltros,
  onFiltrarUrgentes,
  onLimpiarUrgentes,
  urgentesLoading,
}: PlanificacionFiltrosBarProps) {
  const [q, setQ] = useState(filtrosAplicados.q);
  const [rubroId, setRubroId] = useState<number | null>(filtrosAplicados.rubro_id);
  const [urgenteTipo, setUrgenteTipo] = useState(urgentesFiltros.tipo_urgente);
  const [urgenteRubroId, setUrgenteRubroId] = useState<number | null>(urgentesFiltros.rubro_id);
  const [urgenteQ, setUrgenteQ] = useState(urgentesFiltros.q_domicilio);

  useEffect(() => {
    setQ(filtrosAplicados.q);
    setRubroId(filtrosAplicados.rubro_id);
  }, [filtrosAplicados.q, filtrosAplicados.rubro_id, distritoActivoId]);

  useEffect(() => {
    setUrgenteTipo(urgentesFiltros.tipo_urgente);
    setUrgenteRubroId(urgentesFiltros.rubro_id);
    setUrgenteQ(urgentesFiltros.q_domicilio);
  }, [urgentesFiltros.tipo_urgente, urgentesFiltros.rubro_id, urgentesFiltros.q_domicilio]);

  const isTotalMapa = sidebarTab === "total-mapa";

  const handleFiltrarCandidatos = () => {
    onFiltrarCandidatos({ q: q.trim(), rubro_id: rubroId });
  };

  const handleLimpiarCandidatos = () => {
    setQ("");
    setRubroId(null);
    onLimpiarCandidatos();
  };

  const handleFiltrarUrgentes = () => {
    onFiltrarUrgentes({
      tipo_urgente: urgenteTipo,
      rubro_id: urgenteRubroId,
      q_identificador: "",
      q_domicilio: urgenteQ.trim(),
    });
  };

  const handleLimpiarUrgentes = () => {
    setUrgenteTipo("");
    setUrgenteRubroId(null);
    setUrgenteQ("");
    onLimpiarUrgentes();
  };

  const handleUrgenteTipoChange = (tipo: UrgentesFiltrosAplicados["tipo_urgente"]) => {
    setUrgenteTipo(tipo);
    onFiltrarUrgentes({
      tipo_urgente: tipo,
      rubro_id: urgenteRubroId,
      q_identificador: "",
      q_domicilio: urgenteQ.trim(),
    });
  };

  return (
    <Stack sx={planificacionFiltrosBarSx} spacing={0.75}>
      {distritoActivoId == null && isTotalMapa ? (
        <Typography sx={{ fontFamily: tactic, fontSize: "0.75rem", color: GLASS_COLORS.textMuted }}>
          Elegí un distrito en el mapa
        </Typography>
      ) : null}

      {isTotalMapa ? (
        <PlanificacionTipoFilterChips
          variant="totalMapa"
          metricas={metricas}
          cardActiva={cardActiva}
          onCardChange={onCardChange}
          loading={metricasLoading}
          disabled={distritoActivoId == null && metricas == null}
        />
      ) : (
        <PlanificacionTipoFilterChips
          variant="urgentes"
          urgenteTipoActivo={urgenteTipo}
          onUrgenteTipoChange={handleUrgenteTipoChange}
          disabled={urgentesLoading}
        />
      )}

      <PlanificacionRubroSelect
        value={isTotalMapa ? rubroId : urgenteRubroId}
        onChange={isTotalMapa ? setRubroId : setUrgenteRubroId}
        disabled={(isTotalMapa ? candidatosLoading : urgentesLoading) || (isTotalMapa && distritoActivoId == null)}
      />

      <TextField
        size="small"
        fullWidth
        label="Buscar domicilio o referencia"
        placeholder="Calle, número o referencia"
        value={isTotalMapa ? q : urgenteQ}
        onChange={(e) => (isTotalMapa ? setQ(e.target.value) : setUrgenteQ(e.target.value))}
        onKeyDown={(e) => {
          if (e.key !== "Enter") return;
          if (isTotalMapa) handleFiltrarCandidatos();
          else handleFiltrarUrgentes();
        }}
        disabled={isTotalMapa ? distritoActivoId == null : urgentesLoading}
        sx={planificacionTextFieldSx}
      />

      <Stack direction="row" spacing={1} alignItems="center" sx={filterCompactActionsSx}>
        <AppButton
          dsVariant="ghost"
          dsSize="sm"
          onClick={isTotalMapa ? handleLimpiarCandidatos : handleLimpiarUrgentes}
          disabled={isTotalMapa ? candidatosLoading : urgentesLoading}
          sx={filterCompactSecondaryButtonSx}
        >
          Limpiar
        </AppButton>
        <AppButton
          dsVariant="primary"
          dsSize="sm"
          onClick={isTotalMapa ? handleFiltrarCandidatos : handleFiltrarUrgentes}
          disabled={
            isTotalMapa
              ? candidatosLoading || distritoActivoId == null
              : urgentesLoading
          }
          sx={filterCompactPrimaryButtonSx}
        >
          Buscar
        </AppButton>
      </Stack>
    </Stack>
  );
}
