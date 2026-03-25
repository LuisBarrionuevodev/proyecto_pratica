import { useEffect, useState } from "react";

import {
  fetchContraproducencias,
  fetchMotivos,
  fetchMotivosComprobacion,
  fetchRubros,
} from "../../../api/gridApi";

export type CompletarTrabajoCatalogs = {
  motivos: string[];
  motivosComprobacion: string[];
  contraproducencias: string[];
  rubros: string[];
};

type CatalogsState =
  | { status: "loading" }
  | { status: "ready"; data: CompletarTrabajoCatalogs }
  | { status: "error"; message: string };

/**
 * Catálogos de DB para selects en Completar trabajo (contraproducencia, motivos, rubro).
 * El tipo de actuación se resuelve en otro flujo (formulario de tipo por edición).
 */
export function useCompletarTrabajoCatalogs(): CatalogsState {
  const [state, setState] = useState<CatalogsState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    setState({ status: "loading" });
    Promise.all([
      fetchMotivos(),
      fetchMotivosComprobacion(),
      fetchContraproducencias(),
      fetchRubros(),
    ])
      .then(([motivos, motivosComp, contras, rubros]) => {
        if (cancelled) return;
        setState({
          status: "ready",
          data: {
            motivos: [...new Set(motivos.items.map((i) => i.nombre))],
            motivosComprobacion: [...new Set(motivosComp.items.map((i) => i.nombre))],
            contraproducencias: [...new Set(contras.items.map((i) => i.nombre))],
            rubros: [...new Set(rubros.items.map((i) => i.nombre))],
          },
        });
      })
      .catch(() => {
        if (cancelled) return;
        setState({
          status: "error",
          message: "No se pudieron cargar los catálogos (motivos, contraproducencias, rubros).",
        });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
