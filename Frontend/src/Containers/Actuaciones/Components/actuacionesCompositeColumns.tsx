import { Box, Typography } from "@mui/material";
import type { MRT_ColumnDef } from "material-react-table";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import {
  actuacionActaChipsOnly,
  actuacionActasYTramiteAccessor,
  actuacionDocumentacionTramiteSegments,
} from "../utils/actuacionDocumentacionVisual";
import { formatActuacionListDomicilioLinea } from "../../../utils/formatDomicilioLineaVisible";
import {
  BandejaDomicilioYRubroCell,
  BandejaFechaYChipOtCell,
  BandejaSegmentChipsCell,
  bandejaOutlinedChipSx,
  splitCommaList,
} from "./bandejaTableCells";
import { ActuacionDocumentacionChips } from "./ActuacionDocumentacionChips";

/** Actas / trámite: chips apilados (misma regla que domicilio / listas). */
const actasChipsColumnSx = {
  display: "flex",
  flexDirection: "column" as const,
  alignItems: "flex-start",
  gap: 0.65,
  maxWidth: "100%",
};

function inspectoresNombres(r: IActuacionListItem): string[] {
  const fromArr = r.inspectores?.filter((s): s is string => Boolean(s?.trim()));
  if (fromArr && fromArr.length > 0) return fromArr.map((s) => s.trim());
  const texto = r.inspectores_texto?.trim();
  if (texto) return splitCommaList(texto);
  return [r.inspector1, r.inspector2, r.inspector3].filter((s): s is string => Boolean(s?.trim()));
}

function motivosNotif(r: IActuacionListItem): string[] {
  return [r.notificacion_motivo_1, r.notificacion_motivo_2, r.notificacion_motivo_3]
    .map((s) => (s ?? "").trim())
    .filter(Boolean);
}

const chipCompactSx = {
  ...bandejaOutlinedChipSx,
  height: 24,
  fontSize: "0.72rem",
  "& .MuiChip-label": {
    overflow: "hidden",
    textOverflow: "ellipsis",
    px: 0.75,
  },
} as const;

/** Ids de columnas compuestas (p. ej. visibilidad en vista domicilios pendientes). */
export const ACTUACIONES_COMPOSITE_COLUMN_IDS = [
  "col_fecha_ot",
  "col_tipo_contra",
  "col_domicilio_rubro",
  "col_inspectores",
  "col_actas_admin",
  "col_motivos_notif",
  "col_motivo_comp",
  "col_decomiso_merc",
] as const;

/**
 * Columnas solo lectura compactas (fecha/OT, domicilio, actas, chips).
 * La edición sigue en el modal; estos `accessorFn` alimentan orden, filtro y exportación.
 */
export function buildActuacionesCompositeColumns(): MRT_ColumnDef<IActuacionListItem>[] {
  return [
    {
      id: "col_fecha_ot",
      header: "Fecha · OT",
      accessorFn: (row) =>
        [row.fecha_actuacion ?? "", row.orden_trabajo_numero ?? ""].filter(Boolean).join(" "),
      size: 132,
      Cell: ({ row }) => {
        const r = row.original;
        const fecha = (r.fecha_actuacion ?? "").trim() || "—";
        const ot = (r.orden_trabajo_numero ?? "").trim();
        return <BandejaFechaYChipOtCell fecha={fecha} ot={ot} />;
      },
    },
    {
      id: "col_tipo_contra",
      header: "Tipo y contraproducencia",
      accessorFn: (row) =>
        [row.tipo_actuacion ?? "", row.contraproducencia ?? ""].filter((s) => s?.trim()).join(" · "),
      size: 200,
      Cell: ({ row }) => {
        const r = row.original;
        const tipo = (r.tipo_actuacion ?? "").trim();
        const contra = (r.contraproducencia ?? "").trim();
        const segs = [tipo ? `Tipo: ${tipo}` : "", contra ? `Contraproducencia: ${contra}` : ""].filter(Boolean);
        return <BandejaSegmentChipsCell segments={segs.length ? segs : []} />;
      },
    },
    {
      id: "col_domicilio_rubro",
      header: "Domicilio",
      accessorFn: (row) =>
        [formatActuacionListDomicilioLinea(row), row.rubro_nombre ?? ""].filter(Boolean).join(" "),
      size: 220,
      Cell: ({ row }) => {
        const r = row.original;
        const line = formatActuacionListDomicilioLinea(r).trim() || "—";
        return <BandejaDomicilioYRubroCell domicilioLinea={line} rubro={r.rubro_nombre} />;
      },
    },
    {
      id: "col_inspectores",
      header: "Inspectores",
      accessorFn: (row) => inspectoresNombres(row).join(", "),
      size: 200,
      Cell: ({ row }) => <BandejaSegmentChipsCell segments={inspectoresNombres(row.original)} />,
    },
    {
      id: "col_actas_admin",
      header: "Actas y trámite",
      accessorFn: (row) => actuacionActasYTramiteAccessor(row),
      size: 280,
      Cell: ({ row }) => {
        const r = row.original;
        const labels = [...actuacionActaChipsOnly(r), ...actuacionDocumentacionTramiteSegments(r)];
        if (!labels.length) {
          return <Typography sx={{ fontSize: "0.78rem", color: "rgba(255,255,255,0.55)" }}>—</Typography>;
        }
        return (
          <Box sx={actasChipsColumnSx}>
            <ActuacionDocumentacionChips labels={labels} chipSx={chipCompactSx} />
          </Box>
        );
      },
    },
    {
      id: "col_motivos_notif",
      header: "Motivos notificación",
      accessorFn: (row) => motivosNotif(row).join(", "),
      size: 200,
      Cell: ({ row }) => <BandejaSegmentChipsCell segments={motivosNotif(row.original)} />,
    },
    {
      id: "col_motivo_comp",
      header: "Motivo comprobación",
      accessorFn: (row) => (row.comprobacion_motivo ?? "").trim(),
      size: 180,
      Cell: ({ row }) => {
        const v = (row.original.comprobacion_motivo ?? "").trim();
        return v ? (
          <BandejaSegmentChipsCell segments={[v]} />
        ) : (
          <Typography sx={{ fontSize: "0.78rem", color: "rgba(255,255,255,0.55)" }}>—</Typography>
        );
      },
    },
    {
      id: "col_decomiso_merc",
      header: "Decomiso / mercadería",
      accessorFn: (row) => {
        const k = row.decomiso_kilos_total;
        if (k != null && !Number.isNaN(Number(k))) return `${k} kg`;
        return "";
      },
      size: 140,
      Cell: ({ row }) => {
        const r = row.original;
        const k = r.decomiso_kilos_total;
        const chips: string[] = [];
        if (k != null && !Number.isNaN(Number(k))) {
          chips.push(`${k} kg`);
        }
        if (!chips.length) {
          return <Typography sx={{ fontSize: "0.78rem", color: "rgba(255,255,255,0.55)" }}>—</Typography>;
        }
        return <BandejaSegmentChipsCell segments={chips} />;
      },
    },
  ];
}
