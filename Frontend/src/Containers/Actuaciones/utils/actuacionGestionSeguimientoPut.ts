import type {
  IActuacionGestionUiPolicy,
  IActuacionListItem,
} from "../../../api/actuacionesListApi";
import { mergeActuacionIdentidadFromApiRow } from "./contribuyenteCrudOptions";
import {
  faltasSubsanadasUiToBool,
  solicitaCarnetUiToBool,
  type FaltasSubsanadasUiValue,
  type SolicitaCarnetUiValue,
} from "../../CompletarTrabajos/utils/actaSeguimientoUi";

export function resolveActuacionGestionUiPolicy(
  row: IActuacionListItem
): IActuacionGestionUiPolicy | null {
  return row.ui_policy ?? null;
}

export const GESTION_SEGUIMIENTO_PUT_KEYS = [
  "solicita_carnet_manipulador",
  "telefono_contacto_solicitud_carnet",
  "faltas_notificacion_subsanadas",
] as const;

export type GestionSeguimientoPutFields = Pick<
  IActuacionListItem,
  | "solicita_carnet_manipulador"
  | "telefono_contacto_solicitud_carnet"
  | "faltas_notificacion_subsanadas"
>;

function normalizeSeguimientoBool(value: unknown): boolean | null {
  return value === true ? true : value === false ? false : null;
}

function normalizeSeguimientoTelefono(value: unknown): string | null {
  const trimmed = String(value ?? "").trim();
  return trimmed || null;
}

function seguimientoCarnetSnapshot(row: IActuacionListItem): {
  solicita: boolean | null;
  telefono: string | null;
} {
  const merged = mergeActuacionSeguimientoFromApiRow(row);
  const solicita = normalizeSeguimientoBool(merged.solicita_carnet_manipulador);
  return {
    solicita,
    telefono: solicita === true ? normalizeSeguimientoTelefono(merged.telefono_contacto_solicitud_carnet) : null,
  };
}

function seguimientoSubsanacionSnapshot(row: IActuacionListItem): boolean | null {
  const merged = mergeActuacionSeguimientoFromApiRow(row);
  return normalizeSeguimientoBool(merged.faltas_notificacion_subsanadas);
}

/** Quita siempre del body residual los tres campos de Seguimiento. */
export function stripGestionSeguimientoResidualFromPut(row: IActuacionListItem): IActuacionListItem {
  const copy: Record<string, unknown> = { ...row };
  for (const key of GESTION_SEGUIMIENTO_PUT_KEYS) {
    delete copy[key];
  }
  return copy as unknown as IActuacionListItem;
}

/**
 * Campos de seguimiento para el body del PUT (tras sanitizar la fila).
 * Solo reinserta lo que cambió semánticamente respecto de la baseline de edición.
 */
export function buildGestionSeguimientoPutFields(
  row: IActuacionListItem,
  policy: IActuacionGestionUiPolicy | null | undefined,
  baseline?: IActuacionListItem | null
): GestionSeguimientoPutFields {
  const out: GestionSeguimientoPutFields = {};
  if (!policy?.puede_editar_seguimiento || !baseline) {
    return out;
  }

  if (policy.mostrar_solicitud_carnet_manipulador) {
    const current = seguimientoCarnetSnapshot(row);
    const original = seguimientoCarnetSnapshot(baseline);
    if (current.solicita !== original.solicita || current.telefono !== original.telefono) {
      if (current.solicita === true || current.solicita === false) {
        out.solicita_carnet_manipulador = current.solicita;
        out.telefono_contacto_solicitud_carnet = current.solicita ? current.telefono : null;
      }
    }
  }

  if (policy.mostrar_subsanacion_notificacion) {
    const current = seguimientoSubsanacionSnapshot(row);
    const original = seguimientoSubsanacionSnapshot(baseline);
    if (current !== original && (current === true || current === false)) {
      out.faltas_notificacion_subsanadas = current;
    }
  }

  return out;
}

/** Omite campos de seguimiento no permitidos por `ui_policy` antes del PUT. */
export function stripGestionSeguimientoDisallowedFromPut(
  row: IActuacionListItem,
  policyOverride?: IActuacionGestionUiPolicy | null
): IActuacionListItem {
  const copy: Record<string, unknown> = { ...row };
  delete copy.ui_policy;
  delete copy.seguimiento;

  const policy = policyOverride ?? resolveActuacionGestionUiPolicy(row);
  if (!policy?.mostrar_solicitud_carnet_manipulador) {
    delete copy.solicita_carnet_manipulador;
    delete copy.telefono_contacto_solicitud_carnet;
  }
  if (!policy?.mostrar_subsanacion_notificacion) {
    delete copy.faltas_notificacion_subsanadas;
  }
  return copy as unknown as IActuacionListItem;
}

export function mergeActuacionSeguimientoFromApiRow(
  row: IActuacionListItem
): IActuacionListItem {
  const seg = row.seguimiento;
  if (!seg) return row;
  return {
    ...row,
    solicita_carnet_manipulador:
      seg.solicita_carnet_manipulador ?? row.solicita_carnet_manipulador,
    telefono_contacto_solicitud_carnet:
      seg.telefono_contacto_solicitud_carnet ?? row.telefono_contacto_solicitud_carnet,
    faltas_notificacion_subsanadas:
      seg.faltas_notificacion_subsanadas ?? row.faltas_notificacion_subsanadas,
  };
}

/** Fila lista para el modal tras GET `/gestion` (domicilio editable + seguimiento en draft). */
export function prepareActuacionGestionModalRow(
  detail: IActuacionListItem
): IActuacionListItem {
  return mergeActuacionIdentidadFromApiRow(mergeActuacionSeguimientoFromApiRow(detail));
}

/** Quita datos sensibles/de detalle antes de fusionar en la grilla. */
export function stripActuacionRowForListStorage(
  row: IActuacionListItem
): IActuacionListItem {
  const copy: Record<string, unknown> = { ...row };
  delete copy.ui_policy;
  delete copy.seguimiento;
  delete copy.domicilio;
  delete copy.rubro;
  delete copy.contribuyente;
  delete copy.observaciones_ejecucion;
  copy.telefono_contacto_solicitud_carnet = null;
  return copy as unknown as IActuacionListItem;
}

/** Validación cliente de seguimiento antes del PUT de Gestión. */
export function validateGestionSeguimientoFields(
  row: IActuacionListItem,
  baseline?: IActuacionListItem | null
): Record<string, string> {
  const policy = resolveActuacionGestionUiPolicy(row);
  if (!policy?.puede_editar_seguimiento) {
    return {};
  }
  if (baseline) {
    const pending = buildGestionSeguimientoPutFields(row, policy, baseline);
    if (Object.keys(pending).length === 0) {
      return {};
    }
    return validateGestionSeguimientoPutFields(row, policy, pending);
  }
  return validateGestionSeguimientoPutFields(
    row,
    policy,
    buildGestionSeguimientoPutFieldsForValidation(row, policy)
  );
}

function buildGestionSeguimientoPutFieldsForValidation(
  row: IActuacionListItem,
  policy: IActuacionGestionUiPolicy
): GestionSeguimientoPutFields {
  const out: GestionSeguimientoPutFields = {};
  const merged = mergeActuacionSeguimientoFromApiRow(row);
  if (policy.mostrar_solicitud_carnet_manipulador) {
    out.solicita_carnet_manipulador = merged.solicita_carnet_manipulador ?? undefined;
    out.telefono_contacto_solicitud_carnet = merged.telefono_contacto_solicitud_carnet ?? null;
  }
  if (policy.mostrar_subsanacion_notificacion) {
    out.faltas_notificacion_subsanadas = merged.faltas_notificacion_subsanadas ?? undefined;
  }
  return out;
}

function validateGestionSeguimientoPutFields(
  row: IActuacionListItem,
  policy: IActuacionGestionUiPolicy,
  pending: GestionSeguimientoPutFields
): Record<string, string> {
  const merged = mergeActuacionSeguimientoFromApiRow(row);
  const errors: Record<string, string> = {};
  const enviaCarnet =
    "solicita_carnet_manipulador" in pending || "telefono_contacto_solicitud_carnet" in pending;
  const enviaSubs = "faltas_notificacion_subsanadas" in pending;

  if (policy.mostrar_solicitud_carnet_manipulador && enviaCarnet) {
    const sol = merged.solicita_carnet_manipulador;
    if (sol !== true && sol !== false) {
      errors.solicita_carnet_manipulador = "Indique si solicita carnet de manipulador.";
    } else if (sol === true) {
      const tel = (merged.telefono_contacto_solicitud_carnet ?? "").trim();
      if (!tel) {
        errors.telefono_contacto_solicitud_carnet =
          "Ingrese el teléfono de contacto del solicitante.";
      }
    }
  }

  if (policy.mostrar_subsanacion_notificacion && enviaSubs) {
    const subs = merged.faltas_notificacion_subsanadas;
    if (subs !== true && subs !== false) {
      errors.faltas_notificacion_subsanadas =
        "Indique si se subsanaron las faltas de la notificación.";
    }
  }

  return errors;
}

export function gestionSeguimientoDraftFromRow(row: IActuacionListItem): {
  solicitaCarnet: SolicitaCarnetUiValue;
  telefonoCarnet: string;
  faltasSubsanadas: FaltasSubsanadasUiValue;
} {
  const merged = mergeActuacionSeguimientoFromApiRow(row);
  const sol = merged.solicita_carnet_manipulador;
  const subs = merged.faltas_notificacion_subsanadas;
  return {
    solicitaCarnet: sol === true ? "si" : sol === false ? "no" : "",
    telefonoCarnet: (merged.telefono_contacto_solicitud_carnet ?? "").trim(),
    faltasSubsanadas: subs === true ? "si" : subs === false ? "no" : "",
  };
}

export function applyGestionSeguimientoDraftToRow(
  row: IActuacionListItem,
  draft: {
    solicitaCarnet: SolicitaCarnetUiValue;
    telefonoCarnet: string;
    faltasSubsanadas: FaltasSubsanadasUiValue;
  }
): IActuacionListItem {
  const policy = resolveActuacionGestionUiPolicy(row);
  const out: IActuacionListItem = { ...row };
  if (policy?.mostrar_solicitud_carnet_manipulador) {
    const b = solicitaCarnetUiToBool(draft.solicitaCarnet);
    if (b !== undefined) {
      out.solicita_carnet_manipulador = b;
      if (b) {
        out.telefono_contacto_solicitud_carnet = draft.telefonoCarnet.trim() || null;
      } else {
        out.telefono_contacto_solicitud_carnet = null;
      }
    }
  }
  if (policy?.mostrar_subsanacion_notificacion) {
    const subs = faltasSubsanadasUiToBool(draft.faltasSubsanadas);
    if (subs !== undefined) {
      out.faltas_notificacion_subsanadas = subs;
    }
  }

  if (out.seguimiento) {
    const seg = { ...out.seguimiento };
    if (policy?.mostrar_solicitud_carnet_manipulador) {
      seg.solicita_carnet_manipulador = out.solicita_carnet_manipulador ?? null;
      seg.telefono_contacto_solicitud_carnet =
        out.telefono_contacto_solicitud_carnet ?? null;
    }
    if (policy?.mostrar_subsanacion_notificacion) {
      seg.faltas_notificacion_subsanadas = out.faltas_notificacion_subsanadas ?? null;
    }
    out.seguimiento = seg;
  }

  return out;
}
