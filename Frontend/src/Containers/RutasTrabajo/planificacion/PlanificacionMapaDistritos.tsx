import { useMemo } from "react";
import { Box, CircularProgress, LinearProgress, Stack, Typography } from "@mui/material";
import { GeoJSON, MapContainer, Pane, TileLayer } from "react-leaflet";
import type { Feature, FeatureCollection } from "geojson";
import L from "leaflet";

import type { DistritoCatalogoItem } from "../../../api/geolocalizacionApi";
import type { IRutaIniciadorPendienteRow } from "../../../api/rutasTrabajoApi";
import distritosGeoRaw from "../../Mapa/distritos.json";
import { glassCard, GLASS_COLORS } from "../../../styles/GlassStyles";
import type { ICargaDistritoRow } from "./types/planificacion.types";
import { enrichPlanificacionDistritosGeoJson } from "./utils/mergePlanificacionDistritosGeo";
import { PlanificacionMapaDistritoLabelsLayer } from "./PlanificacionMapaDistritoLabelsLayer";
import { PlanificacionMapaLegend } from "./PlanificacionMapaLegend";
import { PlanificacionMapaPendientesLayer } from "./PlanificacionMapaPendientesLayer";
import { PlanificacionMapaUsedLayer } from "./PlanificacionMapaUsedLayer";
import type { PlanificacionUsedMarker } from "./utils/buildPlanificacionUsedMarkers";

const OSM_ATTRIBUTION = "&copy; OpenStreetMap";
const OSM_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";

const TUCUMAN_CENTER: [number, number] = [-26.8241, -65.2226];

const tactic = '"Tactic Sans", sans-serif' as const;

const overlaySx = {
  ...glassCard,
  p: 1,
  maxWidth: 240,
  pointerEvents: "auto" as const,
  boxShadow: "0 8px 28px rgba(0,0,0,0.45)",
  border: `1px solid ${GLASS_COLORS.borderMedium}`,
};

export type PlanificacionMapaDistritosProps = {
  cargaPorDistrito: ICargaDistritoRow[];
  distritoCatalogo: DistritoCatalogoItem[];
  loadingCatalogo: boolean;
  distritoActivoId: number | null;
  /** Nombre legible del distrito activo (catálogo / M2). */
  distritoActivoNombre?: string | null;
  onSelectDistrito: (distritoId: number | null) => void;
  /** Pendientes del distrito (coords opcionales) para marcar solo con distrito elegido. */
  pendientesParaMapa?: IRutaIniciadorPendienteRow[];
  mapFocusIniciadorId?: number | null;
  mapPopupRow?: IRutaIniciadorPendienteRow | null;
  mapFlyToRow?: IRutaIniciadorPendienteRow | null;
  mapPopupOpenNonce?: number;
  onMapMarkerClick?: (row: IRutaIniciadorPendienteRow) => void;
  onMapPopupClose?: () => void;
  onAgregarDesdeMapa?: (row: IRutaIniciadorPendienteRow) => void;
  /** Ids en pool (mapa deshabilita “Agregar” si ya está). */
  poolIniciadorIds?: number[];
  agregandoIniciadorIds?: ReadonlySet<number>;
  /** Pines rojos de iniciadores ya agregados (pool / grupo). */
  usedMarkers?: PlanificacionUsedMarker[];
};

/**
 * Mapa territorial + overlays fijos (carga / distrito activo).
 */
export function PlanificacionMapaDistritos({
  cargaPorDistrito,
  distritoCatalogo,
  loadingCatalogo,
  distritoActivoId,
  distritoActivoNombre,
  onSelectDistrito,
  pendientesParaMapa = [],
  mapFocusIniciadorId = null,
  mapPopupRow = null,
  mapFlyToRow = null,
  mapPopupOpenNonce = 0,
  onMapMarkerClick = () => {
    /* noop */
  },
  onMapPopupClose = () => {
    /* noop */
  },
  onAgregarDesdeMapa = () => {
    /* noop */
  },
  poolIniciadorIds = [],
  agregandoIniciadorIds,
  usedMarkers = [],
}: PlanificacionMapaDistritosProps) {
  const geoData = useMemo(() => {
    const base = distritosGeoRaw as FeatureCollection;
    return enrichPlanificacionDistritosGeoJson(base, distritoCatalogo, cargaPorDistrito);
  }, [distritoCatalogo, cargaPorDistrito]);

  const maxCant = useMemo(() => {
    const vals = geoData.features.map(
      (f) => Number((f.properties as Record<string, unknown>)?.cantidad ?? 0)
    );
    return Math.max(1, ...vals, 1);
  }, [geoData]);

  const cantidadActiva = useMemo(() => {
    if (distritoActivoId == null) return null;
    const row = cargaPorDistrito.find((c) => c.distrito_id === distritoActivoId);
    return row?.cantidad ?? null;
  }, [cargaPorDistrito, distritoActivoId]);

  const intensidadRelativa = useMemo(() => {
    if (cantidadActiva == null || maxCant <= 0) return 0;
    return Math.min(1, cantidadActiva / maxCant);
  }, [cantidadActiva, maxCant]);

  const styleFn = (feature?: Feature) => {
    const p = feature?.properties as Record<string, unknown> | undefined;
    const cant = Number(p?.cantidad ?? 0);
    const id = p?.distrito_id as number | null | undefined;
    const t = maxCant > 0 ? cant / maxCant : 0;
    const fill = `rgba(1, 102, 255, ${0.12 + t * 0.5})`;
    const selected = id != null && id === distritoActivoId;
    return {
      fillColor: fill,
      weight: selected ? 4 : 2,
      opacity: 1,
      color: selected ? "#ffffff" : "rgba(255, 255, 255, 0.62)",
      fillOpacity: selected ? 0.95 : 0.82,
    };
  };

  const mapKey = `${distritoActivoId ?? "none"}-${geoData.features.length}-${distritoCatalogo.length}`;

  return (
    <Box sx={{ position: "relative", width: "100%", minWidth: 0, height: "100%", minHeight: 0 }}>
      {loadingCatalogo && distritoCatalogo.length === 0 ? (
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            minHeight: 280,
            borderRadius: 2,
            border: `1px solid ${GLASS_COLORS.borderMedium}`,
            backgroundColor: GLASS_COLORS.cardBg,
          }}
        >
          <CircularProgress size={32} sx={{ color: GLASS_COLORS.primary }} />
        </Box>
      ) : (
        <Box
          sx={{
            position: "relative",
            borderRadius: 2,
            overflow: "hidden",
            border: `1px solid ${GLASS_COLORS.borderMedium}`,
            height: "100%",
            minHeight: 280,
            "& .leaflet-container": {
              fontFamily: tactic,
              background: "#1a1d22",
            },
            "& .leaflet-div-icon.planif-leaflet-pin, & .leaflet-div-icon.planif-leaflet-distrito-num, & .leaflet-div-icon.planif-leaflet-used-pin": {
              background: "transparent !important",
              border: "none !important",
            },
            "& .leaflet-div-icon.planif-leaflet-distrito-num": {
              pointerEvents: "none",
            },
            "& .leaflet-popup-content-wrapper": {
              background: "transparent",
              boxShadow: "none",
              borderRadius: "8px",
              padding: 0,
            },
            "& .leaflet-popup-content": {
              margin: "6px 8px",
              minWidth: "auto",
            },
            "& .leaflet-popup-tip": {
              background: "rgba(26,29,34,0.92)",
              boxShadow: "none",
            },
            "& .planif-distrito-num-inner": {
              fontSize: "42px",
              fontWeight: 800,
              opacity: 0.26,
              color: "#ffffff",
              fontFamily: tactic,
              lineHeight: 1,
              textAlign: "center",
              textShadow: "0 2px 12px rgba(0,0,0,0.6)",
              pointerEvents: "none",
              userSelect: "none",
              minWidth: "1ch",
            },
          }}
        >
          <MapContainer center={TUCUMAN_CENTER} zoom={12} style={{ height: "100%", width: "100%" }} scrollWheelZoom>
            <TileLayer attribution={OSM_ATTRIBUTION} url={OSM_URL} />
            <GeoJSON
              key={mapKey}
              data={geoData}
              style={styleFn as L.StyleFunction}
              onEachFeature={(feature, layer) => {
                layer.on("click", () => {
                  const p = feature.properties as Record<string, unknown>;
                  const raw = p?.distrito_id;
                  const id = typeof raw === "number" ? raw : raw != null ? Number(raw) : NaN;
                  if (!Number.isFinite(id)) {
                    return;
                  }
                  onSelectDistrito(id);
                });
              }}
            />
            <PlanificacionMapaDistritoLabelsLayer geoData={geoData} />
            <Pane name="planif-pendientes-pane" style={{ zIndex: 650 }}>
              <PlanificacionMapaPendientesLayer
                rows={pendientesParaMapa}
                visible={distritoActivoId != null}
                focusIniciadorId={mapFocusIniciadorId}
                popupRow={mapPopupRow}
                flyToRow={mapFlyToRow}
                popupOpenNonce={mapPopupOpenNonce}
                poolIniciadorIds={poolIniciadorIds}
                agregandoIniciadorIds={agregandoIniciadorIds}
                onMarkerClick={onMapMarkerClick}
                onPopupClose={onMapPopupClose}
                onAgregar={onAgregarDesdeMapa}
              />
            </Pane>
            <Pane name="planif-used-pane" style={{ zIndex: 660 }}>
              <PlanificacionMapaUsedLayer markers={usedMarkers} />
            </Pane>
          </MapContainer>

          <PlanificacionMapaLegend />

          <Stack
            spacing={0.5}
            sx={{
              position: "absolute",
              top: 12,
              right: 12,
              zIndex: 1100,
              pointerEvents: "none",
              alignItems: "flex-end",
            }}
          >
            <Box sx={overlaySx}>
              <Typography
                sx={{
                  fontFamily: tactic,
                  fontSize: "0.62rem",
                  fontWeight: 700,
                  letterSpacing: "0.06em",
                  color: GLASS_COLORS.textMuted,
                  mb: 0.35,
                }}
              >
                Distrito
              </Typography>
              {distritoActivoId == null ? (
                <Typography sx={{ fontFamily: tactic, fontWeight: 700, fontSize: "0.875rem", color: GLASS_COLORS.textPrimary }}>
                  Ninguno
                </Typography>
              ) : (
                <>
                  <Typography
                    sx={{
                      fontFamily: tactic,
                      fontWeight: 700,
                      fontSize: "0.875rem",
                      color: GLASS_COLORS.textPrimary,
                      lineHeight: 1.25,
                    }}
                  >
                    {distritoActivoNombre ?? `Distrito ${distritoActivoId}`}
                  </Typography>
                  {cantidadActiva != null ? (
                    <Box sx={{ mt: 0.75 }}>
                      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 0.35 }}>
                        <Typography sx={{ fontFamily: tactic, fontSize: "0.65rem", color: GLASS_COLORS.textMuted }}>
                          Carga
                        </Typography>
                        <Typography sx={{ fontFamily: tactic, fontSize: "0.7rem", fontWeight: 700, color: GLASS_COLORS.primary }}>
                          {cantidadActiva}
                        </Typography>
                      </Stack>
                      <LinearProgress
                        variant="determinate"
                        value={intensidadRelativa * 100}
                        sx={{
                          height: 5,
                          borderRadius: 1,
                          backgroundColor: "rgba(255,255,255,0.08)",
                          "& .MuiLinearProgress-bar": {
                            backgroundColor: GLASS_COLORS.primary,
                          },
                        }}
                      />
                      <Typography sx={{ fontFamily: tactic, fontSize: "0.62rem", color: GLASS_COLORS.textMuted, mt: 0.25 }}>
                        Máx. {maxCant}
                      </Typography>
                    </Box>
                  ) : (
                    <Typography sx={{ fontFamily: tactic, fontSize: "0.7rem", color: GLASS_COLORS.textMuted, mt: 0.5 }}>
                      Sin dato.
                    </Typography>
                  )}
                </>
              )}
              <Typography
                component="button"
                type="button"
                onClick={() => onSelectDistrito(null)}
                sx={{
                  fontFamily: tactic,
                  fontSize: "0.68rem",
                  color: GLASS_COLORS.primary,
                  mt: 0.75,
                  cursor: "pointer",
                  background: "none",
                  border: "none",
                  padding: 0,
                  textDecoration: "underline",
                  pointerEvents: "auto",
                }}
              >
                Limpiar
              </Typography>
            </Box>
          </Stack>
        </Box>
      )}
      {distritoCatalogo.length === 0 && !loadingCatalogo ? (
        <Box sx={{ mt: 0.75 }}>
          <Typography sx={{ fontFamily: tactic, fontSize: "0.68rem", color: "warning.light" }}>
            Catálogo de distritos no disponible.
          </Typography>
        </Box>
      ) : null}
    </Box>
  );
}
