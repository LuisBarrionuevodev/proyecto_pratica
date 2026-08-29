import type { IRutaIniciadorPendienteRow } from "../../../../api/rutasTrabajoApi";

import {
  buildEstablecimientoSecundario,
  establecimientoDiscriminadoresDesdeRow,
  lineaPrincipalPendiente,
  prioridadCategoriaRow,
  rubroLineaPendiente,
  tipoIniciadorEtiquetaOperativa,
  type PrioridadCat,
} from "./iniciadorDisplay";

/** Props comparables para memo de `PendientePlanifMarker` (sin callbacks). */
export type PendienteMarkerCompareProps = {
  iniciadorId: number;
  lat: number;
  lng: number;
  priority: PrioridadCat;
  /** Campos del row usados en popup/click (evita stale si cambia el contenido). */
  rowSignature: string;
  isFocus: boolean;
  showPopup: boolean;
  popupOpenNonce: number;
  inPool: boolean;
  agregando: boolean;
};

/**
 * Firma estable de datos operativos del row mostrados en popup o entregados al click.
 */
export function pendienteMarkerRowSignature(row: IRutaIniciadorPendienteRow): string {
  const estab = buildEstablecimientoSecundario(establecimientoDiscriminadoresDesdeRow(row));
  return [
    row.id,
    lineaPrincipalPendiente(row),
    rubroLineaPendiente(row),
    tipoIniciadorEtiquetaOperativa(row) ?? "",
    estab ?? "",
  ].join("\u0001");
}

export function pendienteMarkerComparePropsFromRow(
  row: IRutaIniciadorPendienteRow,
  lat: number,
  lng: number,
  partial: Omit<PendienteMarkerCompareProps, "iniciadorId" | "lat" | "lng" | "priority" | "rowSignature">
): PendienteMarkerCompareProps {
  return {
    iniciadorId: row.id,
    lat,
    lng,
    priority: prioridadCategoriaRow(row),
    rowSignature: pendienteMarkerRowSignature(row),
    ...partial,
  };
}

/**
 * Comparador puro para React.memo: true → props equivalentes → omitir rerender.
 */
export function arePendienteMarkerPropsEqual(
  prev: PendienteMarkerCompareProps,
  next: PendienteMarkerCompareProps
): boolean {
  return (
    prev.iniciadorId === next.iniciadorId &&
    prev.lat === next.lat &&
    prev.lng === next.lng &&
    prev.priority === next.priority &&
    prev.rowSignature === next.rowSignature &&
    prev.isFocus === next.isFocus &&
    prev.showPopup === next.showPopup &&
    prev.popupOpenNonce === next.popupOpenNonce &&
    prev.inPool === next.inPool &&
    prev.agregando === next.agregando
  );
}
