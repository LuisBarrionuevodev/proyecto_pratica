import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { Box, Paper, Stack, Tooltip } from "@mui/material";

import type { IRutaTrabajo } from "../../../api/rutasTrabajoApi";
import { moduleSlicesPanelPaperSx } from "../../../styles/GlassStyles";
import { AppButton } from "../../../ui";
import { RutasTrabajoFlowStepper, type RutaFlowStep } from "./RutasTrabajoFlowStepper";

export type RutaTrabajoCompactHeaderProps = {
  ruta: IRutaTrabajo;
  flowStep: RutaFlowStep;
  flowMaxUnlocked: RutaFlowStep;
  onStepChange: (step: RutaFlowStep) => void;
  showStepper?: boolean;
  onElegirOtraRuta?: () => void;
  onContinuarAsignacion?: () => void;
  onVolverPlanificacion?: () => void;
  onContinuarMapaFinal?: () => void;
  continuarMapaFinalDisabled?: boolean;
  continuarMapaFinalTooltip?: string;
  onVolverAsignacion?: () => void;
  onPublicarRuta?: () => void;
  canPublish?: boolean;
  publicarTooltip?: string;
  publishingRuta?: boolean;
  readOnly?: boolean;
  onVolverAlListado?: () => void;
};

/**
 * Header compacto: stepper a la izquierda, acciones del slide a la derecha.
 * Estado/fecha/turno viven en los bloques operativos de cada slide (pool / indicadores).
 */
export function RutaTrabajoCompactHeader({
  ruta: _ruta,
  flowStep,
  flowMaxUnlocked,
  onStepChange,
  showStepper = true,
  onElegirOtraRuta,
  onContinuarAsignacion,
  onVolverPlanificacion,
  onContinuarMapaFinal,
  continuarMapaFinalDisabled,
  continuarMapaFinalTooltip,
  onVolverAsignacion,
  onPublicarRuta,
  canPublish = false,
  publicarTooltip,
  publishingRuta = false,
  readOnly,
  onVolverAlListado,
}: RutaTrabajoCompactHeaderProps) {
  const actionButtons = readOnly ? (
    onVolverAlListado ? (
      <AppButton dsVariant="primary" dsSize="sm" onClick={onVolverAlListado}>
        Volver al listado
      </AppButton>
    ) : null
  ) : flowStep === 1 ? (
    <>
      {onElegirOtraRuta ? (
        <AppButton dsVariant="secondary" dsSize="sm" startIcon={<ArrowBackIcon />} onClick={onElegirOtraRuta}>
          Elegir otra ruta
        </AppButton>
      ) : null}
      {onContinuarAsignacion ? (
        <AppButton dsVariant="primary" dsSize="sm" onClick={onContinuarAsignacion}>
          Continuar a asignación
        </AppButton>
      ) : null}
    </>
  ) : flowStep === 2 ? (
    <>
      {onVolverPlanificacion ? (
        <AppButton dsVariant="secondary" dsSize="sm" onClick={onVolverPlanificacion}>
          Volver a planificación
        </AppButton>
      ) : null}
      {onContinuarMapaFinal ? (
        <Tooltip title={continuarMapaFinalTooltip ?? ""}>
          <span>
            <AppButton
              dsVariant="primary"
              dsSize="sm"
              onClick={onContinuarMapaFinal}
              disabled={continuarMapaFinalDisabled}
            >
              Continuar a mapa final
            </AppButton>
          </span>
        </Tooltip>
      ) : null}
    </>
  ) : (
    <>
      {onVolverAsignacion ? (
        <AppButton dsVariant="secondary" dsSize="sm" onClick={onVolverAsignacion}>
          Volver a asignación
        </AppButton>
      ) : null}
      {onPublicarRuta ? (
        <Tooltip
          title={
            publishingRuta
              ? "Publicando la ruta…"
              : publicarTooltip ??
                (canPublish
                  ? "Publica la ruta para habilitar documentos y operación."
                  : "Completá inspectores (mín. 2 por grupo) y OT guardada en cada ítem.")
          }
          placement="top"
        >
          <span>
            <AppButton
              dsVariant="primary"
              dsSize="sm"
              loading={publishingRuta}
              disabled={!canPublish}
              onClick={() => void onPublicarRuta()}
              data-testid="header-publicar-ruta"
            >
              {publishingRuta ? "Publicando…" : "Publicar"}
            </AppButton>
          </span>
        </Tooltip>
      ) : null}
    </>
  );

  return (
    <Paper
      elevation={0}
      data-testid="ruta-trabajo-compact-header"
      sx={{
        ...moduleSlicesPanelPaperSx,
        width: "100%",
        minWidth: 0,
        boxSizing: "border-box",
        px: { xs: 1.25, sm: 1.5 },
        py: 1,
      }}
    >
      <Stack
        direction={{ xs: "column", md: "row" }}
        alignItems={{ xs: "stretch", md: "center" }}
        spacing={1}
        sx={{ width: "100%", minWidth: 0 }}
      >
        {showStepper ? (
          <Box sx={{ flexShrink: 0, minWidth: 0 }}>
            <RutasTrabajoFlowStepper
              flowStep={flowStep}
              flowMaxUnlocked={flowMaxUnlocked}
              onStepChange={onStepChange}
            />
          </Box>
        ) : null}

        <Box sx={{ flexGrow: 1, minWidth: 8, display: { xs: "none", md: "block" } }} />

        <Stack
          direction="row"
          spacing={0.75}
          alignItems="center"
          flexWrap="wrap"
          useFlexGap
          data-testid="ruta-trabajo-header-actions"
          sx={{
            flexShrink: 0,
            ml: { xs: 0, md: "auto" },
            justifyContent: { xs: "flex-start", md: "flex-end" },
            alignSelf: { xs: "stretch", md: "center" },
          }}
        >
          {actionButtons}
        </Stack>
      </Stack>
    </Paper>
  );
}
