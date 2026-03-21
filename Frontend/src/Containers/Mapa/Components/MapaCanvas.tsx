import { useEffect, useMemo } from "react";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import { Alert, Box, CircularProgress, Typography } from "@mui/material";

import type { MapPointFeature } from "../../../api/mapApi";
import { AppButton } from "../../../ui/AppButton";
import type { MapaOperativoModo } from "../hooks/useMapaOperativo";
import { mapaOperativoSurfaceSx } from "./mapaOperativoStyles";
import {
  alertBaseStyles,
  COLORS,
} from "../../CargarActuaciones/styles/cargarActuacionesStyles";

const DEFAULT_CENTER: [number, number] = [-26.82, -65.22];
const OSM_ATTRIBUTION = "&copy; OpenStreetMap contributors";
const OSM_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";

function createModoIcon(modo: MapaOperativoModo): L.DivIcon {
  const fill = COLORS.primary;
  if (modo === "pendientes") {
    return L.divIcon({
      className: "mapa-op-pend",
      html: `<div style="width:22px;height:22px;border-radius:50%;background:${fill};border:2px solid ${COLORS.white};box-shadow:0 2px 8px rgba(0,0,0,0.4);display:flex;align-items:center;justify-content:center;color:${COLORS.white};font-weight:800;font-size:13px;">!</div>`,
      iconSize: [22, 22],
      iconAnchor: [11, 11],
    });
  }
  return L.divIcon({
    className: "mapa-op-real",
    html: `<div style="width:22px;height:22px;border-radius:50%;background:${fill};border:2px solid ${COLORS.white};box-shadow:0 2px 8px rgba(0,0,0,0.4);display:flex;align-items:center;justify-content:center;color:${COLORS.white};font-weight:800;font-size:12px;">✓</div>`,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  });
}

function FitBounds({ features }: { features: MapPointFeature[] }) {
  const map = useMap();
  useEffect(() => {
    const pts: [number, number][] = [];
    for (const f of features) {
      const c = f.geometry?.coordinates;
      if (c && typeof c[0] === "number" && typeof c[1] === "number") {
        pts.push([c[1], c[0]]);
      }
    }
    if (pts.length === 0) {
      map.setView(DEFAULT_CENTER, 12);
      return;
    }
    if (pts.length === 1) {
      map.setView(pts[0], 14);
      return;
    }
    map.fitBounds(L.latLngBounds(pts), { padding: [40, 40], maxZoom: 15 });
  }, [map, features]);
  return null;
}

export type MapaCanvasProps = {
  modo: MapaOperativoModo;
  features: MapPointFeature[];
  loading: boolean;
  mapExpanded: boolean;
  onToggleExpand: () => void;
};

/**
 * Mapa Leaflet principal dentro de caja canónica; botón expandir y marcadores según features.
 */
export function MapaCanvas({ modo, features, loading, mapExpanded, onToggleExpand }: MapaCanvasProps) {
  const icon = useMemo(() => createModoIcon(modo), [modo]);

  return (
    <Box
      sx={{
        ...mapaOperativoSurfaceSx,
        position: "relative",
        minHeight: mapExpanded ? { xs: "70vh", md: "calc(100vh - 220px)" } : 420,
        height: mapExpanded ? { xs: "70vh", md: "calc(100vh - 220px)" } : 480,
        overflow: "hidden",
        "& .leaflet-container": {
          fontFamily: '"Tactic Sans", sans-serif',
          background: COLORS.grayMedium,
        },
      }}
    >
      <Box
        sx={{
          position: "absolute",
          top: 12,
          right: 12,
          zIndex: 1000,
        }}
      >
        <AppButton dsVariant="secondary" dsSize="sm" onClick={onToggleExpand}>
          {mapExpanded ? "Salir" : "Expandir"}
        </AppButton>
      </Box>

      {loading && (
        <Box
          sx={{
            position: "absolute",
            inset: 0,
            zIndex: 900,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            backgroundColor: "rgba(0,0,0,0.35)",
          }}
        >
          <CircularProgress sx={{ color: COLORS.primary }} />
        </Box>
      )}

      {!loading && features.length === 0 && (
        <Box
          sx={{
            position: "absolute",
            left: 12,
            right: 12,
            top: 56,
            zIndex: 900,
          }}
        >
          <Alert severity="info" sx={alertBaseStyles}>
            Sin datos disponibles para los filtros actuales.
          </Alert>
        </Box>
      )}

      <MapContainer center={DEFAULT_CENTER} zoom={12} style={{ height: "100%", width: "100%" }} scrollWheelZoom>
        <TileLayer attribution={OSM_ATTRIBUTION} url={OSM_URL} />
        <FitBounds features={features} />
        {features.map((f, idx) => {
          const c = f.geometry?.coordinates;
          if (!c || typeof c[0] !== "number" || typeof c[1] !== "number") return null;
          const lat = c[1];
          const lng = c[0];
          const domId = f.properties?.domicilio_id;
          return (
            <Marker key={`${domId ?? idx}-${idx}`} position={[lat, lng]} icon={icon}>
              <Popup>
                <Box sx={{ minWidth: 180, color: COLORS.grayDark }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                    Domicilio #{domId ?? "—"}
                  </Typography>
                  <Typography variant="caption" display="block">
                    Actuaciones: {String(f.properties?.act_count ?? 0)} · Relevamientos:{" "}
                    {String(f.properties?.rel_count ?? 0)}
                  </Typography>
                </Box>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </Box>
  );
}
