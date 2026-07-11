import { Box, Stack, Typography } from "@mui/material";

import type { IRutaIniciadorPendienteRow } from "../../../../api/rutasTrabajoApi";
import { GLASS_COLORS } from "../../../../styles/GlassStyles";
import { AppButton } from "../../../../ui";
import { EstablecimientoSecundarioLine } from "./EstablecimientoSecundarioLine";
import {
  lineaPrincipalPendiente,
  rubroLineaPendiente,
  tipoIniciadorEtiquetaOperativa,
} from "../utils/iniciadorDisplay";

const tactic = '"Tactic Sans", sans-serif' as const;

/** Ancho fijo liviano para popup de mapa (Leaflet + contenido). */
const MAP_POP_CARD_WIDTH = 236;

export type PlanificacionMapaGeopuntoOperativaCardProps = {
  row: IRutaIniciadorPendienteRow;
  yaEnPool: boolean;
  onAgregarAlPool: () => void;
};

/**
 * Ficha mínima solo para popup de mapa en Planificación (no reutilizar patrón de listado).
 */
export function PlanificacionMapaGeopuntoOperativaCard({
  row,
  yaEnPool,
  onAgregarAlPool,
}: PlanificacionMapaGeopuntoOperativaCardProps) {
  const direccion = lineaPrincipalPendiente(row);
  const rubro = rubroLineaPendiente(row);
  const tipo = tipoIniciadorEtiquetaOperativa(row)?.trim() || "—";

  const labelSx = {
    fontFamily: tactic,
    fontSize: "0.58rem",
    fontWeight: 700,
    letterSpacing: "0.04em",
    color: GLASS_COLORS.textMuted,
    textTransform: "uppercase" as const,
    lineHeight: 1.15,
    mb: 0.15,
  };

  const valueSx = {
    fontFamily: tactic,
    fontSize: "0.72rem",
    fontWeight: 600,
    color: GLASS_COLORS.textPrimary,
    lineHeight: 1.28,
    wordBreak: "break-word" as const,
  };

  return (
    <Box
      sx={{
        width: MAP_POP_CARD_WIDTH,
        maxWidth: "100%",
        px: 0.75,
        py: 0.65,
        borderRadius: "8px",
        border: `1px solid rgba(255,255,255,0.12)`,
        backgroundColor: "rgba(26,29,34,0.92)",
        backdropFilter: "blur(8px)",
      }}
    >
      <Stack spacing={0.45}>
        <Box>
          <Typography component="div" sx={labelSx}>
            Dirección
          </Typography>
          <Typography
            component="div"
            sx={{
              ...valueSx,
              display: "-webkit-box",
              WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical",
              overflow: "hidden",
            }}
          >
            {direccion}
          </Typography>
        </Box>
        <Box>
          <Typography component="div" sx={labelSx}>
            Rubro
          </Typography>
          <Typography component="div" sx={valueSx}>
            {rubro}
          </Typography>
          <EstablecimientoSecundarioLine item={row} fontSize="0.68rem" />
        </Box>
        <Box>
          <Typography
            component="div"
            sx={{
              ...labelSx,
              textTransform: "none",
              letterSpacing: "0.02em",
              fontSize: "0.6rem",
              fontWeight: 600,
            }}
          >
            Tipo de iniciador
          </Typography>
          <Typography component="div" sx={valueSx}>
            {tipo}
          </Typography>
        </Box>
        <Stack spacing={0.2} sx={{ pt: 0.15 }}>
          <AppButton
            dsVariant="primary"
            dsSize="sm"
            fullWidth
            disabled={yaEnPool}
            onClick={onAgregarAlPool}
            sx={{ minHeight: 28, py: 0.35, fontSize: "0.75rem", fontWeight: 700 }}
          >
            Agregar
          </AppButton>
          {yaEnPool ? (
            <Typography
              sx={{
                fontFamily: tactic,
                fontSize: "0.62rem",
                color: GLASS_COLORS.textMuted,
                textAlign: "center",
                lineHeight: 1.2,
              }}
            >
              En pool
            </Typography>
          ) : null}
        </Stack>
      </Stack>
    </Box>
  );
}
