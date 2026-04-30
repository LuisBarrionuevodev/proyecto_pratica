import AddIcon from "@mui/icons-material/Add";
import FolderOpenIcon from "@mui/icons-material/FolderOpen";
import PublishedWithChangesIcon from "@mui/icons-material/PublishedWithChanges";
import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  Divider,
  Stack,
  Tab,
  Tabs,
  Typography,
} from "@mui/material";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  InstitutionalMonthCalendarGrid,
  calendarDaysInMonth,
} from "../../../components/calendar/InstitutionalMonthCalendarGrid";
import { listRutasBorrador, listRutasTrabajo, type IRutaTrabajo } from "../../../api/rutasTrabajoApi";
import { GLASS_COLORS, glassSecondaryTabsSx } from "../../../styles/GlassStyles";
import { fechaLocalHoyIso, toIsoDateLocal } from "../../../utils/dateRange";
import { AppButton } from "../../../ui";
import {
  planificacionPanelSubtitleSx,
  rutasInstitutionalDividerSx,
  rutasInstitutionalResumenPaperSx,
  rutasResumenTitleSx,
} from "../styles/institutionalVisual";

const tactic = '"Tactic Sans", sans-serif' as const;

const CONTENT_MAX = 960;

export type RutasListaTab = "borradores" | "publicadas";

function monthBoundsIso(mesAncla: Date): { desde: string; hasta: string } {
  const y = mesAncla.getFullYear();
  const m0 = mesAncla.getMonth();
  const dim = calendarDaysInMonth(y, m0);
  return {
    desde: toIsoDateLocal(new Date(y, m0, 1)),
    hasta: toIsoDateLocal(new Date(y, m0, dim)),
  };
}

function labelTurno(t: IRutaTrabajo["turno"]): string {
  if (t === "MANIANA") return "Mañana";
  if (t === "TARDE") return "Tarde";
  return t;
}

function labelFilaRuta(r: IRutaTrabajo): string {
  const fecha = r.fecha
    ? new Date(r.fecha + "T12:00:00").toLocaleDateString("es-AR", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
      })
    : "—";
  const estado = r.estado_ruta === "PUBLICADA" ? "" : ` · ${r.estado_ruta}`;
  return `Ruta ${r.numero} · ${fecha} · ${labelTurno(r.turno)}${estado}`;
}

function formatFechaLegible(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  if (!y || !m || !d) return iso;
  try {
    return new Intl.DateTimeFormat("es-AR", {
      weekday: "long",
      day: "2-digit",
      month: "long",
      year: "numeric",
    }).format(new Date(y, m - 1, d));
  } catch {
    return iso;
  }
}

async function fetchAllRutasInMonth(params: {
  tab: RutasListaTab;
  desde: string;
  hasta: string;
}): Promise<IRutaTrabajo[]> {
  const per = 100;
  const all: IRutaTrabajo[] = [];
  let page = 1;
  let total = 0;
  do {
    const resp =
      params.tab === "borradores"
        ? await listRutasBorrador({
            fecha_desde: params.desde,
            fecha_hasta: params.hasta,
            page,
            per_page: per,
          })
        : await listRutasTrabajo({
            estado_ruta: "PUBLICADA",
            fecha_desde: params.desde,
            fecha_hasta: params.hasta,
            page,
            per_page: per,
          });
    const chunk = resp.items ?? [];
    all.push(...chunk);
    total = resp.meta?.total ?? 0;
    if (chunk.length === 0) break;
    page += 1;
  } while (all.length < total && page <= 25);
  return all;
}

export type RutasEmptyViewProps = {
  /** Crear borrador; si se pasa `fecha`, el modal puede abrir con esa fecha. */
  onCrearBorrador: (opts?: { fecha?: string }) => void;
  onAbrirRuta: (rutaId: number) => void;
};

const principalGlassSurfaceSx = {
  ...rutasInstitutionalResumenPaperSx,
  width: "100%",
  maxWidth: CONTENT_MAX,
  mx: "auto",
  boxSizing: "border-box" as const,
};

/**
 * Entrada al módulo sin ruta en sesión: slices Borradores / Publicadas + almanaque mensual (misma grilla
 * que Completar trabajo) y listado por día seleccionado (varias rutas por día).
 */
export function RutasEmptyView({ onCrearBorrador, onAbrirRuta }: RutasEmptyViewProps) {
  const [tab, setTab] = useState<RutasListaTab>("borradores");
  const [calMes, setCalMes] = useState(() => {
    const n = new Date();
    return new Date(n.getFullYear(), n.getMonth(), 1);
  });
  const [selectedIso, setSelectedIso] = useState<string>(() => fechaLocalHoyIso());

  const [itemsMes, setItemsMes] = useState<IRutaTrabajo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { desde, hasta } = useMemo(() => monthBoundsIso(calMes), [calMes]);

  const cargarMes = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const all = await fetchAllRutasInMonth({ tab, desde, hasta });
      setItemsMes(all);
      setSelectedIso((prev) => {
        if (prev >= desde && prev <= hasta) return prev;
        const hoy = fechaLocalHoyIso();
        if (hoy >= desde && hoy <= hasta) return hoy;
        return desde;
      });
    } catch {
      setItemsMes([]);
      setError(
        tab === "borradores"
          ? "No se pudieron cargar los borradores del mes."
          : "No se pudieron cargar las rutas publicadas del mes."
      );
    } finally {
      setLoading(false);
    }
  }, [tab, desde, hasta]);

  useEffect(() => {
    void cargarMes();
  }, [cargarMes]);

  const countPorDia = useMemo(() => {
    const m = new Map<string, number>();
    for (const r of itemsMes) {
      const f = r.fecha;
      if (!f) continue;
      m.set(f, (m.get(f) ?? 0) + 1);
    }
    return m;
  }, [itemsMes]);

  const rutasDelDiaSeleccionado = useMemo(() => {
    return itemsMes
      .filter((r) => r.fecha === selectedIso)
      .sort((a, b) => (b.numero ?? 0) - (a.numero ?? 0) || b.id - a.id);
  }, [itemsMes, selectedIso]);

  const hoyIso = fechaLocalHoyIso();

  return (
    <Stack spacing={2.25} sx={{ width: "100%", maxWidth: CONTENT_MAX, mx: "auto", alignItems: "stretch" }}>
      <Box sx={{ ...principalGlassSurfaceSx, p: 0, overflow: "hidden" }}>
        <Box sx={{ borderBottom: `1px solid ${GLASS_COLORS.borderLight}`, px: 0.5, pt: 0.25 }}>
          <Tabs
            value={tab}
            onChange={(_, v) => setTab(v as RutasListaTab)}
            variant="fullWidth"
            sx={glassSecondaryTabsSx}
          >
            <Tab label="Borradores" value="borradores" sx={{ fontFamily: tactic, fontWeight: 600, textTransform: "none" }} />
            <Tab label="Publicadas" value="publicadas" sx={{ fontFamily: tactic, fontWeight: 600, textTransform: "none" }} />
          </Tabs>
        </Box>
        <Stack spacing={2} sx={{ p: 2.25 }}>
          <Typography sx={rutasResumenTitleSx}>Rutas de trabajo</Typography>
          <Typography sx={{ ...planificacionPanelSubtitleSx, fontSize: "0.8125rem", color: GLASS_COLORS.textSecondary }}>
            {tab === "borradores"
              ? "Planificá la semana: elegí un día en el calendario y abrí o creá borradores para esa fecha."
              : "Consultá rutas ya publicadas por día. Al abrir una verás el detalle y el mapa operativo (solo lectura si ya no es borrador)."}
          </Typography>
        </Stack>
      </Box>

      <Box sx={principalGlassSurfaceSx}>
        <Stack spacing={1.75}>
          <Typography sx={rutasResumenTitleSx}>{tab === "borradores" ? "Almanaque — borradores" : "Almanaque — publicadas"}</Typography>
          {loading ? (
            <Box sx={{ display: "flex", justifyContent: "center", py: 3 }}>
              <CircularProgress size={32} sx={{ color: GLASS_COLORS.primary }} />
            </Box>
          ) : null}
          {error ? (
            <Alert severity="error" variant="outlined" sx={{ borderRadius: 2, fontFamily: tactic }}>
              {error}
              <Box sx={{ mt: 1 }}>
                <AppButton dsVariant="ghost" dsSize="sm" onClick={() => void cargarMes()}>
                  Reintentar
                </AppButton>
              </Box>
            </Alert>
          ) : null}
          {!loading && !error ? (
            <InstitutionalMonthCalendarGrid
              monthAnchor={calMes}
              onMonthChange={setCalMes}
              hoyIso={hoyIso}
              selectedIso={selectedIso}
              onSelectDay={setSelectedIso}
              aria-label={
                tab === "borradores"
                  ? "Calendario de borradores: días con actividad y cantidad de rutas"
                  : "Calendario de rutas publicadas por día"
              }
              getDayTitle={(ctx) => {
                const n = countPorDia.get(ctx.iso) ?? 0;
                if (n === 0) return tab === "borradores" ? "Sin borradores este día" : "Sin rutas publicadas este día";
                return n === 1 ? "1 ruta este día" : `${n} rutas este día`;
              }}
              getDayButtonSx={(ctx) => {
                const n = countPorDia.get(ctx.iso) ?? 0;
                if (n > 0) {
                  return {
                    border: `1px solid ${GLASS_COLORS.borderActive}`,
                    bgcolor: "rgba(1, 102, 255, 0.1)",
                  };
                }
                return {};
              }}
              renderDayFooter={(ctx) => {
                const n = countPorDia.get(ctx.iso) ?? 0;
                if (n === 0) return undefined;
                if (n === 1) {
                  return (
                    <Box
                      component="span"
                      sx={{
                        width: 6,
                        height: 6,
                        borderRadius: "50%",
                        bgcolor: GLASS_COLORS.primary,
                        opacity: 0.9,
                      }}
                    />
                  );
                }
                return (
                  <Chip
                    size="small"
                    label={String(n)}
                    sx={{
                      height: 18,
                      minWidth: 22,
                      fontSize: "0.65rem",
                      fontFamily: tactic,
                      fontWeight: 700,
                      borderColor: GLASS_COLORS.borderActive,
                      color: GLASS_COLORS.textPrimary,
                      bgcolor: "rgba(1, 102, 255, 0.16)",
                    }}
                    variant="outlined"
                  />
                );
              }}
            />
          ) : null}
        </Stack>
      </Box>

      <Box sx={principalGlassSurfaceSx}>
        <Stack spacing={1.5}>
          <Typography sx={rutasResumenTitleSx}>Rutas del día</Typography>
          <Typography
            sx={{
              ...planificacionPanelSubtitleSx,
              fontSize: "0.875rem",
              color: GLASS_COLORS.textSecondary,
              textTransform: "capitalize",
            }}
          >
            {formatFechaLegible(selectedIso)}
          </Typography>
          <Divider sx={rutasInstitutionalDividerSx} />

          {rutasDelDiaSeleccionado.length === 0 ? (
            <Typography sx={{ fontFamily: tactic, fontSize: "0.8125rem", color: GLASS_COLORS.textMuted }}>
              {tab === "borradores"
                ? "No hay borradores para esta fecha. Podés crear uno nuevo."
                : "No hay rutas publicadas para esta fecha."}
            </Typography>
          ) : (
            <Stack spacing={1} sx={{ maxHeight: 320, overflowY: "auto", pr: 0.5 }}>
              {rutasDelDiaSeleccionado.map((r) => (
                <AppButton
                  key={r.id}
                  dsVariant="secondary"
                  dsSize="md"
                  fullWidth
                  startIcon={tab === "borradores" ? <FolderOpenIcon /> : <PublishedWithChangesIcon />}
                  onClick={() => onAbrirRuta(r.id)}
                  sx={{
                    fontFamily: tactic,
                    fontWeight: 600,
                    justifyContent: "flex-start",
                    textAlign: "left",
                  }}
                >
                  {labelFilaRuta(r)}
                </AppButton>
              ))}
            </Stack>
          )}

          {tab === "borradores" ? (
            <AppButton
              dsVariant="primary"
              dsSize="md"
              fullWidth
              startIcon={<AddIcon />}
              onClick={() => onCrearBorrador({ fecha: selectedIso })}
              sx={{ fontFamily: tactic, fontWeight: 700, mt: 0.5 }}
            >
              Crear ruta para este día
            </AppButton>
          ) : null}
        </Stack>
      </Box>
    </Stack>
  );
}
