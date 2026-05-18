import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import { Box, Typography } from "@mui/material";

import { GLASS_COLORS } from "../styles/GlassStyles";
import { fechaLocalHoyIso } from "../utils/dateRange";
import {
  institutionalViewHeaderBarSx,
  institutionalViewHeaderDateSx,
  institutionalViewHeaderTitleRowSx,
  institutionalViewHeaderTitleSx,
} from "./institutionalViewHeaderBar.tokens";

export type InstitutionalViewHeaderBarProps = {
  /** Nombre de la vista (ej. breadcrumb desde `resolveBreadcrumbLabel`). */
  title: string;
  /**
   * Fecha institucional fija YYYY-MM-DD en zona local.
   * Por defecto se calcula al render (suficiente para uso normal); pasar valor solo en tests.
   */
  institutionalDateIso?: string;
};

/**
 * Header superior del área de contenido: izquierda nombre de vista, derecha fecha de hoy (institucional).
 *
 * No sustituye filtros ni fechas operativas de cada módulo (ruta del día, Desde/Hasta, etc.).
 */
export function InstitutionalViewHeaderBar({ title, institutionalDateIso }: InstitutionalViewHeaderBarProps) {
  const iso = institutionalDateIso ?? fechaLocalHoyIso();

  return (
    <Box sx={institutionalViewHeaderBarSx} component="header" aria-label="Encabezado de vista">
      <Box sx={institutionalViewHeaderTitleRowSx}>
        <ChevronRightIcon sx={{ fontSize: 14, color: GLASS_COLORS.textMuted, flexShrink: 0 }} aria-hidden />
        <Typography component="span" sx={institutionalViewHeaderTitleSx}>
          {title}
        </Typography>
      </Box>
      <Typography component="time" dateTime={iso} sx={institutionalViewHeaderDateSx}>
        {iso}
      </Typography>
    </Box>
  );
}
