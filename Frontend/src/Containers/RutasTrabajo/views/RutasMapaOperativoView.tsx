import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import { useCallback, useEffect, useRef, useState } from "react";
import { Box, Paper, Stack, Tooltip, Typography } from "@mui/material";

import { useAppFeedback } from "../../../components/feedback/useAppFeedback";
import { downloadOrdenesSalidaYTrabajoDepartamentalPdfs, downloadRutaResumenPdf } from "../../../documentos";
import { MapaFinalResumenLateral } from "../Components/MapaFinalResumenLateral";
import { MapaRutaTrabajo } from "../Components/MapaRutaTrabajo";
import { RutaContextoLine } from "../Components/RutaContextoLine";
import { useRutaMapa } from "../hooks/useRutaMapa";
import {
  planificacionPanelSubtitleSx,
  planificacionPanelTitleSx,
  rutasInstitutionalPanelPaperSx,
  rutasInstitutionalScrollSx,
} from "../styles/institutionalVisual";
import type { RutasMapaOperativoViewProps } from "../types/rutasTrabajoMapa.types";
import { AppButton } from "../../../ui/AppButton";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

const MAPA_FINAL_SECTION_LABEL_SX = {
  fontFamily: '"Tactic Sans", sans-serif',
  fontSize: "0.65rem",
  fontWeight: 600,
  letterSpacing: "0.08em",
  textTransform: "uppercase" as const,
  color: GLASS_COLORS.textMuted,
  mb: 0.35,
};

/**
 * Paso 3 del flujo borrador: mapa, indicadores y documentación.
 * Publicar vive en el header compacto; avisos operativos usan toast global.
 */
export function RutasMapaOperativoView({
  ruta,
  grupos,
  itemsActivos,
  iniciadorById,
  publicarBlockers = [],
  detailLoading = false,
  onEditarInspectores,
  onMoverItem,
  vistaHistoricaReadOnly = false,
}: RutasMapaOperativoViewProps) {
  const feedback = useAppFeedback();
  const mapa = useRutaMapa(grupos, itemsActivos, iniciadorById);
  const { resumenTerritorial } = mapa;
  const rt = resumenTerritorial;
  const coordsCompletas = rt.totalItems > 0 && rt.itemsConCoordenadas === rt.totalItems;
  const coordsParciales = rt.totalItems > 0 && rt.itemsConCoordenadas > 0 && rt.itemsConCoordenadas < rt.totalItems;
  const sinCoords = rt.totalItems > 0 && rt.itemsConCoordenadas === 0;
  const distritosDetectados = rt.distritosCubiertos.length > 0;

  const puedeEditarEquipos = Boolean(!vistaHistoricaReadOnly && ruta?.estado_ruta === "BORRADOR" && !detailLoading);
  const readOnly = Boolean(vistaHistoricaReadOnly);
  const [pdfResumenLoading, setPdfResumenLoading] = useState(false);
  const [pdfOrdenesLoading, setPdfOrdenesLoading] = useState(false);
  const puedeDocumentosPdf = Boolean(readOnly && ruta?.estado_ruta === "PUBLICADA");

  const blockersKeyRef = useRef<string | null>(null);
  useEffect(() => {
    if (readOnly || publicarBlockers.length === 0) {
      blockersKeyRef.current = null;
      return;
    }
    const key = publicarBlockers.join("|");
    if (blockersKeyRef.current === key) return;
    blockersKeyRef.current = key;
    feedback.warning(
      `Falta completar antes de publicar: ${publicarBlockers.join(" ")} Guardá la OT en Asignación y usá «Publicar» cuando todo esté listo.`
    );
  }, [feedback, publicarBlockers, readOnly]);

  const avisoCoordsRef = useRef<string | null>(null);
  useEffect(() => {
    if (!mapa.avisoCoordenadas) {
      avisoCoordsRef.current = null;
      return;
    }
    if (avisoCoordsRef.current === mapa.avisoCoordenadas) return;
    avisoCoordsRef.current = mapa.avisoCoordenadas;
    feedback.warning(mapa.avisoCoordenadas);
  }, [feedback, mapa.avisoCoordenadas]);

  const handleDescargarResumenPdf = useCallback(async () => {
    if (!ruta) return;
    setPdfResumenLoading(true);
    try {
      await downloadRutaResumenPdf(ruta, grupos, itemsActivos);
    } catch (e) {
      console.error(e);
      feedback.error("No se pudo generar el PDF del resumen. Revisá la conexión o intentá de nuevo.");
    } finally {
      setPdfResumenLoading(false);
    }
  }, [feedback, ruta, grupos, itemsActivos]);

  const handleDescargarOrdenesPdf = useCallback(async () => {
    if (!ruta) return;
    setPdfOrdenesLoading(true);
    try {
      const result = await downloadOrdenesSalidaYTrabajoDepartamentalPdfs(ruta, grupos, itemsActivos);
      if (result.itemsSinOt.length > 0) {
        const domicilios = result.itemsSinOt.map((it) => it.domicilioTexto).join("; ");
        if (result.ordenesTrabajoIncluidas === 0) {
          feedback.warning(
            `Se descargó la Orden de Salida. Ningún ítem tiene número de OT asignado; el PDF de órdenes de trabajo departamentales quedó vacío. Direcciones sin OT: ${domicilios}.`
          );
        } else {
          feedback.warning(
            `Se descargaron ambos PDF. ${result.itemsSinOt.length} dirección(es) sin número de OT fueron omitidas del PDF de órdenes de trabajo: ${domicilios}.`
          );
        }
      }
    } catch (e) {
      console.error(e);
      feedback.error("No se pudieron generar los PDF de órdenes. Revisá la conexión o intentá de nuevo.");
    } finally {
      setPdfOrdenesLoading(false);
    }
  }, [feedback, ruta, grupos, itemsActivos]);

  const exportActions = readOnly ? (
    <Stack
      direction={{ xs: "column", sm: "row" }}
      spacing={1}
      flexWrap="wrap"
      useFlexGap
      data-testid="mapa-final-export-actions"
      sx={{ flexShrink: 0, justifyContent: { xs: "flex-start", sm: "flex-end" } }}
    >
      <Tooltip title="PDF con membrete, datos de la ruta, grupos/domicilios y mini-mapa de referencia." placement="top">
        <span>
          <AppButton
            dsVariant="secondary"
            dsSize="sm"
            startIcon={<PictureAsPdfIcon />}
            loading={pdfResumenLoading}
            disabled={detailLoading || !ruta || !puedeDocumentosPdf}
            onClick={() => void handleDescargarResumenPdf()}
          >
            Descargar resumen (PDF)
          </AppButton>
        </span>
      </Tooltip>
      <Tooltip
        title="Descarga dos PDF: Orden de Salida del personal (por inspector) y Órdenes de Trabajo Departamentales (una por OT asignada en la ruta)."
        placement="top"
      >
        <span>
          <AppButton
            dsVariant="secondary"
            dsSize="sm"
            startIcon={<PictureAsPdfIcon />}
            loading={pdfOrdenesLoading}
            disabled={detailLoading || !ruta || !puedeDocumentosPdf}
            onClick={() => void handleDescargarOrdenesPdf()}
          >
            Descargar órdenes de salida y órdenes de trabajo
          </AppButton>
        </span>
      </Tooltip>
    </Stack>
  ) : null;

  return (
    <Stack spacing={1.5} sx={{ minWidth: 0 }} data-testid="mapa-final-view" {...(readOnly ? { "data-ruta-historico-preview": "true" } : {})}>
      <Paper elevation={0} sx={{ ...rutasInstitutionalPanelPaperSx, py: 1.5, px: 2 }} data-testid="mapa-final-indicadores">
        <Stack
          direction={{ xs: "column", md: "row" }}
          justifyContent="space-between"
          alignItems={{ xs: "stretch", md: "flex-start" }}
          spacing={1}
          sx={{ mb: 1 }}
        >
          <Stack spacing={0.35} sx={{ minWidth: 0 }}>
            <Typography sx={{ ...MAPA_FINAL_SECTION_LABEL_SX }}>
              {readOnly ? "Indicadores (snapshot)" : "Indicadores"}
            </Typography>
            {ruta != null ? <RutaContextoLine ruta={ruta} variant="compact" /> : null}
          </Stack>
          {exportActions}
        </Stack>

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
