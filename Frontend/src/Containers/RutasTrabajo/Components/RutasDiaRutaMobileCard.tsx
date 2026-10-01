import FolderOpenIcon from "@mui/icons-material/FolderOpen";
import PublishedWithChangesIcon from "@mui/icons-material/PublishedWithChanges";
import { Box, Stack, Typography } from "@mui/material";

import type { IRutaTrabajo } from "../../../api/rutasTrabajoApi";
import { AppButton } from "../../../ui";
import { GLASS_COLORS, moduleContentPanelPaperSx } from "../../../styles/GlassStyles";
import { FONT_FAMILY_UI } from "../../../theme/typography";
import {
  rutasFormatFechaListado,
  rutasLabelEstadoRuta,
  rutasLabelTurno,
  type RutasListaTab,
} from "../utils/rutasEmptyViewDisplay";

const labelSx = {
  fontFamily: FONT_FAMILY_UI,
  fontSize: "0.6875rem",
  fontWeight: 700,
  letterSpacing: "0.06em",
  textTransform: "uppercase" as const,
  color: GLASS_COLORS.textMuted,
};

const valueSx = {
  fontFamily: FONT_FAMILY_UI,
  fontSize: "0.875rem",
  fontWeight: 500,
  color: GLASS_COLORS.textPrimary,
  lineHeight: 1.4,
  wordBreak: "break-word" as const,
};

export type RutasDiaRutaMobileCardProps = {
  ruta: IRutaTrabajo;
  tab: RutasListaTab;
  onOpen: (rutaId: number) => void;
};

/**
 * Card informativa del día + única acción «Abrir ruta» (móvil).
 */
export function RutasDiaRutaMobileCard({ ruta, tab, onOpen }: RutasDiaRutaMobileCardProps) {
  const Icon = tab === "borradores" ? FolderOpenIcon : PublishedWithChangesIcon;

  return (
    <Box
      sx={{
        ...moduleContentPanelPaperSx,
        p: 1.5,
        display: "flex",
        flexDirection: "column",
        gap: 1,
        minWidth: 0,
        width: "100%",
      }}
    >
      <Box sx={{ minWidth: 0 }}>
        <Typography sx={{ ...valueSx, fontWeight: 700, fontSize: "0.95rem" }}>
          Ruta {ruta.numero}
        </Typography>
        <Typography sx={{ ...valueSx, color: GLASS_COLORS.textSecondary, fontSize: "0.8125rem", mt: 0.25 }}>
          {rutasFormatFechaListado(ruta.fecha)} · {rutasLabelTurno(ruta.turno)}
        </Typography>
      </Box>

      <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap>
        <Box>
          <Typography sx={labelSx}>Estado</Typography>
          <Typography sx={valueSx}>{rutasLabelEstadoRuta(ruta.estado_ruta)}</Typography>
        </Box>
      </Stack>

      <AppButton
        dsVariant="primary"
        dsSize="sm"
        fullWidth
        startIcon={<Icon />}
        onClick={() => onOpen(ruta.id)}
        aria-label="Abrir ruta"
      >
        Abrir ruta
      </AppButton>
    </Box>
  );
}
