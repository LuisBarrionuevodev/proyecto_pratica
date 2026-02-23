import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
} from "material-react-table";
import { useMemo } from "react";
import { DARK_TABLE_CONFIG } from "../../Actuaciones/styles/actuacionesTableStyles";

export type Inspector = {
  id: number;
  nombre: string;
  inspecciones: number;
};

type Props = {
  data: Inspector[];
};

const RankingInspectores = ({ data }: Props) => {
  // Ordenar y agregar posición
  const ranking = useMemo(() => {
    return [...data]
      .sort((a, b) => b.inspecciones - a.inspecciones)
      .map((item, index) => ({
        ...item,
        posicion: index + 1,
      }));
  }, [data]);

  const columns = useMemo<MRT_ColumnDef<typeof ranking[0]>[]>(
    () => [
      {
        accessorKey: "posicion",
        header: "#",
        size: 10,
      },
      {
        accessorKey: "nombre",
        header: "Inspector",
      },
      {
        accessorKey: "inspecciones",
        header: "Inspecciones",
      },
    ],
    []
  );

  const table = useMaterialReactTable({
    columns,
    data: ranking,
    ...DARK_TABLE_CONFIG,
    enableEditing: false,
    enableRowSelection: false,
    enableSelectAll: false,
    enableColumnFilters: false,
    enableGlobalFilter: false,
    enableSorting: false,
    enableTopToolbar: false,
    enableBottomToolbar: true,
     muiTableContainerProps: {
    sx: {
      maxHeight: 350,
      minHeight: 300,
    },
  },
  });

  return <MaterialReactTable table={table} />;
};

export default RankingInspectores;