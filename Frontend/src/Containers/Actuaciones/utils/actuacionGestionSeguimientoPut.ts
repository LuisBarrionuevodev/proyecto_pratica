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

/** Omite campos de seguimiento no permitidos por `ui_policy` antes del PUT. */
export function stripGestionSeguimientoDisallowedFromPut(
  row: IActuacionListItem
): IActuacionListItem {
  const copy: Record<string, unknown> = { ...row };
  delete copy.ui_policy;
  delete copy.seguimiento;

  const policy = resolveActuacionGestionUiPolicy(row);
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
  copy.telefono_contacto_solicitud_carnet = null;
  return copy as unknown as IActuacionListItem;
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
  return out;
}
