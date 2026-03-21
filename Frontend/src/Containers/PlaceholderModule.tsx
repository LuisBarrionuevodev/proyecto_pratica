import { Box, Typography } from "@mui/material";
import { GLASS_COLORS } from "../styles/GlassStyles";

type Props = { titulo: string };

/**
 * Vista mínima para rutas del menú aún sin módulo dedicado (sin APIs inventadas).
 */
export default function PlaceholderModule({ titulo }: Props) {
  return (
    <Box sx={{ p: 3, maxWidth: 560 }}>
      <Typography variant="h6" sx={{ fontFamily: '"Tactic Sans", sans-serif', color: GLASS_COLORS.textPrimary, mb: 1 }}>
        {titulo}
      </Typography>
      <Typography variant="body2" sx={{ color: GLASS_COLORS.textMuted, fontFamily: '"Tactic Sans", sans-serif' }}>
        Módulo en preparación. Próximamente disponible.
      </Typography>
    </Box>
  );
}
