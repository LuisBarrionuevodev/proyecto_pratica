import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import type { IComprobacionDocumentalResponse } from "../../../api/actuacionesPendientesApi";

/** True si hay acta de comprobación cargada (misma regla que `ActasVisitaLectura`). */
export function actuacionTieneComprobacionActa(draft: IActuacionListItem): boolean {
  const nComp = draft.acta_comprobacion_num;
  const mComp = draft.comprobacion_motivo != null ? String(draft.comprobacion_motivo).trim() : "";
  return (nComp != null && String(nComp).trim() !== "") || mComp !== "";
}

/** True si hay acta de notificación (misma regla que `ActasVisitaLectura`). */
export function actuacionTieneNotificacionActa(draft: IActuacionListItem): boolean {
  const nNot = draft.acta_notificacion_num;
  const motivos = [draft.notificacion_motivo_1, draft.notificacion_motivo_2, draft.notificacion_motivo_3]
    .map((x) => (x != null ? String(x).trim() : ""))
    .filter(Boolean);
  return (nNot != null && String(nNot).trim() !== "") || motivos.length > 0;
}

export type ActasComprobacionPuenteTarget = {
  href: string;
  /** Texto del botón principal. */
  label: string;
};

/**
 * Construye la ruta hacia Actas de comprobación según el snapshot documental (GET existente).
 * No llama al backend; solo interpreta `doc` ya cargado en el cliente.
 */
export function buildActasComprobacionPuente(
  actuacionId: number,
  doc: IComprobacionDocumentalResponse | null,
  docLoadFailed: boolean
): ActasComprobacionPuenteTarget {
  if (docLoadFailed || !doc) {
    return {
      href: `/actasComprobacion?tab=expediente&actuacionId=${actuacionId}`,
      label: "Ir a Actas de comprobación",
    };
  }
  if (!doc.expediente_envio) {
    return {
      href: `/actasComprobacion?tab=expediente&actuacionId=${actuacionId}`,
      label: "Cargar expediente de envío…",
    };
  }
  if (!doc.oficio || !doc.expediente_respuesta) {
    return {
      href: `/actasComprobacion?tab=oficio&actuacionId=${actuacionId}`,
      label: "Registrar oficio y expediente de respuesta…",
    };
  }
  return {
    href: `/actasComprobacion?tab=recorrido`,
    label: "Abrir Actas de comprobación (recorrido)",
  };
}

/**
 * Ruta hacia Gestión de notificación con foco por actuación.
 * La página destino elige pestaña de plazo y modal según la fila encontrada.
 */
export function buildGestionNotificacionPuenteHref(actuacionId: number): string {
  return `/gestionNotificacion?actuacionId=${actuacionId}`;
}
