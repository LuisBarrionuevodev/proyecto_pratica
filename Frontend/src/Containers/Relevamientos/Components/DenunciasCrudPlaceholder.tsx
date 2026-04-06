import { Alert, Box, CircularProgress, Paper, Tab, Tabs, Typography } from "@mui/material";
import FiltroDenuncias from "./FiltroDenuncias";
import TablaDenuncias from "./TableDenuncias";
import { useDenunciasBandeja } from "../hooks/useDenunciasBandeja";
import type { DenunciasBandejaSlice } from "../hooks/useDenunciasBandeja";
import { useCallback, useRef, useState } from "react";
import {
  COLORS,
  errorAlertStyles,
  metaInfoStyles,
  metaItemStyles,
  moduleContentColumnSx,
} from "../../Actuaciones/styles/filtroStyles";
import { GLASS_COLORS, glassSecondaryTabsSx, glassTabsSecondaryPanelBarSx } from "../../../styles/GlassStyles";

const DenunciasCrudPlaceholder = () => {
  const [slice, setSlice] = useState<DenunciasBandejaSlice>("pendientes");
  const { denuncias, meta, loading, error, hasSearched, buscar } = useDenunciasBandeja(slice);
  const lastEstadoRealizados = useRef<"all" | "hechas" | "no_hechas">("all");

  const handleFiltrar = useCallback(
    (filters: { desde: string | null; hasta: string | null; estado: "all" | "hechas" | "no_hechas" }) => {
      if (slice === "realizados") {
        lastEstadoRealizados.current = filters.estado;
      }
      void buscar({
        desde: filters.desde,
        hasta: filters.hasta,
        estado: slice === "realizados" ? filters.estado : "all",
        page: 1,
        page_size: 50,
      });
    },
    [buscar, slice]
  );

  const handleRefresh = useCallback(() => {
    if (!meta?.desde || !meta?.hasta) return;
    void buscar({
      desde: meta.desde,
      hasta: meta.hasta,
      estado: slice === "realizados" ? lastEstadoRealizados.current : "all",
      page: meta.page,
      page_size: meta.page_size,
    });
  }, [buscar, meta, slice]);

  return (
    <Box sx={{ ...moduleContentColumnSx, gap: 2 }}>
      <FiltroDenuncias variant={slice === "pendientes" ? "pendientes" : "realizados"} onFiltrar={handleFiltrar} />

      <Paper elevation={0} sx={{ ...glassTabsSecondaryPanelBarSx, width: "100%" }}>
        <Tabs
          value={slice}
          onChange={(_, v: DenunciasBandejaSlice) => setSlice(v)}
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
          ? "Denuncias con iniciador pendiente (gestión operativa). Pulsá Filtrar para cargar."
          : "Historial vía gestión: filtrá por estado (cerradas, abiertas, etc.)."}
      </Typography>

      {error && hasSearched && (
        <Alert severity="error" sx={errorAlertStyles} onClose={() => {}}>
          <strong>Error:</strong> {error}
        </Alert>
      )}

      {!hasSearched && !loading && (
        <Typography variant="body2" sx={{ color: GLASS_COLORS.textSecondary }}>
          Definí el rango de fechas y pulsá <strong>Filtrar</strong>.
        </Typography>
      )}

      {loading && (
        <Box sx={{ display: "flex", justifyContent: "center", padding: "40px" }}>
          <CircularProgress sx={{ color: COLORS.primary }} />
        </Box>
      )}

      {hasSearched && !loading && meta && (
        <Box sx={metaInfoStyles}>
          <Typography sx={metaItemStyles}>
            <strong>Total:</strong> {meta.total}
          </Typography>
          <Typography sx={metaItemStyles}>
            <strong>Mostrando:</strong> {denuncias.length} de {meta.total}
          </Typography>
          <Typography sx={metaItemStyles}>
            <strong>Página:</strong> {meta.page}
          </Typography>
          {meta.desde && meta.hasta && (
            <Typography sx={metaItemStyles}>
              <strong>Rango:</strong> {meta.desde} - {meta.hasta}
            </Typography>
          )}
          {meta.estado && (
            <Typography sx={metaItemStyles}>
              <strong>Estado:</strong> {meta.estado}
            </Typography>
          )}
        </Box>
      )}

      {hasSearched && !loading && (
        <TablaDenuncias
          data={denuncias}
          loading={loading}
          onRefresh={handleRefresh}
          readOnly={slice === "realizados"}
        />
      )}
    </Box>
  );
};

export default DenunciasCrudPlaceholder;
