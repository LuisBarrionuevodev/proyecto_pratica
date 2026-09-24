import { Chip, type ChipProps } from "@mui/material";

import { rutasOperativaChipSx } from "../styles/institutionalVisual";

export type RutasOperativaChipProps = ChipProps;

/**
 * Chip operativo unificado para tipos, estados y métricas en Planificación / Asignación.
 */
export function RutasOperativaChip({
  size = "small",
  variant = "outlined",
  sx,
  ...rest
}: RutasOperativaChipProps) {
  return (
    <Chip
      size={size}
      variant={variant}
      sx={[rutasOperativaChipSx, ...(Array.isArray(sx) ? sx : sx ? [sx] : [])]}
      {...rest}
    />
  );
}
