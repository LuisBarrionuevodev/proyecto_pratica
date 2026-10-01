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
  Typography,
} from "@mui/material";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useTheme } from "@mui/material/styles";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  InstitutionalMonthCalendarGrid,
} from "../../../components/calendar/InstitutionalMonthCalendarGrid";
import {
  INSTITUTIONAL_CALENDAR_CELL_GAP,
  INSTITUTIONAL_CALENDAR_CELL_MIN_HEIGHT,
  institutionalCalendarPanelPadding,
} from "../../../components/calendar/institutionalCalendarLayout";
import { listRutasBorrador, listRutasTrabajo, type IRutaTrabajo } from "../../../api/rutasTrabajoApi";
import { monthBoundsIso } from "../../CompletarTrabajos/utils/completarTrabajoCalendarDisplay";
import { GLASS_COLORS, moduleSlicesTabsSx } from "../../../styles/GlassStyles";
import { fechaLocalHoyIso } from "../../../utils/dateRange";
import { AppButton, ResponsiveScrollableTabs } from "../../../ui";
import { layoutShell } from "../../../theme/tokens";
import { FONT_FAMILY_UI } from "../../../theme/typography";
import { RutasDiaRutaMobileCard } from "../Components/RutasDiaRutaMobileCard";
import {
  rutasInstitutionalDividerSx,
  rutasInstitutionalResumenPaperSx,
  rutasResumenTitleSx,
} from "../styles/institutionalVisual";
import { rutasLabelFilaRutaListado, type RutasListaTab } from "../utils/rutasEmptyViewDisplay";

/** Misma columna centrada que Completar trabajo (max 1400 px). */
const MODULE_CONTENT_MAX_PX = 1400;

const shellStackSx = {
  width: "100%",
  maxWidth: MODULE_CONTENT_MAX_PX,
  mx: "auto",
  boxSizing: "border-box" as const,
  minWidth: 0,
  px: { xs: 0.5, md: 1 },
};

const calendarPanelSurfaceSx = {
  ...rutasInstitutionalResumenPaperSx,
  p: institutionalCalendarPanelPadding,
  width: "100%",
  maxWidth: MODULE_CONTENT_MAX_PX,
  mx: "auto",
  boxSizing: "border-box" as const,
  minWidth: 0,
};

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

const countChipSx = {
  height: 18,
  minWidth: 22,
  fontSize: "0.65rem",
  fontFamily: FONT_FAMILY_UI,
  fontWeight: 700,
  borderColor: GLASS_COLORS.borderActive,
  color: GLASS_COLORS.textPrimary,
  bgcolor: GLASS_COLORS.primaryGlow,
} as const;

/**
 * Entrada sin ruta: tabs Borradores/Publicadas, calendario selector de fecha y listado del día.
 */
export function RutasEmptyView({ onCrearBorrador, onAbrirRuta }: RutasEmptyViewProps) {
  const theme = useTheme();
  const isDesktopShell = useMediaQuery(theme.breakpoints.up(layoutShell.desktopMinBreakpoint));

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

  const listadoTitulo =
    rutasDelDiaSeleccionado.length === 0
      ? null
      : rutasDelDiaSeleccionado.length === 1
        ? "1 ruta en esta fecha"
        : `${rutasDelDiaSeleccionado.length} rutas en esta fecha`;

  return (
    <Stack spacing={2.25} sx={{ ...shellStackSx, alignItems: "stretch" }}>
      <ResponsiveScrollableTabs
        value={tab}
        onChange={(_, v) => setTab(v as RutasListaTab)}
        variant="fullWidth"
        sx={{ ...moduleSlicesTabsSx, width: "100%" }}
        barSx={{ maxWidth: MODULE_CONTENT_MAX_PX, mx: "auto" }}
      >
        <Tab
          label="Borradores"
          value="borradores"
          sx={{ fontFamily: FONT_FAMILY_UI, fontWeight: 600, textTransform: "none" }}
        />
        <Tab
          label="Publicadas"
          value="publicadas"
          sx={{ fontFamily: FONT_FAMILY_UI, fontWeight: 600, textTransform: "none" }}
        />
      </ResponsiveScrollableTabs>

      <Box sx={calendarPanelSurfaceSx}>
        <Stack spacing={2.5}>
          <Typography sx={rutasResumenTitleSx}>{calendarioTitulo}</Typography>

          {loading ? (
            <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
              <CircularProgress size={40} sx={{ color: GLASS_COLORS.primary }} />
            </Box>
          ) : null}

          {error ? (
            <Alert severity="error" variant="outlined" sx={{ borderRadius: 2, fontFamily: FONT_FAMILY_UI }}>
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
              cellMinHeight={INSTITUTIONAL_CALENDAR_CELL_MIN_HEIGHT}
              cellGap={INSTITUTIONAL_CALENDAR_CELL_GAP}
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
                    bgcolor: GLASS_COLORS.primaryGlow,
                    minHeight: INSTITUTIONAL_CALENDAR_CELL_MIN_HEIGHT,
                  };
                }
                return { minHeight: INSTITUTIONAL_CALENDAR_CELL_MIN_HEIGHT };
              }}
              renderDayFooter={(ctx) => {
                const n = countPorDia.get(ctx.iso) ?? 0;
                if (n === 0) return undefined;
                return <Chip size="small" label={String(n)} sx={countChipSx} variant="outlined" />;
              }}
            />
          ) : null}

          {!loading && !error && tab === "borradores" ? (
            <Stack
              direction={{ xs: "column", sm: "row" }}
              spacing={1.25}
              alignItems={{ xs: "stretch", sm: "center" }}
              sx={{ mt: 0.5 }}
            >
              <AppButton
                dsVariant="primary"
                dsSize="lg"
                startIcon={<AddIcon />}
                disabled={!diaSeleccionadoListo}
                onClick={() => {
                  if (selectedIso) onCrearBorrador({ fecha: selectedIso });
                }}
                sx={{
                  fontFamily: FONT_FAMILY_UI,
                  fontWeight: 700,
                  alignSelf: { xs: "stretch", sm: "flex-start" },
                  minWidth: { sm: 280 },
                }}
              >
                Crear ruta para este día
              </AppButton>
            </Stack>
          ) : null}

          {!loading && !error ? (
            <>
              <Divider sx={rutasInstitutionalDividerSx} />

              {listadoTitulo ? (
                <Typography
                  sx={{
                    fontFamily: FONT_FAMILY_UI,
                    fontSize: "0.8125rem",
                    fontWeight: 600,
                    color: GLASS_COLORS.textSecondary,
                  }}
                >
                  {listadoTitulo}
                </Typography>
              ) : null}

              {rutasDelDiaSeleccionado.length === 0 ? (
                <Typography sx={{ fontFamily: FONT_FAMILY_UI, fontSize: "0.8125rem", color: GLASS_COLORS.textMuted }}>
                  {selectedIso == null ? "Seleccioná un día en el calendario." : "Sin rutas para esta fecha."}
                </Typography>
              ) : isDesktopShell ? (
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
                        fontFamily: FONT_FAMILY_UI,
                        fontWeight: 600,
                        justifyContent: "flex-start",
                        textAlign: "left",
                      }}
                    >
                      {rutasLabelFilaRutaListado(r)}
                    </AppButton>
                  ))}
                </Stack>
              ) : (
                <Stack spacing={1.5} sx={{ width: "100%", minWidth: 0 }}>
                  {rutasDelDiaSeleccionado.map((r) => (
                    <RutasDiaRutaMobileCard key={r.id} ruta={r} tab={tab} onOpen={onAbrirRuta} />
                  ))}
                </Stack>
              )}
            </>
          ) : null}
        </Stack>
      </Box>
    </Stack>
  );
}

// Re-export para consumidores que importaban el tipo desde la vista.
export type { RutasListaTab };
