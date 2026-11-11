import { Box, Chip, Tooltip, Typography } from "@mui/material";

import {
  BandejaSegmentChipsCell,
  bandejaOutlinedChipSx,
} from "../../Actuaciones/Components/bandejaTableCells";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { FONT_FAMILY_UI } from "../../../theme/typography";
import type { IComprobacionRecorridoRow } from "../../../api/actuacionesComprobacionActasApi";
import {
  recOficioDocumentalAgrupado,
  recOficioExpOtOrigenMotivosChips,
} from "../utils/recorridoOficioExpLabels";

const groupTitleSx = {
  fontFamily: FONT_FAMILY_UI,
  fontSize: "0.68rem",
  fontWeight: 700,
  letterSpacing: "0.06em",
  lineHeight: 1.2,
  color: GLASS_COLORS.textSecondary,
  textTransform: "uppercase" as const,
};

/**
 * Columna documental Recorrido: compacta con un oficio; agrupada con dos o más.
 */
export function RecorridoOficioDocumentalCell({ row }: { row: IComprobacionRecorridoRow }) {
  const grouped = recOficioDocumentalAgrupado(row);
  if (!grouped) {
    return <BandejaSegmentChipsCell segments={recOficioExpOtOrigenMotivosChips(row)} />;
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 0.75, maxWidth: "100%" }}>
      {grouped.otOrigen ? (
        <Tooltip title={grouped.otOrigen} placement="top-start" enterDelay={400}>
          <Chip size="medium" variant="outlined" label={grouped.otOrigen} sx={bandejaOutlinedChipSx} />
        </Tooltip>
      ) : null}
      {grouped.grupos.map((grupo) => (
        <Box
          key={grupo.titulo}
          sx={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 0.45, maxWidth: "100%" }}
        >
          <Typography component="span" sx={groupTitleSx}>
            {grupo.titulo}
          </Typography>
          {grupo.chips.map((text) => (
            <Tooltip key={`${grupo.titulo}-${text}`} title={text} placement="top-start" enterDelay={400}>
              <Chip size="medium" variant="outlined" label={text} sx={bandejaOutlinedChipSx} />
            </Tooltip>
          ))}
        </Box>
      ))}
      {grouped.motivos ? (
        <Box sx={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 0.45, maxWidth: "100%" }}>
          <Typography component="span" sx={groupTitleSx}>
            MOTIVOS
          </Typography>
          <Tooltip title={grouped.motivos} placement="top-start" enterDelay={400}>
            <Chip size="medium" variant="outlined" label={grouped.motivos} sx={bandejaOutlinedChipSx} />
          </Tooltip>
        </Box>
      ) : null}
    </Box>
  );
}
