import type { Theme } from "@mui/material/styles";

/**
 * Refuerzo visual de error en campos outlined (glass/dense): borde y label alineados al palette.
 * Usar junto con `error` + `helperText` de MUI.
 */
export function fieldErrorOutlineSx(theme: Theme) {
  return {
    "& .MuiOutlinedInput-root.Mui-error .MuiOutlinedInput-notchedOutline": {
      borderColor: theme.palette.error.main,
      borderWidth: 2,
    },
    "& .MuiFormLabel-root.Mui-error": {
      color: theme.palette.error.main,
    },
    "& .MuiOutlinedInput-root.Mui-error:hover .MuiOutlinedInput-notchedOutline": {
      borderColor: theme.palette.error.main,
    },
  };
}
