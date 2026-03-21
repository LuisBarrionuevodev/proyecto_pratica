import { useCallback, useState } from "react";
import { Box, Typography } from "@mui/material";

import { containerStyles } from "../CargarActuaciones/styles/cargarActuacionesStyles";
import { wrapperStyles } from "../Actuaciones/styles/filtroStyles";
import { GLASS_COLORS } from "../../styles/GlassStyles";
import { CompletarEmptyView } from "./views/CompletarEmptyView";
import { CompletarTrabajosGridView } from "./views/CompletarTrabajosGridView";

type VistaCompletar = "empty" | "grid";

/**
 * Módulo Completar trabajos: empty + grilla Glide con datos mock por fecha.
 */
const CompletarTrabajos = () => {
  const [vista, setVista] = useState<VistaCompletar>("empty");
  const [fechaOperativa, setFechaOperativa] = useState<string | null>(null);

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
