import { Stack, Typography } from "@mui/material";

import type { IRutaPoolDiaRow } from "../../../api/rutaPoolDiaApi";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { planificacionPanelTitleSx } from "../styles/institutionalVisual";

const tactic = '"Tactic Sans", sans-serif' as const;

export type PlanificacionResumenPanelProps = {
  poolItems: IRutaPoolDiaRow[];
  candidatosVisibles: number;
  candidatosTotal: number;
  urgentesTotal: number;
  poolEnGrupo: number;
  poolLibre: number;
  distritoNombre?: string | null;
  distritoActivoId: number | null;
};

function StatRow({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <Stack
      direction="row"
      justifyContent="space-between"
      alignItems="baseline"
      gap={1}
      sx={{
        py: 0.75,
        borderBottom: `1px solid ${GLASS_COLORS.borderLight}`,
        "&:last-of-type": { borderBottom: "none" },
      }}
    >
      <Stack spacing={0.15} sx={{ minWidth: 0 }}>
        <Typography
          sx={{
            fontFamily: tactic,
            fontSize: "0.78rem",
            fontWeight: 700,
            color: GLASS_COLORS.textPrimary,
          }}
        >
          {label}
        </Typography>
        {hint ? (
          <Typography sx={{ fontFamily: tactic, fontSize: "0.65rem", color: GLASS_COLORS.textMuted, lineHeight: 1.35 }}>
            {hint}
          </Typography>
        ) : null}
      </Stack>
      <Typography
        sx={{
          fontFamily: tactic,
          fontSize: "1rem",
          fontWeight: 800,
          color: GLASS_COLORS.textPrimary,
          flexShrink: 0,
        }}
      >
        {value}
      </Typography>
    </Stack>
  );
}

/**
 * Tab Resumen: estado operativo rápido (pool, candidatos, urgentes, grupos).
 */
export function PlanificacionResumenPanel({
  poolItems,
  candidatosVisibles,
  candidatosTotal,
  urgentesTotal,
  poolEnGrupo,
  poolLibre,
  distritoNombre,
  distritoActivoId,
}: PlanificacionResumenPanelProps) {
  return (
    <Stack spacing={1} sx={{ minHeight: 0, flex: 1 }}>
      <Typography sx={planificacionPanelTitleSx}>Resumen operativo</Typography>
      <Typography sx={{ fontFamily: tactic, fontSize: "0.75rem", color: GLASS_COLORS.textMuted, lineHeight: 1.45 }}>
        {distritoActivoId != null
          ? `Contexto: ${distritoNombre ?? `Distrito ${distritoActivoId}`}. Los grupos se arman en Asignación.`
          : "Elegí un distrito en el mapa para ver candidatos y métricas locales."}
      </Typography>

      <Stack sx={{ pt: 0.5 }}>
        <StatRow
          label="Candidatos agregables"
          value={distritoActivoId != null ? `${candidatosVisibles} / ${candidatosTotal}` : "—"}
          hint="Visibles en lista y mapa (sin pool)"
        />
        <StatRow label="Urgentes globales" value={urgentesTotal} hint="Bandeja M3 (todas las rutas)" />
        <StatRow label="Pool del día" value={poolItems.length} hint="Ítems en esta ruta" />
        <StatRow
          label="En pool (libre)"
          value={poolLibre}
          hint="Sin grupo asignado — listos para Asignación"
        />
        <StatRow
          label="En grupo"
          value={poolEnGrupo}
          hint="Ya asignados a un grupo — gestionar en Asignación"
        />
      </Stack>
    </Stack>
  );
}
