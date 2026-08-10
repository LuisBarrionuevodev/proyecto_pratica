import { useEffect } from "react";
import { GeoJSON, MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import type { PathOptions } from "leaflet";
import { Alert, Box, CircularProgress } from "@mui/material";

import type { MapPointFeature } from "../../../api/mapApi";
import { AppButton } from "../../../ui/AppButton";
import distritosGeo from "../distritos.json";
import { mapaOperativoSurfaceSx } from "./mapaOperativoStyles";
import { createOperativoPointIcon } from "./mapaOperativoMarkers";
import {
  humanizarTokenBackend,
  humanizarTipoVisitaRecorrido,
} from "../../ActasComprobacion/utils/documentalLabelFormat";
import { alertBaseStyles, COLORS } from "../../CargarActuaciones/styles/cargarActuacionesStyles";

const DEFAULT_CENTER: [number, number] = [-26.82, -65.22];
const OSM_ATTRIBUTION = "&copy; OpenStreetMap contributors";
const OSM_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";

const POPUP_TEXT = "#0f172a";
const POPUP_MUTED = "#64748b";

const popupRealizadoBoxSx = {
  minWidth: 236,
  maxWidth: 268,
  boxSizing: "border-box",
  color: POPUP_TEXT,
  bgcolor: "rgba(255, 255, 255, 0.97)",
  borderRadius: "10px",
  py: 0.45,
  px: 0.65,
};

function tipoActuacionMapaLabel(raw: unknown): string {
  const s = humanizarTipoVisitaRecorrido(raw);
  if (s === "—") return humanizarTokenBackend(raw);
  return s;
}

function RealizadoCompactRow({ label, value }: { label: string; value: string }) {
  const v = value.trim();
  if (!v) return null;
  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "flex-start",
        gap: 0.75,
        py: 0.12,
        borderBottom: "1px solid rgba(15, 23, 42, 0.06)",
        "&:last-of-type": { borderBottom: "none" },
      }}
    >
      <Box
        component="span"
        sx={{
          flex: "0 0 42%",
          maxWidth: "42%",
          fontSize: "0.65rem",
          fontWeight: 700,
          color: POPUP_MUTED,
          lineHeight: 1.2,
          textTransform: "uppercase",
          letterSpacing: "0.02em",
        }}
      >
        {label}
      </Box>
      <Box
        component="span"
        sx={{
          flex: 1,
          fontSize: "0.74rem",
          fontWeight: 600,
          color: POPUP_TEXT,
          lineHeight: 1.25,
          textAlign: "right",
          wordBreak: "break-word",
        }}
      >
        {v}
      </Box>
    </Box>
  );
}

const ACTA_LABELS: Record<string, string> = {
  acta_inspeccion: "Inspección",
  acta_notificacion: "Notificación",
  acta_comprobacion: "Comprobación",
  acta_clausura: "Clausura",
  acta_decomiso: "Decomiso",
};

function MapaRealizadoPopup({ p }: { p: Record<string, unknown> }) {
  const otNum = (p.orden_trabajo_numero != null && String(p.orden_trabajo_numero).trim()) || "";
  const otLine = (p.orden_trabajo_texto != null && String(p.orden_trabajo_texto).trim()) || "";
  const otDisplay = otNum || otLine || "—";
  const actasLines: { label: string; value: string }[] = [];
  for (const [key, label] of Object.entries(ACTA_LABELS)) {
    const v = p[key];
    if (v != null && String(v).trim() !== "") {
      actasLines.push({ label, value: String(v) });
    }
  }
  const actasResumen =
    actasLines.length > 0 ? actasLines.map((a) => `${a.label}: ${a.value}`).join(" · ") : "";
  const oficio = p.contexto_oficio != null ? String(p.contexto_oficio).trim() : "";
  const expe = p.contexto_expediente_oficio != null ? String(p.contexto_expediente_oficio).trim() : "";
  const notifO = p.contexto_notificacion_origen != null ? String(p.contexto_notificacion_origen).trim() : "";
  const dom = String(p.domicilio_texto ?? "").trim();
  const distNom = String(p.distrito_nombre ?? "").trim();
  const domicilioConDistrito = dom && distNom ? `${dom} · ${distNom}` : dom || distNom || "";
  const insp = String(p.inspectores ?? "").trim();
  const local = String(p.nombre_local ?? "").trim();
  const contrib = String(p.contribuyente_o_razon_social ?? "").trim();
  const tipoAct = tipoActuacionMapaLabel(p.tipo_actuacion);
  const doc = String(p.doc_contribuyente ?? "").trim();

  return (
    <Box sx={popupRealizadoBoxSx}>
      <Box sx={{ pb: 0.35, mb: 0.25, borderBottom: "1px solid rgba(15, 23, 42, 0.12)" }}>
        <Box component="span" sx={{ fontSize: "0.62rem", fontWeight: 800, color: POPUP_MUTED, letterSpacing: "0.06em" }}>
          ORDEN DE TRABAJO
        </Box>
        <Box component="div" sx={{ fontSize: "0.9rem", fontWeight: 800, color: POPUP_TEXT, lineHeight: 1.15, mt: 0.15 }}>
          {otDisplay}
        </Box>
      </Box>
      {tipoAct && tipoAct !== "—" ? <RealizadoCompactRow label="Tipo actuación" value={tipoAct} /> : null}
      <RealizadoCompactRow label="Nombre fantasía" value={local} />
      <RealizadoCompactRow label="Contribuyente" value={contrib} />
      <RealizadoCompactRow label="DNI / CUIT" value={doc} />
      <RealizadoCompactRow label="Domicilio" value={domicilioConDistrito} />
      <RealizadoCompactRow label="Inspectores" value={insp} />
      <RealizadoCompactRow label="Actas" value={actasResumen} />
      {oficio ? <RealizadoCompactRow label="Oficio" value={oficio} /> : null}
      {expe ? <RealizadoCompactRow label="Expediente" value={expe} /> : null}
      {notifO ? <RealizadoCompactRow label="Notif. origen" value={notifO} /> : null}
    </Box>
  );
}

function operativoDistritoPathStyle(feature: { properties?: { nombre?: string } }): PathOptions {
  const nombre = String(feature?.properties?.nombre ?? "").trim();
  const m = /^Distrito\s+(\d+)$/i.exec(nombre);
  const n = m ? parseInt(m[1], 10) : 0;
  const hue = (n * 41) % 360;
  return {
    color: `hsla(${hue}, 58%, 18%, 0.92)`,
    weight: 1.85,
    fillColor: `hsl(${hue}, 44%, 44%)`,
    fillOpacity: 0.1,
    opacity: 1,
  };
}

function OperativoDistritosGeo() {
  return (
    <GeoJSON
      data={distritosGeo as never}
      interactive={false}
      style={(f) => operativoDistritoPathStyle(f as { properties?: { nombre?: string } })}
    />
  );
}

function MapInvalidateSize({
  mapExpanded,
  featureCount,
  loading,
}: {
  mapExpanded: boolean;
  featureCount: number;
  loading: boolean;
}) {
  const map = useMap();
  useEffect(() => {
    const run = () => map.invalidateSize({ animate: false });
    run();
    const t1 = window.setTimeout(run, 60);
    const t2 = window.setTimeout(run, 280);
    return () => {
      window.clearTimeout(t1);
      window.clearTimeout(t2);
    };
  }, [map, mapExpanded, featureCount, loading]);
  return null;
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
  features: MapPointFeature[];
  loading: boolean;
  mapExpanded: boolean;
  onToggleExpand: () => void;
  /** Mensaje contextual cuando no hay puntos (p. ej. filtro sin resultados). */
  emptyMessage?: string | null;
};

/** Mapa Leaflet del modo Realizados en MapPage. */
export function MapaCanvas({ features, loading, mapExpanded, onToggleExpand, emptyMessage }: MapaCanvasProps) {
  return (
    <Box
      sx={{
        ...mapaOperativoSurfaceSx,
        position: "relative",
        flex: mapExpanded ? 1 : undefined,
        alignSelf: mapExpanded ? "stretch" : undefined,
        width: "100%",
        minHeight: mapExpanded ? { xs: "70vh", md: "min(92vh, 920px)" } : 420,
        height: mapExpanded ? { xs: "70vh", md: "min(92vh, 920px)" } : 480,
        overflow: "hidden",
        "& .leaflet-container": {
          fontFamily: '"Tactic Sans", sans-serif',
          background: COLORS.grayMedium,
        },
      }}
    >
      <Box sx={{ position: "absolute", top: 12, right: 12, zIndex: 1000 }}>
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

      {!loading && features.length === 0 && emptyMessage && (
        <Box sx={{ position: "absolute", left: 12, right: 12, top: 56, zIndex: 900 }}>
          <Alert severity="info" sx={alertBaseStyles}>
            {emptyMessage}
          </Alert>
        </Box>
      )}

      <MapContainer center={DEFAULT_CENTER} zoom={12} style={{ height: "100%", width: "100%" }} scrollWheelZoom>
        <MapInvalidateSize mapExpanded={mapExpanded} featureCount={features.length} loading={loading} />
        <TileLayer attribution={OSM_ATTRIBUTION} url={OSM_URL} />
        <OperativoDistritosGeo />
        <FitBounds features={features} />
        {features.map((f, idx) => {
          const c = f.geometry?.coordinates;
          if (!c || typeof c[0] !== "number" || typeof c[1] !== "number") return null;
          const lat = c[1];
          const lng = c[0];
          const p = f.properties ?? {};
          const domId = p.domicilio_id;
          const mk = `${domId ?? "x"}-${p.iniciador_id ?? ""}-${p.ruta_item_id ?? ""}-${idx}`;
          const icon = createOperativoPointIcon(p as Record<string, unknown>);
          return (
            <Marker key={mk} position={[lat, lng]} icon={icon}>
              <Popup maxWidth={272} minWidth={220}>
                <MapaRealizadoPopup p={p as Record<string, unknown>} />
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </Box>
  );
}
