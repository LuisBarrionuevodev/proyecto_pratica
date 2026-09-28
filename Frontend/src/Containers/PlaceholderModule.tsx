import { Box, Typography } from "@mui/material";
import { GLASS_COLORS } from "../styles/GlassStyles";
import { FONT_FAMILY_UI } from "../theme/typography";

type Props = { titulo: string };

/**
 * Vista mínima para rutas del menú aún sin módulo dedicado (sin APIs inventadas).
 */
export default function PlaceholderModule({ titulo }: Props) {
  return (
    <Box sx={{ p: 3, maxWidth: 560 }}>
      <Typography variant="h6" sx={{ fontFamily: FONT_FAMILY_UI, color: GLASS_COLORS.textPrimary, mb: 1 }}>
        {titulo}
      </Typography>
      <Typography variant="body2" sx={{ color: GLASS_COLORS.textMuted, fontFamily: FONT_FAMILY_UI }}>
        Módulo en preparación. Próximamente disponible.
      </Typography>
    </Box>
  );
}
