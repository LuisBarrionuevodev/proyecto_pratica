import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Alert,
  Box,
  ButtonBase,
  Chip,
  CircularProgress,
  Divider,
  IconButton,
  Stack,
  Typography,
} from "@mui/material";
import ChevronLeft from "@mui/icons-material/ChevronLeft";
import ChevronRight from "@mui/icons-material/ChevronRight";

import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { fechaLocalHoyIso } from "../../../utils/dateRange";
import {
  getCompletarTrabajoPendientesResumen,
  type ICompletarTrabajoPendienteDiaResumen,
} from "../../../api/completarTrabajoApi";
import { AppButton } from "../../../ui";
import {
  planificacionPanelSubtitleSx,
  rutasInstitutionalDividerSx,
  rutasInstitutionalResumenPaperSx,
  rutasResumenTitleSx,
} from "../../RutasTrabajo/styles/institutionalVisual";
import type { CompletarTrabajosEmptyProps } from "../types";

const TACTIC = '"Tactic Sans", sans-serif' as const;

const CARRUSEL_SCROLL_PX = 380;

/** Ancho máximo del contenido (full-width con cap cómodo en pantallas grandes). */
const COMPLETAR_CONTENT_MAX_PX = 1400;

/** Misma familia que “Resumen de ruta” / paneles grandes en Rutas (glass + padding institucional). */
const principalGlassSurfaceSx = {
  ...rutasInstitutionalResumenPaperSx,
  width: "100%",
  maxWidth: COMPLETAR_CONTENT_MAX_PX,
  mx: "auto",
  boxSizing: "border-box" as const,
};

const carruselScrollSx = {
  overflowX: "auto" as const,
  overflowY: "hidden" as const,
  scrollSnapType: "x proximity" as const,
  scrollbarWidth: "none" as const,
  msOverflowStyle: "none" as const,
  pb: 0.5,
  "&::-webkit-scrollbar": { display: "none" },
};

function toIsoDateLocal(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

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

/** Fecha ISO → DD/MM/AAAA (local). */
function formatFechaLegible(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  if (!y || !m || !d) return iso;
  try {
    return new Intl.DateTimeFormat("es-AR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    }).format(new Date(y, m - 1, d));
  } catch {
    return iso;
  }
}

function formatFechaOperativaCorta(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  if (!y || !m || !d) return iso;
  try {
    return new Intl.DateTimeFormat("es-AR", {
      weekday: "short",
      day: "numeric",
      month: "short",
    }).format(new Date(y, m - 1, d));
  } catch {
    return iso;
  }
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

const CAL_COLS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"] as const;

function daysInMonth(year: number, monthIndex: number): number {
  return new Date(year, monthIndex + 1, 0).getDate();
}

function mondayOffsetFirstOfMonth(year: number, monthIndex: number): number {
  const js = new Date(year, monthIndex, 1).getDay();
  return (js + 6) % 7;
}

type OperativoMonthCalendarProps = {
  mesAncla: Date;
  onMesChange: (next: Date) => void;
  diasMap: Map<string, ICompletarTrabajoPendienteDiaResumen>;
  rangoDesde: string;
  rangoHasta: string;
  hoyIso: string;
  selectedIso: string | null;
  onSelectDay: (iso: string) => void;
};

function OperativoMonthCalendar({
  mesAncla,
  onMesChange,
  diasMap,
  rangoDesde,
  rangoHasta,
  hoyIso,
  selectedIso,
  onSelectDay,
}: OperativoMonthCalendarProps) {
  const y = mesAncla.getFullYear();
  const m0 = mesAncla.getMonth();
  const dim = daysInMonth(y, m0);
  const lead = mondayOffsetFirstOfMonth(y, m0);
  const totalCells = lead + dim;
  const rows = Math.ceil(totalCells / 7);

  const tituloMes = new Intl.DateTimeFormat("es-AR", { month: "long", year: "numeric" }).format(mesAncla);

  const prev = () => onMesChange(new Date(y, m0 - 1, 1));
  const next = () => onMesChange(new Date(y, m0 + 1, 1));

  const cells: { key: string; iso: string | null; dayNum: number | null }[] = [];
  for (let i = 0; i < rows * 7; i++) {
    if (i < lead || i >= lead + dim) {
      cells.push({ key: `pad-${y}-${m0}-${i}`, iso: null, dayNum: null });
    } else {
      const dayNum = i - lead + 1;
      const iso = toIsoDateLocal(new Date(y, m0, dayNum));
      cells.push({ key: iso, iso, dayNum });
    }
  }

  return (
    <Stack spacing={1.25}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" gap={1}>
        <IconButton size="small" onClick={prev} aria-label="Mes anterior" sx={{ color: GLASS_COLORS.textSecondary }}>
          <ChevronLeft />
        </IconButton>
        <Typography
          sx={{
            fontFamily: TACTIC,
            fontWeight: 700,
            fontSize: "0.88rem",
            color: GLASS_COLORS.textPrimary,
            textTransform: "capitalize",
            flex: 1,
            textAlign: "center",
          }}
        >
          {tituloMes}
        </Typography>
        <IconButton size="small" onClick={next} aria-label="Mes siguiente" sx={{ color: GLASS_COLORS.textSecondary }}>
          <ChevronRight />
        </IconButton>
      </Stack>

      <Box
        role="grid"
        aria-label="Calendario operativo: pendiente, completo o sin actividad según el resumen del servidor"
        sx={{
          display: "grid",
          gridTemplateColumns: "repeat(7, 1fr)",
          gap: 0.5,
          textAlign: "center",
        }}
      >
        {CAL_COLS.map((c) => (
          <Typography
            key={c}
            variant="caption"
            sx={{ fontFamily: TACTIC, color: GLASS_COLORS.textMuted, fontSize: "0.64rem", fontWeight: 600 }}
          >
            {c}
          </Typography>
        ))}
        {cells.map((cell) => {
          if (cell.iso == null || cell.dayNum == null) {
            return <Box key={cell.key} sx={{ minHeight: 40 }} />;
          }
          const est = estadoCeldaCalendario(cell.iso, diasMap, rangoDesde, rangoHasta);
          const esHoy = cell.iso === hoyIso;
          const sel = cell.iso === selectedIso;

          const titleHint = titleCeldaCalendario(est);

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
          const color =
            est === "sin_actividad" || est === "sin_dato_fuera" ? GLASS_COLORS.textMuted : GLASS_COLORS.textPrimary;

          return (
            <ButtonBase
              key={cell.key}
              title={titleHint}
              onClick={() => onSelectDay(cell.iso!)}
              sx={{
                minHeight: 40,
                borderRadius: "10px",
                fontFamily: TACTIC,
                fontWeight: esHoy ? 800 : 600,
                fontSize: "0.8rem",
                color,
                bgcolor: bg,
                border,
                boxShadow: sel ? `0 0 0 2px ${GLASS_COLORS.primary}` : "none",
                transition: "background-color 0.12s ease, border-color 0.12s ease",
                "&:hover": {
                  bgcolor:
                    est === "sin_actividad" || est === "sin_dato_fuera"
                      ? "rgba(255,255,255,0.05)"
                      : "rgba(255,255,255,0.06)",
                },
                "&.Mui-focusVisible": {
                  outline: `2px solid ${GLASS_COLORS.primary}`,
                  outlineOffset: 2,
                },
              }}
            >
              <Stack alignItems="center" spacing={0.15}>
                <span>{cell.dayNum}</span>
                {esHoy ? (
                  <Box
                    component="span"
                    sx={{
                      width: 5,
                      height: 5,
                      borderRadius: "50%",
                      bgcolor: GLASS_COLORS.primary,
                      opacity: 0.85,
                    }}
                  />
                ) : (
                  <Box sx={{ height: 5 }} />
                )}
              </Stack>
            </ButtonBase>
          );
        })}
      </Box>
    </Stack>
  );
}

type DiaCarouselCardProps = {
  dia: ICompletarTrabajoPendienteDiaResumen;
  hoyIso: string;
  onElegir: (fechaIso: string) => void;
};

function DiaCarouselCard({ dia, hoyIso, onElegir }: DiaCarouselCardProps) {
  const { fecha, total, atrasado } = dia;
  const esHoy = fecha === hoyIso;

  return (
    <ButtonBase
      focusRipple
      onClick={() => onElegir(fecha)}
      sx={{
        flex: "0 0 auto",
        scrollSnapAlign: "start" as const,
        width: { xs: 216, sm: 244, md: 262 },
        minWidth: { xs: 216, sm: 244, md: 262 },
        maxWidth: { xs: 216, sm: 244, md: 262 },
        minHeight: { xs: 132, sm: 140 },
        textAlign: "left",
        borderRadius: "14px",
        p: { xs: 1.5, sm: 1.75 },
        display: "block",
        bgcolor: "rgba(255,255,255,0.03)",
        border: `1px solid ${GLASS_COLORS.borderLight}`,
        transition: "border-color 0.15s ease, box-shadow 0.15s ease, background-color 0.15s ease",
        ...(atrasado
          ? {
              borderColor: "rgba(255, 138, 128, 0.65)",
              boxShadow: "inset 0 0 0 1px rgba(255, 138, 128, 0.12)",
            }
          : {
              borderColor: "rgba(255,255,255,0.12)",
            }),
        "&:hover": {
          bgcolor: "rgba(255,255,255,0.06)",
          borderColor: GLASS_COLORS.borderMedium,
        },
        "&.Mui-focusVisible": {
          outline: `2px solid ${GLASS_COLORS.primary}`,
          outlineOffset: 2,
        },
      }}
    >
      <Stack spacing={0.85} alignItems="flex-start" justifyContent="space-between" sx={{ minHeight: 1 }}>
        <Stack direction="row" spacing={0.6} alignItems="center" flexWrap="wrap" useFlexGap>
          {atrasado ? (
            <Chip
              size="small"
              label="Atrasado"
              color="warning"
              variant="outlined"
              sx={{ height: 24, fontSize: "0.68rem", fontFamily: TACTIC, fontWeight: 700 }}
            />
          ) : null}
          {esHoy ? (
            <Chip
              size="small"
              label="Hoy"
              variant="outlined"
              sx={{
                height: 24,
                fontSize: "0.65rem",
                fontFamily: TACTIC,
                borderColor: GLASS_COLORS.primary,
                color: GLASS_COLORS.primary,
              }}
            />
          ) : null}
        </Stack>
        <Typography
          sx={{
            fontFamily: TACTIC,
            fontWeight: 700,
            fontSize: { xs: "0.95rem", sm: "1rem" },
            color: GLASS_COLORS.textPrimary,
            lineHeight: 1.25,
            textTransform: "capitalize",
          }}
        >
          {formatFechaOperativaCorta(fecha)}
        </Typography>
        <Typography
          sx={{
            fontFamily: TACTIC,
            color: GLASS_COLORS.textSecondary,
            fontSize: { xs: "0.78rem", sm: "0.8125rem" },
            fontWeight: 600,
            lineHeight: 1.35,
          }}
        >
          {total === 1 ? "1 pendiente" : `${total} pendientes`}
        </Typography>
      </Stack>
    </ButtonBase>
  );
}

/**
 * Entrada al módulo: superficie glass grande con pendientes + carrusel; debajo, calendario operativo.
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

  const carruselRef = useRef<HTMLDivElement>(null);

  const diasMap = useMemo(() => buildDiasMap(dias), [dias]);
  const diasCarrusel = useMemo(
    () => dias.filter((d) => categoriaCalendarioDesdeRow(d) === "CON_PENDIENTES"),
    [dias]
  );

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

  const scrollCarrusel = (delta: number) => {
    carruselRef.current?.scrollBy({ left: delta, behavior: "smooth" });
  };

  const hoyIso = metaResumen?.hoy ?? hoyLocal;
  const rangoDesde = metaResumen?.desde ?? rango.desde;
  const rangoHasta = metaResumen?.hasta ?? rango.hasta;

  return (
    <Stack spacing={2.25} sx={{ width: "100%", maxWidth: COMPLETAR_CONTENT_MAX_PX, mx: "auto" }}>
      {loading ? (
        <Box sx={principalGlassSurfaceSx}>
          <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
            <CircularProgress size={36} />
          </Box>
        </Box>
      ) : null}

      {error ? (
        <Box sx={principalGlassSurfaceSx}>
          <Alert severity="error" variant="outlined" sx={{ borderRadius: 2 }}>
            {error}
            <Box sx={{ mt: 1 }}>
              <AppButton dsVariant="ghost" dsSize="sm" onClick={() => void cargarResumen()}>
                Reintentar
              </AppButton>
            </Box>
          </Alert>
        </Box>
      ) : null}

      {!loading && !error ? (
        <>
          <Box sx={principalGlassSurfaceSx}>
            <Stack spacing={2}>
              <Stack
                direction={{ xs: "column", sm: "row" }}
                spacing={{ xs: 0.75, sm: 2 }}
                alignItems={{ xs: "flex-start", sm: "baseline" }}
                justifyContent="space-between"
              >
                <Typography sx={rutasResumenTitleSx}>Trabajos pendientes</Typography>
                <Typography
                  sx={{
                    ...planificacionPanelSubtitleSx,
                    fontWeight: 600,
                    fontSize: "0.8125rem",
                    color: GLASS_COLORS.textSecondary,
                  }}
                >
                  Hoy: {formatFechaLegible(hoyIso)}
                </Typography>
              </Stack>
              <Divider sx={rutasInstitutionalDividerSx} />
              {diasCarrusel.length === 0 ? (
                <Typography sx={{ ...planificacionPanelSubtitleSx, fontSize: "0.78rem" }}>
                  Sin jornadas en el rango cargado.
                </Typography>
              ) : (
                <Box sx={{ position: "relative", mx: { xs: -0.5, sm: -0.25 } }}>
                  <IconButton
                    size="small"
                    aria-label="Desplazar carrusel a la izquierda"
                    onClick={() => scrollCarrusel(-CARRUSEL_SCROLL_PX)}
                    sx={{
                      display: { xs: "none", md: "flex" },
                      position: "absolute",
                      left: -2,
                      top: "50%",
                      transform: "translateY(-50%)",
                      zIndex: 2,
                      bgcolor: "rgba(0,0,0,0.32)",
                      color: GLASS_COLORS.textPrimary,
                      "&:hover": { bgcolor: "rgba(0,0,0,0.48)" },
                    }}
                  >
                    <ChevronLeft />
                  </IconButton>
                  <IconButton
                    size="small"
                    aria-label="Desplazar carrusel a la derecha"
                    onClick={() => scrollCarrusel(CARRUSEL_SCROLL_PX)}
                    sx={{
                      display: { xs: "none", md: "flex" },
                      position: "absolute",
                      right: -2,
                      top: "50%",
                      transform: "translateY(-50%)",
                      zIndex: 2,
                      bgcolor: "rgba(0,0,0,0.32)",
                      color: GLASS_COLORS.textPrimary,
                      "&:hover": { bgcolor: "rgba(0,0,0,0.48)" },
                    }}
                  >
                    <ChevronRight />
                  </IconButton>
                  <Box
                    ref={carruselRef}
                    sx={{ ...carruselScrollSx, display: "flex", gap: { xs: 1.25, sm: 1.5 }, px: { xs: 0, md: 3 }, py: 0.25 }}
                  >
                    {diasCarrusel.map((dia) => (
                      <DiaCarouselCard key={dia.fecha} dia={dia} hoyIso={hoyIso} onElegir={abrirGrid} />
                    ))}
                  </Box>
                </Box>
              )}
            </Stack>
          </Box>

          <Box sx={principalGlassSurfaceSx}>
            <Stack spacing={1.5}>
              <Typography sx={rutasResumenTitleSx}>Calendario operativo</Typography>
              <OperativoMonthCalendar
                mesAncla={calMes}
                onMesChange={setCalMes}
                diasMap={diasMap}
                rangoDesde={rangoDesde}
                rangoHasta={rangoHasta}
                hoyIso={hoyIso}
                selectedIso={selectedCalDay}
                onSelectDay={setSelectedCalDay}
              />
              <Stack
                direction={{ xs: "column", sm: "row" }}
                spacing={1.25}
                alignItems={{ xs: "stretch", sm: "center" }}
                sx={{ mt: 0.5 }}
              >
                <AppButton
                  dsVariant="primary"
                  dsSize="sm"
                  onClick={() => selectedCalDay && abrirGrid(selectedCalDay)}
                  disabled={!selectedCalDay}
                  sx={{ alignSelf: { xs: "stretch", sm: "flex-start" }, minWidth: { sm: 220 } }}
                >
                  Ir a la grilla del día
                </AppButton>
              </Stack>
            </Stack>
          </Box>
        </>
      ) : null}
    </Stack>
  );
}
