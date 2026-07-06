import { useEffect } from "react";
import { Box } from "@mui/material";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import type { DomicilioPendienteItem } from "../types";

const defaultCenter: [number, number] = [-26.8241, -65.2226];

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

function FitBounds({ items }: { items: DomicilioPendienteItem[] }) {
  const map = useMap();
  const withCoords = items.filter((i) => i.lat != null && i.lng != null);

  useEffect(() => {
    if (withCoords.length === 0) {
      map.setView(defaultCenter, 13);
      return;
    }
    if (withCoords.length === 1) {
      map.setView([withCoords[0].lat!, withCoords[0].lng!], 15);
      return;
    }
    const bounds = L.latLngBounds(withCoords.map((i) => [i.lat!, i.lng!] as [number, number]));
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });
  }, [map, withCoords]);

  return null;
}

type Props = {
  items: DomicilioPendienteItem[];
  selectedId: number | null;
  onSelect: (item: DomicilioPendienteItem) => void;
  height?: string | number;
};

/** Mapa operativo con puntos problemáticos (PR6B). */
export function DomicilioOperativoMap({
  items,
  selectedId,
  onSelect,
  height = "min(62vh, 520px)",
}: Props) {
  const mappable = items.filter((i) => i.lat != null && i.lng != null);

  return (
    <Box sx={{ borderRadius: 2, overflow: "hidden", flex: 1, minHeight: 280 }}>
      <MapContainer center={defaultCenter} zoom={13} style={{ height, width: "100%" }}>
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitBounds items={mappable} />
        {mappable.map((item) => (
          <Marker
            key={item.domicilio_id}
            position={[item.lat!, item.lng!]}
            icon={item.domicilio_id === selectedId ? selectedIcon : pointIcon}
            eventHandlers={{
              click: () => onSelect(item),
            }}
          >
            <Popup>
              #{item.domicilio_id} — {item.calle_normalizada ?? item.calle_raw ?? "—"}
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </Box>
  );
}
