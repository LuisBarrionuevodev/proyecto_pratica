import { useCallback, useEffect, useState } from "react";
import { Box } from "@mui/material";

import { containerStyles } from "../CargarActuaciones/styles/cargarActuacionesStyles";
import { wrapperStyles } from "../Actuaciones/styles/filtroStyles";
import { CompletarEmptyView } from "./views/CompletarEmptyView";
import { CompletarTrabajosGridView } from "./views/CompletarTrabajosGridView";
import { fetchCompletarTrabajoCatalogsCached } from "./hooks/completarTrabajoCatalogsCache";

type VistaCompletar = "empty" | "grid";

/**
 * Módulo Completar trabajos: selector de fecha + grilla MRT con datos reales.
 * No incluye actas previas (notif./comprob. previa): no obligatorias aquí; el origen va por iniciador.
 */
const CompletarTrabajos = () => {
  const [vista, setVista] = useState<VistaCompletar>("empty");
  const [fechaOperativa, setFechaOperativa] = useState<string | null>(null);

  useEffect(() => {
    void fetchCompletarTrabajoCatalogsCached();
  }, []);

  const handleVerTrabajos = useCallback((fecha: string) => {
    setFechaOperativa(fecha);
    setVista("grid");
  }, []);

  const handleVolver = useCallback(() => {
    setVista("empty");
  }, []);

  return (
    <Box sx={containerStyles}>
      <Box sx={wrapperStyles}>
       
        {vista === "empty" && <CompletarEmptyView onVerTrabajos={handleVerTrabajos} />}
        {vista === "grid" && fechaOperativa != null && (
          <CompletarTrabajosGridView fecha={fechaOperativa} onVolver={handleVolver} />
        )}
      </Box>
    </Box>
  );
};

export default CompletarTrabajos;
