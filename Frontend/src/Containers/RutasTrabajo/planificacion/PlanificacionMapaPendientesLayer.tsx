import { memo, useCallback, useEffect, useMemo, useRef } from "react";
import { Marker, Popup, useMap } from "react-leaflet";
import type { Marker as LeafletMarker } from "leaflet";

import type { IRutaIniciadorPendienteRow } from "../../../api/rutasTrabajoApi";
import { PlanificacionMapaGeopuntoOperativaCard } from "./components/PlanificacionMapaGeopuntoOperativaCard";
import { parseIniciadorLatLng } from "./utils/iniciadorCoords";
import { prioridadCategoriaRow, type PrioridadCat } from "./utils/iniciadorDisplay";
import { planificacionPendientePinIcon } from "./utils/planificacionMapaPins";
import {
  arePendienteMarkerPropsEqual,
  pendienteMarkerRowSignature,
  type PendienteMarkerCompareProps,
} from "./utils/planificacionPendienteMarkerCompare";

function MapFlyTo({ target }: { target: IRutaIniciadorPendienteRow | null }) {
  const map = useMap();
  useEffect(() => {
    if (!target) return;
    const ll = parseIniciadorLatLng(target);
    if (!ll) return;
    map.flyTo([ll.lat, ll.lng], 16, { duration: 0.45 });
  }, [target, map]);
  return null;
}

type PendienteMarkerProps = {
  row: IRutaIniciadorPendienteRow;
  lat: number;
  lng: number;
  priority: PrioridadCat;
  rowSignature: string;
  isFocus: boolean;
  showPopup: boolean;
  popupOpenNonce: number;
  inPool: boolean;
  agregando: boolean;
  onMarkerClick: (row: IRutaIniciadorPendienteRow) => void;
  onPopupClose: () => void;
  onAgregar: (row: IRutaIniciadorPendienteRow) => void;
};

function pendienteMarkerPropsToCompare(props: PendienteMarkerProps): PendienteMarkerCompareProps {
  return {
    iniciadorId: props.row.id,
    lat: props.lat,
    lng: props.lng,
    priority: props.priority,
    rowSignature: props.rowSignature,
    isFocus: props.isFocus,
    showPopup: props.showPopup,
    popupOpenNonce: props.popupOpenNonce,
    inPool: props.inPool,
    agregando: props.agregando,
  };
}

function pendientePlanifMarkerAreEqual(prev: PendienteMarkerProps, next: PendienteMarkerProps): boolean {
  if (
    prev.onMarkerClick !== next.onMarkerClick ||
    prev.onPopupClose !== next.onPopupClose ||
    prev.onAgregar !== next.onAgregar
  ) {
    return false;
  }
  return arePendienteMarkerPropsEqual(
    pendienteMarkerPropsToCompare(prev),
    pendienteMarkerPropsToCompare(next)
  );
}

/**
 * Un marcador + popup controlado: abre el popup al primer toque o al foco desde la lista (flyTo + estado).
 */
const PendientePlanifMarker = memo(function PendientePlanifMarker({
  row,
  lat,
  lng,
  priority,
  isFocus,
  showPopup,
  popupOpenNonce,
  inPool,
  agregando,
  onMarkerClick,
  onPopupClose,
  onAgregar,
}: PendienteMarkerProps) {
  const markerRef = useRef<LeafletMarker | null>(null);
  const rowRef = useRef(row);
  rowRef.current = row;

  const onMarkerClickRef = useRef(onMarkerClick);
  onMarkerClickRef.current = onMarkerClick;

  const onAgregarRef = useRef(onAgregar);
  onAgregarRef.current = onAgregar;

  useEffect(() => {
    if (!showPopup) return;
    const m = markerRef.current;
    if (!m) return;
    const id = window.requestAnimationFrame(() => {
      m.openPopup();
    });
    return () => window.cancelAnimationFrame(id);
  }, [showPopup, row.id, popupOpenNonce]);

  const markerClickHandlers = useMemo(
    () => ({
      click: () => onMarkerClickRef.current(rowRef.current),
    }),
    []
  );

  const popupCloseHandlers = useMemo(
    () => ({
      remove: onPopupClose,
    }),
    [onPopupClose]
  );

  const handleAgregarAlPool = useCallback(() => {
    onAgregarRef.current(rowRef.current);
  }, []);

  const icon = planificacionPendientePinIcon(priority, isFocus);

  return (
    <Marker
      ref={markerRef}
      position={[lat, lng]}
      icon={icon}
      zIndexOffset={isFocus ? 800 : 0}
      eventHandlers={markerClickHandlers}
    >
      {showPopup ? (
        <Popup
          key={`${row.id}-${popupOpenNonce}`}
          eventHandlers={popupCloseHandlers}
          maxWidth={248}
          minWidth={220}
          autoPan
          autoPanPadding={[10, 10]}
          keepInView
        >
          <PlanificacionMapaGeopuntoOperativaCard
            row={row}
            yaEnPool={inPool}
            agregando={agregando}
            onAgregarAlPool={handleAgregarAlPool}
          />
        </Popup>
      ) : null}
    </Marker>
  );
}, pendientePlanifMarkerAreEqual);

export type PlanificacionMapaPendientesLayerProps = {
  rows: IRutaIniciadorPendienteRow[];
  /** Solo con distrito elegido en el mapa. */
  visible: boolean;
  focusIniciadorId: number | null;
  popupRow: IRutaIniciadorPendienteRow | null;
  flyToRow: IRutaIniciadorPendienteRow | null;
  /** Se incrementa al abrir el popup desde la lista para forzar remount estable del Popup de Leaflet. */
  popupOpenNonce?: number;
  /** Ids ya presentes en el pool del día (botón deshabilitado + leyenda breve). */
  poolIniciadorIds?: number[];
  agregandoIniciadorIds?: ReadonlySet<number>;
  onMarkerClick: (row: IRutaIniciadorPendienteRow) => void;
  onPopupClose: () => void;
  onAgregar: (row: IRutaIniciadorPendienteRow) => void;
};

/**
 * Marca pendientes con geocodificación cuando hay distrito activo; card operativa al tocar el geopunto.
 */
export function PlanificacionMapaPendientesLayer({
  rows,
  visible,
  focusIniciadorId,
  popupRow,
  flyToRow,
  popupOpenNonce = 0,
  poolIniciadorIds = [],
  agregandoIniciadorIds,
  onMarkerClick,
  onPopupClose,
  onAgregar,
}: PlanificacionMapaPendientesLayerProps) {
  const puntos = useMemo(() => rows.filter((r) => parseIniciadorLatLng(r) != null), [rows]);
  const poolSet = useMemo(() => new Set(poolIniciadorIds), [poolIniciadorIds]);
  const agregandoSet = agregandoIniciadorIds ?? new Set<number>();

  if (!visible) return null;

  return (
    <>
      <MapFlyTo target={flyToRow} />
      {puntos.map((row) => {
        const ll = parseIniciadorLatLng(row);
        if (!ll) return null;
        const isFocus = focusIniciadorId === row.id;
        const showPopup = popupRow?.id === row.id;
        const inPool = poolSet.has(row.id);
        return (
          <PendientePlanifMarker
            key={row.id}
            row={row}
            lat={ll.lat}
            lng={ll.lng}
            priority={prioridadCategoriaRow(row)}
            rowSignature={pendienteMarkerRowSignature(row)}
            isFocus={isFocus}
            showPopup={showPopup}
            popupOpenNonce={popupOpenNonce}
            inPool={inPool}
            agregando={agregandoSet.has(row.id)}
            onMarkerClick={onMarkerClick}
            onPopupClose={onPopupClose}
            onAgregar={onAgregar}
          />
        );
      })}
    </>
  );
}
