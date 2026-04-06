import { Box, Paper, Stack, Typography } from "@mui/material";

import type { IRutaGrupoMin, IRutaTrabajo } from "../../../api/rutasTrabajoApi";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { planificacionPanelSubtitleSx, rutasInstitutionalResumenPaperSx, rutasResumenTitleSx } from "../styles/institutionalVisual";

const TACTIC = '"Tactic Sans", sans-serif' as const;

interface Props {
  ruta: IRutaTrabajo | null;
  grupos: IRutaGrupoMin[];
  itemsCount: number;
}

const ResumenRutaTrabajo = ({ ruta, grupos, itemsCount }: Props) => {
  const totalInspectores = grupos.reduce((acc, grupo) => acc + grupo.inspectores.length, 0);
  if (!ruta) {
    return (
      <Paper elevation={0} sx={rutasInstitutionalResumenPaperSx}>
        <Typography sx={rutasResumenTitleSx}>Resumen de ruta</Typography>
        <Typography sx={{ ...planificacionPanelSubtitleSx, mt: 0.75 }}>
          Todavía no hay una ruta seleccionada. Creá una ruta para comenzar.
        </Typography>
      </Paper>
    );
  }

  return (
    <Paper elevation={0} sx={rutasInstitutionalResumenPaperSx}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
        <Typography sx={rutasResumenTitleSx}>Resumen de ruta</Typography>
      </Stack>
      <Stack direction="row" spacing={2.5} flexWrap="wrap">
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
        <Box sx={{ minWidth: 360, flex: 1 }}>
          <Typography variant="caption" sx={{ color: GLASS_COLORS.textMuted, fontFamily: TACTIC }}>
            Observaciones
          </Typography>
          <Typography variant="body2" sx={{ fontFamily: TACTIC, color: GLASS_COLORS.textSecondary, lineHeight: 1.45 }}>
            {ruta.observaciones || "Sin observaciones registradas"}
          </Typography>
        </Box>
      </Stack>
    </Paper>
  );
};

export default ResumenRutaTrabajo;
