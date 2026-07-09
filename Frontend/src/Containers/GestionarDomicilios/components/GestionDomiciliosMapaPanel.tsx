import { useEffect } from "react";
import { Box } from "@mui/material";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import type { GestionDomiciliosMapPoint } from "../../../api/gestionDomiciliosApi";

export const GESTION_MAP_DEFAULT_CENTER: [number, number] = [-26.8241, -65.2226];

const pointIcon = L.divIcon({
  className: "",
  html: `<div style="width:14px;height:14px;background:#1976d2;border-radius:50%;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.35);"></div>`,
  iconSize: [14, 14],
  iconAnchor: [7, 7],
});

const selectedIcon = L.divIcon({
  className: "",
  html: `<div style="width:18px;height:18px;background:#FF9800;border-radius:50%;border:2px solid white;box-shadow:0 3px 8px rgba(0,0,0,0.4);"></div>`,
  iconSize: [18, 18],
  iconAnchor: [9, 9],
});

function MapViewport({
  points,
  selectedId,
  focusCenter,
}: {
  points: GestionDomiciliosMapPoint[];
  selectedId: number | null;
  focusCenter: [number, number] | null;
}) {
  const map = useMap();

  useEffect(() => {
    if (focusCenter) {
      map.setView(focusCenter, 15);
      return;
    }
    if (points.length === 0) {
      map.setView(GESTION_MAP_DEFAULT_CENTER, 13);
      return;
    }
    if (points.length === 1) {
      map.setView([points[0].lat, points[0].lng], 15);
      return;
    }
    const bounds = L.latLngBounds(points.map((p) => [p.lat, p.lng] as [number, number]));
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });
  }, [focusCenter, map, points]);

  return null;
}

type Props = {
  mapPoints: GestionDomiciliosMapPoint[];
  selectedId: number | null;
  focusCenter: [number, number] | null;
  onSelectPoint: (point: GestionDomiciliosMapPoint) => void;
  height?: string | number;
};

/** Mapa operativo PR6C.6 desde ``map_points`` del endpoint nuevo. */
export function GestionDomiciliosMapaPanel({
  mapPoints,
  selectedId,
  focusCenter,
  onSelectPoint,
  height = "100%",
}: Props) {
  return (
    <Box sx={{ borderRadius: 2, overflow: "hidden", height, minHeight: 320 }}>
      <MapContainer
        center={GESTION_MAP_DEFAULT_CENTER}
        zoom={13}
        style={{ height: "100%", width: "100%", minHeight: 320 }}
      >
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <MapViewport points={mapPoints} selectedId={selectedId} focusCenter={focusCenter} />
        {mapPoints.map((point) => (
          <Marker
            key={point.domicilio_id}
            position={[point.lat, point.lng]}
            icon={point.domicilio_id === selectedId ? selectedIcon : pointIcon}
            eventHandlers={{
              click: () => onSelectPoint(point),
            }}
          >
            <Popup>
              #{point.domicilio_id} — {point.label}
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </Box>
  );
}
