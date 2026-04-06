import { Alert, Box, Chip, Paper, Stack, Tooltip, Typography } from "@mui/material";

import { MapaFinalResumenLateral } from "../Components/MapaFinalResumenLateral";
import { MapaRutaTrabajo } from "../Components/MapaRutaTrabajo";
import { useRutaMapa } from "../hooks/useRutaMapa";
import {
  planificacionPanelSubtitleSx,
  planificacionPanelTitleSx,
  rutasInstitutionalAlertBaseSx,
  rutasInstitutionalPanelPaperSx,
  rutasInstitutionalScrollSx,
  rutasResumenTitleSx,
} from "../styles/institutionalVisual";
import type { RutasMapaOperativoViewProps } from "../types/rutasTrabajoMapa.types";
import { AppButton } from "../../../ui/AppButton";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

function turnoLabel(t: string) {
  return t === "MANIANA" ? "Mañana" : t === "TARDE" ? "Tarde" : t;
}

/**
 * Vista Mapa final (paso 3): validación territorial del borrador ya asignado y publicación.
 * Solo lectura respecto a grupos/ítems; las correcciones se hacen en Asignación.
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
}: RutasMapaOperativoViewProps) {
  const mapa = useRutaMapa(grupos, itemsActivos, iniciadorById);
  const { resumenTerritorial } = mapa;
  const rt = resumenTerritorial;
  const coordsCompletas = rt.totalItems > 0 && rt.itemsConCoordenadas === rt.totalItems;
  const coordsParciales = rt.totalItems > 0 && rt.itemsConCoordenadas > 0 && rt.itemsConCoordenadas < rt.totalItems;
  const sinCoords = rt.totalItems > 0 && rt.itemsConCoordenadas === 0;
  const distritosDetectados = rt.distritosCubiertos.length > 0;

  const chipOutlineSx = {
    fontSize: "0.7rem",
    borderColor: GLASS_COLORS.borderLight,
    color: GLASS_COLORS.textSecondary,
    backgroundColor: "rgba(255,255,255,0.03)",
  } as const;

  return (
    <Stack spacing={2.5}>
      <Paper elevation={0} sx={rutasInstitutionalPanelPaperSx}>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems={{ sm: "flex-start" }} justifyContent="space-between">
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography sx={rutasResumenTitleSx}>Mapa final — validación territorial</Typography>
            <Typography sx={{ ...planificacionPanelSubtitleSx, mt: 0.75, fontSize: "0.8125rem", color: GLASS_COLORS.textSecondary }}>
              Último paso antes de publicar: revisá cómo quedó la ruta en el mapa por grupo (colores y recorridos). Acá no se
              reasigna trabajo; si necesitás cambios, usá Asignación.
            </Typography>
            <Typography sx={{ ...planificacionPanelSubtitleSx, mt: 0.5, display: "block", fontSize: "0.72rem" }}>
              La publicación de la ruta solo está disponible desde esta pantalla, una vez validada la distribución.
            </Typography>
            {ruta && (
              <Stack direction="row" flexWrap="wrap" gap={0.75} sx={{ mt: 1.25 }}>
                <Chip size="small" variant="outlined" label={ruta.fecha} sx={chipOutlineSx} />
                <Chip size="small" variant="outlined" label={turnoLabel(ruta.turno)} sx={chipOutlineSx} />
                {ruta.display_name != null && ruta.display_name !== "" && (
                  <Chip size="small" variant="outlined" label={ruta.display_name} sx={chipOutlineSx} />
                )}
              </Stack>
            )}
          </Box>
          <Stack
            direction={{ xs: "column", sm: "row" }}
            spacing={1}
            flexWrap="wrap"
            useFlexGap
            sx={{ width: { xs: "100%", sm: "auto" }, flexShrink: 0 }}
          >
            <AppButton dsVariant="secondary" dsSize="md" fullWidth onClick={onVolverAsignacion} sx={{ minWidth: { sm: 200 } }}>
              Volver a Asignación
            </AppButton>
            <Tooltip
              title={
                publishingRuta
                  ? "Procesando publicación…"
                  : canPublish
                    ? "Confirma el borrador y pasa la ruta a estado publicado para ejecución (según validaciones del servidor)."
                    : "Solo podés publicar una ruta en BORRADOR con el detalle cargado y listo para validar."
              }
              placement="top"
            >
              <span style={{ width: "100%", display: "inline-flex" }}>
                <AppButton
                  dsVariant="primary"
                  dsSize="md"
                  fullWidth
                  loading={publishingRuta}
                  disabled={!canPublish}
                  onClick={() => void onPublicarRuta?.()}
                  sx={{
                    minWidth: { sm: 220 },
                    fontWeight: 700,
                    boxShadow: canPublish && !publishingRuta ? (t) => `0 0 0 1px ${t.palette.primary.dark}40` : undefined,
                  }}
                >
                  {publishingRuta ? "Publicando ruta…" : "Publicar ruta"}
                </AppButton>
              </span>
            </Tooltip>
          </Stack>
        </Stack>
      </Paper>

      <Paper elevation={0} sx={{ ...rutasInstitutionalPanelPaperSx, py: 1.5 }}>
        <Typography sx={{ ...planificacionPanelSubtitleSx, display: "block", mb: 1, letterSpacing: 0.02, fontWeight: 600 }}>
          Indicadores del borrador (solo lectura)
        </Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} flexWrap="wrap" useFlexGap alignItems={{ sm: "flex-start" }}>
          <Box sx={{ minWidth: 100 }}>
            <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
              Trabajos en ruta
            </Typography>
            <Typography variant="body2" sx={{ fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>
              {rt.totalItems}
            </Typography>
          </Box>
          <Box sx={{ minWidth: 120 }}>
            <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
              {coordsParciales ? "En mapa (geocod.)" : "Puntos en mapa"}
            </Typography>
            <Typography
              variant="body2"
              sx={{
                fontWeight: 700,
                fontVariantNumeric: "tabular-nums",
                color: sinCoords ? "warning.main" : coordsParciales ? "warning.light" : coordsCompletas ? "success.light" : "text.primary",
              }}
            >
              {rt.totalItems === 0 ? "—" : `${rt.itemsConCoordenadas} / ${rt.totalItems}`}
            </Typography>
            {coordsParciales && (
              <Typography variant="caption" color="warning.light" sx={{ display: "block", mt: 0.25, lineHeight: 1.35 }}>
                Parcial: faltan coords en algunos domicilios
              </Typography>
            )}
            {sinCoords && (
              <Typography variant="caption" color="warning.light" sx={{ display: "block", mt: 0.25, lineHeight: 1.35 }}>
                Ningún punto dibujado: revisá geocodificación
              </Typography>
            )}
          </Box>
          <Box sx={{ minWidth: 100 }}>
            <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
              Distritos en datos
            </Typography>
            <Typography
              variant="body2"
              sx={{
                fontWeight: 700,
                fontVariantNumeric: "tabular-nums",
                color: rt.totalItems > 0 && !distritosDetectados ? "text.secondary" : "text.primary",
              }}
            >
              {rt.totalItems === 0 ? "—" : distritosDetectados ? rt.distritosCubiertos.length : "0"}
            </Typography>
            {rt.totalItems > 0 && !distritosDetectados && (
              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.25, lineHeight: 1.35, opacity: 0.9 }}>
                Sin nombre de distrito en ítems
              </Typography>
            )}
          </Box>
          {rt.hintCobertura && (
            <Box sx={{ flex: 1, minWidth: { xs: "100%", sm: 200 } }}>
              <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                Cobertura / dispersión
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.45 }}>
                {rt.hintCobertura}
              </Typography>
            </Box>
          )}
        </Stack>
      </Paper>

      {mapa.avisoCoordenadas && (
        <Alert
          severity="warning"
          sx={{
            ...rutasInstitutionalAlertBaseSx,
            borderColor: "rgba(255, 183, 77, 0.35)",
            "& .MuiAlert-icon": { color: "warning.light" },
          }}
        >
          {mapa.avisoCoordenadas}
        </Alert>
      )}

      <Stack
        direction={{ xs: "column", md: "row" }}
        spacing={2}
        alignItems="stretch"
        sx={{ minHeight: { xs: "auto", md: 420 } }}
      >
        <Box sx={{ flex: 1, minWidth: 0, minHeight: { xs: 360, md: 480 } }}>
          <MapaRutaTrabajo
            center={mapa.mapCenter}
            zoom={mapa.mapZoom}
            markers={mapa.markers}
            polylines={mapa.polylines}
            mapHeight="min(72vh, 680px)"
          />
        </Box>

        <Paper
          elevation={0}
          sx={{
            ...rutasInstitutionalPanelPaperSx,
            flex: { md: "0 0 300px" },
            maxWidth: { md: 340 },
            minWidth: { md: 260 },
            maxHeight: { md: "min(72vh, 680px)" },
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            minHeight: 0,
          }}
        >
          <Box sx={{ flexShrink: 0 }}>
            <Typography sx={{ ...planificacionPanelTitleSx, mb: 0.5 }}>Leyenda por grupo</Typography>
            <Typography sx={{ ...planificacionPanelSubtitleSx, display: "block", mb: 1, fontSize: "0.72rem" }}>
              Color = grupo en el mapa. Solo lectura.
            </Typography>
          </Box>
          <Box sx={{ flex: 1, minHeight: 0, overflow: "auto", pr: 0.5, ...rutasInstitutionalScrollSx }}>
            {ruta == null ? (
              <Typography sx={{ ...planificacionPanelSubtitleSx, fontSize: "0.8125rem", color: GLASS_COLORS.textSecondary }}>
                Abrí una ruta desde el flujo para ver el mapa y el resumen.
              </Typography>
            ) : (
              <MapaFinalResumenLateral gruposVista={mapa.gruposVista} />
            )}
          </Box>
        </Paper>
      </Stack>
    </Stack>
  );
}
