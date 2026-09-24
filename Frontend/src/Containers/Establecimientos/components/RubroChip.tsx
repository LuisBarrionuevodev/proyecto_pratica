import { Chip } from "@mui/material";

import { bandejaOutlinedChipSx } from "../../Actuaciones/Components/bandejaTableCells";

type Props = { rubro: string };

/**
 * Chip de rubro alineado al estilo de bandeja Actuaciones (texto blanco, borde outlined).
 */
export function RubroChip({ rubro }: Props) {
  const label = (rubro ?? "").trim() || "—";
  return <Chip size="medium" variant="outlined" label={label} sx={bandejaOutlinedChipSx} />;
}
