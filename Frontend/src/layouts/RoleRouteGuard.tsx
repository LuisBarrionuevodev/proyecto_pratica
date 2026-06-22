import { Navigate, useLocation } from "react-router-dom";
import { Box, CircularProgress } from "@mui/material";

import { isPathAllowedForRole } from "../auth/roles";
import { useAppSession } from "../auth/AppSessionProvider";

export type RoleRouteGuardProps = {
  children: React.ReactNode;
};

/**
 * Bloquea rutas no permitidas según rol (RELEVADOR u otros futuros).
 * Espera bootstrap de sesión (default deny mientras loading).
 */
export function RoleRouteGuard({ children }: RoleRouteGuardProps) {
  const location = useLocation();
  const { status, role } = useAppSession();

  if (status === "loading") {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: 240, py: 4 }}>
        <CircularProgress size={32} sx={{ color: "#0166FF" }} />
      </Box>
    );
  }

  if (status === "unauthenticated" || !role) {
    return <Navigate to="/login" replace />;
  }

  if (status === "error") {
    return <Navigate to="/login" replace />;
  }

  if (!isPathAllowedForRole(role, location.pathname)) {
    return <Navigate to="/inicio" replace />;
  }

  return children;
}
