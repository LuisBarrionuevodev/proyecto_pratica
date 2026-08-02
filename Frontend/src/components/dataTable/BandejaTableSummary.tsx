import type { ReactNode } from "react";
import { Box, Typography } from "@mui/material";

import { metaInfoStyles, metaItemStyles } from "../../Containers/Actuaciones/styles/filtroStyles";

type BandejaTableSummaryProps = {
  children: ReactNode;
};

/**
 * Barra de resumen de tabla (Total / Mostrando / Página / Rango) con estilo bandeja.
 */
export function BandejaTableSummary({ children }: BandejaTableSummaryProps) {
  return <Box sx={metaInfoStyles}>{children}</Box>;
}

type BandejaTableSummaryItemProps = {
  label: string;
  value: ReactNode;
};

export function BandejaTableSummaryItem({ label, value }: BandejaTableSummaryItemProps) {
  return (
    <Typography sx={metaItemStyles} component="div">
      <strong>{label}:</strong> {value}
    </Typography>
  );
}
