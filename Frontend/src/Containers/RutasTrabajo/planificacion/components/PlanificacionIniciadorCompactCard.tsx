import { Box, Chip, IconButton, Stack, Tooltip, Typography } from "@mui/material";
import MapOutlinedIcon from "@mui/icons-material/MapOutlined";

import type { IRutaIniciadorPendienteRow } from "../../../../api/rutasTrabajoApi";
import { GLASS_COLORS } from "../../../../styles/GlassStyles";
import { AppButton } from "../../../../ui";
import {
  abrirUbicacionEnMapaExterno,
  etiquetaTipoCorta,
  lineaPrincipalPendiente,
  prioridadCategoriaRow,
  subtituloRubroFecha,
  type PrioridadCat,
} from "../utils/iniciadorDisplay";

const tactic = '"Tactic Sans", sans-serif' as const;

function chipPrioridadSx(cat: PrioridadCat) {
  if (cat === "ALTA") {
    return {
      borderColor: "rgba(255, 138, 128, 0.55)",
      color: "#ffab91",
      backgroundColor: "rgba(255, 82, 82, 0.12)",
    };
  }
  if (cat === "MEDIA") {
    return {
      borderColor: "rgba(255, 213, 79, 0.45)",
      color: "#ffe082",
      backgroundColor: "rgba(255, 193, 7, 0.1)",
    };
  }
  return {
    borderColor: GLASS_COLORS.borderMedium,
    color: GLASS_COLORS.textSecondary,
    backgroundColor: "rgba(255,255,255,0.04)",
  };
}

export type PlanificacionIniciadorCompactCardProps = {
  row: IRutaIniciadorPendienteRow;
  agregarLabel: string;
  onAgregar: () => void;
  agregarVariant?: "primary" | "secondary";
};

/**
 * Fila compacta operativa: badges prioridad/tipo, domicilio, rubro·fecha, acciones.
 */
export function PlanificacionIniciadorCompactCard({
  row,
  agregarLabel,
  onAgregar,
  agregarVariant = "primary",
}: PlanificacionIniciadorCompactCardProps) {
  const cat = prioridadCategoriaRow(row);
  const subt = subtituloRubroFecha(row);
  const principal = lineaPrincipalPendiente(row);
  const puedeMapa = principal !== "—";

  return (
    <Box
      sx={{
        px: 1.1,
        py: 0.85,
        borderRadius: "10px",
        border: `1px solid ${GLASS_COLORS.borderLight}`,
        backgroundColor: GLASS_COLORS.cardBg,
        transition: "border-color 0.15s ease, background-color 0.15s ease",
        "&:hover": {
          borderColor: GLASS_COLORS.borderMedium,
          backgroundColor: "rgba(255,255,255,0.04)",
        },
      }}
    >
      <Stack spacing={0.65}>
        <Stack direction="row" alignItems="center" flexWrap="wrap" useFlexGap spacing={0.5}>
          <Chip
            size="small"
            label={cat}
            variant="outlined"
            sx={{
              height: 22,
              fontFamily: tactic,
              fontSize: "0.65rem",
              fontWeight: 700,
              letterSpacing: "0.04em",
              ...chipPrioridadSx(cat),
            }}
          />
          <Chip
            size="small"
            label={etiquetaTipoCorta(row)}
            variant="outlined"
            sx={{
              height: 22,
              maxWidth: "100%",
              fontFamily: tactic,
              fontSize: "0.65rem",
              fontWeight: 600,
              borderColor: GLASS_COLORS.borderMedium,
              color: GLASS_COLORS.textSecondary,
              backgroundColor: "rgba(255,255,255,0.03)",
              "& .MuiChip-label": { px: 0.85, overflow: "hidden", textOverflow: "ellipsis" },
            }}
          />
        </Stack>
        <Typography
          sx={{
            fontFamily: tactic,
            fontWeight: 600,
            fontSize: "0.82rem",
            lineHeight: 1.35,
            color: GLASS_COLORS.textPrimary,
            display: "-webkit-box",
            WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
          }}
        >
          {principal}
        </Typography>
        {subt ? (
          <Typography sx={{ fontFamily: tactic, fontSize: "0.72rem", color: GLASS_COLORS.textMuted, lineHeight: 1.3 }}>
            {subt}
          </Typography>
        ) : null}
        <Stack direction="row" alignItems="center" justifyContent="flex-end" spacing={0.5} sx={{ pt: 0.25 }}>
          <Tooltip title={puedeMapa ? "Ver ubicación aproximada en mapa (OSM)" : "Sin domicilio para buscar"}>
            <span>
              <IconButton
                size="small"
                disabled={!puedeMapa}
                onClick={() => abrirUbicacionEnMapaExterno(row)}
                sx={{
                  color: GLASS_COLORS.textSecondary,
                  "&:hover": { color: GLASS_COLORS.primary, backgroundColor: "rgba(1, 102, 255, 0.08)" },
                }}
                aria-label="Ver en mapa"
              >
                <MapOutlinedIcon sx={{ fontSize: 18 }} />
              </IconButton>
            </span>
          </Tooltip>
          <AppButton dsVariant={agregarVariant} dsSize="sm" onClick={onAgregar}>
            {agregarLabel}
          </AppButton>
        </Stack>
      </Stack>
    </Box>
  );
}
