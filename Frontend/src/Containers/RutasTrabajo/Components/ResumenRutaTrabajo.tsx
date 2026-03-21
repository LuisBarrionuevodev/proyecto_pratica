import { Box, Paper, Stack, Typography } from "@mui/material";

import type { IRutaGrupoMin, IRutaTrabajo } from "../../../api/rutasTrabajoApi";
import { rutasInstitutionalResumenPaperSx } from "../styles/institutionalVisual";

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
        <Typography variant="subtitle1">Resumen de ruta</Typography>
        <Typography variant="body2" color="text.secondary">
          Todavía no hay una ruta seleccionada. Creá una ruta para comenzar.
        </Typography>
      </Paper>
    );
  }

  return (
    <Paper elevation={0} sx={rutasInstitutionalResumenPaperSx}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
          Resumen de ruta
        </Typography>
      </Stack>
      <Stack direction="row" spacing={2.5} flexWrap="wrap">
        <Box>
          <Typography variant="caption" color="text.secondary">
            Fecha
          </Typography>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            {ruta.fecha}
          </Typography>
        </Box>
        <Box>
          <Typography variant="caption" color="text.secondary">
            Turno
          </Typography>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            {ruta.turno}
          </Typography>
        </Box>
        <Box>
          <Typography variant="caption" color="text.secondary">
            Grupos
          </Typography>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            {grupos.length}
          </Typography>
        </Box>
        <Box>
          <Typography variant="caption" color="text.secondary">
            Items
          </Typography>
          <Typography variant="body2" sx={{ fontWeight: 700 }}>
            {itemsCount}
          </Typography>
        </Box>
        <Box>
          <Typography variant="caption" color="text.secondary">
            Inspectores
          </Typography>
          <Typography variant="body2" sx={{ fontWeight: 700 }}>
            {totalInspectores}
          </Typography>
        </Box>
        <Box sx={{ minWidth: 360, flex: 1 }}>
          <Typography variant="caption" color="text.secondary">
            Observaciones
          </Typography>
          <Typography variant="body2">{ruta.observaciones || "Sin observaciones registradas"}</Typography>
        </Box>
      </Stack>
    </Paper>
  );
};

export default ResumenRutaTrabajo;
