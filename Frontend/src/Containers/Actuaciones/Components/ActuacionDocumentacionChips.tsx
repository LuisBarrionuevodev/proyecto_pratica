import { Box, Chip, Tooltip } from "@mui/material";
import type { SxProps, Theme } from "@mui/material";
import type { ReactNode } from "react";

export type ActuacionDocumentacionChipsProps = {
  labels: string[];
  chipSx: SxProps<Theme>;
  /** Si no hay etiquetas. */
  empty?: ReactNode;
};

/**
 * Chips compactos para documentación propia / origen (F2.3).
 * Reutilizable en tabla y modal de Actuaciones.
 */
export function ActuacionDocumentacionChips({ labels, chipSx, empty }: ActuacionDocumentacionChipsProps) {
  if (!labels.length) {
    return empty ?? null;
  }
  return (
    <Box
      sx={{
        display: "flex",
        flexWrap: "wrap",
        gap: 0.5,
        alignItems: "center",
        alignContent: "flex-start",
        maxWidth: "100%",
      }}
    >
      {labels.map((text, idx) => (
        <Tooltip key={`d-${idx}-${text.slice(0, 40)}`} title={text} placement="top" enterDelay={320}>
          <Chip size="small" variant="outlined" label={text} sx={chipSx} />
        </Tooltip>
      ))}
    </Box>
  );
}
