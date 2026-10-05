import type { ReactNode } from "react";
import { Box } from "@mui/material";

import textDigitaliza from "../../assets/TextDigitaliza.svg";

type PublicAuthScreenLayoutProps = {
  children: ReactNode;
};

const brandImgSx = {
  height: "auto",
  objectFit: "contain" as const,
  userSelect: "none" as const,
  pointerEvents: "none" as const,
};

/**
 * Login / recuperación: `TextDigitaliza.svg` (desktop arriba-izq; mobile encabezado centrado).
 * Fondo público vía `body.public-route` → BackgroundInicio2.
 */
export function PublicAuthScreenLayout({ children }: PublicAuthScreenLayoutProps) {
  return (
    <Box
      sx={{
        position: "relative",
        minHeight: "100vh",
        width: "100%",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        px: { xs: 2, sm: 3 },
        py: { xs: 3, sm: 8 },
        boxSizing: "border-box",
        overflowX: "hidden",
      }}
    >
      <Box
        component="img"
        src={textDigitaliza}
        alt="Digitaliza"
        data-testid="public-auth-brand-logo-mobile"
        sx={{
          ...brandImgSx,
          display: { xs: "block", sm: "none" },
          width: { xs: 200, sm: 220 },
          maxWidth: "min(100%, 240px)",
          mb: { xs: 2, sm: 0 },
          flexShrink: 0,
        }}
      />

      <Box
        component="img"
        src={textDigitaliza}
        alt=""
        aria-hidden
        data-testid="public-auth-brand-logo-desktop"
        sx={{
          ...brandImgSx,
          display: { xs: "none", sm: "block" },
          position: "absolute",
          top: { sm: 24, md: 28 },
          left: { sm: 28, md: 40 },
          width: { sm: 220, md: 250 },
          zIndex: 1,
        }}
      />

      <Box
        sx={{
          width: "100%",
          maxWidth: 520,
          zIndex: 2,
          minWidth: 0,
          flex: { xs: "0 1 auto", sm: "0 1 auto" },
        }}
      >
        {children}
      </Box>
    </Box>
  );
}
