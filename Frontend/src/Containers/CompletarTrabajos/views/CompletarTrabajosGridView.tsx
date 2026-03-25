import { useEffect, useState } from "react";
import { Alert, Box, Typography } from "@mui/material";

import { alertBaseStyles, COLORS } from "../../Actuaciones/styles/filtroStyles";
import { AppButton } from "../../../ui";
import { glassCard } from "../../../styles/GlassStyles";
import { CompletarTrabajosMRT } from "../components/CompletarTrabajosMRT";
import { useCompletarTrabajoCatalogs, useTrabajosDelDia } from "../hooks";

export type CompletarTrabajosGridViewProps = {
  fecha: string;
  onVolver: () => void;
};

const DEFAULT_PER_PAGE = 20;

/**
 * Vista principal: trabajos del día (API paginada) + edición inline MRT para cierre.
 */
export function CompletarTrabajosGridView({ fecha, onVolver }: CompletarTrabajosGridViewProps) {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(DEFAULT_PER_PAGE);
  const [refreshNonce, setRefreshNonce] = useState(0);

  const catalogsState = useCompletarTrabajoCatalogs();

  useEffect(() => {
    setPage(1);
  }, [fecha]);

  const { rows, meta, loading, error } = useTrabajosDelDia(fecha, {
    page,
    perPage: perPage,
    refreshNonce,
  });

  const total = meta?.total ?? 0;
  const catalogs = catalogsState.status === "ready" ? catalogsState.data : null;
  const catalogsError = catalogsState.status === "error" ? catalogsState.message : null;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2, width: "100%", minHeight: 0 }}>
      <Box sx={{ ...glassCard, p: 2 }}>
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
            variant="body1"
            sx={{
              fontFamily: '"Tactic Sans", sans-serif',
              color: COLORS.white,
              fontWeight: 600,
              letterSpacing: "0.02em",
            }}
          >
            {fecha}
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
      {catalogsError && (
        <Alert severity="warning" sx={{ ...alertBaseStyles, mb: 0 }}>
          {catalogsError}
        </Alert>
      )}
      {!error && meta != null && (
        <Typography
          variant="caption"
          sx={{
            fontFamily: '"Tactic Sans", sans-serif',
            color: "rgba(255,255,255,0.5)",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
          }}
        >
          Total trabajos: {meta.total}
        </Typography>
      )}
      {!error && total === 0 && !loading && (
        <Typography
          variant="body2"
          sx={{ color: "rgba(255,255,255,0.5)", fontFamily: '"Tactic Sans", sans-serif' }}
        >
          No hay trabajos pendientes para el día operativo elegido. Revisá que sea la misma fecha de la ruta (no el día del
          borrador), que la ruta esté publicada y que queden ítems EN_PROCESO.
        </Typography>
      )}
      {(total > 0 || loading) && (
        <CompletarTrabajosMRT
          rows={rows}
          loading={loading}
          total={total}
          page={page}
          perPage={perPage}
          onPageChange={setPage}
          onPerPageChange={(n) => {
            setPerPage(n);
            setPage(1);
          }}
          catalogs={catalogs}
          onCierreExitoso={() => setRefreshNonce((n) => n + 1)}
        />
      )}
    </Box>
  );
}
