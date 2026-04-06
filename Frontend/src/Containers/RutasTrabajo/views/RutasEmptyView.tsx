import AddIcon from "@mui/icons-material/Add";
import FactCheckIcon from "@mui/icons-material/FactCheck";
import { Box, Stack, Typography } from "@mui/material";
import { useMemo } from "react";

import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { AppButton, CardGlass } from "../../../ui";

const tactic = '"Tactic Sans", sans-serif' as const;

export type RutasEmptyViewProps = {
  /** Abre el modal de creación de ruta (BORRADOR). */
  onCrearBorrador: () => void;
};

/**
 * Vista inicial cuando no hay borrador en la pestaña TABLA: planificación diaria, fecha y CTA para crear ruta.
 * Superficie `CardGlass` alineada al resto de Rutas de trabajo.
 */
export function RutasEmptyView({ onCrearBorrador }: RutasEmptyViewProps) {
  const fechaHoyLegible = useMemo(
    () =>
      new Date().toLocaleDateString("es-AR", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
      }),
    []
  );

  return (
    <Box
      sx={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        py: { xs: 2, sm: 4 },
        px: 1,
        minHeight: { xs: "auto", sm: "min(52vh, 420px)" },
      }}
    >
      <CardGlass
        sx={{
          maxWidth: 480,
          width: "100%",
          textAlign: "center",
        }}
        contentPadding="md"
      >
        <Stack spacing={2.25} alignItems="center">
          <Box
            sx={{
              width: 76,
              height: 76,
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              backgroundColor: "rgba(1, 102, 255, 0.1)",
              border: `1px solid ${GLASS_COLORS.borderActive}`,
              boxShadow: `0 0 24px ${GLASS_COLORS.primaryGlow}`,
            }}
            aria-hidden
          >
            <FactCheckIcon sx={{ fontSize: 38, color: GLASS_COLORS.primary }} />
          </Box>

          <Typography
            component="p"
            sx={{
              fontFamily: tactic,
              fontSize: "0.6875rem",
              fontWeight: 600,
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              color: GLASS_COLORS.textMuted,
              m: 0,
            }}
          >
            Planificación diaria
          </Typography>

          <Typography
            variant="h5"
            component="h2"
            sx={{
              fontFamily: tactic,
              fontWeight: 700,
              color: GLASS_COLORS.textPrimary,
              lineHeight: 1.25,
              m: 0,
            }}
          >
            Rutas de trabajo
          </Typography>

          <Typography
            sx={{
              fontFamily: tactic,
              fontSize: "1.375rem",
              fontWeight: 700,
              color: GLASS_COLORS.primary,
              lineHeight: 1.2,
              m: 0,
            }}
          >
            {fechaHoyLegible}
          </Typography>

          <Typography
            variant="body2"
            sx={{
              fontFamily: tactic,
              color: GLASS_COLORS.textSecondary,
              maxWidth: 360,
              mx: "auto",
              lineHeight: 1.55,
            }}
          >
            ¿Querés crear una ruta de trabajo para hoy? El borrador te permite armar grupos, asignar iniciadores y
            publicar cuando esté listo.
          </Typography>

          <AppButton
            dsVariant="primary"
            dsSize="lg"
            fullWidth
            startIcon={<AddIcon />}
            onClick={onCrearBorrador}
            sx={{
              fontFamily: tactic,
              fontWeight: 700,
              mt: 0.5,
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            Crear nueva ruta
          </AppButton>
        </Stack>
      </CardGlass>
    </Box>
  );
}
