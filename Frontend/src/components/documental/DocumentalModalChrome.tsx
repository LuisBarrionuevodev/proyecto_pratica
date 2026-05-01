import { Box, Chip, Typography } from "@mui/material";

import {
  docModalChipSx,
  docModalFooterButtonsSx,
  docModalFooterRowSx,
  docModalHeaderStackSx,
  docModalReferenceSx,
  docModalSubtitleSx,
  docModalTitleSx,
} from "../../styles/documentalModalTokens";
import { AppButton } from "../../ui";

export type DocumentalModalTitleStackProps = {
  /** Texto del chip de dominio (p. ej. «Notificación», «Comprobación»). */
  dominioChip: string;
  titulo: string;
  subtitulo?: string | null;
  /** Misma referencia que en modales de comprobación: actuación base del circuito. */
  actuacionId?: number | null;
};

/**
 * Cabecera estándar de modales documentales (chip dominio → título → subtítulo → actuación).
 * Unifica jerarquía visual entre Notificación y Comprobación.
 */
export function DocumentalModalTitleStack({
  dominioChip,
  titulo,
  subtitulo,
  actuacionId,
}: DocumentalModalTitleStackProps) {
  return (
    <Box sx={{ ...docModalHeaderStackSx, width: "100%" }}>
      <Chip label={dominioChip} size="small" sx={docModalChipSx} variant="outlined" />
      <Typography component="span" variant="h6" sx={docModalTitleSx}>
        {titulo}
      </Typography>
      {subtitulo ? (
        <Typography variant="body2" sx={docModalSubtitleSx}>
          {subtitulo}
        </Typography>
      ) : null}
      {actuacionId != null ? (
        <Typography variant="caption" component="div" sx={{ ...docModalReferenceSx, maxWidth: "100%" }}>
          Actuación #{actuacionId}
        </Typography>
      ) : null}
    </Box>
  );
}

export type DocumentalModalFooterProps = {
  onCerrar: () => void;
  cerrarDisabled?: boolean;
};

/** Pie estándar: solo «Cerrar» (el refresco de bandejas queda en la barra de la página). */
export function DocumentalModalFooter({ onCerrar, cerrarDisabled }: DocumentalModalFooterProps) {
  return (
    <Box sx={docModalFooterRowSx}>
      <Box sx={{ flex: "1 1 120px", minWidth: 0 }} />
      <Box sx={docModalFooterButtonsSx}>
        <AppButton dsVariant="primary" dsSize="sm" onClick={onCerrar} disabled={cerrarDisabled}>
          Cerrar
        </AppButton>
      </Box>
    </Box>
  );
}
