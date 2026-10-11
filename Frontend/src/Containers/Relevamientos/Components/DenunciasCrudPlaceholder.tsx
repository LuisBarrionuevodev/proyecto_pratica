import { Alert, Box, Paper, Tab, Tabs, Typography } from "@mui/material";
import FiltroDenuncias from "./FiltroDenuncias";
import TablaDenuncias from "./TableDenuncias";
import { useDenunciasBandeja } from "../hooks/useDenunciasBandeja";
import type { DenunciasBandejaSlice } from "../hooks/useDenunciasBandeja";
import { useCallback, useState } from "react";
import {
  errorAlertStyles,
  metaInfoStyles,
  metaItemStyles,
  moduleContentColumnSx,
} from "../../Actuaciones/styles/filtroStyles";
import { GLASS_COLORS, glassSecondaryTabsSx, glassTabsSecondaryPanelBarSx } from "../../../styles/GlassStyles";
import { FONT_FAMILY_UI } from "../../../theme/typography";

const DenunciasCrudPlaceholder = () => {
  const [slice, setSlice] = useState<DenunciasBandejaSlice>("pendientes");
  const { denuncias, meta, loading, error, hasSearched, buscar, limpiarLista } = useDenunciasBandeja(slice);
  const handleFiltrar = useCallback(
    (filters: { desde: string | null; hasta: string | null }) => {
      void buscar({
        desde: filters.desde,
        hasta: filters.hasta,
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
      page: meta.page,
      page_size: meta.page_size,
    });
  }, [buscar, meta]);

  return (
    <Box sx={moduleContentColumnSx}>
      <FiltroDenuncias
        variant={slice === "pendientes" ? "pendientes" : "procesados"}
        onFiltrar={handleFiltrar}
        onLimpiarLista={limpiarLista}
      />

      <Paper elevation={0} sx={{ ...glassTabsSecondaryPanelBarSx, width: "100%" }}>
        <Tabs
          value={slice}
          onChange={(_, v: DenunciasBandejaSlice) => setSlice(v)}
          variant="scrollable"
          allowScrollButtonsMobile
          sx={glassSecondaryTabsSx}
        >
          <Tab label="Pendientes" value="pendientes" />
          <Tab label="Procesados" value="procesados" />
        </Tabs>
      </Paper>

      <Typography
        variant="body2"
        sx={{ color: GLASS_COLORS.textMuted, fontFamily: FONT_FAMILY_UI }}
      >
        {slice === "pendientes"
          ? "Denuncias con iniciador pendiente (gestión operativa). Pulsá Filtrar para cargar."
          : "Denuncias con cierre terminal en ruta (resultado operativo). Solo lectura."}
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

      {hasSearched && meta && !loading && (
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

      {hasSearched && !loading && meta?.total === 0 && (
        <Typography variant="body2" sx={{ color: GLASS_COLORS.textSecondary }}>
          {slice === "procesados"
            ? "No hay denuncias procesadas."
            : "No hay denuncias pendientes en el rango seleccionado."}
        </Typography>
      )}

      {hasSearched && ((meta?.total ?? 0) > 0 || loading) ? (
        <TablaDenuncias
          data={denuncias}
          loading={loading}
          onRefresh={handleRefresh}
          readOnly={slice === "procesados"}
          showResultadoProcesado={slice === "procesados"}
        />
      ) : null}
    </Box>
  );
};

export default DenunciasCrudPlaceholder;
