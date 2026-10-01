import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import FolderOpenIcon from "@mui/icons-material/FolderOpen";
import PublishedWithChangesIcon from "@mui/icons-material/PublishedWithChanges";
import { Box, Stack, Typography } from "@mui/material";

import type { IRutaTrabajo } from "../../../api/rutasTrabajoApi";
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
 * Card táctil de acceso a ruta (listado del día en móvil).
 */
export function RutasDiaRutaMobileCard({ ruta, tab, onOpen }: RutasDiaRutaMobileCardProps) {
  const open = () => onOpen(ruta.id);
  const Icon = tab === "borradores" ? FolderOpenIcon : PublishedWithChangesIcon;

  return (
    <Box
      component="button"
      type="button"
      aria-label="Abrir ruta"
      onClick={open}
      sx={{
        ...moduleContentPanelPaperSx,
        p: 1.5,
        display: "flex",
        flexDirection: "column",
        gap: 1,
        minWidth: 0,
        width: "100%",
        textAlign: "left",
        cursor: "pointer",
        border: "none",
        font: "inherit",
        color: "inherit",
        "&:hover": { filter: "brightness(1.02)" },
      }}
    >
      <Box sx={{ display: "flex", alignItems: "flex-start", gap: 1, minWidth: 0 }}>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography sx={{ ...valueSx, fontWeight: 700, fontSize: "0.95rem" }}>
            Ruta {ruta.numero}
          </Typography>
          <Typography sx={{ ...valueSx, color: GLASS_COLORS.textSecondary, fontSize: "0.8125rem", mt: 0.25 }}>
            {rutasFormatFechaListado(ruta.fecha)} · {rutasLabelTurno(ruta.turno)}
          </Typography>
        </Box>
        <Box
          aria-hidden
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: GLASS_COLORS.textSecondary,
            flexShrink: 0,
            pointerEvents: "none",
          }}
        >
          <ChevronRightIcon fontSize="small" />
        </Box>
      </Box>

      <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap>
        <Box>
          <Typography sx={labelSx}>Estado</Typography>
          <Typography sx={valueSx}>{rutasLabelEstadoRuta(ruta.estado_ruta)}</Typography>
        </Box>
      </Stack>

      <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, color: GLASS_COLORS.primary }}>
        <Icon sx={{ fontSize: 18 }} />
        <Typography sx={{ fontFamily: FONT_FAMILY_UI, fontSize: "0.8125rem", fontWeight: 700 }}>
          Abrir ruta
        </Typography>
      </Box>
    </Box>
  );
}
