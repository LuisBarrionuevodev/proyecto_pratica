import { Chip } from "@mui/material";

export type ResultadoProcesadoCodigo =
  | "REALIZADO"
  | "NO_EXISTE_LOCAL"
  | "CERRADO"
  | string;

function chipColor(codigo: string | null | undefined): "success" | "warning" | "default" {
  if (codigo === "REALIZADO") return "success";
  if (codigo === "NO_EXISTE_LOCAL") return "warning";
  return "default";
}

interface ResultadoProcesadoChipProps {
  label: string | null | undefined;
  codigo?: ResultadoProcesadoCodigo | null;
  /** Atributo data-testid opcional para tests. */
  testId?: string;
}

export function ResultadoProcesadoChip({ label, codigo, testId }: ResultadoProcesadoChipProps) {
  const text = label?.trim() || "—";
  return (
    <Chip
      size="small"
      label={text}
      color={chipColor(codigo ?? undefined)}
      variant="outlined"
      data-testid={testId}
      sx={{ maxWidth: "100%" }}
    />
  );
}
