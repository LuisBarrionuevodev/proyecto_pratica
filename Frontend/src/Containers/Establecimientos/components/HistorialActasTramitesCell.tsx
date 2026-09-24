/** @jsxImportSource react */

import { Box, Typography } from "@mui/material";

import { ActuacionDocumentacionChips } from "../../Actuaciones/Components/ActuacionDocumentacionChips";
import { bandejaOutlinedChipSx } from "../../Actuaciones/Components/bandejaTableCells";
import {
  historialActasTramitesChipLabels,
  type HistorialActasPayload,
  type HistorialTramitesPayload,
} from "../utils/historialActasTramitesVisual";

const chipCompactSx = bandejaOutlinedChipSx;

const actasChipsColumnSx = {
  display: "flex",
  flexDirection: "column" as const,
  alignItems: "flex-start",
  gap: 0.65,
  maxWidth: "100%",
};

export type HistorialActasTramitesCellProps = {
  actas?: HistorialActasPayload | null;
  tramites?: HistorialTramitesPayload | null;
};

/**
 * Columna “Actas y trámites” del historial de Establecimientos (misma visual que Actuaciones).
 */
export function HistorialActasTramitesCell({ actas, tramites }: HistorialActasTramitesCellProps) {
  const labels = historialActasTramitesChipLabels(actas, tramites);
  if (!labels.length) {
    return <Typography sx={{ fontSize: "0.78rem", color: "rgba(255,255,255,0.55)" }}>—</Typography>;
  }
  return (
    <Box sx={actasChipsColumnSx}>
      <ActuacionDocumentacionChips labels={labels} chipSx={chipCompactSx} />
    </Box>
  );
}
