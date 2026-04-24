import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import ImageIcon from "@mui/icons-material/Image";
import { useCallback, useEffect, useRef, useState } from "react";
import { Alert, Box, Paper, Stack, Tooltip, Typography } from "@mui/material";

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
import { printMapaFinalGruposOperativo } from "../utils/exportMapaFinalGruposPrint";
import { buildMapaFinalCapturaFilename, downloadMapaFinalRegionPng } from "../utils/exportMapaFinalCaptura";
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

/** Estado duplicado en chips; se mantiene en DOM para `estadoCapturaRef` en export PNG. */
const MAPA_RESUMEN_ESTADO_CAPTURA_SR_ONLY = {
  position: "absolute" as const,
  width: 1,
  height: 1,
  padding: 0,
  margin: -1,
  overflow: "hidden",
  clip: "rect(0, 0, 0, 0)",
  whiteSpace: "nowrap" as const,
  borderWidth: 0,
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
  capturaMapaFinalRef,
  exportGruposPrintRef,
  vistaHistoricaReadOnly = false,
  onVolverAlListado,
}: RutasMapaOperativoViewProps) {
  const mapa = useRutaMapa(grupos, itemsActivos, iniciadorById);
  const exportOperativoRef = useRef<HTMLDivElement>(null);
  const estadoCapturaRef = useRef<HTMLSpanElement>(null);
  const { resumenTerritorial } = mapa;
  const rt = resumenTerritorial;
  const coordsCompletas = rt.totalItems > 0 && rt.itemsConCoordenadas === rt.totalItems;
  const coordsParciales = rt.totalItems > 0 && rt.itemsConCoordenadas > 0 && rt.itemsConCoordenadas < rt.totalItems;
  const sinCoords = rt.totalItems > 0 && rt.itemsConCoordenadas === 0;
  const distritosDetectados = rt.distritosCubiertos.length > 0;

  const estadoLabel = ruta ? estadoRutaVisible(ruta.estado_ruta) : null;
  const puedeEditarEquipos = Boolean(!vistaHistoricaReadOnly && ruta?.estado_ruta === "BORRADOR" && !detailLoading);
  const readOnly = Boolean(vistaHistoricaReadOnly);
  const [historicoPngLoading, setHistoricoPngLoading] = useState(false);
  const [historicoGruposLoading, setHistoricoGruposLoading] = useState(false);

  const etiquetaImpresionHistorico = estadoLabel ?? ruta?.estado_ruta ?? "Publicada";

  const ejecutarCapturaMapaFinal = useCallback(
    async (opts?: { estadoEtiqueta?: string }) => {
      const el = exportOperativoRef.current;
      if (!el || !ruta) {
        throw new Error("No hay vista de mapa para capturar.");
      }
      const span = estadoCapturaRef.current;
      const prevText = span?.textContent ?? null;
      if (opts?.estadoEtiqueta != null && span) {
        span.textContent = opts.estadoEtiqueta;
      }
      try {
        await new Promise<void>((resolve) => {
          requestAnimationFrame(() => requestAnimationFrame(() => resolve()));
        });
        await new Promise<void>((r) => setTimeout(r, 400));
        const filename = buildMapaFinalCapturaFilename(ruta);
        await downloadMapaFinalRegionPng(el, filename);
      } finally {
        if (span && prevText != null) {
          span.textContent = prevText;
        }
      }
    },
    [ruta]
  );

  const ejecutarExportGruposPrint = useCallback(
    async (opts?: { estadoEtiqueta?: string }) => {
      if (!ruta) {
        throw new Error("No hay ruta cargada para exportar grupos.");
      }
      const estadoEtiqueta = opts?.estadoEtiqueta ?? estadoLabel ?? "—";
      await printMapaFinalGruposOperativo({
        ruta,
        gruposVista: mapa.gruposVista,
        estadoEtiqueta,
      });
    },
    [ruta, mapa.gruposVista, estadoLabel]
  );

  useEffect(() => {
    if (!capturaMapaFinalRef) return;
    capturaMapaFinalRef.current = ejecutarCapturaMapaFinal;
    return () => {
      capturaMapaFinalRef.current = null;
    };
  }, [capturaMapaFinalRef, ejecutarCapturaMapaFinal]);

  useEffect(() => {
    if (!exportGruposPrintRef) return;
    exportGruposPrintRef.current = ejecutarExportGruposPrint;
    return () => {
      exportGruposPrintRef.current = null;
    };
  }, [exportGruposPrintRef, ejecutarExportGruposPrint]);

  const handleHistoricoDescargarPng = useCallback(async () => {
    setHistoricoPngLoading(true);
    try {
      await ejecutarCapturaMapaFinal({ estadoEtiqueta: etiquetaImpresionHistorico });
    } catch (e) {
      console.error(e);
    } finally {
      setHistoricoPngLoading(false);
    }
  }, [ejecutarCapturaMapaFinal, etiquetaImpresionHistorico]);

  const handleHistoricoImprimirGrupos = useCallback(async () => {
    setHistoricoGruposLoading(true);
    try {
      await ejecutarExportGruposPrint({ estadoEtiqueta: etiquetaImpresionHistorico });
    } catch (e) {
      console.error(e);
    } finally {
      setHistoricoGruposLoading(false);
    }
  }, [ejecutarExportGruposPrint, etiquetaImpresionHistorico]);

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
      <Box sx={{ position: "relative" }}>
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
        <Box component="span" sx={MAPA_RESUMEN_ESTADO_CAPTURA_SR_ONLY} aria-hidden>
          <Box component="span" ref={estadoCapturaRef}>
            {estadoLabel ?? "—"}
          </Box>
        </Box>
      </Box>
    );

  const headerActions = readOnly ? (
    <>
      <Tooltip title="Descarga PNG del bloque mapa + resumen (misma acción que tras publicar)." placement="top">
        <span style={{ display: "flex", width: "100%" }}>
          <AppButton
            dsVariant="secondary"
            dsSize="md"
            fullWidth
            startIcon={<ImageIcon />}
            loading={historicoPngLoading}
            disabled={detailLoading || !ruta}
            onClick={() => void handleHistoricoDescargarPng()}
            sx={{ ...rutaResumenHeaderAccionButtonSx, fontWeight: 600 }}
          >
            Reimprimir mapa (PNG)
          </AppButton>
        </span>
      </Tooltip>
      <Tooltip title="Abre el cuadro de impresión de la hoja de grupos (podés guardar como PDF según el navegador)." placement="top">
        <span style={{ display: "flex", width: "100%" }}>
          <AppButton
            dsVariant="secondary"
            dsSize="md"
            fullWidth
            startIcon={<PictureAsPdfIcon />}
            loading={historicoGruposLoading}
            disabled={detailLoading || !ruta}
            onClick={() => void handleHistoricoImprimirGrupos()}
            sx={{ ...rutaResumenHeaderAccionButtonSx, fontWeight: 600 }}
          >
            Reimprimir hoja de grupos
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
            ? "Publicando y generando exportaciones…"
            : canPublish
              ? "Publica la ruta, descarga captura PNG del mapa y abre el cuadro de impresión de la hoja de grupos (guardar como PDF según el navegador)."
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
    <Stack
      ref={exportOperativoRef}
      spacing={2}
      sx={{ minWidth: 0 }}
      {...(readOnly ? { "data-ruta-historico-preview": "true" } : {})}
    >
      <RutaResumenHeaderCard
        title={readOnly ? "Resumen ruta histórico" : "Resumen de ruta"}
        subtitle={readOnly ? null : "Revisión final antes de publicar: equipos y direcciones se gestionan en Asignación."}
        chips={chips}
        summary={resumenIdentificacion}
        actions={headerActions}
      />

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
