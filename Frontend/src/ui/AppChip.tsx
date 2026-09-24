import { forwardRef } from "react";
import type { ChipProps } from "@mui/material/Chip";
import Chip from "@mui/material/Chip";
import type { Theme } from "@mui/material/styles";
import { useTheme } from "@mui/material/styles";
import { color as tokenColor } from "../theme/tokens";

export type AppChipTone = "neutral" | "primary" | "success" | "warning" | "error" | "info";

export type AppChipProps = Omit<ChipProps, "color"> & {
  tone?: AppChipTone;
};

function toneSx(tone: AppChipTone, theme: Theme): ChipProps["sx"] {
  switch (tone) {
    case "primary":
      return {
        backgroundColor: theme.palette.primary.dark,
        color: theme.palette.primary.contrastText,
        border: `1px solid ${tokenColor.borderMedium}`,
      };
    case "success":
      return {
        backgroundColor: theme.palette.success.dark,
        color: theme.palette.success.contrastText,
      };
    case "warning":
      return {
        backgroundColor: theme.palette.warning.dark,
        color: theme.palette.warning.contrastText,
      };
    case "error":
      return {
        backgroundColor: theme.palette.error.dark,
        color: theme.palette.error.contrastText,
      };
    case "info":
      return {
        backgroundColor: theme.palette.info.dark,
        color: theme.palette.info.contrastText,
      };
    case "neutral":
    default:
      return {
        backgroundColor: tokenColor.cardBg,
        color: tokenColor.textSecondary,
        border: `1px solid ${tokenColor.borderLight}`,
      };
  }
}

/**
 * Chip del design system DIGITALIZA.
 *
 * Qué hace: Chip con tonos semánticos y neutral basado en tokens.
 */
export const AppChip = forwardRef<HTMLDivElement, AppChipProps>(function AppChip(
  { tone = "neutral", size = "small", sx, ...rest },
  ref
) {
  const theme = useTheme();
  const chipToneSx = toneSx(tone, theme);

  return (
    <Chip
      ref={ref}
      size={size}
      variant="filled"
      sx={[chipToneSx, ...(Array.isArray(sx) ? sx : sx ? [sx] : [])]}
      {...rest}
    />
  );
});

AppChip.displayName = "AppChip";
