import type { CardProps } from "@mui/material/Card";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Box from "@mui/material/Box";
import type { ReactNode } from "react";
import { glassCard } from "../styles/GlassStyles";
import { color as tokenColor } from "../theme/tokens";

export type CardGlassPadding = "none" | "sm" | "md";

export type CardGlassProps = CardProps & {
  header?: ReactNode;
  footer?: ReactNode;
  interactive?: boolean;
  contentPadding?: CardGlassPadding;
};

const paddingMap: Record<CardGlassPadding, number> = { none: 0, sm: 1.5, md: 2 };

/**
 * Tarjeta estilo glass; aplica `glassCard` en el root y controla padding en hijos (CardContent sin padding por defecto).
 */
export function CardGlass({
  children,
  header,
  footer,
  interactive = false,
  contentPadding = "md",
  onClick,
  sx,
  ...rest
}: CardGlassProps) {
  const isInteractive = interactive || Boolean(onClick);
  const px = paddingMap[contentPadding];

  return (
    <Card
      onClick={onClick}
      sx={[
        glassCard,
        isInteractive && {
          cursor: "pointer",
          transition: "background-color 0.2s ease, border-color 0.2s ease",
          "&:hover": {
            backgroundColor: tokenColor.hoverBg,
            borderColor: tokenColor.borderMedium,
          },
        },
        ...(Array.isArray(sx) ? sx : sx ? [sx] : []),
      ]}
      {...rest}
    >
      {header != null && (
        <Box sx={{ px: 2, pt: 2, pb: 1, flexShrink: 0 }}>
          {header}
        </Box>
      )}
      <CardContent
        sx={{
          p: 0,
          flexGrow: 1,
          display: "flex",
          flexDirection: "column",
          "&:last-child": { pb: 0 },
        }}
      >
        <Box
          sx={{
            px,
            pt: header != null ? (px > 0 ? 1 : 0) : px,
            pb: footer != null ? (px > 0 ? 1 : 0) : px,
          }}
        >
          {children}
        </Box>
      </CardContent>
      {footer != null && (
        <Box sx={{ px: 2, pb: 2, pt: 0, flexShrink: 0 }}>
          {footer}
        </Box>
      )}
    </Card>
  );
}
