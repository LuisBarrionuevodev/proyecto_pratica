import type { JSX } from "react";
import { ThemeProvider, Box, Alert, Typography, CircularProgress } from "@mui/material";
import NavLeft from "../../Componets/NavLeft";
import { darkTheme } from "../../configs/theme";
import { useRelevamientosFiltradas } from "./hooks/useRelevamientosFiltradas";
import FiltroRelevamientos from "./Components/FiltroRelevamientos";
import TablaRelevamientos from "./Components/TableRelevamientos";
import {
  wrapperStyles,
  titleStyles,
  metaInfoStyles,
  metaItemStyles,
  errorAlertStyles,
} from "../Actuaciones/styles/filtroStyles";

const Relevamientos = (): JSX.Element => {
  const { relevamientos, meta, loading, error, hasSearched, buscar } = useRelevamientosFiltradas();

  const handleFiltrar = (filtros: {
    desde: string | null;
    hasta: string | null;
    inspector: string | null;
    calle: string | null;
    numero: string | null;
  }) => {
    buscar(filtros);
  };

  return (
    <>
      <NavLeft />
      <ThemeProvider theme={darkTheme}>
        <Box sx={wrapperStyles}>
        <Typography sx={titleStyles}>Relevamientos</Typography>

        <FiltroRelevamientos onFiltrar={handleFiltrar} />

        {error && hasSearched && (
          <Alert severity="error" sx={errorAlertStyles} onClose={() => {}}>
            <strong>Error:</strong> {error}
          </Alert>
        )}

        {loading && (
          <Box sx={{ display: "flex", justifyContent: "center", padding: "40px" }}>
            <CircularProgress sx={{ color: "#0166FF" }} />
          </Box>
        )}

        {hasSearched && !loading && meta && (
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

        {hasSearched && !loading && (
          <TablaRelevamientos
            data={relevamientos}
            loading={loading}
            onRefresh={() =>
              handleFiltrar({
                desde: meta?.desde || null,
                hasta: meta?.hasta || null,
                inspector: meta?.inspector || null,
                calle: meta?.calle || null,
                numero: meta?.numero || null,
              })
            }
          />
        )}
        </Box>
      </ThemeProvider>
    </>
  );
};

export default Relevamientos;
