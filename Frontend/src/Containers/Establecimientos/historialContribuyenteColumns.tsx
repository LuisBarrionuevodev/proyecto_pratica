/** @jsxImportSource react */

import type { MRT_ColumnDef } from "material-react-table";

import {
  BandejaEllipsisCell,
  BandejaTipoActuacionChipCell,
} from "../Actuaciones/Components/bandejaTableCells";
import type { IHistorialContribuyenteRow } from "../../api/historialContribuyenteApi";
import { HistorialActasTramitesCell } from "./components/HistorialActasTramitesCell";
import { HistorialInspectoresCell } from "./components/HistorialInspectoresCell";
import { RubroChip } from "./components/RubroChip";
import { historialActasTramitesChipLabels } from "./utils/historialActasTramitesVisual";
import { historialContribuyenteDomicilioTexto } from "./utils/historialContribuyenteDomicilio";
import { formatFechaDateOnlyEsAR } from "../../utils/formatFechaDateOnlyEsAR";

/**
 * Columnas del historial por DNI/CUIT (consulta; incluye domicilio y rubro por fila).
 */
export function buildHistorialContribuyenteColumns(): MRT_ColumnDef<IHistorialContribuyenteRow>[] {
  return [
    {
      accessorKey: "fecha",
      header: "FECHA",
      size: 130,
      Cell: ({ row }) => <BandejaEllipsisCell value={formatFechaDateOnlyEsAR(row.original.fecha)} />,
    },
    {
      accessorKey: "tipo_actuacion",
      header: "TIPO DE ACTUACIÓN",
      size: 200,
      accessorFn: (row) =>
        [row.tipo_actuacion ?? "", row.contraproducencia ?? ""].filter((s) => s?.trim()).join(" · "),
      Cell: ({ row }) => (
        <BandejaTipoActuacionChipCell
          tipo={row.original.tipo_actuacion}
          contraproducencia={row.original.contraproducencia}
        />
      ),
    },
    {
      accessorKey: "domicilio_texto",
      header: "DOMICILIO",
      size: 200,
      grow: true,
      accessorFn: (row) => historialContribuyenteDomicilioTexto(row),
      Cell: ({ row }) => (
        <BandejaEllipsisCell value={historialContribuyenteDomicilioTexto(row.original)} />
      ),
    },
    {
      accessorKey: "rubro_nombre",
      header: "RUBRO",
      size: 160,
      Cell: ({ row }) => <RubroChip rubro={row.original.rubro_nombre ?? "—"} />,
    },
    {
      accessorKey: "inspectores_texto",
      header: "INSPECTORES",
      size: 180,
      grow: true,
      Cell: ({ row }) => (
        <HistorialInspectoresCell inspectoresTexto={row.original.inspectores_texto} />
      ),
    },
    {
      id: "actas_tramites",
      header: "ACTAS Y TRÁMITES",
      size: 280,
      grow: true,
      accessorFn: (row) =>
        historialActasTramitesChipLabels(row.actas, row.tramites).join(" · ") ||
        row.actas_tramites_texto?.trim() ||
        "",
      Cell: ({ row }) => (
        <HistorialActasTramitesCell actas={row.original.actas} tramites={row.original.tramites} />
      ),
    },
    {
      accessorKey: "estado",
      header: "ESTADO",
      size: 120,
      Cell: ({ row }) => (
        <BandejaEllipsisCell value={row.original.estado?.trim() || "—"} />
      ),
    },
  ];
}
