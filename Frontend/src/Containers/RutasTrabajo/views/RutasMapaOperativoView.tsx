import { Alert, Box, Chip, Divider, Paper, Stack, Tooltip, Typography } from "@mui/material";

import { COLORS } from "../../CargarActuaciones/styles/cargarActuacionesStyles";
import ResumenRutaTrabajo from "../Components/ResumenRutaTrabajo";
import { MapaRutaTrabajo } from "../components/MapaRutaTrabajo";
import { useRutaMapa } from "../hooks/useRutaMapa";
import {
  rutasInstitutionalDividerSx,
  rutasInstitutionalGrupoPaperSx,
  rutasInstitutionalPanelPaperSx,
} from "../styles/institutionalVisual";
import type { RutasMapaOperativoViewProps } from "../types/rutasTrabajoMapa.types";
import { AppButton } from "../../../ui/AppButton";

const alertSx = {
  fontFamily: '"Tactic Sans", sans-serif',
  borderRadius: "10px",
  backgroundColor: "rgba(255,255,255,0.06)",
  color: COLORS.white,
  border: `1px solid ${COLORS.border}`,
  "& .MuiAlert-icon": { color: COLORS.white },
  "& .MuiAlert-message": { fontFamily: '"Tactic Sans", sans-serif' },
} as const;

/**
 * Vista MAPA operativa: resumen de ruta, panel de grupos (solo lectura), mapa Leaflet/OSM y acciones volver/publicar.
 */
export function RutasMapaOperativoView({
  ruta,
  grupos,
  itemsActivos,
  iniciadorById,
  onVolverPlanificacion,
  onPublicarRuta,
  canPublish = false,
}: RutasMapaOperativoViewProps) {
  const mapa = useRutaMapa(grupos, itemsActivos, iniciadorById);

  return (
    <Stack spacing={2}>
      <Paper elevation={0} sx={rutasInstitutionalPanelPaperSx}>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems={{ sm: "center" }} justifyContent="space-between">
          <Box>
            <Typography variant="subtitle1" sx={{ fontWeight: 700, color: "text.primary" }}>
              Mapa operativo
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>
              Grupos e ítems sobre el territorio. Los recorridos se dibujan cuando haya coordenadas por domicilio.
            </Typography>
          </Box>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <AppButton dsVariant="secondary" dsSize="sm" onClick={onVolverPlanificacion}>
              Volver a planificación
            </AppButton>
            <Tooltip
              title={canPublish ? "Publicar la ruta (requiere endpoint activo)." : "Sin endpoint de publicación en esta versión."}
              placement="top"
            >
              <span>
                <AppButton
                  dsVariant="primary"
                  dsSize="sm"
                  disabled={!canPublish}
                  onClick={() => void onPublicarRuta?.()}
                >
                  Publicar ruta
                </AppButton>
              </span>
            </Tooltip>
          </Stack>
        </Stack>
      </Paper>

      <ResumenRutaTrabajo ruta={ruta} grupos={grupos} itemsCount={itemsActivos.length} />

      {mapa.avisoCoordenadas && (
        <Alert severity="info" sx={alertSx}>
          {mapa.avisoCoordenadas}
        </Alert>
      )}

      <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems="stretch" sx={{ minHeight: 360 }}>
        <Paper
          elevation={0}
          sx={{
            ...rutasInstitutionalPanelPaperSx,
            flex: { md: "0 0 320px" },
            maxWidth: { md: 360 },
            minWidth: { md: 280 },
            maxHeight: { md: "min(58vh, 560px)" },
            overflow: "auto",
          }}
        >
          <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
            Grupos
          </Typography>
          {grupos.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No hay grupos en esta ruta. Creá grupos en la pestaña TABLA.
            </Typography>
          ) : (
            <Stack spacing={1.2}>
              {mapa.gruposVista.map((gv) => (
                <Paper key={gv.id} elevation={0} sx={rutasInstitutionalGrupoPaperSx(gv.color)}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                    {gv.nombre}
                  </Typography>
                  <Stack direction="row" spacing={0.75} sx={{ mt: 0.75 }} flexWrap="wrap" useFlexGap>
                    <Chip size="small" label={`${gv.itemCount} ítems`} color="primary" variant="outlined" />
                    {gv.estado ? <Chip size="small" label={gv.estado} variant="outlined" /> : null}
                  </Stack>
                  <Divider sx={{ my: 1, ...rutasInstitutionalDividerSx }} />
                  <Typography variant="caption" color="text.secondary" sx={{ display: "block", lineHeight: 1.45 }}>
                    {gv.inspectoresResumen}
                  </Typography>
                  {gv.items.length > 0 && (
                    <Box sx={{ mt: 1 }}>
                      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 0.5 }}>
                        Orden en mapa (cuando haya coords)
                      </Typography>
                      <Stack spacing={0.35}>
                        {gv.items.slice(0, 8).map((it) => (
                          <Typography key={it.itemId} variant="caption" sx={{ pl: 0.5, borderLeft: `3px solid ${gv.color}` }}>
                            {it.orden}. {it.etiqueta}
                          </Typography>
                        ))}
                        {gv.items.length > 8 ? (
                          <Typography variant="caption" color="text.secondary">
                            +{gv.items.length - 8} más…
                          </Typography>
                        ) : null}
                      </Stack>
                    </Box>
                  )}
                </Paper>
              ))}
            </Stack>
          )}
        </Paper>

        <Box sx={{ flex: 1, minWidth: 0 }}>
          <MapaRutaTrabajo
            center={mapa.mapCenter}
            zoom={mapa.mapZoom}
            markers={mapa.markers}
            polylines={mapa.polylines}
          />
        </Box>
      </Stack>
    </Stack>
  );
}
