import type { MRT_ColumnDef } from "material-react-table";
import { formatDomicilioLineaVisible } from "../../../utils/formatDomicilioLineaVisible";
import { BandejaEllipsisCell } from "../../Actuaciones/Components/bandejaTableCells";
import type { DomicilioPendienteItem } from "../types";
import { DomicilioClasificacionChips, scoreUnificadoLabel } from "./DomicilioClasificacionChips";

/** Columnas read-only de clasificación compuesta para tablas de Gestión Domicilios. */
export function buildDomicilioClasificacionColumns(): MRT_ColumnDef<DomicilioPendienteItem>[] {
  return [
    {
      id: "domicilio_cargado",
      header: "Domicilio cargado",
      size: 220,
      Cell: ({ row }) => (
        <BandejaEllipsisCell
          value={
            formatDomicilioLineaVisible(row.original) ||
            [row.original.calle_raw, row.original.numero_raw ?? row.original.numero]
              .filter(Boolean)
              .join(" ") ||
            "—"
          }
        />
      ),
    },
    {
      accessorKey: "calle_normalizada",
      header: "Calle sugerida",
      size: 200,
      Cell: ({ cell }) => <BandejaEllipsisCell value={String(cell.getValue() ?? "—")} />,
    },
    {
      id: "numero_esquina",
      header: "Número / esquina",
      size: 140,
      Cell: ({ row }) => {
        const tipo = row.original.numero_tipo;
        const val =
          tipo === "ESQUINA"
            ? row.original.esquina_normalizada || row.original.numero || row.original.numero_raw
            : row.original.numero || row.original.numero_raw;
        return <BandejaEllipsisCell value={String(val ?? "—")} />;
      },
    },
    {
      accessorKey: "nomenclatura_estado",
      header: "Estado nomenclatura",
      size: 160,
      Cell: ({ row }) => (
        <BandejaEllipsisCell value={String(row.original.nomenclatura_estado ?? row.original.calle_status ?? "—")} />
      ),
    },
    {
      id: "geocode_estado_compuesto",
      header: "Estado geocode",
      size: 150,
      Cell: ({ row }) => (
        <BandejaEllipsisCell value={String(row.original.geocode_estado ?? row.original.geo_status ?? "—")} />
      ),
    },
    {
      accessorKey: "score_unificado",
      header: "Score",
      size: 110,
      Cell: ({ row }) => (
        <BandejaEllipsisCell value={scoreUnificadoLabel(row.original.score_unificado)} />
      ),
    },
    {
      accessorKey: "source",
      header: "Fuente",
      size: 90,
      Cell: ({ cell }) => <BandejaEllipsisCell value={String(cell.getValue() ?? "—")} />,
    },
    {
      id: "clasificacion_chips",
      header: "Clasificación",
      size: 320,
      Cell: ({ row }) => <DomicilioClasificacionChips item={row.original} compact />,
    },
  ];
}
