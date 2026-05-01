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
import { GLASS_COLORS, glassSecondaryTabsSx, glassTabsSecondaryPanelBarSx } from "../../../styles/GlassStyles";
import { fechaLocalHoyIso, toIsoDateLocal } from "../../../utils/dateRange";
import { AppButton } from "../../../ui";
import {
  rutasInstitutionalDividerSx,
  rutasInstitutionalResumenPaperSx,
  rutasResumenTitleSx,
} from "../styles/institutionalVisual";

const tactic = '"Tactic Sans", sans-serif' as const;

/** Misma anchura y superficie que `CompletarEmptyView` → `principalGlassSurfaceSx`. */
const MODULE_CONTENT_MAX_PX = 1400;

const shellStackSx = {
  width: "100%",
  maxWidth: MODULE_CONTENT_MAX_PX,
  mx: "auto",
  boxSizing: "border-box" as const,
};

/** Copia del bloque calendario de Completar trabajo (`principalGlassSurfaceSx`). */
const calendarPanelSurfaceSx = {
  ...rutasInstitutionalResumenPaperSx,
  width: "100%",
  maxWidth: MODULE_CONTENT_MAX_PX,
  mx: "auto",
  boxSizing: "border-box" as const,
};

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

/** Fila de listado: sin repetir la fecha del día (ya va en el header). */
function labelFilaRutaListado(r: IRutaTrabajo): string {
  const estado = r.estado_ruta === "PUBLICADA" ? "" : ` · ${r.estado_ruta}`;
  return `Ruta ${r.numero} · ${labelTurno(r.turno)}${estado}`;
}

/** Fecha compacta para la banda superior (derecha). */
function formatoFechaHeader(iso: string | null): string {
  if (iso == null || iso === "") return "—";
  const [y, m, d] = iso.split("-").map(Number);
  if (!y || !m || !d) return iso;
  try {
    return new Intl.DateTimeFormat("es-AR", {
      weekday: "short",
      day: "numeric",
      month: "short",
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
  onCrearBorrador: (opts?: { fecha?: string }) => void;
  onAbrirRuta: (rutaId: number) => void;
};

const tabsHeaderRowSx = {
  ...glassTabsSecondaryPanelBarSx,
  width: "100%",
  boxSizing: "border-box" as const,
  borderRadius: 0,
  border: "none",
  borderBottom: `1px solid ${GLASS_COLORS.borderLight}`,
  p: 0,
  py: 1,
  px: 1.25,
  display: "flex",
  flexDirection: "row",
  alignItems: "center",
  gap: 1,
  flexWrap: "nowrap",
} as const;

const countChipSx = {
  height: 18,
  minWidth: 22,
  fontSize: "0.65rem",
  fontFamily: tactic,
  fontWeight: 700,
  borderColor: GLASS_COLORS.borderActive,
  color: GLASS_COLORS.textPrimary,
  bgcolor: "rgba(1, 102, 255, 0.16)",
} as const;

/**
 * Entrada sin ruta: box superior (tabs + fecha a la derecha), box inferior (misma superficie que Completar trabajo).
 */
export function RutasEmptyView({ onCrearBorrador, onAbrirRuta }: RutasEmptyViewProps) {
  const [tab, setTab] = useState<RutasListaTab>("borradores");
  const [calMes, setCalMes] = useState(() => {
    const n = new Date();
    return new Date(n.getFullYear(), n.getMonth(), 1);
  });
  const [selectedIso, setSelectedIso] = useState<string | null>(null);

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
        if (prev != null && prev >= desde && prev <= hasta) return prev;
        const hoy = fechaLocalHoyIso();
        if (hoy >= desde && hoy <= hasta) return hoy;
        return null;
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
    if (selectedIso == null) return [];
    return itemsMes
      .filter((r) => r.fecha === selectedIso)
      .sort((a, b) => (b.numero ?? 0) - (a.numero ?? 0) || b.id - a.id);
  }, [itemsMes, selectedIso]);

  const hoyIso = fechaLocalHoyIso();
  const calendarioTitulo = tab === "borradores" ? "Calendario · Planificación" : "Calendario · Publicadas";
  const diaSeleccionadoListo = selectedIso != null && selectedIso >= desde && selectedIso <= hasta;

  return (
    <Stack spacing={2.25} sx={{ ...shellStackSx, alignItems: "stretch" }}>
      {/* Box superior: solo tabs + fecha a la derecha */}
      <Box
        sx={{
          ...rutasInstitutionalResumenPaperSx,
          ...shellStackSx,
          p: 0,
          overflow: "hidden",
        }}
      >
        <Box sx={tabsHeaderRowSx}>
          <Tabs
            value={tab}
            onChange={(_, v) => setTab(v as RutasListaTab)}
            variant="fullWidth"
            sx={{ ...glassSecondaryTabsSx, flex: 1, minWidth: 0 }}
          >
            <Tab label="Borradores" value="borradores" sx={{ fontFamily: tactic, fontWeight: 600, textTransform: "none" }} />
            <Tab label="Publicadas" value="publicadas" sx={{ fontFamily: tactic, fontWeight: 600, textTransform: "none" }} />
          </Tabs>
          <Typography
            sx={{
              flexShrink: 0,
              fontFamily: tactic,
              fontWeight: 700,
              fontSize: { xs: "0.75rem", sm: "0.8125rem" },
              color: diaSeleccionadoListo ? GLASS_COLORS.textPrimary : GLASS_COLORS.textMuted,
              textTransform: "capitalize",
              whiteSpace: "nowrap",
              maxWidth: { xs: "42%", sm: "38%" },
              textAlign: "right",
              lineHeight: 1.25,
            }}
            title={selectedIso ?? undefined}
          >
            {formatoFechaHeader(selectedIso)}
          </Typography>
        </Box>
      </Box>

      {/* Box inferior: mismo look que el panel calendario de Completar trabajo */}
      <Box sx={calendarPanelSurfaceSx}>
        <Stack spacing={1.5}>
          <Typography sx={rutasResumenTitleSx}>{calendarioTitulo}</Typography>

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
              onSelectDay={(iso) => setSelectedIso(iso)}
              aria-label={
                tab === "borradores" ? "Calendario de borradores por día" : "Calendario de rutas publicadas por día"
              }
              getDayTitle={(ctx) => {
                const n = countPorDia.get(ctx.iso) ?? 0;
                if (n === 0) return "Sin rutas este día";
                return n === 1 ? "1 ruta" : `${n} rutas`;
              }}
              getDayButtonSx={(ctx) => {
                const n = countPorDia.get(ctx.iso) ?? 0;
                if (n > 0) {
                  return {
                    border: `1px solid ${GLASS_COLORS.borderActive}`,
                    bgcolor: "rgba(1, 102, 255, 0.1)",
                    minHeight: 40,
                  };
                }
                return { minHeight: 40 };
              }}
              renderDayFooter={(ctx) => {
                const n = countPorDia.get(ctx.iso) ?? 0;
                if (n === 0) return undefined;
                return <Chip size="small" label={String(n)} sx={countChipSx} variant="outlined" />;
              }}
            />
          ) : null}

          {!loading && !error ? (
            <>
              <Divider sx={rutasInstitutionalDividerSx} />

              {rutasDelDiaSeleccionado.length === 0 ? (
                <Typography sx={{ fontFamily: tactic, fontSize: "0.8125rem", color: GLASS_COLORS.textMuted }}>
                  {selectedIso == null ? "Seleccioná un día en el calendario." : "Sin rutas para esta fecha."}
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
                      {labelFilaRutaListado(r)}
                    </AppButton>
                  ))}
                </Stack>
              )}

              {tab === "borradores" ? (
                <AppButton
                  dsVariant="primary"
                  dsSize="lg"
                  fullWidth
                  startIcon={<AddIcon />}
                  disabled={!diaSeleccionadoListo}
                  onClick={() => {
                    if (selectedIso) onCrearBorrador({ fecha: selectedIso });
                  }}
                  sx={{
                    fontFamily: tactic,
                    fontWeight: 700,
                    mt: 0.5,
                  }}
                >
                  Crear ruta para este día
                </AppButton>
              ) : null}
            </>
          ) : null}
        </Stack>
      </Box>
    </Stack>
  );
}
