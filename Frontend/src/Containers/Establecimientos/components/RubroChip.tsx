import { Chip } from "@mui/material";
import type { IEstablecimientoListRow } from "../types/establecimientos.types";
import { COLORS } from "../../CargarActuaciones/styles/cargarActuacionesStyles";

const RUBRO_SX: Record<IEstablecimientoListRow["rubroSlug"], { bg: string; color: string }> = {
  gastronomia: { bg: "rgba(1, 102, 255, 0.2)", color: "#8BB8FF" },
  industrial: { bg: "rgba(255, 152, 0, 0.2)", color: "#FFCC80" },
  minorista: { bg: "rgba(156, 39, 176, 0.22)", color: "#E1BEE7" },
  servicios: { bg: "rgba(0, 188, 212, 0.18)", color: "#80DEEA" },
  otro: { bg: "rgba(255,255,255,0.08)", color: COLORS.grayLight },
};

type Props = { rubro: string; slug: IEstablecimientoListRow["rubroSlug"] };

/**
 * Chip de rubro alineado a la referencia UX (etiquetas de categoría en listado).
 */
export function RubroChip({ rubro, slug }: Props) {
  const t = RUBRO_SX[slug] ?? RUBRO_SX.otro;
  return (
    <Chip
      label={rubro}
      size="small"
      sx={{
        height: 22,
        fontFamily: '"Tactic Sans", sans-serif',
        fontSize: "10px",
        fontWeight: 600,
        letterSpacing: "0.04em",
        backgroundColor: t.bg,
        color: t.color,
        border: `1px solid ${COLORS.border}`,
      }}
    />
  );
}
