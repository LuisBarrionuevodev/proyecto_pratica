import { Box, Chip, Tooltip, Typography } from "@mui/material";
import type { MRT_ColumnDef } from "material-react-table";
import { formatDomicilioLineaVisible } from "../../../utils/formatDomicilioLineaVisible";
import { BandejaEllipsisCell } from "../../Actuaciones/Components/bandejaTableCells";
import { scoreUnificadoNumeric } from "../domicilioClasificacionLabels";
import {
  labelMatchStrategy,
  scoreDisplayWithStrategy,
} from "../domicilioMatchStrategyLabels";
import {
  labelPriorityBand,
  priorityBandFromScore,
} from "../domicilioPriorityLabels";
import type { DomicilioPendienteItem } from "../types";
import { DomicilioClasificacionChips } from "./DomicilioClasificacionChips";

function domicilioLinea(item: DomicilioPendienteItem): string {
  return (
    formatDomicilioLineaVisible(item) ||
    [item.calle_raw, item.numero_raw ?? item.numero].filter(Boolean).join(" ") ||
    "—"
  );
}

function fuenteLabel(item: DomicilioPendienteItem): string {
  const source = (item.source ?? "").trim();
  const provider = (item.provider ?? "").trim();
  if (source && provider) return `${source} · ${provider}`;
  return source || provider || "—";
}

/** Columnas compactas de lectura para tablas de Gestión Domicilios. */
export function buildDomicilioDisplayColumns(options?: {
  showErrorDetail?: boolean;
}): MRT_ColumnDef<DomicilioPendienteItem>[] {
  const cols: MRT_ColumnDef<DomicilioPendienteItem>[] = [
    {
      id: "domicilio",
      header: "Domicilio",
      size: 240,
      Cell: ({ row }) => {
        const linea = domicilioLinea(row.original);
        const rawHint =
          row.original.calle_raw &&
          row.original.calle_normalizada &&
          row.original.calle_raw !== row.original.calle_normalizada
            ? row.original.calle_raw
            : null;
        return (
          <Box sx={{ minWidth: 0 }}>
            <BandejaEllipsisCell value={linea} />
            {rawHint ? (
              <Typography variant="caption" color="text.secondary" noWrap title={rawHint}>
                Cargado: {rawHint}
              </Typography>
            ) : null}
          </Box>
        );
      },
    },
    {
      accessorKey: "calle_normalizada",
      header: "Calle sugerida",
      size: 200,
      Cell: ({ cell }) => <BandejaEllipsisCell value={String(cell.getValue() ?? "—")} />,
    },
    {
      id: "clasificacion",
      header: "Clasificación",
      size: 220,
      Cell: ({ row }) => (
        <DomicilioClasificacionChips item={row.original} compact />
      ),
    },
    {
      id: "score_unificado_col",
      header: "Score",
      size: 100,
      Cell: ({ row }) => {
        const score = row.original.score_unificado;
        const num = scoreUnificadoNumeric(score);
        if (num === "—") return <BandejaEllipsisCell value="—" />;
        const display = scoreDisplayWithStrategy(
          score,
          row.original.match_strategy,
          row.original.confidence_reason
        );
        const strategyHint = labelMatchStrategy(
          row.original.match_strategy,
          row.original.confidence_reason
        );
        const tooltip =
          row.original.confidence_reason?.trim() ||
          (strategyHint !== "—" ? `Estrategia: ${strategyHint}` : undefined);
        const cell = <BandejaEllipsisCell value={display} />;
        if (!tooltip) return cell;
        return (
          <Tooltip title={tooltip} placement="top" arrow>
            <Box component="span" sx={{ display: "block", minWidth: 0 }}>
              {cell}
            </Box>
          </Tooltip>
        );
      },
    },
    {
      id: "fuente",
      header: "Fuente",
      size: 110,
      Cell: ({ row }) => <BandejaEllipsisCell value={fuenteLabel(row.original)} />,
    },
    {
      id: "actualizacion",
      header: "Actualización",
      size: 120,
      Cell: ({ row }) => {
        const hint =
          row.original.quality != null && String(row.original.quality).trim()
            ? `Calidad ${row.original.quality}`
            : null;
        return <BandejaEllipsisCell value={hint ?? "—"} />;
      },
    },
  ];

  if (options?.showErrorDetail) {
    cols.push({
      accessorKey: "error_msg",
      header: "Detalle",
      size: 180,
      Cell: ({ cell }) => <BandejaEllipsisCell value={String(cell.getValue() ?? "—")} />,
    });
  }

  return cols;
}

function matchColumn(): MRT_ColumnDef<DomicilioPendienteItem> {
  return {
    id: "match_strategy_col",
    header: "Match",
    size: 130,
    Cell: ({ row }) => {
      const label = labelMatchStrategy(
        row.original.match_strategy,
        row.original.confidence_reason
      );
      if (label === "—") return <BandejaEllipsisCell value="—" />;
      return (
        <Tooltip
          title={row.original.confidence_reason?.trim() || label}
          placement="top"
          arrow
        >
          <Box component="span" sx={{ display: "block", minWidth: 0 }}>
            <BandejaEllipsisCell value={label} />
          </Box>
        </Tooltip>
      );
    },
  };
}

function priorityColumn(): MRT_ColumnDef<DomicilioPendienteItem> {
  return {
    id: "prioridad",
    header: "Prioridad",
    size: 90,
    Cell: ({ row }) => {
      const band = priorityBandFromScore(row.original.score_unificado);
      if (!band) return <BandejaEllipsisCell value="—" />;
      const color =
        band === "alta" ? "error" : band === "media" ? "warning" : ("success" as const);
      return <Chip size="small" label={labelPriorityBand(band)} color={color} variant="outlined" />;
    },
  };
}

/** Columnas tab «Para revisar» PR6B. */
export function buildParaRevisarColumns(): MRT_ColumnDef<DomicilioPendienteItem>[] {
  const base = buildDomicilioDisplayColumns();
  const withoutActualizacion = base.filter((c) => c.id !== "actualizacion");
  const domIdx = withoutActualizacion.findIndex((c) => c.id === "domicilio");
  const cols = [...withoutActualizacion];
  if (domIdx >= 0) {
    cols.splice(domIdx + 1, 0, priorityColumn());
  } else {
    cols.unshift(priorityColumn());
  }
  const scoreIdx = cols.findIndex((c) => c.id === "score_unificado_col");
  if (scoreIdx >= 0) {
    cols.splice(scoreIdx + 1, 0, matchColumn());
  } else {
    cols.push(matchColumn());
  }
  return cols;
}

/** @deprecated Usar buildDomicilioDisplayColumns — alias de compatibilidad interna. */
export function buildDomicilioClasificacionColumns(): MRT_ColumnDef<DomicilioPendienteItem>[] {
  return buildDomicilioDisplayColumns();
}
