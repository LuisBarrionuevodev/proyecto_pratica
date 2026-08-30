/**
 * Máquina de estados operativos para VERIFICAR E INFORMAR (GESTIÓN-FIX.2C.4).
 * Los tres estados son mutuamente excluyentes.
 */

export type VerificarEstadoOperativo =
  | ""
  | "CONTRAPRODUCENCIA"
  | "NO_INSPECCION"
  | "SI_INSPECCION";

/** Persistido inválido: contra y realizo boolean coexisten. */
export type VerificarEstadoResuelto = VerificarEstadoOperativo | "INCONSISTENTE";

export const MSG_VERIFICAR_ESTADO_REQUERIDO =
  "Resultado de Verificar e Informar: seleccione una opción.";

export const MSG_VERIFICAR_LEGACY_INCONSISTENTE =
  "Resultado de Verificar e Informar: la actuación contiene un estado anterior inconsistente. Seleccione nuevamente el resultado correcto.";

export const MSG_VERIFICAR_SI_A_CONTRA_CON_ACTAS =
  "Para registrar una contraproducencia, primero debe quitar las actas labradas de la nueva inspección.";

export const VERIFICAR_ESTADO_OPTS: { value: string; label: string }[] = [
  { value: "", label: "—" },
  { value: "CONTRAPRODUCENCIA", label: "Contraproducencia" },
  { value: "NO_INSPECCION", label: "No realizó nueva inspección" },
  { value: "SI_INSPECCION", label: "Sí realizó nueva inspección" },
];

export function isPersistedVerificarOperationalInconsistent(row: {
  contraproducencia?: string | null;
  realizo_nueva_inspeccion?: boolean | null;
}): boolean {
  const contra = (row.contraproducencia ?? "").trim();
  const realizo = row.realizo_nueva_inspeccion;
  return Boolean(contra) && realizo !== null && realizo !== undefined;
}

/**
 * Reconstruye el estado operativo Verificar desde datos persistidos.
 */
export function resolveVerificarEstadoFromPersisted(row: {
  contraproducencia?: string | null;
  realizo_nueva_inspeccion?: boolean | null;
}): VerificarEstadoResuelto {
  if (isPersistedVerificarOperationalInconsistent(row)) {
    return "INCONSISTENTE";
  }
  const contra = (row.contraproducencia ?? "").trim();
  if (contra) return "CONTRAPRODUCENCIA";
  if (row.realizo_nueva_inspeccion === true) return "SI_INSPECCION";
  if (row.realizo_nueva_inspeccion === false) return "NO_INSPECCION";
  return "";
}

/**
 * Deriva campos UI legacy (realizo/contra) desde el estado operativo canónico.
 */
export function deriveVerificarUiFromEstado(
  estado: VerificarEstadoOperativo,
  contraproducencia = ""
): {
  verificarEstadoOperativo: VerificarEstadoOperativo;
  contraproducencia: string;
  realizoNuevaInspeccion: "" | "si" | "no";
} {
  switch (estado) {
    case "CONTRAPRODUCENCIA":
      return {
        verificarEstadoOperativo: estado,
        contraproducencia,
        realizoNuevaInspeccion: "",
      };
    case "NO_INSPECCION":
      return {
        verificarEstadoOperativo: estado,
        contraproducencia: "",
        realizoNuevaInspeccion: "no",
      };
    case "SI_INSPECCION":
      return {
        verificarEstadoOperativo: estado,
        contraproducencia: "",
        realizoNuevaInspeccion: "si",
      };
    default:
      return {
        verificarEstadoOperativo: "",
        contraproducencia: "",
        realizoNuevaInspeccion: "",
      };
  }
}

/**
 * Payload POST corregir-cierre-oficio para Verificar (nunca híbrido).
 */
export function verificarEstadoToPayload(params: {
  tipoActuacion: string;
  verificarEstado: VerificarEstadoOperativo;
  contraproducencia: string;
}): {
  tipo_actuacion: string;
  resultado_cumplimiento_oficio: null;
  contraproducencia: string | null;
  realizo_nueva_inspeccion: boolean | null;
} {
  const base = {
    tipo_actuacion: params.tipoActuacion,
    resultado_cumplimiento_oficio: null as null,
  };
  switch (params.verificarEstado) {
    case "CONTRAPRODUCENCIA":
      return {
        ...base,
        realizo_nueva_inspeccion: null,
        contraproducencia: params.contraproducencia.trim() || null,
      };
    case "NO_INSPECCION":
      return {
        ...base,
        realizo_nueva_inspeccion: false,
        contraproducencia: null,
      };
    case "SI_INSPECCION":
      return {
        ...base,
        realizo_nueva_inspeccion: true,
        contraproducencia: null,
      };
    default:
      return {
        ...base,
        realizo_nueva_inspeccion: null,
        contraproducencia: null,
      };
  }
}
