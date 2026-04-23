import { useCallback, useEffect, useRef } from "react";
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
import { printMapaFinalGruposOperativo } from "../utils/exportMapaFinalGruposPrint";
import { buildMapaFinalCapturaFilename, downloadMapaFinalRegionPng } from "../utils/exportMapaFinalCaptura";
import { AppButton } from "../../../ui/AppButton";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

function turnoLabel(t: string) {
  return t === "MANIANA" ? "Mañana" : t === "TARDE" ? "Tarde" : t;
}

function estadoRutaVisible(estado: string | undefined): string | null {
  if (!estado?.trim()) return null;
  const e = estado.trim();
  if (e === "BORRADOR") return "Borrador";
  if (e === "PUBLICADA") return "Publicada";
  return e
    .split("_")
    .filter(Boolean)
    .map((w) => w.charAt(0) + w.slice(1).toLowerCase())
    .join(" ");
}

const MAPA_FINAL_SECTION_LABEL_SX = {
  fontFamily: '"Tactic Sans", sans-serif',
  fontSize: "0.65rem",
  fontWeight: 600,
  letterSpacing: "0.08em",
  textTransform: "uppercase" as const,
  color: GLASS_COLORS.textMuted,
  mb: 1,
};

const HISTORICO_ALERT_SX = {
  ...rutasInstitutionalAlertBaseSx,
  borderColor: "rgba(100, 180, 255, 0.35)",
  "& .MuiAlert-icon": { color: "info.light" },
  "& .MuiAlert-message": { fontSize: "0.875rem", lineHeight: 1.45 },
} as const;

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

  const chipOutlineSx = {
    fontSize: "0.7rem",
    borderColor: GLASS_COLORS.borderLight,
    color: GLASS_COLORS.textSecondary,
    backgroundColor: "rgba(255,255,255,0.03)",
  } as const;

  const chipEstadoSx = {
    ...chipOutlineSx,
    fontWeight: 600,
    color: GLASS_COLORS.textPrimary,
    borderColor: GLASS_COLORS.borderMedium,
  } as const;

  const estadoLabel = ruta ? estadoRutaVisible(ruta.estado_ruta) : null;
  const puedeEditarEquipos = Boolean(!vistaHistoricaReadOnly && ruta?.estado_ruta === "BORRADOR" && !detailLoading);
  const readOnly = Boolean(vistaHistoricaReadOnly);

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

  /** En histórico no se registran handles de captura/impresión (evita uso accidental; PR futuro re-asignará desde aquí). */
  useEffect(() => {
    if (readOnly || !capturaMapaFinalRef) return;
    capturaMapaFinalRef.current = ejecutarCapturaMapaFinal;
    return () => {
      capturaMapaFinalRef.current = null;
    };
  }, [readOnly, capturaMapaFinalRef, ejecutarCapturaMapaFinal]);

  useEffect(() => {
    if (readOnly || !exportGruposPrintRef) return;
    exportGruposPrintRef.current = ejecutarExportGruposPrint;
    return () => {
      exportGruposPrintRef.current = null;
    };
  }, [readOnly, exportGruposPrintRef, ejecutarExportGruposPrint]);

  useEffect(() => {
    if (!readOnly) return;
    if (capturaMapaFinalRef) capturaMapaFinalRef.current = null;
    if (exportGruposPrintRef) exportGruposPrintRef.current = null;
  }, [readOnly, capturaMapaFinalRef, exportGruposPrintRef]);

  return (
    <Stack spacing={2}>
      <Paper elevation={0} sx={rutasInstitutionalPanelPaperSx}>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems={{ sm: "flex-start" }} justifyContent="space-between">
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography sx={{ ...rutasResumenTitleSx, fontSize: "1.0625rem", letterSpacing: "0.04em" }}>
              {readOnly ? "Consulta histórica · Mapa operativo" : "Mapa final"}
            </Typography>
            <Typography
              sx={{
                ...planificacionPanelSubtitleSx,
                mt: 0.35,
                fontSize: "0.72rem",
                color: GLASS_COLORS.textMuted,
                maxWidth: 520,
              }}
            >
              {readOnly
                ? "Resumen de la ruta tal como quedó registrada. Solo lectura: no se puede editar ni volver a publicar desde aquí."
                : "Revisión final antes de publicar: equipos y direcciones se gestionan en Asignación."}
            </Typography>
            {ruta && (
              <Stack direction="row" flexWrap="wrap" gap={0.75} sx={{ mt: 1.25 }} alignItems="center">
                {estadoLabel && <Chip size="small" variant="outlined" label={estadoLabel} sx={chipEstadoSx} />}
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
            sx={{
              width: { xs: "100%", sm: "auto" },
              flexShrink: 0,
              alignItems: { sm: "stretch" },
            }}
          >
            {readOnly ? (
              <AppButton
                dsVariant="primary"
                dsSize="md"
                fullWidth
                onClick={() => onVolverAlListado?.()}
                sx={{ minWidth: { sm: 200 }, fontWeight: 700 }}
              >
                Volver al listado
              </AppButton>
            ) : (
              <>
                <AppButton dsVariant="secondary" dsSize="md" fullWidth onClick={onVolverAsignacion} sx={{ minWidth: { sm: 180 } }}>
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
                  <span style={{ width: "100%", display: "inline-flex" }}>
                    <AppButton
                      dsVariant="primary"
                      dsSize="md"
                      fullWidth
                      loading={publishingRuta}
                      disabled={!canPublish}
                      onClick={() => void onPublicarRuta?.()}
                      sx={{
                        minWidth: { sm: 160 },
                        fontWeight: 700,
                        boxShadow: canPublish && !publishingRuta ? (t) => `0 0 0 1px ${t.palette.primary.dark}40` : undefined,
                      }}
                    >
                      {publishingRuta ? "Publicando…" : "Publicar"}
                    </AppButton>
                  </span>
                </Tooltip>
              </>
            )}
          </Stack>
        </Stack>
      </Paper>

      {readOnly && (
        <Alert severity="info" sx={HISTORICO_ALERT_SX}>
          <strong>Solo consulta.</strong> Esta ruta ya no está en borrador: el mapa y el panel lateral son un registro operativo
          para consulta. Las acciones de planificación, asignación y publicación no están disponibles en esta vista.
        </Alert>
      )}

      <Stack
        ref={exportOperativoRef}
        spacing={2}
        sx={{ minWidth: 0 }}
        {...(readOnly ? { "data-ruta-historico-preview": "true" } : {})}
      >
        <Paper elevation={0} sx={{ ...rutasInstitutionalPanelPaperSx, py: 1.25, px: 2 }}>
          <Typography sx={MAPA_FINAL_SECTION_LABEL_SX}>
            {readOnly ? "Identificación de la ruta (historial)" : "Resumen para respaldo"}
          </Typography>
          {ruta ? (
            <Typography
              component="div"
              variant="body2"
              sx={{
                mt: 0.5,
                fontSize: "0.8125rem",
                lineHeight: 1.45,
                color: GLASS_COLORS.textSecondary,
                fontWeight: 500,
              }}
            >
              <Box component="span" sx={{ color: GLASS_COLORS.textPrimary, fontWeight: 700 }}>
                Ruta {ruta.numero}
              </Box>
              <Box component="span" sx={{ opacity: 0.85 }}>{` · id ${ruta.id}`}</Box>
              <Box component="span" sx={{ opacity: 0.85 }}>{` · ${ruta.fecha}`}</Box>
              <Box component="span" sx={{ opacity: 0.85 }}>{` · ${turnoLabel(ruta.turno)}`}</Box>
              {ruta.display_name != null && ruta.display_name !== "" ? (
                <Box component="span" sx={{ opacity: 0.85 }}>{` · ${ruta.display_name}`}</Box>
              ) : null}
              <Box component="span" sx={{ opacity: 0.85 }}>
                {" · Estado registrado: "}
                <Box component="span" ref={estadoCapturaRef} sx={{ color: GLASS_COLORS.textPrimary, fontWeight: 700 }}>
                  {estadoLabel ?? "—"}
                </Box>
              </Box>
            </Typography>
          ) : (
            <Typography sx={{ ...planificacionPanelSubtitleSx, fontSize: "0.8125rem", color: GLASS_COLORS.textSecondary, mt: 0.5 }}>
              Sin ruta cargada.
            </Typography>
          )}
        </Paper>

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
                  onEditarInspectores={readOnly ? undefined : onEditarInspectores}
                  puedeEditarEquipos={puedeEditarEquipos}
                  readOnly={readOnly}
                />
              )}
            </Box>
          </Paper>
        </Stack>
      </Stack>
    </Stack>
  );
}
