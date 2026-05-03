import { useEffect } from "react";
import { MapContainer, Marker, Popup, TileLayer, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";
import { Alert, Box, CircularProgress, Typography } from "@mui/material";

import type { MapPointFeature } from "../../../api/mapApi";
import { AppButton } from "../../../ui/AppButton";
import type { MapaOperativoModo } from "../hooks/useMapaOperativo";
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

const popupBoxSx = { minWidth: 220, maxWidth: 340, color: COLORS.grayDark };

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
    <Box sx={{ mt: 1.25 }}>
      <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 0.25 }}>
        {label}
      </Typography>
      <Typography variant="body2">{v}</Typography>
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
      <Typography variant="caption" display="block" sx={{ mt: 0.75, color: "text.secondary", lineHeight: 1.35 }}>
        Si el pin no coincide con el local, mové la posición y guardá. Se actualiza el geocode del domicilio (MANUAL,
        OK).
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
        <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>
          Pendiente de completar trabajo
        </Typography>
        <Typography variant="body2" sx={{ mt: 1.25 }}>
          {formatIsoDateAr(p.fecha_ref)}
        </Typography>
        <Typography variant="body2" sx={{ mt: 1.25 }}>
          {ot}
        </Typography>
      </Box>
    );
  }

  if (layer === "ruta_realizado") {
    const otNum = (p.orden_trabajo_numero != null && String(p.orden_trabajo_numero).trim()) || "—";
    const actasLines: { label: string; value: string }[] = [];
    for (const [key, label] of Object.entries(ACTA_LABELS)) {
      const v = p[key];
      if (v != null && String(v).trim() !== "") {
        actasLines.push({ label, value: String(v) });
      }
    }
    const oficio = p.contexto_oficio != null ? String(p.contexto_oficio).trim() : "";
    const expe = p.contexto_expediente_oficio != null ? String(p.contexto_expediente_oficio).trim() : "";
    const notifO = p.contexto_notificacion_origen != null ? String(p.contexto_notificacion_origen).trim() : "";

    return (
      <Box sx={popupBoxSx}>
        <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>
          Orden de trabajo
        </Typography>
        <Typography variant="body1" sx={{ mt: 0.5, fontWeight: 600 }}>
          {otNum}
        </Typography>

        {(() => {
          const t = tipoActuacionMapaLabel(p.tipo_actuacion);
          if (!t || t === "—") return null;
          return (
            <Box sx={{ mt: 1.25 }}>
              <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 0.25 }}>
                Tipo de actuación
              </Typography>
              <Typography variant="body2">{t}</Typography>
            </Box>
          );
        })()}

        <MapPopupField label="Nombre de fantasía del local" value={String(p.nombre_local ?? "").trim()} />
        <MapPopupField
          label="Nombre y apellido o razón social"
          value={String(p.contribuyente_o_razon_social ?? "").trim()}
        />
        <MapPopupField label="DNI o CUIT" value={String(p.doc_contribuyente ?? "").trim()} />
        <MapPopupField label="Domicilio" value={String(p.domicilio_texto ?? "").trim()} />
        <MapPopupField label="Inspectores" value={String(p.inspectores ?? "").trim()} />

        {actasLines.length > 0 ? (
          <Box sx={{ mt: 1.25 }}>
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 0.35 }}>
              Actas labradas
            </Typography>
            {actasLines.map((a) => (
              <Typography key={a.label} variant="body2" display="block">
                {a.label}: {a.value}
              </Typography>
            ))}
          </Box>
        ) : null}

        {oficio ? <MapPopupField label="Oficio" value={oficio} /> : null}
        {expe ? <MapPopupField label="Expediente (oficio)" value={expe} /> : null}
        {notifO ? <MapPopupField label="Notificación de origen" value={notifO} /> : null}
      </Box>
    );
  }

  /* Cola / iniciador pendiente */
  const ubic = (p.ubicacion_texto != null && String(p.ubicacion_texto).trim()) || "—";
  const tipoIni = humanizarTokenBackend(p.tipo_iniciador);
  const fechaCre = formatIsoDateAr(p.iniciador_creado_en);

  return (
    <Box sx={popupBoxSx}>
      <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>
        Pendiente
      </Typography>
      <Typography variant="body2" sx={{ mt: 1.25 }}>
        {tipoIni}
      </Typography>
      <Typography variant="body2" sx={{ mt: 1.25 }}>
        {ubic}
      </Typography>
      <Typography variant="body2" sx={{ mt: 1.25 }}>
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
              <Popup>
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
              Arrastrá el pin naranja o tocá el mapa para la nueva posición. Luego confirmá para guardar en el servidor.
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
