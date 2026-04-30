import { useEffect, useMemo, useRef } from "react";
import { Marker, Popup, useMap } from "react-leaflet";
import type { Marker as LeafletMarker } from "leaflet";

import type { IRutaIniciadorPendienteRow } from "../../../api/rutasTrabajoApi";
import { PlanificacionMapaGeopuntoOperativaCard } from "./components/PlanificacionMapaGeopuntoOperativaCard";
import { parseIniciadorLatLng } from "./utils/iniciadorCoords";
import { prioridadCategoriaRow } from "./utils/iniciadorDisplay";
import { planificacionPendientePinIcon } from "./utils/planificacionMapaPins";

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
  isFocus: boolean;
  showPopup: boolean;
  popupOpenNonce: number;
  inPool: boolean;
  onMarkerClick: (row: IRutaIniciadorPendienteRow) => void;
  onPopupClose: () => void;
  onAgregar: (row: IRutaIniciadorPendienteRow) => void;
};

/**
 * Un marcador + popup controlado: abre el popup al primer toque o al foco desde la lista (flyTo + estado).
 */
function PendientePlanifMarker({
  row,
  lat,
  lng,
  isFocus,
  showPopup,
  popupOpenNonce,
  inPool,
  onMarkerClick,
  onPopupClose,
  onAgregar,
}: PendienteMarkerProps) {
  const markerRef = useRef<LeafletMarker | null>(null);

  useEffect(() => {
    if (!showPopup) return;
    const m = markerRef.current;
    if (!m) return;
    const id = window.requestAnimationFrame(() => {
      m.openPopup();
    });
    return () => window.cancelAnimationFrame(id);
  }, [showPopup, row.id, popupOpenNonce]);

  const icon = planificacionPendientePinIcon(prioridadCategoriaRow(row), isFocus);

  return (
    <Marker
      ref={markerRef}
      position={[lat, lng]}
      icon={icon}
      zIndexOffset={isFocus ? 800 : 0}
      eventHandlers={{
        click: () => onMarkerClick(row),
      }}
    >
      {showPopup ? (
        <Popup
          key={`${row.id}-${popupOpenNonce}`}
          eventHandlers={{
            remove: onPopupClose,
          }}
          maxWidth={248}
          minWidth={220}
          autoPan
          autoPanPadding={[10, 10]}
          keepInView
        >
          <PlanificacionMapaGeopuntoOperativaCard
            row={row}
            yaEnPool={inPool}
            onAgregarAlPool={() => onAgregar(row)}
          />
        </Popup>
      ) : null}
    </Marker>
  );
}

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
  onMarkerClick,
  onPopupClose,
  onAgregar,
}: PlanificacionMapaPendientesLayerProps) {
  const puntos = useMemo(() => rows.filter((r) => parseIniciadorLatLng(r) != null), [rows]);
  const poolSet = useMemo(() => new Set(poolIniciadorIds), [poolIniciadorIds]);

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
            isFocus={isFocus}
            showPopup={showPopup}
            popupOpenNonce={popupOpenNonce}
            inPool={inPool}
            onMarkerClick={onMarkerClick}
            onPopupClose={onPopupClose}
            onAgregar={onAgregar}
          />
        );
      })}
    </>
  );
}
