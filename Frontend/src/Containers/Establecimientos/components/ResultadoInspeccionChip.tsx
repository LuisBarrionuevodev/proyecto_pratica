import { Chip } from "@mui/material";
import type { ResultadoInspeccionUi } from "../types/establecimientos.types";
const MAP: Record<ResultadoInspeccionUi, { border: string; color: string; bg: string }> = {
  CONFORME: { border: "#2D9F4B", color: "#6BFF6B", bg: "rgba(45, 159, 75, 0.12)" },
  APROBADO: { border: "#2D9F4B", color: "#6BFF6B", bg: "rgba(45, 159, 75, 0.12)" },
  OBSERVADO: { border: "#FF9800", color: "#FFD699", bg: "rgba(255, 152, 0, 0.12)" },
  INFRACCION: { border: "#C62828", color: "#FF8A80", bg: "rgba(198, 40, 40, 0.15)" },
};

type Props = { resultado: ResultadoInspeccionUi };

export function ResultadoInspeccionChip({ resultado }: Props) {
  const s = MAP[resultado];
  return (
    <Chip
      label={resultado}
      size="small"
      variant="outlined"
      sx={{
        height: 22,
        fontFamily: '"Tactic Sans", sans-serif',
        fontSize: "10px",
        fontWeight: 600,
        borderColor: s.border,
        color: s.color,
        backgroundColor: s.bg,
      }}
    />
  );
}
