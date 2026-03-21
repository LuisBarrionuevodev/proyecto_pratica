import { Alert, Box, CircularProgress, Typography } from "@mui/material";
import FiltroDenuncias from "./FiltroDenuncias";
import TablaDenuncias from "./TableDenuncias";
import { useDenunciasFiltradas } from "../hooks/useDenunciasFiltradas";
import {
  COLORS,
  errorAlertStyles,
  metaInfoStyles,
  metaItemStyles,
  moduleContentColumnSx,
} from "../../Actuaciones/styles/filtroStyles";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

const DenunciasCrudPlaceholder = () => {
  const { denuncias, meta, loading, error, hasSearched, buscar } = useDenunciasFiltradas();

  return (
    <Box sx={{ ...moduleContentColumnSx, gap: 2 }}>
      <Typography
        variant="body2"
        sx={{ color: GLASS_COLORS.textMuted, fontFamily: '"Tactic Sans", sans-serif' }}
      >
        Listado operativo de denuncias. Los resultados se cargan solo al pulsar <strong>Filtrar</strong> (no se
        combinan con filtros de relevamientos).
      </Typography>

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

      {!hasSearched && !loading && (
        <Typography variant="body2" sx={{ color: GLASS_COLORS.textSecondary }}>
          Definí el rango de fechas y pulsá <strong>Filtrar</strong> para ver denuncias.
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
