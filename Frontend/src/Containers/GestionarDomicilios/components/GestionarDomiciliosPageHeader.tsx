import RefreshIcon from "@mui/icons-material/Refresh";
import { Box, IconButton, Tooltip, Typography } from "@mui/material";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

type GestionarDomiciliosPageHeaderProps = {
  onRefresh?: () => void;
  loading?: boolean;
  lastUpdatedLabel?: string | null;
};

/** Cabecera de la vista Gestión de Domicilios (solo presentación). */
export function GestionarDomiciliosPageHeader({
  onRefresh,
  loading = false,
  lastUpdatedLabel,
}: GestionarDomiciliosPageHeaderProps) {
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: { xs: "column", sm: "row" },
        alignItems: { xs: "flex-start", sm: "center" },
        justifyContent: "space-between",
        gap: 1.5,
        pb: 0.5,
      }}
    >
      <Box sx={{ minWidth: 0 }}>
        <Typography
          variant="h5"
          sx={{
            fontWeight: 700,
            fontSize: { xs: "1.25rem", sm: "1.35rem" },
            lineHeight: 1.25,
            color: GLASS_COLORS.textPrimary,
          }}
        >
          Gestión de Domicilios
        </Typography>
        <Typography variant="body2" sx={{ color: GLASS_COLORS.textSecondary, mt: 0.5 }}>
          Cola operativa de geolocalización
        </Typography>
        <Typography variant="body2" sx={{ color: "text.secondary", mt: 0.75, maxWidth: 720 }}>
          Ubicá domicilios en el mapa, revisá pendientes y corregí puntos manualmente.
        </Typography>
      </Box>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexShrink: 0 }}>
        {lastUpdatedLabel ? (
          <Typography variant="caption" sx={{ color: "text.secondary" }}>
            {lastUpdatedLabel}
          </Typography>
        ) : null}
        {onRefresh ? (
          <Tooltip title="Refrescar">
            <span>
              <IconButton
                size="small"
                aria-label="Refrescar domicilios"
                disabled={loading}
                onClick={() => void onRefresh()}
                sx={{ color: GLASS_COLORS.textSecondary }}
              >
                <RefreshIcon fontSize="small" />
              </IconButton>
            </span>
          </Tooltip>
        ) : null}
      </Box>
    </Box>
  );
}
