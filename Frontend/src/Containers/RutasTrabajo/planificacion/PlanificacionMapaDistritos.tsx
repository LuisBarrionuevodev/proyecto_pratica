import { useMemo } from "react";
import { Box, CircularProgress, LinearProgress, Stack, Typography } from "@mui/material";
import { GeoJSON, MapContainer, TileLayer } from "react-leaflet";
import type { Feature, FeatureCollection } from "geojson";
import L from "leaflet";

import type { DistritoCatalogoItem } from "../../../api/geolocalizacionApi";
import distritosGeoRaw from "../../Mapa/distritos.json";
import { glassCard, GLASS_COLORS } from "../../../styles/GlassStyles";
import type { ICargaDistritoRow } from "./types/planificacion.types";
import { enrichPlanificacionDistritosGeoJson } from "./utils/mergePlanificacionDistritosGeo";

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
      weight: selected ? 4 : 1,
      opacity: 1,
      color: selected ? "#ffffff" : "rgba(255,255,255,0.35)",
      fillOpacity: selected ? 0.95 : 0.88,
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
          </MapContainer>

          <Stack
            spacing={1}
            sx={{
              position: "absolute",
              top: 12,
              left: 12,
              zIndex: 1100,
              pointerEvents: "none",
            }}
          >
            <Box sx={overlaySx}>
              <Typography
                sx={{ fontFamily: tactic, fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.08em", color: GLASS_COLORS.textMuted, mb: 0.5 }}
              >
                CARGA TERRITORIAL
              </Typography>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.75 }}>
                <Box
                  sx={{
                    width: 36,
                    height: 8,
                    borderRadius: 1,
                    background: `linear-gradient(90deg, rgba(1,102,255,0.2) 0%, rgba(1,102,255,0.95) 100%)`,
                    border: `1px solid ${GLASS_COLORS.borderLight}`,
                  }}
                />
                <Typography sx={{ fontFamily: tactic, fontSize: "0.7rem", color: GLASS_COLORS.textSecondary }}>baja → alta</Typography>
              </Stack>
              <Typography sx={{ fontFamily: tactic, fontSize: "0.72rem", color: GLASS_COLORS.textSecondary, lineHeight: 1.35 }}>
                Tocá un distrito para filtrar pendientes en la columna izquierda.
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
                <>
                  <Typography sx={{ fontFamily: tactic, fontWeight: 700, fontSize: "0.88rem", color: GLASS_COLORS.textPrimary }}>
                    Vista general
                  </Typography>
                  <Typography sx={{ fontFamily: tactic, fontSize: "0.72rem", color: GLASS_COLORS.textSecondary, mt: 0.5 }}>
                    Ningún distrito seleccionado
                  </Typography>
                </>
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
                        Relativo al máximo del día ({maxCant})
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
        <Typography sx={{ fontFamily: tactic, fontSize: "0.72rem", color: GLASS_COLORS.textMuted }}>
          Leyenda: intensidad azul = carga relativa · borde blanco grueso = selección
        </Typography>
        {distritoCatalogo.length === 0 && !loadingCatalogo ? (
          <Typography sx={{ fontFamily: tactic, fontSize: "0.72rem", color: "#ffab40" }}>
            Catálogo de distritos no disponible; recargá la página.
          </Typography>
        ) : null}
      </Box>
    </Box>
  );
}
