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
import { PlanificacionMapaPendientesLayer } from "./PlanificacionMapaPendientesLayer";

const OSM_ATTRIBUTION = "&copy; OpenStreetMap";
const OSM_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";

const TUCUMAN_CENTER: [number, number] = [-26.8241, -65.2226];

const tactic = '"Tactic Sans", sans-serif' as const;

const overlaySx = {
  ...glassCard,
  p: 1.25,
  maxWidth: 220,
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
    <Box sx={{ position: "relative", width: "100%", minWidth: 0 }}>
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
            height: "min(48vh, 420px)",
            minHeight: 280,
            "& .leaflet-container": {
              fontFamily: tactic,
              background: "#1a1d22",
            },
            "& .leaflet-div-icon.planif-leaflet-pin, & .leaflet-div-icon.planif-leaflet-distrito-num": {
              background: "transparent !important",
              border: "none !important",
            },
            "& .leaflet-div-icon.planif-leaflet-distrito-num": {
              pointerEvents: "none",
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
                onMarkerClick={onMapMarkerClick}
                onPopupClose={onMapPopupClose}
                onAgregar={onAgregarDesdeMapa}
              />
            </Pane>
          </MapContainer>

          <Stack
            spacing={1}
            sx={{
              position: "absolute",
              bottom: 12,
              right: 12,
              zIndex: 1100,
              pointerEvents: "none",
              alignItems: "flex-end",
            }}
          >
            <Box sx={overlaySx}>
              <Typography
                sx={{ fontFamily: tactic, fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.08em", color: GLASS_COLORS.textMuted, mb: 0.5 }}
              >
                CARGA
              </Typography>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }}>
                <Box
                  sx={{
                    width: 36,
                    height: 8,
                    borderRadius: 1,
                    background: `linear-gradient(90deg, rgba(1,102,255,0.2) 0%, rgba(1,102,255,0.95) 100%)`,
                    border: `1px solid ${GLASS_COLORS.borderLight}`,
                  }}
                />
                <Typography sx={{ fontFamily: tactic, fontSize: "0.68rem", color: GLASS_COLORS.textSecondary }}>baja → alta</Typography>
              </Stack>
              <Typography
                sx={{ fontFamily: tactic, fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.06em", color: GLASS_COLORS.textMuted, mb: 0.35, mt: 0.25 }}
              >
                PRIORIDAD (PIN)
              </Typography>
              <Stack direction="row" spacing={0.75} alignItems="center" sx={{ mb: 0.5 }}>
                <Box sx={{ width: 10, height: 10, borderRadius: "50%", backgroundColor: "#2e7d32", border: "1px solid #a5d6a7" }} />
                <Typography sx={{ fontFamily: tactic, fontSize: "0.65rem", color: GLASS_COLORS.textSecondary }}>baja</Typography>
                <Box sx={{ width: 10, height: 10, borderRadius: "50%", backgroundColor: "#f9a825", border: "1px solid #fff59d", ml: 0.5 }} />
                <Typography sx={{ fontFamily: tactic, fontSize: "0.65rem", color: GLASS_COLORS.textSecondary }}>media</Typography>
                <Box sx={{ width: 10, height: 10, borderRadius: "50%", backgroundColor: "#c62828", border: "1px solid #ffab91", ml: 0.5 }} />
                <Typography sx={{ fontFamily: tactic, fontSize: "0.65rem", color: GLASS_COLORS.textSecondary }}>alta</Typography>
              </Stack>
              <Typography sx={{ fontFamily: tactic, fontSize: "0.68rem", color: GLASS_COLORS.textMuted, lineHeight: 1.35 }}>
                Tocá un distrito para filtrar y ver puntos. Número en mapa = pendientes en zona.
              </Typography>
            </Box>
          </Stack>

          <Stack
            spacing={0.75}
            sx={{
              position: "absolute",
              top: 12,
              right: 12,
              zIndex: 1100,
              pointerEvents: "none",
              alignItems: "flex-end",
            }}
          >
            <Box sx={{ ...overlaySx, maxWidth: 260 }}>
              <Typography
                sx={{ fontFamily: tactic, fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.08em", color: GLASS_COLORS.textMuted, mb: 0.5 }}
              >
                DISTRITO ACTIVO
              </Typography>
              {distritoActivoId == null ? (
                <Typography sx={{ fontFamily: tactic, fontWeight: 700, fontSize: "0.88rem", color: GLASS_COLORS.textPrimary }}>
                  Toda la ciudad
                </Typography>
              ) : (
                <>
                  <Typography sx={{ fontFamily: tactic, fontWeight: 700, fontSize: "0.88rem", color: GLASS_COLORS.textPrimary, lineHeight: 1.25 }}>
                    {distritoActivoNombre ?? `Distrito #${distritoActivoId}`}
                  </Typography>
                  {cantidadActiva != null ? (
                    <Box sx={{ mt: 1 }}>
                      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 0.35 }}>
                        <Typography sx={{ fontFamily: tactic, fontSize: "0.68rem", color: GLASS_COLORS.textMuted }}>Carga en zona</Typography>
                        <Typography sx={{ fontFamily: tactic, fontSize: "0.72rem", fontWeight: 700, color: GLASS_COLORS.primary }}>
                          {cantidadActiva} pend.
                        </Typography>
                      </Stack>
                      <LinearProgress
                        variant="determinate"
                        value={intensidadRelativa * 100}
                        sx={{
                          height: 6,
                          borderRadius: 1,
                          backgroundColor: "rgba(255,255,255,0.08)",
                          "& .MuiLinearProgress-bar": {
                            backgroundColor: GLASS_COLORS.primary,
                          },
                        }}
                      />
                      <Typography sx={{ fontFamily: tactic, fontSize: "0.65rem", color: GLASS_COLORS.textMuted, mt: 0.35 }}>
                        vs. máx. día ({maxCant})
                      </Typography>
                    </Box>
                  ) : (
                    <Typography sx={{ fontFamily: tactic, fontSize: "0.72rem", color: GLASS_COLORS.textSecondary, mt: 0.5 }}>
                      Sin dato de carga M2 para este polígono.
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
                  fontSize: "0.72rem",
                  color: GLASS_COLORS.primary,
                  mt: 1,
                  cursor: "pointer",
                  background: "none",
                  border: "none",
                  padding: 0,
                  textDecoration: "underline",
                  pointerEvents: "auto",
                }}
              >
                Quitar selección
              </Typography>
            </Box>
          </Stack>
        </Box>
      )}
      <Box sx={{ mt: 1, display: "flex", gap: 1, alignItems: "center", flexWrap: "wrap" }}>
        <Typography sx={{ fontFamily: tactic, fontSize: "0.7rem", color: GLASS_COLORS.textMuted }}>
          Azul = carga · borde claro = límites · selección reforzada · pin = prioridad
        </Typography>
        {distritoCatalogo.length === 0 && !loadingCatalogo ? (
          <Typography sx={{ fontFamily: tactic, fontSize: "0.72rem", color: "warning.light" }}>
            Catálogo de distritos no disponible; recargá la página.
          </Typography>
        ) : null}
      </Box>
    </Box>
  );
}
