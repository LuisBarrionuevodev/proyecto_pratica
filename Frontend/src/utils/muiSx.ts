import type { SxProps, Theme } from "@mui/material/styles";

/**
 * Combina múltiples `SxProps` en un array válido para MUI (evita errores TS con spreads anidados).
 */
export function mergeSx(
  ...styles: Array<SxProps<Theme> | false | null | undefined>
): SxProps<Theme> {
  const merged: SxProps<Theme>[] = [];
  for (const style of styles) {
    if (!style) continue;
    if (Array.isArray(style)) {
      merged.push(...style);
    } else {
      merged.push(style);
    }
  }
  return merged as SxProps<Theme>;
}
