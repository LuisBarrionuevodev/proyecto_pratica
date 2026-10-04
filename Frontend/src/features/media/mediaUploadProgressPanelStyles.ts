import type { SxProps, Theme } from "@mui/material/styles";

import type { DigitalizaThemeMode } from "../../theme/colors";
import { catalogDropdownPaperStyle } from "../../theme/catalogMenuTheme";
import { getSemanticColors } from "../../theme/colors";

/** Panel global de carga de evidencia: superficie sólida (sin glass). */
export function mediaUploadProgressPanelSx(mode: DigitalizaThemeMode): SxProps<Theme> {
  const c = getSemanticColors(mode);
  const paper = catalogDropdownPaperStyle(c, mode);
  return {
    ...paper,
    borderRadius: 2,
    p: 2.5,
    boxSizing: "border-box",
    minWidth: 0,
    maxWidth: "100%",
  };
}

export function mediaUploadProgressDialogPaperSx(mode: DigitalizaThemeMode): SxProps<Theme> {
  const c = getSemanticColors(mode);
  const paper = catalogDropdownPaperStyle(c, mode);
  return {
    ...paper,
    backgroundImage: "none",
    backdropFilter: "none",
    WebkitBackdropFilter: "none",
    boxShadow: c.shadow.panel,
  };
}
