import { useEffect } from "react";
import { GeoJSON, MapContainer, Marker, Popup, TileLayer, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";
import type { PathOptions } from "leaflet";
import { Alert, Box, CircularProgress, Typography } from "@mui/material";

import type { MapPointFeature } from "../../../api/mapApi";
import { AppButton } from "../../../ui/AppButton";
import type { MapaOperativoModo } from "../hooks/useMapaOperativo";
import distritosGeo from "../distritos.json";
import { mapaOperativoSurfaceSx } from "./mapaOperativoStyles";
import { createOperativoPointIcon } from "./mapaOperativoMarkers";
import {
  humanizarTokenBackend,
  humanizarTipoVisitaRecorrido,
} from "../../ActasComprobacion/utils/documentalLabelFormat";
import {
  alertBaseStyles,
  COLORS,
} from "../../CargarActuaciones/styles/cargarActuacionesStyles";

const DEFAULT_CENTER: [number, number] = [-26.82, -65.22];
const OSM_ATTRIBUTION = "&copy; OpenStreetMap contributors";
const OSM_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";

/** Leaflet popup vive fuera del árbol MUI: colores fijos para legibilidad (fondo claro institucional). */
const POPUP_TEXT = "#0f172a";
const POPUP_MUTED = "#64748b";

const popupBoxSx = {
  minWidth: 200,
  maxWidth: 300,
  boxSizing: "border-box",
  color: POPUP_TEXT,
  bgcolor: "rgba(255, 255, 255, 0.97)",
  borderRadius: "10px",
  py: 0.75,
  px: 1,
};

/** Popup realizados: ancho fijo compacto tipo ficha. */
const popupRealizadoBoxSx = {
  ...popupBoxSx,
  minWidth: 236,
  maxWidth: 268,
  py: 0.45,
  px: 0.65,
};

function formatIsoDateAr(iso: unknown): string {
  if (iso == null || String(iso).trim() === "") return "—";
  const s = String(iso).trim().slice(0, 10);
  const parts = s.split("-");
  if (parts.length === 3 && parts[0].length === 4) {
    return `${parts[2]}/${parts[1]}/${parts[0]}`;
  }
  return String(iso);
}

function tipoActuacionMapaLabel(raw: unknown): string {
  const s = humanizarTipoVisitaRecorrido(raw);
  if (s === "—") return humanizarTokenBackend(raw);
  return s;
}

function MapPopupField({ label, value }: { label: string; value: string }) {
  const v = value.trim();
  if (!v) return null;
  return (
    <Box sx={{ mt: 0.35 }}>
      <Typography
        variant="caption"
        display="block"
        sx={{ mb: 0, lineHeight: 1.15, fontSize: "0.7rem", color: POPUP_MUTED, fontWeight: 600 }}
      >
        {label}
      </Typography>
      <Typography variant="body2" sx={{ lineHeight: 1.3, mt: 0.05, fontSize: "0.8125rem", color: POPUP_TEXT, fontWeight: 500 }}>
        {v}
      </Typography>
    </Box>
  );
}

/** Fila densa etiqueta / valor (popup realizados). */
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
      <Typography
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
      </Typography>
      <Typography
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
      </Typography>
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

export type RelocalOperativoDraft = {
  domicilio_id: number;
  lat: number;
  lng: number;
};

const draftRelocalIcon = L.divIcon({
  className: "mapa-operativo-relocal-draft",
  html: `<div style="width:30px;height:30px;border-radius:50%;background:#ff9800;border:3px solid #fff;box-shadow:0 2px 10px rgba(0,0,0,0.45);cursor:grab;"></div>`,
  iconSize: [30, 30],
  iconAnchor: [15, 15],
});

function MapClickToRelocal({
  enabled,
  onPick,
}: {
  enabled: boolean;
  onPick: (lat: number, lng: number) => void;
}) {
  useMapEvents({
    click(e) {
      if (!enabled) return;
      onPick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

/** Cierra popups de Leaflet al entrar en modo relocalización (evita card superpuesta al pin de borrador). */
function ClosePopupWhenRelocal({ active }: { active: boolean }) {
  const map = useMap();
  useEffect(() => {
    if (active) {
      map.closePopup();
    }
  }, [active, map]);
  return null;
}

function RelocalDraftMarker({
  position,
  onDragEnd,
}: {
  position: [number, number];
  onDragEnd: (lat: number, lng: number) => void;
}) {
  return (
    <Marker
      position={position}
      draggable
      zIndexOffset={2000}
      icon={draftRelocalIcon}
      eventHandlers={{
        dragend: (e) => {
          const ll = (e.target as L.Marker).getLatLng();
          onDragEnd(ll.lat, ll.lng);
        },
      }}
    />
  );
}

function RelocalizarControl({
  modo,
  layer,
  domicilioId,
  lat,
  lng,
  relocalGuardando,
  onIniciarRelocalizacion,
}: {
  modo: MapaOperativoModo;
  layer: string;
  domicilioId: number | null;
  lat: number;
  lng: number;
  relocalGuardando: boolean;
  onIniciarRelocalizacion?: (payload: RelocalOperativoDraft) => void;
}) {
  const can =
    modo === "pendientes" &&
    typeof onIniciarRelocalizacion === "function" &&
    domicilioId != null &&
    !Number.isNaN(domicilioId) &&
    layer === "iniciador_backlog";

  if (!can) return null;

  return (
    <Box sx={{ mt: 1.5, pt: 1, borderTop: "1px solid rgba(0,0,0,0.08)" }} onClick={(e) => e.stopPropagation()}>
      <AppButton
        dsVariant="secondary"
        dsSize="sm"
        loading={relocalGuardando}
        disabled={relocalGuardando}
        onClick={() => onIniciarRelocalizacion({ domicilio_id: domicilioId!, lat, lng })}
      >
        Relocalizar
      </AppButton>
      <Typography variant="caption" display="block" sx={{ mt: 0.75, color: POPUP_MUTED, lineHeight: 1.35 }}>
        Mové el pin o tocá el mapa y guardá. Actualiza el geocode del domicilio.
      </Typography>
    </Box>
  );
}

function MapaOperativoPopup({
  p,
  modo,
  lat,
  lng,
  relocalGuardando,
  onIniciarRelocalizacion,
}: {
  p: Record<string, unknown>;
  modo: MapaOperativoModo;
  lat: number;
  lng: number;
  relocalGuardando: boolean;
  onIniciarRelocalizacion?: (payload: RelocalOperativoDraft) => void;
}) {
  const layer = String(p.map_layer ?? "");
  const domParsed = p.domicilio_id != null ? Number(p.domicilio_id) : NaN;
  const domicilioIdNum = Number.isFinite(domParsed) ? domParsed : null;

  if (layer === "ruta_en_proceso") {
    const ot = (p.orden_trabajo_texto != null && String(p.orden_trabajo_texto).trim()) || "Sin asignar";
    return (
      <Box sx={popupBoxSx}>
        <Typography variant="subtitle2" sx={{ fontWeight: 800, lineHeight: 1.2, color: POPUP_TEXT }}>
          Pendiente en completar trabajo
        </Typography>
        <Typography variant="body2" sx={{ mt: 0.5, lineHeight: 1.3, color: POPUP_TEXT }}>
          {formatIsoDateAr(p.fecha_ref)}
        </Typography>
        <Typography variant="body2" sx={{ mt: 0.35, lineHeight: 1.3, color: POPUP_TEXT }}>
          {ot}
        </Typography>
      </Box>
    );
  }

  if (layer === "ruta_realizado") {
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
    const domicilioConDistrito =
      dom && distNom ? `${dom} · ${distNom}` : dom || distNom || "";
    const insp = String(p.inspectores ?? "").trim();
    const local = String(p.nombre_local ?? "").trim();
    const contrib = String(p.contribuyente_o_razon_social ?? "").trim();
    const tipoAct = tipoActuacionMapaLabel(p.tipo_actuacion);
    const doc = String(p.doc_contribuyente ?? "").trim();

    return (
      <Box sx={popupRealizadoBoxSx}>
        <Box sx={{ pb: 0.35, mb: 0.25, borderBottom: "1px solid rgba(15, 23, 42, 0.12)" }}>
          <Typography sx={{ fontSize: "0.62rem", fontWeight: 800, color: POPUP_MUTED, letterSpacing: "0.06em" }}>
            ORDEN DE TRABAJO
          </Typography>
          <Typography sx={{ fontSize: "0.9rem", fontWeight: 800, color: POPUP_TEXT, lineHeight: 1.15, mt: 0.15 }}>
            {otDisplay}
          </Typography>
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

  /* Cola / iniciador pendiente */
  const ubic = (p.ubicacion_texto != null && String(p.ubicacion_texto).trim()) || "—";
  const tipoIni = humanizarTokenBackend(p.tipo_iniciador);
  const fechaCre = formatIsoDateAr(p.iniciador_creado_en);

  return (
    <Box sx={popupBoxSx}>
      <Typography variant="subtitle2" sx={{ fontWeight: 800, lineHeight: 1.2, color: POPUP_TEXT }}>
        Pendiente
      </Typography>
      <Typography variant="body2" sx={{ mt: 0.5, lineHeight: 1.3, color: POPUP_TEXT }}>
        {tipoIni}
      </Typography>
      <Typography variant="body2" sx={{ mt: 0.35, lineHeight: 1.3, color: POPUP_TEXT }}>
        {ubic}
      </Typography>
      <Typography variant="body2" sx={{ mt: 0.35, lineHeight: 1.3, color: POPUP_TEXT }}>
        {fechaCre}
      </Typography>
      <RelocalizarControl
        modo={modo}
        layer={layer}
        domicilioId={domicilioIdNum}
        lat={lat}
        lng={lng}
        relocalGuardando={relocalGuardando}
        onIniciarRelocalizacion={onIniciarRelocalizacion}
      />
    </Box>
  );
}

/** Color estable por número de distrito (nombre «Distrito N» del GeoJSON). */
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

/** Polígonos de distrito como referencia visual; sin interacción para no tapar marcadores. */
function OperativoDistritosGeo() {
  return (
    <GeoJSON
      data={distritosGeo as never}
      interactive={false}
      style={(f) => operativoDistritoPathStyle(f as { properties?: { nombre?: string } })}
    />
  );
}

/**
 * Leaflet no recalcula tiles al cambiar el tamaño del contenedor (p. ej. expandir mapa).
 * Invalida tamaño tras layout y cuando cambian datos o modo expandido.
 */
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
    const run = () => {
      map.invalidateSize({ animate: false });
    };
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
  modo: MapaOperativoModo;
  features: MapPointFeature[];
  loading: boolean;
  mapExpanded: boolean;
  onToggleExpand: () => void;
  /** Borrador de relocalización (solo mapa pendientes); pin naranja arrastrable + clic en mapa. */
  relocalDraft: RelocalOperativoDraft | null;
  onRelocalDraftMove: (lat: number, lng: number) => void;
  onIniciarRelocalizacion: (payload: RelocalOperativoDraft) => void;
  onCancelarRelocalizacion: () => void;
  onConfirmarRelocalizacion: () => void;
  relocalGuardando: boolean;
};

/**
 * Mapa Leaflet principal dentro de caja canónica; botón expandir y marcadores según features.
 * En modo pendientes permite relocalizar domicilio vía pin de borrador y `POST /geo/:id/manual`.
 */
export function MapaCanvas({
  modo,
  features,
  loading,
  mapExpanded,
  onToggleExpand,
  relocalDraft,
  onRelocalDraftMove,
  onIniciarRelocalizacion,
  onCancelarRelocalizacion,
  onConfirmarRelocalizacion,
  relocalGuardando,
}: MapaCanvasProps) {
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
        <MapInvalidateSize mapExpanded={mapExpanded} featureCount={features.length} loading={loading} />
        <TileLayer attribution={OSM_ATTRIBUTION} url={OSM_URL} />
        <OperativoDistritosGeo />
        <FitBounds features={features} />
        {modo === "pendientes" && relocalDraft != null ? (
          <MapClickToRelocal enabled onPick={onRelocalDraftMove} />
        ) : null}
        {modo === "pendientes" && relocalDraft != null ? (
          <ClosePopupWhenRelocal active />
        ) : null}
        {modo === "pendientes" && relocalDraft != null ? (
          <RelocalDraftMarker
            position={[relocalDraft.lat, relocalDraft.lng]}
            onDragEnd={onRelocalDraftMove}
          />
        ) : null}
        {features.map((f, idx) => {
          const c = f.geometry?.coordinates;
          if (!c || typeof c[0] !== "number" || typeof c[1] !== "number") return null;
          const lat = c[1];
          const lng = c[0];
          const p = f.properties ?? {};
          const domId = p.domicilio_id;
          const mk = `${domId ?? "x"}-${p.iniciador_id ?? ""}-${p.ruta_item_id ?? ""}-${idx}`;
          const icon = createOperativoPointIcon(modo, p as Record<string, unknown>);
          return (
            <Marker key={mk} position={[lat, lng]} icon={icon}>
              <Popup maxWidth={272} minWidth={220}>
                <MapaOperativoPopup
                  p={p as Record<string, unknown>}
                  modo={modo}
                  lat={lat}
                  lng={lng}
                  relocalGuardando={relocalGuardando}
                  onIniciarRelocalizacion={modo === "pendientes" ? onIniciarRelocalizacion : undefined}
                />
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
      {modo === "pendientes" && relocalDraft != null ? (
        <Box
          sx={{
            position: "absolute",
            left: 12,
            right: 12,
            bottom: 12,
            zIndex: 1000,
            pointerEvents: "auto",
            maxWidth: 420,
          }}
        >
          <Alert severity="info" sx={{ ...alertBaseStyles, py: 0.75 }}>
            <Typography variant="body2" sx={{ fontWeight: 700, mb: 0.5 }}>
              Relocalización · domicilio #{relocalDraft.domicilio_id}
            </Typography>
            <Typography variant="caption" display="block" sx={{ mb: 1 }}>
              Arrastrá el pin naranja o tocá el mapa. Confirmá para guardar.
            </Typography>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
              <AppButton
                dsVariant="primary"
                dsSize="sm"
                loading={relocalGuardando}
                onClick={onConfirmarRelocalizacion}
              >
                Guardar ubicación
              </AppButton>
              <AppButton dsVariant="ghost" dsSize="sm" disabled={relocalGuardando} onClick={onCancelarRelocalizacion}>
                Cancelar
              </AppButton>
            </Box>
          </Alert>
        </Box>
      ) : null}
    </Box>
  );
}
