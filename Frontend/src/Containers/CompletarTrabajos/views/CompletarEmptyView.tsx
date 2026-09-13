import { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, Box, CircularProgress, Stack, Typography } from "@mui/material";

import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { fechaLocalHoyIso, toIsoDateLocal } from "../../../utils/dateRange";
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
import { pendientesFooterLabel } from "../utils/completarTrabajoCalendarDisplay";

const TACTIC = '"Tactic Sans", sans-serif' as const;

const COMPLETAR_CONTENT_MAX_PX = 1400;
const COMPLETAR_CALENDAR_CELL_MIN_HEIGHT = 56;

const completarCalendarPanelSurfaceSx = {
  ...rutasInstitutionalResumenPaperSx,
  width: "100%",
  maxWidth: COMPLETAR_CONTENT_MAX_PX,
  mx: "auto",
  boxSizing: "border-box" as const,
};

const pendientesFooterSx = {
  fontFamily: TACTIC,
  fontSize: "0.68rem",
  fontWeight: 600,
  lineHeight: 1.2,
  color: "inherit",
  textAlign: "center" as const,
  px: 0.25,
};

function compareIso(a: string, b: string): number {
  return a.localeCompare(b);
}

function isoInRange(iso: string, desde: string, hasta: string): boolean {
  return compareIso(iso, desde) >= 0 && compareIso(iso, hasta) <= 0;
}

function defaultResumenRango(): { desde: string; hasta: string } {
  const hoy = new Date();
  const desdeDt = new Date(hoy);
  desdeDt.setDate(desdeDt.getDate() - 45);
  const hastaDt = new Date(hoy);
  hastaDt.setDate(hastaDt.getDate() + 30);
  return { desde: toIsoDateLocal(desdeDt), hasta: toIsoDateLocal(hastaDt) };
}

function buildDiasMap(dias: ICompletarTrabajoPendienteDiaResumen[]): Map<string, ICompletarTrabajoPendienteDiaResumen> {
  const m = new Map<string, ICompletarTrabajoPendienteDiaResumen>();
  for (const d of dias) m.set(d.fecha, d);
  return m;
}

type DiaCeldaEstado = "atrasado" | "pendiente" | "completo" | "sin_actividad" | "sin_dato_fuera";

/** Prioriza `categoria_calendario` del API; fallback solo si el campo no viene (API vieja). */
function categoriaCalendarioDesdeRow(row: ICompletarTrabajoPendienteDiaResumen): "CON_PENDIENTES" | "COMPLETO" {
  const c = row.categoria_calendario;
  if (c === "COMPLETO" || c === "CON_PENDIENTES") return c;
  return row.total > 0 ? "CON_PENDIENTES" : "COMPLETO";
}

/**
 * Estado visual de celda alineado al contrato del resumen:
 * - fila `CON_PENDIENTES` → pendiente / atrasado según `atrasado`
 * - fila `COMPLETO` → completo
 * - sin fila y fecha en [desde, hasta] → sin actividad
 * - sin fila y fuera del rango → sin dato
 */
function estadoCeldaCalendario(
  iso: string,
  diasMap: Map<string, ICompletarTrabajoPendienteDiaResumen>,
  desde: string,
  hasta: string
): DiaCeldaEstado {
  const row = diasMap.get(iso);
  if (row) {
    const cat = categoriaCalendarioDesdeRow(row);
    if (cat === "COMPLETO") return "completo";
    return row.atrasado ? "atrasado" : "pendiente";
  }
  if (isoInRange(iso, desde, hasta)) return "sin_actividad";
  return "sin_dato_fuera";
}

function titleCeldaCalendario(est: DiaCeldaEstado): string {
  switch (est) {
    case "atrasado":
      return "Pendientes de cierre — día atrasado";
    case "pendiente":
      return "Pendientes de cierre";
    case "completo":
      return "Actividad en ruta publicada, sin pendientes de cierre";
    case "sin_actividad":
      return "Sin actividad en Completar trabajo (sin ítems con actuación en ruta publicada este día)";
    case "sin_dato_fuera":
      return "Fuera del período del resumen cargado";
  }
}

/**
 * Entrada al módulo: calendario operativo como selector principal de jornada.
 */
export function CompletarEmptyView({ initialFecha, onVerTrabajos }: CompletarTrabajosEmptyProps) {
  const hoyLocal = fechaLocalHoyIso();
  const defaultSeleccion = initialFecha ?? hoyLocal;

  const rango = useMemo(() => defaultResumenRango(), []);

  const [dias, setDias] = useState<ICompletarTrabajoPendienteDiaResumen[]>([]);
  const [metaResumen, setMetaResumen] = useState<{ desde: string; hasta: string; hoy: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [calMes, setCalMes] = useState(() => {
    const n = new Date();
    return new Date(n.getFullYear(), n.getMonth(), 1);
  });
  const [selectedCalDay, setSelectedCalDay] = useState<string | null>(defaultSeleccion);

  const diasMap = useMemo(() => buildDiasMap(dias), [dias]);

  const cargarResumen = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getCompletarTrabajoPendientesResumen({
        fecha_desde: rango.desde,
        fecha_hasta: rango.hasta,
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
  }, [rango.desde, rango.hasta]);

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
  const rangoDesde = metaResumen?.desde ?? rango.desde;
  const rangoHasta = metaResumen?.hasta ?? rango.hasta;

  return (
    <Stack spacing={2} sx={{ width: "100%", maxWidth: COMPLETAR_CONTENT_MAX_PX, mx: "auto" }}>
      <Box sx={completarCalendarPanelSurfaceSx}>
        <Stack spacing={2}>
          <Typography sx={rutasResumenTitleSx}>Calendario operativo</Typography>

          {loading ? (
            <Box sx={{ display: "flex", justifyContent: "center", py: 5 }}>
              <CircularProgress size={36} />
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
                cellGap={0.75}
                aria-label="Calendario operativo: pendiente, completo o sin actividad según el resumen del servidor"
                getDayTitle={(ctx) => {
                  const est = estadoCeldaCalendario(ctx.iso, diasMap, rangoDesde, rangoHasta);
                  const pendientes = pendientesFooterLabel(diasMap.get(ctx.iso));
                  const base = titleCeldaCalendario(est);
                  return pendientes ? `${base} — ${pendientes}` : base;
                }}
                getDayButtonSx={(ctx) => {
                  const est = estadoCeldaCalendario(ctx.iso, diasMap, rangoDesde, rangoHasta);
                  const bg =
                    est === "atrasado"
                      ? "rgba(211, 47, 47, 0.14)"
                      : est === "pendiente"
                        ? "rgba(255, 152, 0, 0.12)"
                        : est === "completo"
                          ? "rgba(56, 142, 60, 0.12)"
                          : "rgba(255,255,255,0.025)";
                  const border =
                    est === "atrasado"
                      ? "1px solid rgba(255, 138, 128, 0.5)"
                      : est === "pendiente"
                        ? "1px solid rgba(255, 183, 77, 0.38)"
                        : est === "completo"
                          ? "1px solid rgba(129, 199, 132, 0.35)"
                          : `1px solid ${GLASS_COLORS.borderLight}`;
                  return {
                    bgcolor: bg,
                    border,
                    color: "#FFFFFF",
                    minHeight: COMPLETAR_CALENDAR_CELL_MIN_HEIGHT,
                    "&:hover": {
                      bgcolor:
                        est === "sin_actividad" || est === "sin_dato_fuera"
                          ? "rgba(255,255,255,0.05)"
                          : "rgba(255,255,255,0.06)",
                    },
                  };
                }}
                renderDayFooter={(ctx) => {
                  const label = pendientesFooterLabel(diasMap.get(ctx.iso));
                  if (!label) return undefined;
                  return <Typography component="span" sx={pendientesFooterSx}>{label}</Typography>;
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
