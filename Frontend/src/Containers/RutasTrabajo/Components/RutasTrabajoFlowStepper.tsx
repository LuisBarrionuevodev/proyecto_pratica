import { Box, Stack, Typography } from "@mui/material";
import CheckRoundedIcon from "@mui/icons-material/CheckRounded";

import { GLASS_COLORS } from "../../../styles/GlassStyles";

const tactic = '"Tactic Sans", sans-serif' as const;

export type RutaFlowStep = 1 | 2 | 3;

const STEPS: { step: RutaFlowStep; label: string }[] = [
  { step: 1, label: "Planificación" },
  { step: 2, label: "Asignación" },
  { step: 3, label: "Mapa final" },
];

export type RutasTrabajoFlowStepperProps = {
  /** Paso visible (1–3). */
  flowStep: RutaFlowStep;
  /** Máximo paso desbloqueado por CTAs (1 = solo planificación). */
  flowMaxUnlocked: RutaFlowStep;
  onStepChange: (step: RutaFlowStep) => void;
};

/**
 * Navegación secuencial del borrador: paso actual, completados y futuros bloqueados hasta avanzar con CTA.
 */
export function RutasTrabajoFlowStepper({ flowStep, flowMaxUnlocked, onStepChange }: RutasTrabajoFlowStepperProps) {
  return (
    <Stack
      component="nav"
      aria-label="Etapas del borrador de ruta"
      direction="row"
      alignItems="center"
      flexWrap="wrap"
      useFlexGap
      spacing={1}
    >
      {STEPS.map(({ step, label }, idx) => {
        const disabled = step > flowMaxUnlocked;
        const active = flowStep === step;
        /** Pasos estrictamente anteriores al actual (al volver atrás no marcamos “completado” etapas posteriores). */
        const completed = flowStep > step;

        return (
          <Stack key={step} direction="row" alignItems="center" spacing={1}>
            {idx > 0 ? (
              <Box
                component="span"
                sx={{
                  width: 24,
                  height: 1,
                  backgroundColor: disabled ? GLASS_COLORS.borderLight : GLASS_COLORS.borderMedium,
                  opacity: 0.8,
                }}
                aria-hidden
              />
            ) : null}
            <Box
              component="button"
              type="button"
              disabled={disabled}
              aria-current={active ? "step" : undefined}
              onClick={() => {
                if (!disabled) onStepChange(step);
              }}
              sx={{
                fontFamily: tactic,
                fontSize: "0.8rem",
                fontWeight: active ? 700 : 600,
                letterSpacing: "0.02em",
                borderRadius: "10px",
                border: `1px solid ${
                  active ? GLASS_COLORS.borderActive : completed ? GLASS_COLORS.borderMedium : GLASS_COLORS.borderLight
                }`,
                backgroundColor: active
                  ? "rgba(1, 102, 255, 0.18)"
                  : completed
                    ? "rgba(255,255,255,0.06)"
                    : "rgba(0,0,0,0.2)",
                color: disabled ? GLASS_COLORS.textMuted : GLASS_COLORS.textPrimary,
                px: 1.5,
                py: 0.75,
                cursor: disabled ? "not-allowed" : "pointer",
                opacity: disabled ? 0.45 : 1,
                display: "inline-flex",
                alignItems: "center",
                gap: 0.75,
                transition: "background-color 0.15s, border-color 0.15s",
                "&:hover:not(:disabled)": {
                  backgroundColor: active ? "rgba(1, 102, 255, 0.22)" : "rgba(255,255,255,0.08)",
                },
              }}
            >
              <Box
                component="span"
                sx={{
                  width: 22,
                  height: 22,
                  borderRadius: "50%",
                  fontSize: "0.7rem",
                  fontWeight: 800,
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                  border: `1px solid ${active ? GLASS_COLORS.primary : GLASS_COLORS.borderLight}`,
                  backgroundColor: completed ? "rgba(76, 175, 80, 0.2)" : "transparent",
                  color: active ? GLASS_COLORS.primary : GLASS_COLORS.textSecondary,
                }}
              >
                {completed ? <CheckRoundedIcon sx={{ fontSize: 16 }} /> : step}
              </Box>
              <Typography component="span" sx={{ fontFamily: tactic, fontSize: "inherit", fontWeight: "inherit" }}>
                {label}
              </Typography>
            </Box>
          </Stack>
        );
      })}
    </Stack>
  );
}
