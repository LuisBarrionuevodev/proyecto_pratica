import { Box, Stack } from "@mui/material";

import { AppSelect } from "../../ui";
import { OFICIO_CUMPLE_OPTS } from "../../Containers/CompletarTrabajos/utils/completarTrabajoReinspeccionOficioUi";
import {
  REALIZO_NUEVA_INSPECCION_OPTS,
} from "../../Containers/CompletarTrabajos/utils/completarTrabajoTipoIniciadorUi";
import type { ReinspeccionOficioCumplimientoUi } from "./resolveReinspeccionOficioFormContext";

const CUMPLIMIENTO_OPTS: { value: string; label: string }[] = [
  { value: "", label: "—" },
  { value: "CUMPLE", label: "Sí (cumple)" },
  { value: "NO_CUMPLE", label: "No (no cumple)" },
  { value: "CONTRAPRODUCENCIA", label: "No cumple — con contraproducencia" },
];

export type ReinspeccionOficioResultadoFieldsProps = {
  esRatificacion: boolean;
  esVerificar: boolean;
  subtipoReadonly?: boolean;
  subtipoLabel?: string;
  cumplimientoUi: ReinspeccionOficioCumplimientoUi;
  onCumplimientoUiChange: (v: ReinspeccionOficioCumplimientoUi) => void;
  contraproducencia: string;
  onContraproducenciaChange: (v: string) => void;
  contraOptions: { value: string; label: string }[];
  realizoNuevaInspeccion: "" | "si" | "no";
  onRealizoNuevaInspeccionChange: (v: "" | "si" | "no") => void;
  fieldErrors?: Record<string, string>;
  disabled?: boolean;
  /** Completar Trabajo muestra contraproducencia en bloque aparte cuando Verificar = No. */
  verificarContraExterna?: boolean;
};

/**
 * Campos compartidos de resultado operativo para reinspección por oficio.
 * Sin submit: el padre maneja lifecycle y endpoints.
 */
export function ReinspeccionOficioResultadoFields({
  esRatificacion,
  esVerificar,
  cumplimientoUi,
  onCumplimientoUiChange,
  contraproducencia,
  onContraproducenciaChange,
  contraOptions,
  realizoNuevaInspeccion,
  onRealizoNuevaInspeccionChange,
  fieldErrors = {},
  disabled = false,
  verificarContraExterna = false,
}: ReinspeccionOficioResultadoFieldsProps) {
  const fe = (k: string) => fieldErrors[k] ?? "";

  return (
    <Stack spacing={2} component="div">
      {esRatificacion ? (
        <>
          <AppSelect
            appearance="glass"
            label="¿Dio cumplimiento?"
            value={cumplimientoUi}
            onChange={(e) =>
              onCumplimientoUiChange((e.target.value as ReinspeccionOficioCumplimientoUi) || "")
            }
            fullWidth
            options={CUMPLIMIENTO_OPTS}
            disabled={disabled}
            error={Boolean(fe("resultado_cumplimiento_oficio"))}
            helperText={fe("resultado_cumplimiento_oficio") || "Indicá si el establecimiento dio cumplimiento al oficio."}
          />
          {cumplimientoUi === "CONTRAPRODUCENCIA" ? (
            <AppSelect
              appearance="glass"
              label="Contraproducencia"
              value={contraproducencia}
              onChange={(e) => onContraproducenciaChange(e.target.value as string)}
              fullWidth
              options={[{ value: "", label: "—" }, ...contraOptions]}
              disabled={disabled}
              error={Boolean(fe("contraproducencia"))}
              helperText={fe("contraproducencia") || undefined}
            />
          ) : null}
        </>
      ) : null}

      {esVerificar ? (
        <Box>
          <AppSelect
            appearance="glass"
            label="¿Realizó nueva inspección?"
            value={realizoNuevaInspeccion}
            onChange={(e) =>
              onRealizoNuevaInspeccionChange((e.target.value as "" | "si" | "no") || "")
            }
            fullWidth
            options={REALIZO_NUEVA_INSPECCION_OPTS}
            disabled={disabled}
            error={Boolean(fe("realizo_nueva_inspeccion"))}
            helperText={
              fe("realizo_nueva_inspeccion") ||
              "Si realizó inspección, elegí Sí para cargar actas. Si no, elegí No para cerrar sin actas normales."
            }
          />
          {realizoNuevaInspeccion === "no" && !verificarContraExterna ? (
            <AppSelect
              appearance="glass"
              label="Contraproducencia"
              value={contraproducencia}
              onChange={(e) => onContraproducenciaChange(e.target.value as string)}
              fullWidth
              sx={{ mt: 2 }}
              options={[{ value: "", label: "Sin contraproducencia (visita realizada)" }, ...contraOptions]}
              disabled={disabled}
              error={Boolean(fe("contraproducencia"))}
              helperText={fe("contraproducencia") || undefined}
            />
          ) : null}
        </Box>
      ) : null}
    </Stack>
  );
}

/** Re-export para ratificación que usa solo CUMPLE/NO_CUMPLE en Completar (legacy opts). */
export { OFICIO_CUMPLE_OPTS };
