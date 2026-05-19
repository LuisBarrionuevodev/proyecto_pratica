import type { JSX } from "react";
import { useCallback, useState } from "react";
import { Alert, Box, Paper, Tab, Tabs, Typography } from "@mui/material";
import TablaRelevamientos from "./Components/TableRelevamientos";
import FiltroRelevamientos from "./Components/FiltroRelevamientos";
import { useRelevamientosBandeja } from "./hooks/useRelevamientosBandeja";
import type { RelevamientosBandejaSlice } from "./hooks/useRelevamientosBandeja";
import {
  moduleContentColumnSx,
  metaInfoStyles,
  metaItemStyles,
  errorAlertStyles,
} from "../Actuaciones/styles/filtroStyles";
import { GLASS_COLORS, glassSecondaryTabsSx, glassTabsSecondaryPanelBarSx } from "../../styles/GlassStyles";

const RelevamientosContainer = (): JSX.Element => {
  const [slice, setSlice] = useState<RelevamientosBandejaSlice>("pendientes");
  const { relevamientos, meta, loading, error, hasSearched, buscar } = useRelevamientosBandeja(slice);

  const handleFiltrar = useCallback(
    (filtros: {
      desde: string | null;
      hasta: string | null;
      inspector: string | null;
      calle: string | null;
      numero: string | null;
    }) => {
      void buscar({
        desde: filtros.desde,
        hasta: filtros.hasta,
        inspector: filtros.inspector,
        calle: filtros.calle,
        numero: filtros.numero,
        page: 1,
        page_size: 50,
      });
    },
    [buscar]
  );

  const handleRefresh = useCallback(() => {
    if (!meta?.desde || !meta?.hasta) return;
    void buscar({
      desde: meta.desde,
      hasta: meta.hasta,
      inspector: meta.inspector,
      calle: meta.calle,
      numero: meta.numero,
      page: meta.page,
      page_size: meta.page_size,
    });
  }, [buscar, meta]);

  return (
    <Box sx={moduleContentColumnSx}>
      <FiltroRelevamientos onFiltrar={handleFiltrar} />

      <Paper elevation={0} sx={{ ...glassTabsSecondaryPanelBarSx, width: "100%" }}>
        <Tabs
          value={slice}
          onChange={(_, v: RelevamientosBandejaSlice) => setSlice(v)}
          variant="scrollable"
          allowScrollButtonsMobile
          sx={glassSecondaryTabsSx}
        >
          <Tab label="Pendientes" value="pendientes" />
          <Tab label="Realizados" value="realizados" />
        </Tabs>
      </Paper>

      <Typography
        variant="body2"
        sx={{ color: GLASS_COLORS.textMuted, fontFamily: '"Tactic Sans", sans-serif' }}
      >
        {slice === "pendientes"
          ? "Solo relevamientos con iniciador pendiente (editables)."
          : "Relevamientos con actuación completada en ruta (CUMPLIDO); solo lectura en esta vista."}
      </Typography>

      {error && hasSearched && (
        <Alert severity="error" sx={errorAlertStyles} onClose={() => {}}>
          <strong>Error:</strong> {error}
        </Alert>
      )}

      {!hasSearched && !loading && (
        <Typography variant="body2" sx={{ color: GLASS_COLORS.textSecondary }}>
          Definí el rango de fechas (y opcionalmente inspector/calle/número) y pulsá <strong>Filtrar</strong>.
        </Typography>
      )}

      {hasSearched && meta && (
        <Box sx={metaInfoStyles}>
          <Typography sx={metaItemStyles}>
            <strong>Total:</strong> {meta.total}
          </Typography>
          <Typography sx={metaItemStyles}>
            <strong>Mostrando:</strong> {relevamientos.length} de {meta.total}
          </Typography>
          <Typography sx={metaItemStyles}>
            <strong>Página:</strong> {meta.page}
          </Typography>
          {meta.desde && meta.hasta && (
            <Typography sx={metaItemStyles}>
              <strong>Rango:</strong> {meta.desde} - {meta.hasta}
            </Typography>
          )}
          {meta.inspector && (
            <Typography sx={metaItemStyles}>
              <strong>Inspector:</strong> {meta.inspector}
            </Typography>
          )}
          {meta.calle && (
            <Typography sx={metaItemStyles}>
              <strong>Calle:</strong> {meta.calle}
            </Typography>
          )}
          {meta.numero && (
            <Typography sx={metaItemStyles}>
              <strong>Número:</strong> {meta.numero}
            </Typography>
          )}
        </Box>
      )}

      {hasSearched && (
        <TablaRelevamientos
          data={relevamientos}
          loading={loading}
          onRefresh={handleRefresh}
          numeroAllowFreeSolo
          enableEditing={slice === "pendientes"}
          hideRowActions={slice === "realizados"}
          hideDeleteAction={slice === "realizados"}
        />
      )}
    </Box>
  );
};

export default RelevamientosContainer;
