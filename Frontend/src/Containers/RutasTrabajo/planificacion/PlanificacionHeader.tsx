import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { Box, Stack, Typography } from "@mui/material";
import type { IRutaTrabajo } from "../../../api/rutasTrabajoApi";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { AppButton } from "../../../ui";

export type PlanificacionHeaderProps = {
  ruta: IRutaTrabajo;
  /** Vuelve a la pantalla inicial (elegir otro borrador o crear ruta). */
  onVolverAElegirRuta: () => void;
  onContinuarAsignacion: () => void;
  continuarDisabled?: boolean;
};

const tactic = '"Tactic Sans", sans-serif' as const;

/**
 * Cabecera de la etapa Planificación: metadatos de ruta y CTA hacia Asignación.
 */
export function PlanificacionHeader({
  ruta,
  onVolverAElegirRuta,
  onContinuarAsignacion,
  continuarDisabled = false,
}: PlanificacionHeaderProps) {
  const fechaFmt = ruta.fecha
    ? new Date(ruta.fecha + "T12:00:00").toLocaleDateString("es-AR", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      })
    : "—";
  const turnoLabel = ruta.turno === "MANIANA" ? "Mañana" : "Tarde";

  return (
    <Box sx={{ mb: 1 }}>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={2}
        alignItems={{ sm: "center" }}
        justifyContent="space-between"
      >
        <Box>
          <Typography sx={{ fontFamily: tactic, fontWeight: 700, fontSize: "1.35rem", color: GLASS_COLORS.textPrimary }}>
            Planificación
          </Typography>
          <Stack direction="row" spacing={1.5} flexWrap="wrap" alignItems="center" sx={{ mt: 1 }}>
            <Typography sx={{ fontFamily: tactic, color: GLASS_COLORS.textSecondary, fontSize: "0.8125rem" }}>
              {fechaFmt} · {turnoLabel}
            </Typography>
            <Box
              component="span"
              sx={{
                px: 1,
                py: 0.25,
                borderRadius: 1,
                fontFamily: tactic,
                fontSize: "0.75rem",
                fontWeight: 700,
                backgroundColor: "rgba(1, 102, 255, 0.15)",
                color: GLASS_COLORS.primary,
                border: `1px solid ${GLASS_COLORS.borderActive}`,
              }}
            >
              {ruta.estado_ruta}
            </Box>
          </Stack>
        </Box>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          spacing={1.25}
          alignItems={{ xs: "stretch", sm: "center" }}
          sx={{ width: { xs: "100%", sm: "auto" } }}
        >
          <AppButton
            dsVariant="secondary"
            dsSize="md"
            startIcon={<ArrowBackIcon />}
            onClick={onVolverAElegirRuta}
            sx={{ fontFamily: tactic, fontWeight: 600, order: { xs: 2, sm: 1 } }}
          >
            Elegir otra ruta
          </AppButton>
          <AppButton
            dsVariant="primary"
            dsSize="md"
            disabled={continuarDisabled}
            onClick={onContinuarAsignacion}
            sx={{ fontFamily: tactic, fontWeight: 700, order: { xs: 1, sm: 2 } }}
          >
            Continuar a asignación
          </AppButton>
        </Stack>
      </Stack>
    </Box>
  );
}
