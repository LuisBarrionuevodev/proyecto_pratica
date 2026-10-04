import type {
  IActuacionGestionUiPolicy,
  IActuacionListItem,
} from "../../../api/actuacionesListApi";
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

/**
 * Campos de seguimiento para el body del PUT (tras sanitizar la fila).
 * Usa `ui_policy` capturada antes de `sanitizeActuacionRowForCanalActasPut`.
 */
export function buildGestionSeguimientoPutFields(
  row: IActuacionListItem,
  policy: IActuacionGestionUiPolicy | null | undefined
): Pick<
  IActuacionListItem,
  | "solicita_carnet_manipulador"
  | "telefono_contacto_solicitud_carnet"
  | "faltas_notificacion_subsanadas"
> {
  const out: Pick<
    IActuacionListItem,
    | "solicita_carnet_manipulador"
    | "telefono_contacto_solicitud_carnet"
    | "faltas_notificacion_subsanadas"
  > = {};
  if (!policy?.puede_editar_seguimiento) {
    return out;
  }
  const merged = mergeActuacionSeguimientoFromApiRow(row);

  if (policy.mostrar_solicitud_carnet_manipulador) {
    const sol = merged.solicita_carnet_manipulador;
    if (sol === true || sol === false) {
      out.solicita_carnet_manipulador = sol;
      out.telefono_contacto_solicitud_carnet = sol
        ? (merged.telefono_contacto_solicitud_carnet ?? "").trim() || null
        : null;
    }
  }

  if (policy.mostrar_subsanacion_notificacion) {
    const subs = merged.faltas_notificacion_subsanadas;
    if (subs === true || subs === false) {
      out.faltas_notificacion_subsanadas = subs;
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
  return mergeActuacionSeguimientoFromApiRow(detail);
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
  copy.telefono_contacto_solicitud_carnet = null;
  return copy as unknown as IActuacionListItem;
}

/** Validación cliente de seguimiento antes del PUT de Gestión. */
export function validateGestionSeguimientoFields(
  row: IActuacionListItem
): Record<string, string> {
  const policy = resolveActuacionGestionUiPolicy(row);
  if (!policy?.puede_editar_seguimiento) {
    return {};
  }
  const merged = mergeActuacionSeguimientoFromApiRow(row);
  const errors: Record<string, string> = {};

  if (policy.mostrar_solicitud_carnet_manipulador) {
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

  if (policy.mostrar_subsanacion_notificacion) {
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
