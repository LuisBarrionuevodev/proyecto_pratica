import { Box, Chip, Tooltip, Typography } from "@mui/material";
import type { MRT_TableOptions } from "material-react-table";

import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { mergeMrtBodyCellPropsWithActuacionesPreset } from "../../../styles/mrtGlassDataTablePreset";
import { COLORS, DARK_TABLE_CONFIG } from "../styles/actuacionesTableStyles";

/** Texto de valor en celdas de bandeja (comprobación / notificación / tablas F3.10). */
export const bandejaValueTextSx = {
  fontWeight: 600,
  fontSize: "0.8125rem",
  lineHeight: 1.35,
  color: GLASS_COLORS.textPrimary,
  fontFamily: '"Tactic Sans", sans-serif',
} as const;

/** Alias explícito para renderers custom que no heredan del TableCell (F3.10). */
export const dataTableCellTextSx = bandejaValueTextSx;

/** Chip outlined reutilizable en bandejas y grilla compacta de actuaciones. */
export const bandejaOutlinedChipSx = {
  height: 28,
  maxWidth: "100%",
  fontWeight: 600,
  fontSize: "0.78rem",
  color: GLASS_COLORS.textPrimary,
  borderColor: "rgba(255,255,255,0.38)",
  backgroundColor: "rgba(255,255,255,0.07)",
  "& .MuiChip-label": {
    overflow: "hidden",
    textOverflow: "ellipsis",
    px: 1,
  },
} as const;

const chipSx = bandejaOutlinedChipSx;

/** Parte en dos (o más) segmentos separados por punto medio · (p. ej. fecha · OT). */
export function splitMiddleDot(value: string): string[] {
  if (!value || value.trim() === "" || value === "—") return [];
  return value
    .split(/\s*·\s*/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}

/** Motivos u otra lista separada por comas. */
export function splitCommaList(value: string): string[] {
  if (!value || value.trim() === "" || value === "—") return [];
  return value
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}

/**
 * Celda truncada con tooltip (bandeja compacta).
 * Tipografía reforzada (seminegrita + color primario de texto glass).
 */
export function BandejaEllipsisCell({ value }: { value: string }) {
  const body = (
    <Box
      component="span"
      sx={{
        display: "block",
        overflow: "hidden",
        textOverflow: "ellipsis",
        whiteSpace: "nowrap",
        maxWidth: "100%",
        ...bandejaValueTextSx,
      }}
    >
      {value}
    </Box>
  );
  if (!value || value === "—") return body;
  return (
    <Tooltip title={value} placement="top-start" enterDelay={400}>
      {body}
    </Tooltip>
  );
}

/**
 * Uno o más chips apilados (valores compuestos o lista corta).
 */
export function BandejaSegmentChipsCell({ segments }: { segments: string[] }) {
  const clean = segments.map((s) => (s ?? "").trim()).filter((s) => s.length > 0 && s !== "—");
  if (clean.length === 0) {
    return <BandejaEllipsisCell value="—" />;
  }
  return (
    <Box sx={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 0.65, maxWidth: "100%" }}>
      {clean.map((text, i) => (
        <Tooltip key={`${i}-${text.slice(0, 24)}`} title={text} placement="top-start" enterDelay={400}>
          <Chip size="medium" variant="outlined" label={text} sx={chipSx} />
        </Tooltip>
      ))}
    </Box>
  );
}

/**
 * Fecha en texto plano + orden de trabajo en chip (regla unificada bandejas / actuaciones).
 */
export function BandejaFechaYChipOtCell({ fecha, ot }: { fecha: string; ot: string }) {
  const f = (fecha ?? "").trim() || "—";
  const oRaw = (ot ?? "").trim();
  const otLabel =
    !oRaw || oRaw === "—" ? "OT —" : /^ot\b/i.test(oRaw) ? oRaw : `OT ${oRaw}`;
  return (
    <Box sx={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 0.65, maxWidth: "100%" }}>
      <BandejaEllipsisCell value={f} />
      <Tooltip title={oRaw || "—"} placement="top-start" enterDelay={400}>
        <Chip size="medium" variant="outlined" label={otLabel} sx={chipSx} />
      </Tooltip>
    </Box>
  );
}

/**
 * Domicilio: calle y número en chips apilados (regla unificada).
 * Con `withLabels` (default true) se prefija "Calle" / "Nº" para distinguir segmentos vacíos mixtos.
 */
export function BandejaDomicilioChipsCell({
  calle,
  numero,
  withLabels = true,
}: {
  calle: string;
  numero: string;
  withLabels?: boolean;
}) {
  const c = (calle ?? "").trim();
  const n = (numero ?? "").trim();
  const segments: string[] = [];
  if (c) segments.push(withLabels ? `Calle ${c}` : c);
  if (n) segments.push(withLabels ? `Nº ${n}` : n);
  return <BandejaSegmentChipsCell segments={segments} />;
}

/**
 * Domicilio en **una sola línea** (calle + número o esquina ya resueltos por el caller) y **rubro** en chip debajo.
 */
export function BandejaDomicilioYRubroCell({
  domicilioLinea,
  rubro,
}: {
  domicilioLinea: string;
  rubro?: string | null;
}) {
  const line = (domicilioLinea ?? "").trim() || "—";
  const r = (rubro ?? "").trim();
  return (
    <Box sx={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 0.65, maxWidth: "100%" }}>
      <BandejaEllipsisCell value={line} />
      {r ? (
        <Tooltip title={r} placement="top-start" enterDelay={400}>
          <Chip size="small" variant="outlined" label={r} sx={chipSx} />
        </Tooltip>
      ) : (
        <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)" }}>—</Typography>
      )}
    </Box>
  );
}

/** N.º de acta (u otra referencia de acta) en chip outlined. */
export function BandejaActaChipCell({ label }: { label: string }) {
  const v = (label ?? "").trim();
  if (!v || v === "—") {
    return <BandejaEllipsisCell value="—" />;
  }
  return (
    <Tooltip title={v} placement="top-start" enterDelay={400}>
      <Chip size="medium" variant="outlined" label={v} sx={chipSx} />
    </Tooltip>
  );
}

export const BANDEJA_MRT_BODY_CELL_PROPS = {
  muiTableBodyCellProps: mergeMrtBodyCellPropsWithActuacionesPreset(
    DARK_TABLE_CONFIG.muiTableBodyCellProps,
    () => ({
      sx: {
        fontWeight: 600,
        fontSize: "12px",
        color: COLORS.white,
      },
    })
  ),
} as Partial<MRT_TableOptions<any>>;

/**
 * Layout MRT de bandeja (Actas Comprobación / Notificación): body 12px seminegrita + densidad compact.
 * Usar con `...DARK_TABLE_CONFIG` en tablas de gestión F3.10.
 */
export const BANDEJA_MRT_READ_ONLY_TABLE_PROPS: Partial<MRT_TableOptions<any>> = {
  ...BANDEJA_MRT_BODY_CELL_PROPS,
  initialState: { density: "compact" },
};
