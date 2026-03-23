import { useEffect, useMemo } from "react";
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import { Box } from "@mui/material";

import type { RutaMapaMarker, RutaMapaPolyline } from "../types/rutasTrabajoMapa.types";

/** Misma URL y atribución que `Mapa/Components/MapView.tsx`. */
const OSM_ATTRIBUTION = "&copy; OpenStreetMap";
const OSM_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";

function createNumberedDivIcon(order: number, colorHex: string): L.DivIcon {
  return L.divIcon({
    className: "ruta-num-marker",
    html: `<div style="width:26px;height:26px;border-radius:50%;background:${colorHex};color:#fff;font-weight:700;font-size:11px;display:flex;align-items:center;justify-content:center;border:2px solid rgba(255,255,255,0.95);box-shadow:0 1px 4px rgba(0,0,0,0.35);">${order}</div>`,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
  });
}

/**
 * Ajusta vista del mapa a markers y polilíneas cuando hay datos.
 */
function FitMapToData({
  markers,
  polylines,
}: {
  markers: RutaMapaMarker[];
  polylines: RutaMapaPolyline[];
}) {
  const map = useMap();
  useEffect(() => {
    const pts: L.LatLngExpression[] = [];
    markers.forEach((m) => pts.push([m.lat, m.lng]));
    polylines.forEach((p) => p.positions.forEach((pos) => pts.push(pos)));
    if (pts.length === 0) return;
    if (pts.length === 1) {
      map.setView(pts[0] as [number, number], 15);
      return;
    }
    const b = L.latLngBounds(pts);
    map.fitBounds(b, { padding: [32, 32], maxZoom: 16 });
  }, [map, markers, polylines]);
  return null;
}

export type MapaRutaTrabajoProps = {
  center: [number, number];
  zoom: number;
  markers: RutaMapaMarker[];
  polylines: RutaMapaPolyline[];
  /** Altura del contenedor del mapa (Leaflet requiere altura definida). */
  mapHeight?: string | number;
};

/**
 * Mapa Leaflet + OSM para una ruta: tiles estándar del proyecto, markers numerados por orden de ítem y polilíneas por grupo.
 * Sin coordenadas en datos, solo muestra el área de referencia.
 */
export function MapaRutaTrabajo({ center, zoom, markers, polylines, mapHeight = "min(58vh, 560px)" }: MapaRutaTrabajoProps) {
  const key = useMemo(() => `${center[0]}-${center[1]}-${zoom}`, [center, zoom]);

  return (
    <Box
      sx={{
        borderRadius: 2,
        overflow: "hidden",
        border: (theme) => `1px solid ${theme.palette.divider}`,
        height: mapHeight,
        minHeight: 320,
        position: "relative",
        "& .leaflet-container": {
          fontFamily: '"Tactic Sans", sans-serif',
          background: "#1a1d22",
        },
      }}
    >
      <MapContainer key={key} center={center} zoom={zoom} style={{ height: "100%", width: "100%" }} scrollWheelZoom>
        <TileLayer attribution={OSM_ATTRIBUTION} url={OSM_URL} />
        <FitMapToData markers={markers} polylines={polylines} />
        {polylines.map((pl) => (
          <Polyline
            key={`pl-${pl.grupoId}`}
            positions={pl.positions}
            pathOptions={{
              color: pl.color,
              weight: 4,
              opacity: 0.85,
              dashArray: "10 8",
            }}
          />
        ))}
        {markers.map((m) => (
          <Marker key={`mk-${m.itemId}`} position={[m.lat, m.lng]} icon={createNumberedDivIcon(m.orden, m.color)}>
            <Popup>
              <div style={{ minWidth: 180 }}>
                <strong>#{m.orden}</strong>
                <div style={{ marginTop: 4, fontSize: 13 }}>{m.etiqueta}</div>
                {m.rubroNombre ? (
                  <div style={{ marginTop: 6, fontSize: 12, opacity: 0.9 }}>Rubro: {m.rubroNombre}</div>
                ) : null}
                {m.distritoNombre ? (
                  <div style={{ fontSize: 12, opacity: 0.9 }}>Distrito: {m.distritoNombre}</div>
                ) : null}
                {m.ordenTrabajoLabel ? (
                  <div style={{ fontSize: 12, opacity: 0.9 }}>{m.ordenTrabajoLabel}</div>
                ) : null}
                {m.geoStatus ? (
                  <div style={{ marginTop: 4, fontSize: 11, opacity: 0.75 }}>Geo: {m.geoStatus}</div>
                ) : null}
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </Box>
  );
}
