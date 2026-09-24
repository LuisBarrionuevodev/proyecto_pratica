import { Stack } from "@mui/material";

import { AppSelect } from "../../ui";
import { ReinspeccionOficioResultadoFields } from "./ReinspeccionOficioResultadoFields";
import {
  tipoActuacionReinspeccionOficioOpts,
} from "./reinspeccionOficioSubtipo";
import type { ReinspeccionOficioFormState } from "./useReinspeccionOficioFormState";

export type ReinspeccionOficioFormProps = {
  form: ReinspeccionOficioFormState;
  contraOptions: { value: string; label: string }[];
  fieldErrors?: Record<string, string>;
  disabled?: boolean;
  /** Completar Trabajo: Verificar usa split legacy con contra externa. */
  verificarContraExterna?: boolean;
  showSubtipoSelector?: boolean;
};

/**
 * Formulario compartido de decisión operativa para reinspección por oficio.
 * Usado en Completar Trabajo y Editar Actuación.
 */
export function ReinspeccionOficioForm({
  form,
  contraOptions,
  fieldErrors = {},
  disabled = false,
  verificarContraExterna = false,
  showSubtipoSelector = true,
}: ReinspeccionOficioFormProps) {
  const fe = (k: string) => fieldErrors[k] ?? "";

  return (
    <Stack spacing={2}>
      {showSubtipoSelector && !form.subtipoReadonly ? (
        <AppSelect
          appearance="glass"
          label="Tipo de actuación"
          value={form.subtipo}
          onChange={(e) => form.setSubtipo(e.target.value as string)}
          fullWidth
          options={tipoActuacionReinspeccionOficioOpts()}
          disabled={disabled}
          error={Boolean(fe("tipo_actuacion"))}
          helperText={fe("tipo_actuacion") || "Elegí el subtipo de cierre del oficio."}
        />
      ) : null}

      {form.subtipo ? (
        <ReinspeccionOficioResultadoFields
          esRatificacion={form.esRatificacion}
          esVerificar={form.esVerificar}
          cumplimientoUi={form.cumplimientoUi}
          onCumplimientoUiChange={form.setCumplimientoUi}
          contraproducencia={form.contraproducencia}
          onContraproducenciaChange={form.setContraproducencia}
          contraOptions={contraOptions}
          realizoNuevaInspeccion={form.realizoNuevaInspeccion}
          onRealizoNuevaInspeccionChange={form.setRealizoNuevaInspeccion}
          verificarEstadoOperativo={form.verificarEstadoOperativo}
          onVerificarEstadoOperativoChange={form.setVerificarEstadoOperativo}
          fieldErrors={fieldErrors}
          disabled={disabled}
          verificarContraExterna={verificarContraExterna}
        />
      ) : null}
    </Stack>
  );
}
