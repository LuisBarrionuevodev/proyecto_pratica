import { useEffect, useState } from "react";

import {
  fetchCompletarTrabajoCatalogsCached,
  type CompletarTrabajoCatalogs,
} from "./completarTrabajoCatalogsCache";

export type { CompletarTrabajoCatalogs };

type CatalogsState =
  | { status: "loading" }
  | { status: "ready"; data: CompletarTrabajoCatalogs }
  | { status: "error"; message: string };

/**
 * Suscripción al cache de catálogos de Completar trabajo (carga única por sesión vía módulo cache).
 */
export function useCompletarTrabajoCatalogs(): CatalogsState {
  const [state, setState] = useState<CatalogsState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    fetchCompletarTrabajoCatalogsCached()
      .then((data) => {
        if (cancelled) return;
        setState({ status: "ready", data });
      })
      .catch(() => {
        if (cancelled) return;
        setState({
          status: "error",
          message: "No se pudieron cargar los catálogos (motivos, contraproducencias, rubros, inspectores).",
        });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
