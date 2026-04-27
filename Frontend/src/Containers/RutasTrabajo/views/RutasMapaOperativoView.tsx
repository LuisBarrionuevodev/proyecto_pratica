import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import { useCallback, useState } from "react";
import { Alert, Box, Paper, Stack, Tooltip, Typography } from "@mui/material";

import { downloadOrdenesSalidaPdf, downloadRutaResumenPdf } from "../../../documentos";
import { MapaFinalResumenLateral } from "../Components/MapaFinalResumenLateral";
import { MapaRutaTrabajo } from "../Components/MapaRutaTrabajo";
import { RutaResumenHeaderCard, rutaResumenHeaderAccionButtonSx } from "../Components/RutaResumenHeaderCard";
import { useRutaMapa } from "../hooks/useRutaMapa";
import {
  planificacionPanelSubtitleSx,
  planificacionPanelTitleSx,
  rutasInstitutionalAlertBaseSx,
  rutasInstitutionalPanelPaperSx,
  rutasInstitutionalScrollSx,
} from "../styles/institutionalVisual";
import type { RutasMapaOperativoViewProps } from "../types/rutasTrabajoMapa.types";
import { estadoRutaVisible, turnoLabel } from "../utils/rutaResumenLabels";
import { AppButton } from "../../../ui/AppButton";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

const MAPA_FINAL_SECTION_LABEL_SX = {
  fontFamily: '"Tactic Sans", sans-serif',
  fontSize: "0.65rem",
  fontWeight: 600,
  letterSpacing: "0.08em",
  textTransform: "uppercase" as const,
  color: GLASS_COLORS.textMuted,
  mb: 1,
};

/**
 * Paso 3 del flujo borrador: mapa, indicadores y publicación.
 * Con `vistaHistoricaReadOnly`: misma superficie visual en solo lectura (consulta de ruta ya publicada u otro estado no borrador).
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
  onMoverItem,
  vistaHistoricaReadOnly = false,
  onVolverAlListado,
}: RutasMapaOperativoViewProps) {
  const mapa = useRutaMapa(grupos, itemsActivos, iniciadorById);
  const { resumenTerritorial } = mapa;
  const rt = resumenTerritorial;
  const coordsCompletas = rt.totalItems > 0 && rt.itemsConCoordenadas === rt.totalItems;
  const coordsParciales = rt.totalItems > 0 && rt.itemsConCoordenadas > 0 && rt.itemsConCoordenadas < rt.totalItems;
  const sinCoords = rt.totalItems > 0 && rt.itemsConCoordenadas === 0;
  const distritosDetectados = rt.distritosCubiertos.length > 0;

  const estadoLabel = ruta ? estadoRutaVisible(ruta.estado_ruta) : null;
  const puedeEditarEquipos = Boolean(!vistaHistoricaReadOnly && ruta?.estado_ruta === "BORRADOR" && !detailLoading);
  const readOnly = Boolean(vistaHistoricaReadOnly);
  const [pdfResumenLoading, setPdfResumenLoading] = useState(false);
  const [pdfOrdenesLoading, setPdfOrdenesLoading] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const puedeDocumentosPdf = Boolean(readOnly && ruta?.estado_ruta === "PUBLICADA");

  const handleDescargarResumenPdf = useCallback(async () => {
    if (!ruta) return;
    setPdfError(null);
    setPdfResumenLoading(true);
    try {
      await downloadRutaResumenPdf(ruta, grupos, itemsActivos);
    } catch (e) {
      console.error(e);
      setPdfError("No se pudo generar el PDF del resumen. Revisá la conexión o intentá de nuevo.");
    } finally {
      setPdfResumenLoading(false);
    }
  }, [ruta, grupos, itemsActivos]);

  const handleDescargarOrdenesPdf = useCallback(async () => {
    if (!ruta) return;
    setPdfError(null);
    setPdfOrdenesLoading(true);
    try {
      await downloadOrdenesSalidaPdf(ruta, grupos, itemsActivos);
    } catch (e) {
      console.error(e);
      setPdfError("No se pudo generar el PDF de órdenes de salida. Revisá la conexión o intentá de nuevo.");
    } finally {
      setPdfOrdenesLoading(false);
    }
  }, [ruta, grupos, itemsActivos]);

  const chips =
    ruta == null
      ? []
      : [
          ...(estadoLabel ? [{ key: "estado", label: estadoLabel, variant: "estado" as const }] : []),
          { key: "fecha", label: ruta.fecha },
          { key: "turno", label: turnoLabel(ruta.turno) },
          ...(ruta.display_name != null && ruta.display_name !== ""
            ? [{ key: "dn", label: ruta.display_name, variant: "default" as const }]
            : []),
        ];

  const resumenIdentificacion =
    ruta == null ? null : (
      <Typography
        component="div"
        variant="body2"
        sx={{
          fontSize: "0.8125rem",
          lineHeight: 1.45,
          color: GLASS_COLORS.textSecondary,
          fontWeight: 500,
        }}
      >
        <Box component="span" sx={{ color: GLASS_COLORS.textPrimary, fontWeight: 700 }}>
          Ruta {ruta.numero}
        </Box>
      </Typography>
    );

  const headerActions = readOnly ? (
    <>
      <Tooltip title="PDF con membrete, datos de la ruta, grupos/domicilios y mini-mapa de referencia." placement="top">
        <span style={{ display: "flex", width: "100%" }}>
          <AppButton
            dsVariant="secondary"
            dsSize="md"
            fullWidth
            startIcon={<PictureAsPdfIcon />}
            loading={pdfResumenLoading}
            disabled={detailLoading || !ruta || !puedeDocumentosPdf}
            onClick={() => void handleDescargarResumenPdf()}
            sx={{ ...rutaResumenHeaderAccionButtonSx, fontWeight: 600 }}
          >
            Descargar resumen (PDF)
          </AppButton>
        </span>
      </Tooltip>
      <Tooltip title="PDF institucional: una hoja por inspector con orden de salida triplicada (Original / Duplicado / Triplicado)." placement="top">
        <span style={{ display: "flex", width: "100%" }}>
          <AppButton
            dsVariant="secondary"
            dsSize="md"
            fullWidth
            startIcon={<PictureAsPdfIcon />}
            loading={pdfOrdenesLoading}
            disabled={detailLoading || !ruta || !puedeDocumentosPdf}
            onClick={() => void handleDescargarOrdenesPdf()}
            sx={{ ...rutaResumenHeaderAccionButtonSx, fontWeight: 600 }}
          >
            Descargar órdenes de salida (PDF)
          </AppButton>
        </span>
      </Tooltip>
      <AppButton
        dsVariant="primary"
        dsSize="md"
        fullWidth
        onClick={() => onVolverAlListado?.()}
        sx={{ ...rutaResumenHeaderAccionButtonSx, fontWeight: 700 }}
      >
        Volver al listado
      </AppButton>
    </>
  ) : (
    <>
      <AppButton
        dsVariant="secondary"
        dsSize="md"
        fullWidth
        onClick={onVolverAsignacion}
        sx={{ ...rutaResumenHeaderAccionButtonSx, fontWeight: 600 }}
      >
        Asignación
      </AppButton>
      <Tooltip
        title={
          publishingRuta
            ? "Publicando la ruta…"
            : canPublish
              ? "Publica la ruta. Luego podrás descargar desde esta pantalla el resumen y las órdenes de salida en PDF."
              : "Solo con borrador listo."
        }
        placement="top"
      >
        <span style={{ width: "100%", display: "flex" }}>
          <AppButton
            dsVariant="primary"
            dsSize="md"
            fullWidth
            loading={publishingRuta}
            disabled={!canPublish}
            onClick={() => void onPublicarRuta?.()}
            sx={{
              ...rutaResumenHeaderAccionButtonSx,
              fontWeight: 700,
              boxShadow: canPublish && !publishingRuta ? (t) => `0 0 0 1px ${t.palette.primary.dark}40` : undefined,
            }}
          >
            {publishingRuta ? "Publicando…" : "Publicar"}
          </AppButton>
        </span>
      </Tooltip>
    </>
  );

  return (
    <Stack spacing={2} sx={{ minWidth: 0 }} {...(readOnly ? { "data-ruta-historico-preview": "true" } : {})}>
      <RutaResumenHeaderCard
        title={readOnly ? "Resumen ruta histórico" : "Resumen de ruta"}
        subtitle={readOnly ? null : "Revisión final antes de publicar: equipos y direcciones se gestionan en Asignación."}
        chips={chips}
        summary={resumenIdentificacion}
        actions={headerActions}
      />

      {pdfError ? (
        <Alert
          severity="error"
          onClose={() => setPdfError(null)}
          sx={{
            ...rutasInstitutionalAlertBaseSx,
            "& .MuiAlert-message": { fontSize: "0.875rem", lineHeight: 1.4 },
          }}
        >
          {pdfError}
        </Alert>
      ) : null}

      <Paper elevation={0} sx={{ ...rutasInstitutionalPanelPaperSx, py: 1.5, px: 2 }}>
        <Typography sx={MAPA_FINAL_SECTION_LABEL_SX}>
          {readOnly ? "Indicadores (snapshot)" : "Indicadores"}
        </Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.75} flexWrap="wrap" useFlexGap alignItems={{ sm: "flex-start" }}>
          <Box sx={{ minWidth: 88 }}>
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", fontSize: "0.68rem" }}>
              Direcciones
            </Typography>
            <Typography variant="body2" sx={{ fontWeight: 700, fontVariantNumeric: "tabular-nums", mt: 0.15 }}>
              {rt.totalItems}
            </Typography>
          </Box>
          <Box sx={{ minWidth: 100 }}>
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", fontSize: "0.68rem" }}>
              En mapa
            </Typography>
            <Typography
              variant="body2"
              sx={{
                mt: 0.15,
                fontWeight: 700,
                fontVariantNumeric: "tabular-nums",
                color: sinCoords ? "warning.main" : coordsParciales ? "warning.light" : coordsCompletas ? "success.light" : "text.primary",
              }}
            >
              {rt.totalItems === 0 ? "—" : `${rt.itemsConCoordenadas}/${rt.totalItems}`}
            </Typography>
            {coordsParciales && (
              <Typography variant="caption" color="warning.light" sx={{ display: "block", mt: 0.2, fontSize: "0.65rem" }}>
                Incompleto
              </Typography>
            )}
            {sinCoords && (
              <Typography variant="caption" color="warning.light" sx={{ display: "block", mt: 0.2, fontSize: "0.65rem" }}>
                Sin ubicación
              </Typography>
            )}
          </Box>
          <Box sx={{ minWidth: 80 }}>
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", fontSize: "0.68rem" }}>
              Distritos
            </Typography>
            <Typography
              variant="body2"
              sx={{
                mt: 0.15,
                fontWeight: 700,
                fontVariantNumeric: "tabular-nums",
                color: rt.totalItems > 0 && !distritosDetectados ? "text.secondary" : "text.primary",
              }}
            >
              {rt.totalItems === 0 ? "—" : distritosDetectados ? rt.distritosCubiertos.length : "0"}
            </Typography>
          </Box>
          {rt.hintCobertura && (
            <Box sx={{ flex: 1, minWidth: { xs: "100%", sm: 160 } }}>
              <Typography variant="caption" color="text.secondary" sx={{ display: "block", fontSize: "0.68rem" }}>
                Ámbito
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.15, lineHeight: 1.35, fontSize: "0.8125rem" }}>
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
            "& .MuiAlert-message": { fontSize: "0.875rem", lineHeight: 1.4 },
          }}
        >
          {mapa.avisoCoordenadas}
        </Alert>
      )}

      <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems="stretch" sx={{ minHeight: { xs: "auto", md: 420 } }}>
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
            flex: { md: "0 0 360px" },
            maxWidth: { md: 440 },
            minWidth: { md: 300 },
            maxHeight: { md: "min(72vh, 680px)" },
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            minHeight: 0,
          }}
        >
          <Box sx={{ flexShrink: 0 }}>
            <Typography sx={{ ...planificacionPanelTitleSx, mb: 0.25, fontSize: "0.875rem" }}>
              {readOnly ? "Grupos y direcciones (consulta)" : "Grupos y direcciones"}
            </Typography>
            {readOnly ? (
              <Typography
                sx={{
                  ...planificacionPanelSubtitleSx,
                  fontSize: "0.68rem",
                  color: GLASS_COLORS.textMuted,
                  mb: 0.5,
                }}
              >
                Datos al momento de la consulta; sin edición de equipos ni visitas.
              </Typography>
            ) : null}
          </Box>
          <Box sx={{ flex: 1, minHeight: 0, overflow: "auto", pr: 0.5, ...rutasInstitutionalScrollSx }}>
            {ruta == null ? (
              <Typography sx={{ ...planificacionPanelSubtitleSx, fontSize: "0.8125rem", color: GLASS_COLORS.textSecondary }}>
                {readOnly ? "No hay ruta seleccionada." : "Seleccioná una ruta en el flujo."}
              </Typography>
            ) : (
              <MapaFinalResumenLateral
                gruposVista={mapa.gruposVista}
                gruposModelo={grupos}
                itemsActivos={itemsActivos}
                onEditarInspectores={readOnly ? undefined : onEditarInspectores}
                onMoverItem={readOnly ? undefined : onMoverItem}
                puedeEditarEquipos={puedeEditarEquipos}
                readOnly={readOnly}
              />
            )}
          </Box>
        </Paper>
      </Stack>
    </Stack>
  );
}
