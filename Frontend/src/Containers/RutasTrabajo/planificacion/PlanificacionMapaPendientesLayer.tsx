import { useEffect, useMemo } from "react";
import { CircleMarker, Popup, useMap } from "react-leaflet";
import { Box } from "@mui/material";

import type { IRutaIniciadorPendienteRow } from "../../../api/rutasTrabajoApi";
import { PlanificacionIniciadorCompactCard } from "./components/PlanificacionIniciadorCompactCard";
import { parseIniciadorLatLng } from "./utils/iniciadorCoords";

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

export type PlanificacionMapaPendientesLayerProps = {
  rows: IRutaIniciadorPendienteRow[];
  /** Solo con distrito elegido en el mapa. */
  visible: boolean;
  focusIniciadorId: number | null;
  popupRow: IRutaIniciadorPendienteRow | null;
  flyToRow: IRutaIniciadorPendienteRow | null;
  onMarkerClick: (row: IRutaIniciadorPendienteRow) => void;
  onPopupClose: () => void;
  onAgregar: (row: IRutaIniciadorPendienteRow) => void;
};

/**
 * Marca pendientes con geocodificación cuando hay distrito activo; popup alineado a la card de lista.
 */
export function PlanificacionMapaPendientesLayer({
  rows,
  visible,
  focusIniciadorId,
  popupRow,
  flyToRow,
  onMarkerClick,
  onPopupClose,
  onAgregar,
}: PlanificacionMapaPendientesLayerProps) {
  const puntos = useMemo(() => rows.filter((r) => parseIniciadorLatLng(r) != null), [rows]);

  if (!visible) return null;

  return (
    <>
      <MapFlyTo target={flyToRow} />
      {puntos.map((row) => {
        const ll = parseIniciadorLatLng(row);
        if (!ll) return null;
        const isFocus = focusIniciadorId === row.id;
        const showPopup = popupRow?.id === row.id;
        return (
          <CircleMarker
            key={row.id}
            center={[ll.lat, ll.lng]}
            radius={isFocus ? 14 : 10}
            pathOptions={{
              color: isFocus ? "#ffffff" : "#7ecbff",
              weight: isFocus ? 3 : 2,
              fillColor: isFocus ? "#0166ff" : "rgba(0, 180, 255, 0.85)",
              fillOpacity: 1,
            }}
            eventHandlers={{
              click: () => onMarkerClick(row),
            }}
          >
            {showPopup ? (
              <Popup
                eventHandlers={{
                  remove: onPopupClose,
                }}
                maxWidth={340}
                minWidth={260}
              >
                <Box sx={{ m: -0.5 }}>
                  <PlanificacionIniciadorCompactCard
                    row={row}
                    agregarLabel="Agregar"
                    onAgregar={() => onAgregar(row)}
                    showVerEnMapaButton={false}
                  />
                </Box>
              </Popup>
            ) : null}
          </CircleMarker>
        );
      })}
    </>
  );
}
