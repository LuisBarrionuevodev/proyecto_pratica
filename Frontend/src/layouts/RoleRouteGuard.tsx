import { Navigate, useLocation } from "react-router-dom";



import { isPathAllowedForRole } from "../auth/roles";

import { useAppSession } from "../auth/AppSessionProvider";



export type RoleRouteGuardProps = {

  children: React.ReactNode;

};



/**

 * Bloquea rutas no permitidas según rol (RELEVADOR u otros futuros).

 * Espera sesión resuelta (default deny).

 */

export function RoleRouteGuard({ children }: RoleRouteGuardProps) {

  const location = useLocation();

  const { status, role } = useAppSession();



  if (status === "loading") {

    return null;

  }



  if (!role) {

    return <Navigate to="/login" replace />;

  }



  if (!isPathAllowedForRole(role, location.pathname)) {

    return <Navigate to="/inicio" replace />;

  }



  return children;

}

