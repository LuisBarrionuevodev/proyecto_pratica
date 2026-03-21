import type { PaperProps } from "@mui/material/Paper";
import Paper from "@mui/material/Paper";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import type { SxProps, Theme } from "@mui/material/styles";
import type { ReactNode } from "react";

/** TODO: mover a tokens cuando se unifique con dashboard */
const CARD_DATA_PANEL_BG = "#2B2E34";

export type CardDataSurface = "flat" | "outlined" | "elevated";
export type CardDataPadding = "none" | "sm" | "md" | "lg";

export type CardDataProps = Omit<PaperProps, "title"> & {
  title?: ReactNode;
  subtitle?: ReactNode;
  action?: ReactNode;
  padding?: CardDataPadding;
  surface?: CardDataSurface;
  headerSx?: SxProps<Theme>;
  contentSx?: SxProps<Theme>;
};

const paddingMap: Record<CardDataPadding, number> = { none: 0, sm: 1.5, md: 2, lg: 3 };

function surfaceProps(surface: CardDataSurface): Pick<PaperProps, "variant" | "elevation"> & {
  sx: PaperProps["sx"];
} {
  switch (surface) {
    case "outlined":
      return {
        variant: "outlined",
        elevation: 0,
        sx: { borderColor: "divider", backgroundColor: CARD_DATA_PANEL_BG },
      };
    case "elevated":
      return {
        variant: "elevation",
        elevation: 4,
        sx: { backgroundColor: CARD_DATA_PANEL_BG },
      };
    case "flat":
    default:
      return {
        variant: "elevation",
        elevation: 0,
        sx: { backgroundColor: CARD_DATA_PANEL_BG },
      };
  }
}

/**
 * Panel de datos (métricas / charts), distinto de CardGlass.
 */
export function CardData({
  title,
  subtitle,
  action,
  children,
  padding = "md",
  surface = "flat",
  headerSx,
  contentSx,
  sx,
  ...rest
}: CardDataProps) {
  const sp = surfaceProps(surface);
  const p = paddingMap[padding];
  const hasHeader = title != null || subtitle != null || action != null;

  return (
    <Paper
      {...rest}
      variant={sp.variant}
      elevation={sp.elevation}
      sx={[sp.sx, ...(Array.isArray(sx) ? sx : sx ? [sx] : [])]}
    >
      {hasHeader && (
        <Box
          sx={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: 2,
            p,
            pb: title != null || subtitle != null ? 1 : p,
            ...headerSx,
          }}
        >
          <Box>
            {title != null && (
              <Typography variant="h6" component="div">
                {title}
              </Typography>
            )}
            {subtitle != null && (
              <Typography variant="body2" color="text.secondary">
                {subtitle}
              </Typography>
            )}
          </Box>
          {action != null && <Box sx={{ flexShrink: 0 }}>{action}</Box>}
        </Box>
      )}
      <Box
        sx={{
          px: p,
          pb: p,
          pt: hasHeader ? 0 : p,
          ...contentSx,
        }}
      >
        {children}
      </Box>
    </Paper>
  );
}
