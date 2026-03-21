import { useEffect, useState } from "react";
import { Alert, Box, Paper, Typography } from "@mui/material";

import {
  alertBaseStyles,
  gridContainerStyles,
} from "../../CargarActuaciones/styles/cargarActuacionesStyles";
import { AppButton } from "../../../ui";
import { CompletarTrabajosGrid } from "../components/CompletarTrabajosGrid";
import { useTrabajosDelDia } from "../hooks";
import type { TrabajoDelDiaRow } from "../types/completarTrabajos.types";

export type CompletarTrabajosGridViewProps = {
  fecha: string;
  onVolver: () => void;
};

/**
 * Vista principal con grilla Glide: trabajos del día para la fecha elegida (mock).
 */
export function CompletarTrabajosGridView({ fecha, onVolver }: CompletarTrabajosGridViewProps) {
  const { rows: fetchedRows, loading, error } = useTrabajosDelDia(fecha);
  const [rows, setRows] = useState<TrabajoDelDiaRow[]>([]);

  useEffect(() => {
    setRows(fetchedRows);
  }, [fetchedRows]);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <Paper sx={{ ...gridContainerStyles, overflow: "hidden" }}>
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            px: 2,
            pt: 2,
            pb: 1,
          }}
        >
          <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.7)" }}>
            Fecha operativa: {fecha}
          </Typography>
          <AppButton dsVariant="secondary" onClick={onVolver}>
            Volver
          </AppButton>
        </Box>

        <Box sx={{ px: 2, pb: 2 }}>
          {error && (
            <Alert severity="error" sx={{ ...alertBaseStyles, mb: 2 }}>
              {error}
            </Alert>
          )}
          {!error && rows.length === 0 && !loading && (
            <Typography
              variant="body2"
              sx={{ mb: 2, color: "rgba(255,255,255,0.5)", fontFamily: '"Tactic Sans", sans-serif' }}
            >
              No hay trabajos para esta fecha (mock vacío).
            </Typography>
          )}
          {(rows.length > 0 || loading) && (
            <CompletarTrabajosGrid rows={rows} onRowsChange={setRows} loading={loading} />
          )}
        </Box>
      </Paper>
    </Box>
  );
}
