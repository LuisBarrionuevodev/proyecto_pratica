import { useEffect, useState } from "react";
import { Alert, Box, Typography } from "@mui/material";

import {
  alertBaseStyles,
  COLORS,
  filtroContainerStyles,
  filtroTitleStyles,
} from "../../Actuaciones/styles/filtroStyles";
import { AppButton } from "../../../ui";
import { CompletarTrabajosMRT } from "../components/CompletarTrabajosMRT";
import { useTrabajosDelDia } from "../hooks";
import type { TrabajoDelDiaRow } from "../types/completarTrabajos.types";

export type CompletarTrabajosGridViewProps = {
  fecha: string;
  onVolver: () => void;
};

/**
 * Vista principal con MRT (edición por fila): trabajos del día para la fecha elegida (mock).
 */
export function CompletarTrabajosGridView({ fecha, onVolver }: CompletarTrabajosGridViewProps) {
  const { rows: fetchedRows, loading, error } = useTrabajosDelDia(fecha);
  const [rows, setRows] = useState<TrabajoDelDiaRow[]>([]);

  useEffect(() => {
    setRows(fetchedRows);
  }, [fetchedRows]);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2, width: "100%", minHeight: 0 }}>
      <Box sx={filtroContainerStyles}>
        <Typography sx={filtroTitleStyles}>Trabajos del día</Typography>
        <Box
          sx={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 2,
          }}
        >
          <Typography
            variant="body2"
            sx={{
              fontFamily: '"Tactic Sans", sans-serif',
              color: COLORS.white,
              "& strong": { color: COLORS.primary, fontWeight: 700 },
            }}
          >
            Fecha operativa: <strong>{fecha}</strong>
          </Typography>
          <AppButton dsVariant="ghost" onClick={onVolver} sx={{ alignSelf: { xs: "stretch", sm: "center" } }}>
            Volver
          </AppButton>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ ...alertBaseStyles, mb: 0 }}>
          {error}
        </Alert>
      )}
      {!error && rows.length === 0 && !loading && (
        <Typography
          variant="body2"
          sx={{ color: "rgba(255,255,255,0.5)", fontFamily: '"Tactic Sans", sans-serif' }}
        >
          No hay trabajos para esta fecha (mock vacío).
        </Typography>
      )}
      {(rows.length > 0 || loading) && (
        <CompletarTrabajosMRT rows={rows} onRowsChange={setRows} loading={loading} />
      )}
    </Box>
  );
}
