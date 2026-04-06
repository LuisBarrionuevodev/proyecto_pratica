import { Alert, Box, CircularProgress, Paper, Stack, Tooltip, Typography } from "@mui/material";

import { COLORS } from "../../CargarActuaciones/styles/cargarActuacionesStyles";
import ResumenRutaTrabajo from "../Components/ResumenRutaTrabajo";
import PanelGruposRuta from "../Components/PanelGruposRuta";
import { MapaRutaTrabajo } from "../Components/MapaRutaTrabajo";
import { useRutaMapa } from "../hooks/useRutaMapa";
import { rutasInstitutionalPanelPaperSx } from "../styles/institutionalVisual";
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
 * Vista Mapa final (paso 3): resumen, mapa Leaflet/OSM y gestión de ítems/grupos (mismos handlers que Asignación).
 */
export function RutasMapaOperativoView({
  ruta,
  grupos,
  itemsActivos,
  iniciadorById,
  onVolverAsignacion,
  onPublicarRuta,
  canPublish = false,
  publishingRuta = false,
  detailLoading = false,
  onEditarInspectores,
  onEliminarGrupo,
  onMoverItem,
  onQuitarItem,
  onGuardarOtItem,
}: RutasMapaOperativoViewProps) {
  const mapa = useRutaMapa(grupos, itemsActivos, iniciadorById);
  const canGestionMapa =
    ruta != null &&
    onEditarInspectores != null &&
    onEliminarGrupo != null &&
    onMoverItem != null &&
    onQuitarItem != null &&
    onGuardarOtItem != null;

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
            <AppButton dsVariant="secondary" dsSize="sm" onClick={onVolverAsignacion}>
              Volver a asignación
            </AppButton>
            <Tooltip
              title={
                publishingRuta
                  ? "Publicando la ruta…"
                  : canPublish
                    ? "Publicar la ruta: valida grupos, inspectores, ítems y OT, y genera las actuaciones mínimas."
                    : "Solo se puede publicar una ruta en BORRADOR con el detalle cargado."
              }
              placement="top"
            >
              <span>
                <AppButton
                  dsVariant="primary"
                  dsSize="sm"
                  disabled={!canPublish || publishingRuta}
                  onClick={() => void onPublicarRuta?.()}
                >
                  {publishingRuta ? "Publicando…" : "Publicar ruta"}
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
            Grupos e ítems
          </Typography>
          {ruta == null ? (
            <Typography variant="body2" color="text.secondary">
              Creá o abrí una ruta desde la pestaña TABLA para gestionar grupos e ítems aquí.
            </Typography>
          ) : grupos.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No hay grupos en esta ruta. Creá grupos en la pestaña TABLA.
            </Typography>
          ) : canGestionMapa ? (
            detailLoading ? (
              <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
                <CircularProgress size={32} />
              </Box>
            ) : (
              <PanelGruposRuta
                grupos={grupos}
                items={itemsActivos}
                iniciadorById={iniciadorById}
                onEditarInspectores={onEditarInspectores}
                onEliminarGrupo={onEliminarGrupo}
                onMoverItem={onMoverItem}
                onQuitarItem={onQuitarItem}
                onGuardarOtItem={onGuardarOtItem}
              />
            )
          ) : (
            <Typography variant="body2" color="text.secondary">
              Gestioná ítems desde TABLA.
            </Typography>
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
