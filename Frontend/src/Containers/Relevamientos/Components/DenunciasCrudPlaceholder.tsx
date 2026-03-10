import { Alert, Box, CircularProgress, Typography } from "@mui/material";
import { useEffect, useMemo } from "react";
import FiltroDenuncias from "./FiltroDenuncias";
import TablaDenuncias from "./TableDenuncias";
import { useDenunciasFiltradas } from "../hooks/useDenunciasFiltradas";
import { getCurrentMonthRange } from "../../../utils/dateRange";
import {
  errorAlertStyles,
  filtroContainerStyles,
  metaInfoStyles,
  metaItemStyles,
  titleStyles,
} from "../../Actuaciones/styles/filtroStyles";

const DenunciasCrudPlaceholder = () => {
  const { denuncias, meta, loading, error, hasSearched, buscar } = useDenunciasFiltradas();
  const defaultRange = useMemo(() => getCurrentMonthRange(), []);

  useEffect(() => {
    buscar({
      desde: defaultRange.desde,
      hasta: defaultRange.hasta,
      estado: "all",
    });
  }, [buscar, defaultRange.desde, defaultRange.hasta]);

  return (
    <Box sx={filtroContainerStyles}>
      <Typography sx={titleStyles}>Denuncias</Typography>
      <FiltroDenuncias
        onFiltrar={(filters) =>
          buscar({
            desde: filters.desde,
            hasta: filters.hasta,
            estado: filters.estado,
          })
        }
      />

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
          onRefresh={() =>
            buscar({
              desde: meta?.desde || null,
              hasta: meta?.hasta || null,
              estado: "all",
              page: meta?.page || 1,
              page_size: meta?.page_size || 50,
            })
          }
        />
      )}
    </Box>
  );
};

export default DenunciasCrudPlaceholder;
