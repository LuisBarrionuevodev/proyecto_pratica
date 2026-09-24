import { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, Box, CircularProgress, Stack, Typography } from "@mui/material";

import { fechaLocalHoyIso } from "../../../utils/dateRange";
import { InstitutionalMonthCalendarGrid } from "../../../components/calendar/InstitutionalMonthCalendarGrid";
import {
  getCompletarTrabajoPendientesResumen,
  type ICompletarTrabajoPendienteDiaResumen,
} from "../../../api/completarTrabajoApi";
import { AppButton } from "../../../ui";
import {
  rutasInstitutionalResumenPaperSx,
  rutasResumenTitleSx,
} from "../../RutasTrabajo/styles/institutionalVisual";
import type { CompletarTrabajosEmptyProps } from "../types";
import {
  completarCeldaSurfaceSx,
  completarCeldaTitle,
  completarPendingFooterSx,
  monthBoundsIso,
  pendientesFooterLabel,
  resolvePendienteCeldaTono,
} from "../utils/completarTrabajoCalendarDisplay";

const COMPLETAR_CONTENT_MAX_PX = 1400;
const COMPLETAR_CALENDAR_CELL_MIN_HEIGHT = 72;
const COMPLETAR_CALENDAR_CELL_GAP = 1;

const completarCalendarPanelSurfaceSx = {
  ...rutasInstitutionalResumenPaperSx,
  width: "100%",
  maxWidth: COMPLETAR_CONTENT_MAX_PX,
  mx: "auto",
  boxSizing: "border-box" as const,
  p: { xs: 2.5, md: 3.5 },
};

function buildDiasMap(dias: ICompletarTrabajoPendienteDiaResumen[]): Map<string, ICompletarTrabajoPendienteDiaResumen> {
  const m = new Map<string, ICompletarTrabajoPendienteDiaResumen>();
  for (const d of dias) m.set(d.fecha, d);
  return m;
}

/**
 * Entrada al módulo: calendario operativo como selector principal de jornada.
 * El resumen se carga por mes visible (evita dataset stale al navegar meses anteriores).
 */
export function CompletarEmptyView({ initialFecha, onVerTrabajos }: CompletarTrabajosEmptyProps) {
  const hoyLocal = fechaLocalHoyIso();
  const defaultSeleccion = initialFecha ?? hoyLocal;

  const [dias, setDias] = useState<ICompletarTrabajoPendienteDiaResumen[]>([]);
  const [metaResumen, setMetaResumen] = useState<{ desde: string; hasta: string; hoy: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [calMes, setCalMes] = useState(() => {
    const anchor = defaultSeleccion ? new Date(`${defaultSeleccion}T12:00:00`) : new Date();
    return new Date(anchor.getFullYear(), anchor.getMonth(), 1);
  });
  const [selectedCalDay, setSelectedCalDay] = useState<string | null>(defaultSeleccion);

  const mesVisible = useMemo(() => monthBoundsIso(calMes), [calMes]);
  const diasMap = useMemo(() => buildDiasMap(dias), [dias]);

  const cargarResumen = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getCompletarTrabajoPendientesResumen({
        fecha_desde: mesVisible.desde,
        fecha_hasta: mesVisible.hasta,
      });
      setDias(res.dias ?? []);
      setMetaResumen({
        desde: res.meta.fecha_desde,
        hasta: res.meta.fecha_hasta,
        hoy: res.meta.hoy,
      });
    } catch (e: unknown) {
      const msg =
        e && typeof e === "object" && "response" in e
          ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : null;
      setError(msg || "No se pudo cargar el resumen.");
      setDias([]);
      setMetaResumen(null);
    } finally {
      setLoading(false);
    }
  }, [mesVisible.desde, mesVisible.hasta]);

  useEffect(() => {
    void cargarResumen();
  }, [cargarResumen]);

  const abrirGrid = useCallback(
    (fechaIso: string) => {
      onVerTrabajos?.(fechaIso);
    },
    [onVerTrabajos]
  );

  const hoyIso = metaResumen?.hoy ?? hoyLocal;

  return (
    <Stack spacing={2} sx={{ width: "100%", maxWidth: COMPLETAR_CONTENT_MAX_PX, mx: "auto", px: { xs: 0.5, md: 1 } }}>
      <Box sx={completarCalendarPanelSurfaceSx}>
        <Stack spacing={2.5}>
          <Typography sx={rutasResumenTitleSx}>Calendario operativo</Typography>

          {loading ? (
            <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
              <CircularProgress size={40} />
            </Box>
          ) : null}

          {error ? (
            <Alert severity="error" variant="outlined" sx={{ borderRadius: 2 }}>
              {error}
              <Box sx={{ mt: 1 }}>
                <AppButton dsVariant="ghost" dsSize="sm" onClick={() => void cargarResumen()}>
                  Reintentar
                </AppButton>
              </Box>
            </Alert>
          ) : null}

          {!loading && !error ? (
            <>
              <InstitutionalMonthCalendarGrid
                monthAnchor={calMes}
                onMonthChange={setCalMes}
                hoyIso={hoyIso}
                selectedIso={selectedCalDay}
                onSelectDay={setSelectedCalDay}
                cellMinHeight={COMPLETAR_CALENDAR_CELL_MIN_HEIGHT}
                cellGap={COMPLETAR_CALENDAR_CELL_GAP}
                aria-label="Calendario operativo: verde sin pendientes, amarillo 1 a 5, rojo 6 o más"
                getDayTitle={(ctx) => {
                  const row = diasMap.get(ctx.iso);
                  const tono = resolvePendienteCeldaTono(row);
                  const pendientes = pendientesFooterLabel(row);
                  return completarCeldaTitle(tono, pendientes);
                }}
                getDayButtonSx={(ctx) => {
                  const row = diasMap.get(ctx.iso);
                  const tono = resolvePendienteCeldaTono(row);
                  const surface = completarCeldaSurfaceSx(tono);
                  return {
                    bgcolor: surface.bgcolor,
                    border: surface.border,
                    color: "#FFFFFF",
                    minHeight: COMPLETAR_CALENDAR_CELL_MIN_HEIGHT,
                    "&:hover": {
                      bgcolor:
                        tono === "neutral"
                          ? "rgba(255,255,255,0.05)"
                          : "rgba(255,255,255,0.07)",
                    },
                  };
                }}
                renderDayFooter={(ctx) => {
                  const label = pendientesFooterLabel(diasMap.get(ctx.iso));
                  if (!label) return undefined;
                  return (
                    <Typography component="span" sx={completarPendingFooterSx}>
                      {label}
                    </Typography>
                  );
                }}
              />
              <Stack
                direction={{ xs: "column", sm: "row" }}
                spacing={1.25}
                alignItems={{ xs: "stretch", sm: "center" }}
                sx={{ mt: 0.5 }}
              >
                <AppButton
                  dsVariant="primary"
                  dsSize="lg"
                  onClick={() => selectedCalDay && abrirGrid(selectedCalDay)}
                  disabled={!selectedCalDay}
                  sx={{
                    alignSelf: { xs: "stretch", sm: "flex-start" },
                    minWidth: { sm: 280 },
                  }}
                >
                  Ir a la grilla del día
                </AppButton>
              </Stack>
            </>
          ) : null}
        </Stack>
      </Box>
    </Stack>
  );
}
