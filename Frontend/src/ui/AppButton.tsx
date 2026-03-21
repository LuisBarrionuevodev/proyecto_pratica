import { forwardRef } from "react";
import type { ButtonProps } from "@mui/material/Button";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";

export type AppButtonDsVariant = "primary" | "secondary" | "ghost" | "danger";
export type AppButtonDsSize = "sm" | "md" | "lg";

export type AppButtonProps = Omit<ButtonProps, "color" | "variant" | "size"> & {
  dsVariant?: AppButtonDsVariant;
  dsSize?: AppButtonDsSize;
  loading?: boolean;
};

function mapDsVariant(
  ds: AppButtonDsVariant
): Pick<ButtonProps, "color" | "variant"> & { extraSx?: ButtonProps["sx"] } {
  switch (ds) {
    case "secondary":
      return { variant: "outlined", color: "primary" };
    case "ghost":
      return {
        variant: "text",
        color: "inherit",
        extraSx: {
          color: "text.primary",
          "&:hover": { backgroundColor: "action.hover" },
        },
      };
    case "danger":
      return { variant: "contained", color: "error" };
    case "primary":
    default:
      return { variant: "contained", color: "primary" };
  }
}

function mapDsSize(ds: AppButtonDsSize): NonNullable<ButtonProps["sx"]> {
  switch (ds) {
    case "sm":
      return { minHeight: 32, px: 1.5, py: 0.5, fontSize: "0.8125rem" };
    case "lg":
      return { minHeight: 44, px: 2.5, py: 1, fontSize: "1rem" };
    case "md":
    default:
      return { minHeight: 40, px: 2, py: 0.75, fontSize: "0.875rem" };
  }
}

/**
 * Botón del design system DIGITALIZA.
 *
 * Qué hace: variantes `primary` | `secondary` | `ghost` | `danger` y tamaños `sm` | `md` | `lg`.
 * Parámetros: props de MUI Button salvo color/variant/size; `dsVariant`, `dsSize`, `loading`.
 * Retorno: elemento button.
 */
export const AppButton = forwardRef<HTMLButtonElement, AppButtonProps>(function AppButton(
  {
    dsVariant = "primary",
    dsSize = "md",
    loading = false,
    disabled,
    startIcon,
    sx,
    ...rest
  },
  ref
) {
  const mapped = mapDsVariant(dsVariant);
  const sizeSx = mapDsSize(dsSize);

  return (
    <Button
      ref={ref}
      {...rest}
      variant={mapped.variant}
      color={mapped.color}
      disabled={disabled || loading}
      startIcon={
        loading ? (
          <CircularProgress color="inherit" size={16} thickness={5} />
        ) : (
          startIcon
        )
      }
      sx={[sizeSx, mapped.extraSx, ...(Array.isArray(sx) ? sx : sx ? [sx] : [])]}
    />
  );
});

AppButton.displayName = "AppButton";
