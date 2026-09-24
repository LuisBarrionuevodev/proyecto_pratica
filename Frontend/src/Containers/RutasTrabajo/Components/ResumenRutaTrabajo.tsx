import { Box, Stack, Typography } from "@mui/material";

import type { IRutaGrupoMin, IRutaTrabajo } from "../../../api/rutasTrabajoApi";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { planificacionPanelSubtitleSx } from "../styles/institutionalVisual";

const TACTIC = '"Tactic Sans", sans-serif' as const;

interface MetricasProps {
  ruta: IRutaTrabajo | null;
  grupos: IRutaGrupoMin[];
  itemsCount: number;
  /** Si true, no repite Fecha/Turno (p. ej. cuando ya van en chips del header). */
  omitFechaTurno?: boolean;
}

/**
 * Métricas de resumen (sin tarjeta ni título). Para incrustar en `RutaResumenHeaderCard` u otros layouts.
 */
export function RutaResumenMetricasInline({ ruta, grupos, itemsCount, omitFechaTurno = false }: MetricasProps) {
  const totalInspectores = grupos.reduce((acc, grupo) => acc + grupo.inspectores.length, 0);
  if (!ruta) {
    return (
      <Typography sx={{ ...planificacionPanelSubtitleSx, mt: 0.75 }}>Sin ruta. Crear borrador.</Typography>
    );
  }

  return (
    <Stack direction="row" spacing={2.5} flexWrap="wrap" rowGap={1.25}>
      {!omitFechaTurno ? (
        <>
          <Box>
            <Typography variant="caption" sx={{ color: GLASS_COLORS.textMuted, fontFamily: TACTIC }}>
              Fecha
            </Typography>
            <Typography variant="body2" sx={{ fontWeight: 600, fontFamily: TACTIC, color: GLASS_COLORS.textPrimary }}>
              {ruta.fecha}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" sx={{ color: GLASS_COLORS.textMuted, fontFamily: TACTIC }}>
              Turno
            </Typography>
            <Typography variant="body2" sx={{ fontWeight: 600, fontFamily: TACTIC, color: GLASS_COLORS.textPrimary }}>
              {ruta.turno}
            </Typography>
          </Box>
        </>
      ) : null}
      <Box>
        <Typography variant="caption" sx={{ color: GLASS_COLORS.textMuted, fontFamily: TACTIC }}>
          Grupos
        </Typography>
        <Typography variant="body2" sx={{ fontWeight: 600, fontFamily: TACTIC, color: GLASS_COLORS.textPrimary }}>
          {grupos.length}
        </Typography>
      </Box>
      <Box>
        <Typography variant="caption" sx={{ color: GLASS_COLORS.textMuted, fontFamily: TACTIC }}>
          Items
        </Typography>
        <Typography variant="body2" sx={{ fontWeight: 700, fontFamily: TACTIC, color: GLASS_COLORS.textPrimary }}>
          {itemsCount}
        </Typography>
      </Box>
      <Box>
        <Typography variant="caption" sx={{ color: GLASS_COLORS.textMuted, fontFamily: TACTIC }}>
          Inspectores
        </Typography>
        <Typography variant="body2" sx={{ fontWeight: 700, fontFamily: TACTIC, color: GLASS_COLORS.textPrimary }}>
          {totalInspectores}
        </Typography>
      </Box>
      <Box sx={{ minWidth: 200, flex: 1, maxWidth: 480 }}>
        <Typography variant="caption" sx={{ color: GLASS_COLORS.textMuted, fontFamily: TACTIC }}>
          Observaciones
        </Typography>
        <Typography variant="body2" sx={{ fontFamily: TACTIC, color: GLASS_COLORS.textSecondary, lineHeight: 1.4 }}>
          {ruta.observaciones?.trim() || "—"}
        </Typography>
      </Box>
    </Stack>
  );
}
