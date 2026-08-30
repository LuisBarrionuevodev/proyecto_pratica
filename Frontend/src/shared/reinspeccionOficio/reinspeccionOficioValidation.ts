import type { ReinspeccionOficioCumplimientoUi } from "./resolveReinspeccionOficioFormContext";
import {
  isPersistedVerificarOperationalInconsistent,
  MSG_VERIFICAR_ESTADO_REQUERIDO,
  MSG_VERIFICAR_SI_A_CONTRA_CON_ACTAS,
  resolveVerificarEstadoFromPersisted,
  verificarEstadoToPayload,
  type VerificarEstadoOperativo,
  type VerificarEstadoResuelto,
} from "./verificarEstadoOperativo";

export type ReinspeccionOficioValidationInput = {
  esRatificacion: boolean;
  esVerificar: boolean;
  cumplimientoUi: ReinspeccionOficioCumplimientoUi;
  contraproducencia: string;
  realizoNuevaInspeccion: "" | "si" | "no";
  verificarEstadoOperativo?: VerificarEstadoOperativo;
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

export { MSG_VERIFICAR_ESTADO_REQUERIDO, isPersistedVerificarOperationalInconsistent };
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
    const estado = input.verificarEstadoOperativo ?? "";
    if (!estado) {
      return {
        ok: false,
        field: "verificar_estado_operativo",
        message: MSG_VERIFICAR_ESTADO_REQUERIDO,
      };
    }
    if (estado === "CONTRAPRODUCENCIA" && !input.contraproducencia.trim()) {
      return {
        ok: false,
        field: "contraproducencia",
        message: "Seleccioná la contraproducencia correspondiente.",
      };
    }
    if (input.tieneActasInspeccionNormal) {
      if (estado === "NO_INSPECCION") {
        return { ok: false, field: "verificar_estado_operativo", message: MSG_SI_A_NO_CON_ACTAS };
      }
      if (estado === "CONTRAPRODUCENCIA") {
        return {
          ok: false,
          field: "verificar_estado_operativo",
          message: MSG_VERIFICAR_SI_A_CONTRA_CON_ACTAS,
        };
      }
    }
    return { ok: true };
  }

  return { ok: true };
}

/**
 * True si el estado persistido viola el invariante CUMPLE + contraproducencia.
 */
export function isPersistedOficioOperationalInconsistent(original: {
  resultado_cumplimiento_oficio?: string | null;
  contraproducencia?: string | null;
}): boolean {
  const res = (original.resultado_cumplimiento_oficio ?? "").trim().toUpperCase();
  const contra = (original.contraproducencia ?? "").trim();
  return res === "CUMPLE" && Boolean(contra);
}

export function oficioCorreccionPayloadFromUi(params: {
  tipoActuacion: string;
  cumplimientoUi: ReinspeccionOficioCumplimientoUi;
  contraproducencia: string;
  realizoNuevaInspeccion: "" | "si" | "no";
  verificarEstadoOperativo?: VerificarEstadoOperativo;
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
  if (params.esVerificar && params.verificarEstadoOperativo) {
    return verificarEstadoToPayload({
      tipoActuacion: params.tipoActuacion,
      verificarEstado: params.verificarEstadoOperativo,
      contraproducencia: params.contraproducencia,
    });
  }
  return base;
}

export function oficioCorreccionDirty(
  original: {
    tipo_actuacion?: string | null;
    resultado_cumplimiento_oficio?: string | null;
    contraproducencia?: string | null;
    realizo_nueva_inspeccion?: boolean | null;
  },
  current: {
    tipoActuacion?: string;
    cumplimientoUi: ReinspeccionOficioCumplimientoUi;
    contraproducencia: string;
    realizoNuevaInspeccion: "" | "si" | "no";
    verificarEstadoOperativo?: VerificarEstadoOperativo;
  }
): boolean {
  const origTipo = (original.tipo_actuacion ?? "").trim();
  const currTipo = (current.tipoActuacion ?? origTipo).trim();
  if (origTipo && currTipo && origTipo !== currTipo) {
    return true;
  }
  if (isPersistedOficioOperationalInconsistent(original)) {
    return true;
  }
  if (isPersistedVerificarOperationalInconsistent(original)) {
    return true;
  }

  const origVerificarEstado = resolveVerificarEstadoFromPersisted(original);
  if (origVerificarEstado === "INCONSISTENTE") {
    return true;
  }
  if (current.verificarEstadoOperativo !== undefined) {
    if (origVerificarEstado !== current.verificarEstadoOperativo) {
      return true;
    }
    if (
      current.verificarEstadoOperativo === "CONTRAPRODUCENCIA" &&
      (original.contraproducencia ?? "").trim() !== current.contraproducencia.trim()
    ) {
      return true;
    }
    return false;
  }

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

/** Re-export para tests y consumidores. */
export type { VerificarEstadoOperativo, VerificarEstadoResuelto };
