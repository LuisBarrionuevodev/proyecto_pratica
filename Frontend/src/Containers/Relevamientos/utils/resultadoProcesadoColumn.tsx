import type { MRT_ColumnDef } from "material-react-table";
import { ResultadoProcesadoChip } from "../Components/ResultadoProcesadoChip";

export interface RowConResultadoProcesado {
  resultado_label?: string | null;
  resultado_codigo?: string | null;
}

export function resultadoProcesadoMrtColumn<T extends RowConResultadoProcesado>(): MRT_ColumnDef<T> {
  return {
    id: "resultado_procesado",
    accessorKey: "resultado_label",
    header: "Resultado",
    size: 160,
    Cell: ({ row }) => (
      <ResultadoProcesadoChip
        label={row.original.resultado_label}
        codigo={row.original.resultado_codigo}
        testId="bandeja-resultado-chip"
      />
    ),
  };
}
