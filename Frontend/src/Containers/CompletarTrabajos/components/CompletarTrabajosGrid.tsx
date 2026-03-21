import { useCallback, useMemo } from "react";
import DataEditor, {
  type EditableGridCell,
  type GridCell,
  GridCellKind,
  type GridColumn,
  GridColumnIcon,
  type Item,
} from "@glideapps/glide-data-grid";
import type { Theme as GlideTheme } from "@glideapps/glide-data-grid";
import "@glideapps/glide-data-grid/dist/index.css";
import { Box, CircularProgress, Typography } from "@mui/material";

import type { TrabajoDelDiaRow } from "../types/completarTrabajos.types";

/** Paleta Glide alineada a CargarActuaciones (institucional; copia local). */
const COMPLETAR_GRID_COLORS = {
  primary: "#0166FF",
  white: "#FFFFFF",
  grayDark: "#2B2E34",
  rowOdd: "#1E2127",
  border: "#3a3d44",
  warningLight: "#3D2E1E",
  textMedium: "#CCCCCC",
} as const;

const completarTrabajosGlideTheme: Partial<GlideTheme> = {
  accentColor: COMPLETAR_GRID_COLORS.primary,
  accentLight: "#4D94FF",
  textDark: COMPLETAR_GRID_COLORS.white,
  textMedium: COMPLETAR_GRID_COLORS.textMedium,
  textLight: "#999999",
  textBubble: COMPLETAR_GRID_COLORS.white,
  textHeader: COMPLETAR_GRID_COLORS.white,
  textGroupHeader: COMPLETAR_GRID_COLORS.white,
  textHeaderSelected: COMPLETAR_GRID_COLORS.primary,
  bgIconHeader: "transparent",
  fgIconHeader: COMPLETAR_GRID_COLORS.white,
  bgCell: COMPLETAR_GRID_COLORS.grayDark,
  bgCellMedium: COMPLETAR_GRID_COLORS.rowOdd,
  bgHeader: COMPLETAR_GRID_COLORS.grayDark,
  bgHeaderHasFocus: COMPLETAR_GRID_COLORS.border,
  bgHeaderHovered: COMPLETAR_GRID_COLORS.border,
  bgBubble: COMPLETAR_GRID_COLORS.grayDark,
  bgBubbleSelected: COMPLETAR_GRID_COLORS.primary,
  bgSearchResult: COMPLETAR_GRID_COLORS.warningLight,
  borderColor: COMPLETAR_GRID_COLORS.border,
  horizontalBorderColor: COMPLETAR_GRID_COLORS.border,
  drilldownBorder: COMPLETAR_GRID_COLORS.primary,
  linkColor: COMPLETAR_GRID_COLORS.primary,
  headerFontStyle: "600 12px",
  baseFontStyle: "11px",
  fontFamily: '"Tactic Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
};

const completarTrabajosGridContainerSx = {
  position: "relative" as const,
  height: { xs: 420, md: 520 },
  minHeight: 360,
  border: `1px solid ${COMPLETAR_GRID_COLORS.border}`,
  borderRadius: "8px",
  boxShadow:
    "0px 3px 1px -2px rgba(0,0,0,0.2), 0px 2px 2px 0px rgba(0,0,0,0.14), 0px 1px 5px 0px rgba(0,0,0,0.12)",
  backgroundImage: "linear-gradient(rgba(255, 255, 255, 0.069), rgba(255, 255, 255, 0.069))",
  backgroundColor: COMPLETAR_GRID_COLORS.grayDark,
  overflow: "hidden",
};

type DataColKey = keyof Omit<TrabajoDelDiaRow, "id">;

type ColDef = {
  key: DataColKey;
  title: string;
  width: number;
  group: string;
  readonly: boolean;
  kind: "text" | "number";
};

const COLUMN_DEFS: ColDef[] = [
  { key: "fecha", title: "Fecha", width: 104, group: "Base", readonly: true, kind: "text" },
  { key: "tipoIniciador", title: "Tipo iniciador", width: 168, group: "Base", readonly: true, kind: "text" },
  { key: "ordenTrabajo", title: "OT", width: 112, group: "Base", readonly: true, kind: "text" },
  { key: "inspectores", title: "Inspectores", width: 160, group: "Base", readonly: true, kind: "text" },
  { key: "calle", title: "Calle", width: 180, group: "Base", readonly: false, kind: "text" },
  { key: "interseccion", title: "Intersección", width: 140, group: "Base", readonly: false, kind: "text" },
  { key: "nombre", title: "Nombre", width: 120, group: "Identificación", readonly: true, kind: "text" },
  { key: "apellido", title: "Apellido", width: 120, group: "Identificación", readonly: true, kind: "text" },
  { key: "dni", title: "DNI", width: 100, group: "Identificación", readonly: true, kind: "text" },
  {
    key: "contraproducencia",
    title: "Contraproducencia",
    width: 140,
    group: "Resultado",
    readonly: false,
    kind: "text",
  },
  { key: "actaInspeccion", title: "Acta inspección", width: 120, group: "Resultado", readonly: false, kind: "text" },
  { key: "notificacion", title: "Notificación", width: 120, group: "Resultado", readonly: false, kind: "text" },
  {
    key: "actaComprobacion",
    title: "Acta comprobación",
    width: 140,
    group: "Resultado",
    readonly: false,
    kind: "text",
  },
  { key: "motivo", title: "Motivo", width: 120, group: "Resultado", readonly: false, kind: "text" },
  { key: "actaClausura", title: "Acta clausura", width: 120, group: "Resultado", readonly: false, kind: "text" },
  { key: "actaDecomiso", title: "Acta decomiso", width: 120, group: "Resultado", readonly: false, kind: "text" },
  {
    key: "kilosDecomisados",
    title: "Kg decomisados",
    width: 120,
    group: "Resultado",
    readonly: false,
    kind: "number",
  },
  { key: "motivo1", title: "Motivo 1", width: 130, group: "Motivos", readonly: false, kind: "text" },
  { key: "motivo2", title: "Motivo 2", width: 130, group: "Motivos", readonly: false, kind: "text" },
  { key: "motivo3", title: "Motivo 3", width: 130, group: "Motivos", readonly: false, kind: "text" },
];

export type CompletarTrabajosGridProps = {
  rows: TrabajoDelDiaRow[];
  onRowsChange: (rows: TrabajoDelDiaRow[]) => void;
  loading?: boolean;
};

function cellText(value: string | null | undefined): string {
  if (value === null || value === undefined) return "";
  return String(value);
}

function parseNullableText(data: string): string | null {
  const t = data.trim();
  return t === "" ? null : t;
}

export function CompletarTrabajosGrid({ rows, onRowsChange, loading = false }: CompletarTrabajosGridProps) {
  const getGroupDetails = useCallback((groupName: string) => {
    return {
      name: groupName,
      icon: GridColumnIcon.HeaderArray,
      overrideTheme: {
        bgIconHeader: "transparent",
        fgIconHeader: COMPLETAR_GRID_COLORS.white,
        textGroupHeader: COMPLETAR_GRID_COLORS.white,
      },
    };
  }, []);

  const columns = useMemo<GridColumn[]>(
    () =>
      COLUMN_DEFS.map((c) => ({
        id: c.key,
        title: c.title,
        width: c.width,
        group: c.group,
      })),
    []
  );

  const getCellContent = useCallback(
    ([col, row]: Item): GridCell => {
      const dataRow = rows[row];
      if (!dataRow) {
        return { kind: GridCellKind.Text, data: "", displayData: "", allowOverlay: false };
      }
      const def = COLUMN_DEFS[col];
      const raw = dataRow[def.key];

      if (def.kind === "number") {
        const n = typeof raw === "number" && Number.isFinite(raw) ? raw : undefined;
        return {
          kind: GridCellKind.Number,
          data: n,
          displayData: n === undefined ? "" : String(n),
          allowOverlay: !def.readonly,
          readonly: def.readonly,
        };
      }

      const text = cellText(raw as string | null);
      const displayEmpty = def.readonly ? "—" : "";
      return {
        kind: GridCellKind.Text,
        data: text,
        displayData: text === "" ? displayEmpty : text,
        allowOverlay: !def.readonly,
        readonly: def.readonly,
      };
    },
    [rows]
  );

  const onCellEdited = useCallback(
    ([col, row]: Item, newValue: EditableGridCell) => {
      const def = COLUMN_DEFS[col];
      if (def.readonly || row < 0 || row >= rows.length) return;

      const copy = rows.map((r) => ({ ...r }));
      const target = copy[row];

      if (def.kind === "number") {
        if (newValue.kind !== GridCellKind.Number) return;
        const v = newValue.data;
        (target as Record<string, unknown>)[def.key] =
          v === undefined || v === null || Number.isNaN(v) ? null : v;
      } else if (newValue.kind === GridCellKind.Text) {
        (target as Record<string, unknown>)[def.key] = parseNullableText(newValue.data);
      } else {
        return;
      }

      onRowsChange(copy);
    },
    [rows, onRowsChange]
  );

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
      <Box sx={completarTrabajosGridContainerSx}>
        {loading && (
          <Box
            sx={{
              position: "absolute",
              inset: 0,
              zIndex: 2,
              bgcolor: "rgba(0, 0, 0, 0.45)",
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
              alignItems: "center",
              gap: 1,
            }}
          >
            <CircularProgress size={28} sx={{ color: COMPLETAR_GRID_COLORS.primary }} />
            <Typography
              variant="body2"
              sx={{ fontFamily: completarTrabajosGlideTheme.fontFamily, color: COMPLETAR_GRID_COLORS.textMedium }}
            >
              Cargando trabajos…
            </Typography>
          </Box>
        )}
        <DataEditor
          getCellContent={getCellContent}
          columns={columns}
          rows={rows.length}
          onCellEdited={onCellEdited}
          rowMarkers="none"
          smoothScrollX
          smoothScrollY
          rowHeight={36}
          headerHeight={42}
          groupHeaderHeight={36}
          getCellsForSelection
          getGroupDetails={getGroupDetails}
          theme={completarTrabajosGlideTheme}
        />
      </Box>
      <Typography
        variant="caption"
        sx={{
          fontFamily: completarTrabajosGlideTheme.fontFamily,
          color: COMPLETAR_GRID_COLORS.textMedium,
        }}
      >
        Los cambios son solo en pantalla; aún no se guardan en el servidor.
      </Typography>
    </Box>
  );
}
