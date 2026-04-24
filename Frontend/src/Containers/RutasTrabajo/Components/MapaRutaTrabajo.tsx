import { useEffect, useMemo } from "react";
import { MapContainer, Marker, Polyline, Popup, TileLayer, Tooltip, useMap } from "react-leaflet";
import L from "leaflet";
import { Box } from "@mui/material";

import type { RutaMapaMarker, RutaMapaPolyline } from "../types/rutasTrabajoMapa.types";
import { MARKER_RING_BOXSHADOW } from "../utils/mapaRutaGrupoTrazado";

/** Misma URL y atribución que `Mapa/Components/MapView.tsx`. */
const OSM_ATTRIBUTION = "&copy; OpenStreetMap";
const OSM_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";

function createNumberedDivIcon(order: number, colorHex: string, grupoCodigo: string, styleIndex: number): L.DivIcon {
  const ring = MARKER_RING_BOXSHADOW[styleIndex % MARKER_RING_BOXSHADOW.length];
  const boxShadow = `${ring}, 0 2px 6px rgba(0,0,0,0.5)`;
  const html = `<div style="display:flex;flex-direction:column;align-items:center;">
<div style="width:26px;height:26px;border-radius:50%;background:${colorHex};color:#fff;font-weight:700;font-size:11px;display:flex;align-items:center;justify-content:center;border:2px solid #f5f5f5;box-shadow:${boxShadow};">${order}</div>
<div style="margin-top:2px;font-size:8px;font-weight:800;color:#f8f8f8;line-height:1;text-shadow:0 0 5px #000,0 0 5px #000;letter-spacing:0.06em;">${grupoCodigo}</div>
</div>`;
  return L.divIcon({
    className: "ruta-num-marker",
    html,
    iconSize: [30, 40],
    iconAnchor: [15, 38],
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
 * Mapa Leaflet + OSM: direcciones numeradas, código Gn por grupo en pin y en trazo, patrón/grosor de línea por grupo (legible en B/N).
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
        "& .ruta-grupo-line-tooltip.leaflet-tooltip": {
          background: "rgba(12, 14, 18, 0.94)",
          color: "#f0f0f0",
          border: "1px solid rgba(255,255,255,0.35)",
          borderRadius: "8px",
          padding: "3px 8px",
          fontSize: "10px",
          fontWeight: 600,
          boxShadow: "0 2px 8px rgba(0,0,0,0.45)",
          whiteSpace: "nowrap",
          maxWidth: 220,
          overflow: "hidden",
          textOverflow: "ellipsis",
        },
        "& .ruta-grupo-line-tooltip.leaflet-tooltip-top:before": {
          borderTopColor: "rgba(12, 14, 18, 0.94)",
        },
        "& .ruta-grupo-line-tooltip.leaflet-tooltip-bottom:before": {
          borderBottomColor: "rgba(12, 14, 18, 0.94)",
        },
      }}
    >
      <MapContainer key={key} center={center} zoom={zoom} style={{ height: "100%", width: "100%" }} scrollWheelZoom>
        {/* crossOrigin mejora chances de que los tiles entren en capturas canvas (html-to-image). */}
        <TileLayer attribution={OSM_ATTRIBUTION} url={OSM_URL} crossOrigin="anonymous" />
        <FitMapToData markers={markers} polylines={polylines} />
        {polylines.map((pl) => (
          <Polyline
            key={`pl-${pl.grupoId}`}
            positions={pl.positions}
            pathOptions={{
              color: pl.color,
              weight: pl.weight,
              opacity: 0.88,
              dashArray: pl.dashArray,
              lineCap: "round",
              lineJoin: "round",
            }}
          >
            <Tooltip permanent direction="center" opacity={1} className="ruta-grupo-line-tooltip">
              <span>
                <strong style={{ letterSpacing: "0.06em" }}>{pl.grupoCodigo}</strong>
                {pl.grupoNombreCorto ? (
                  <span style={{ fontWeight: 500, opacity: 0.9 }}>{` · ${pl.grupoNombreCorto}`}</span>
                ) : null}
              </span>
            </Tooltip>
          </Polyline>
        ))}
        {markers.map((m) => (
          <Marker
            key={`mk-${m.itemId}`}
            position={[m.lat, m.lng]}
            icon={createNumberedDivIcon(m.orden, m.color, m.grupoCodigo, m.grupoStyleIndex)}
          >
            <Popup>
              <div style={{ minWidth: 200, fontFamily: '"Tactic Sans", sans-serif', color: "#1a1d22" }}>
                <div
                  style={{
                    fontSize: 10,
                    fontWeight: 700,
                    letterSpacing: "0.06em",
                    textTransform: "uppercase",
                    color: "#5c6370",
                  }}
                >
                  Visita {m.orden}
                </div>
                <strong style={{ display: "block", marginTop: 4, fontSize: 13, fontWeight: 700, color: "#1a1d22" }}>{m.etiqueta}</strong>
                <div style={{ marginTop: 4, fontSize: 11, color: "#3d4450" }}>{m.nombreGrupo}</div>
                {m.rubroNombre ? (
                  <div style={{ marginTop: 6, fontSize: 12, color: "#3d4450" }}>Rubro: {m.rubroNombre}</div>
                ) : null}
                {m.distritoNombre ? (
                  <div style={{ fontSize: 12, color: "#3d4450" }}>Distrito: {m.distritoNombre}</div>
                ) : null}
                {m.tipoIniciadorLabel ? (
                  <div style={{ fontSize: 12, color: "#3d4450" }}>Tipo: {m.tipoIniciadorLabel}</div>
                ) : (
                  <div style={{ fontSize: 12, color: "#5c6370" }}>Tipo: —</div>
                )}
                {m.ordenTrabajoLabel ? (
                  <div style={{ fontSize: 12, color: "#3d4450" }}>{m.ordenTrabajoLabel}</div>
                ) : null}
                {m.geoStatusLabel ? (
                  <div style={{ marginTop: 4, fontSize: 11, color: "#5c6370" }}>Ubicación: {m.geoStatusLabel}</div>
                ) : null}
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </Box>
  );
}
