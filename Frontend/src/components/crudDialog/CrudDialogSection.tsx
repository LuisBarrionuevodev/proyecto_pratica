import { Box, Typography } from "@mui/material";
import type { SxProps, Theme } from "@mui/material/styles";

import type { ReactNode } from "react";

import {
  crudDialogSectionPlainSx,
  crudDialogSectionSoftSx,
  crudDialogSectionTitleSx,
} from "../../styles/crudDialogTokens";

export type CrudDialogSectionVariant = "plain" | "soft";

export type CrudDialogSectionProps = {
  title?: string | null;
  children: ReactNode;
  /** `plain` (default): sección liviana con divisor. `soft`: contenedor apenas marcado. */
  variant?: CrudDialogSectionVariant;
  /** Override opcional del estilo del título de sección. */
  titleSx?: SxProps<Theme>;
};

/** Sección dentro del contenido del modal CRUD (sin card pesada por defecto). */
export function CrudDialogSection({
  title,
  children,
  variant = "plain",
  titleSx,
}: CrudDialogSectionProps) {
  const sectionSx = variant === "soft" ? crudDialogSectionSoftSx : crudDialogSectionPlainSx;

  return (
    <Box component="section" sx={sectionSx}>
      {title ? (
        <Typography component="h3" sx={[crudDialogSectionTitleSx, ...(titleSx ? [titleSx] : [])]}>
          {title}
        </Typography>
      ) : null}
      {children}
    </Box>
  );
}


