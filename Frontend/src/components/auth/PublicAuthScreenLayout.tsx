import type { ReactNode } from "react";
import { Box } from "@mui/material";

import logoDigitalizaPng from "../../documentos/assets/logo-smt.png";

type PublicAuthScreenLayoutProps = {
  children: ReactNode;
};

/**
 * Login / recuperación: logo institucional fijo arriba a la izquierda; formulario centrado.
 */
export function PublicAuthScreenLayout({ children }: PublicAuthScreenLayoutProps) {
  return (
    <Box
      sx={{
        position: "relative",
        minHeight: "100vh",
        width: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        px: 2,
        py: { xs: 10, sm: 8 },
        boxSizing: "border-box",
        overflowX: "hidden",
      }}
    >
      <Box
        component="img"
        src={logoDigitalizaPng}
        alt="Digitaliza"
        data-testid="public-auth-brand-logo"
        sx={{
          position: "absolute",
          top: { xs: 16, sm: 24 },
          left: { xs: 16, sm: 32 },
          width: { xs: 108, sm: 140, md: 156 },
          height: "auto",
          objectFit: "contain",
          zIndex: 1,
          pointerEvents: "none",
          userSelect: "none",
        }}
      />
      <Box sx={{ width: "100%", maxWidth: 480, zIndex: 2 }}>{children}</Box>
    </Box>
  );
}
