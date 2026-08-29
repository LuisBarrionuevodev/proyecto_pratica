import type { ReinspeccionOficioCumplimientoUi } from "./resolveReinspeccionOficioFormContext";

export type ReinspeccionOficioValidationInput = {
  esRatificacion: boolean;
  esVerificar: boolean;
  cumplimientoUi: ReinspeccionOficioCumplimientoUi;
  contraproducencia: string;
  realizoNuevaInspeccion: "" | "si" | "no";
  tieneActasInspeccionNormal: boolean;
  subtipoPendiente?: boolean;
};

export type ReinspeccionOficioValidationResult =
  | { ok: true }
  | { ok: false; field: string; message: string };

export const MSG_RESULTADO_REQUERIDO = "Resultado de cumplimiento: seleccione una opción.";
export const MSG_REALIZO_REQUERIDO = "Nueva inspección: indique si realizó una nueva inspección.";
export const MSG_SI_A_NO_CON_ACTAS =
  "Para indicar que no realizó una nueva inspección, primero debe quitar las actas labradas.";
export const MSG_SUBTIPO_REQUERIDO = "Elegí el tipo de actuación.";

/**
 * Validación compartida de corrección/cierre por oficio.
 */
export function validateReinspeccionOficioForm(
  input: ReinspeccionOficioValidationInput
): ReinspeccionOficioValidationResult {
  if (input.subtipoPendiente) {
    return { ok: false, field: "tipo_actuacion", message: MSG_SUBTIPO_REQUERIDO };
  }

  if (input.esRatificacion) {
    if (!input.cumplimientoUi) {
      return { ok: false, field: "resultado_cumplimiento_oficio", message: MSG_RESULTADO_REQUERIDO };
    }
    if (input.cumplimientoUi === "CONTRAPRODUCENCIA" && !input.contraproducencia.trim()) {
      return {
        ok: false,
        field: "contraproducencia",
        message: "Seleccioná la contraproducencia correspondiente.",
      };
    }
    return { ok: true };
  }

  if (input.esVerificar) {
    if (!input.realizoNuevaInspeccion) {
      return { ok: false, field: "realizo_nueva_inspeccion", message: MSG_REALIZO_REQUERIDO };
    }
    if (input.realizoNuevaInspeccion === "no" && input.tieneActasInspeccionNormal) {
      return { ok: false, field: "realizo_nueva_inspeccion", message: MSG_SI_A_NO_CON_ACTAS };
    }
    return { ok: true };
  }

  return { ok: true };
}

export function oficioCorreccionPayloadFromUi(params: {
  tipoActuacion: string;
  cumplimientoUi: ReinspeccionOficioCumplimientoUi;
  contraproducencia: string;
  realizoNuevaInspeccion: "" | "si" | "no";
  esRatificacion: boolean;
  esVerificar: boolean;
}): {
  tipo_actuacion: string;
  resultado_cumplimiento_oficio?: string | null;
  contraproducencia?: string | null;
  realizo_nueva_inspeccion?: boolean | null;
} {
  const base = { tipo_actuacion: params.tipoActuacion };
  if (params.esRatificacion) {
    if (params.cumplimientoUi === "CUMPLE") {
      return { ...base, resultado_cumplimiento_oficio: "CUMPLE", contraproducencia: null };
    }
    if (params.cumplimientoUi === "NO_CUMPLE") {
      return { ...base, resultado_cumplimiento_oficio: "NO_CUMPLE", contraproducencia: null };
    }
    if (params.cumplimientoUi === "CONTRAPRODUCENCIA") {
      return {
        ...base,
        resultado_cumplimiento_oficio: null,
        contraproducencia: params.contraproducencia.trim() || null,
      };
    }
    return base;
  }
  if (params.esVerificar) {
    const rni =
      params.realizoNuevaInspeccion === "si"
        ? true
        : params.realizoNuevaInspeccion === "no"
          ? false
          : null;
    return {
      ...base,
      realizo_nueva_inspeccion: rni,
      contraproducencia: params.contraproducencia.trim() || null,
      resultado_cumplimiento_oficio: null,
    };
  }
  return base;
}

export function oficioCorreccionDirty(
  original: {
    resultado_cumplimiento_oficio?: string | null;
    contraproducencia?: string | null;
    realizo_nueva_inspeccion?: boolean | null;
  },
  current: {
    cumplimientoUi: ReinspeccionOficioCumplimientoUi;
    contraproducencia: string;
    realizoNuevaInspeccion: "" | "si" | "no";
  }
): boolean {
  const origCumpl =
    (original.resultado_cumplimiento_oficio ?? "").trim().toUpperCase() === "CUMPLE"
      ? "CUMPLE"
      : (original.contraproducencia ?? "").trim()
        ? "CONTRAPRODUCENCIA"
        : (original.resultado_cumplimiento_oficio ?? "").trim().toUpperCase() === "NO_CUMPLE"
          ? "NO_CUMPLE"
          : ("" as ReinspeccionOficioCumplimientoUi);

  const origRealizo =
    original.realizo_nueva_inspeccion === true
      ? "si"
      : original.realizo_nueva_inspeccion === false
        ? "no"
        : "";

  return (
    origCumpl !== current.cumplimientoUi ||
    (original.contraproducencia ?? "").trim() !== current.contraproducencia.trim() ||
    origRealizo !== current.realizoNuevaInspeccion
  );
}
