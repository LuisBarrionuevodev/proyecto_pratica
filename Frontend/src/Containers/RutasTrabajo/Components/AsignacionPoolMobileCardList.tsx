import { useCallback, useMemo } from "react";
import { Box, Checkbox, Chip, Stack, Typography } from "@mui/material";

import type { IRutaIniciadorPendienteRow } from "../../../api/rutasTrabajoApi";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { FONT_FAMILY_UI } from "../../../theme/typography";
import { detalleOperativoTexto } from "../utils/iniciadorDetalleOperativo";
import {
  domicilioLineaAsignacion,
  prioridadDisplayOperativo,
  rubroLineaAsignacion,
  tipoLabelOperativo,
} from "../utils/asignacionTableDisplay";
import { rutasInstitutionalItemPaperSx, rutasOperativaChipSx } from "../styles/institutionalVisual";

export type AsignacionPoolMobileCardListProps = {
  rows: IRutaIniciadorPendienteRow[];
  selectedIds: number[];
  assignedIniciadorIds: Set<number>;
  onSelectionChange: (ids: number[]) => void;
};

/**
 * Proyección móvil del pool de Asignación (misma selección por iniciador_id que MRT).
 */
export function AsignacionPoolMobileCardList({
  rows,
  selectedIds,
  assignedIniciadorIds,
  onSelectionChange,
}: AsignacionPoolMobileCardListProps) {
  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds]);

  const toggleRow = useCallback(
    (row: IRutaIniciadorPendienteRow) => {
      if (assignedIniciadorIds.has(row.id)) return;
      const next = selectedSet.has(row.id)
        ? selectedIds.filter((id) => id !== row.id)
        : [...selectedIds, row.id];
      onSelectionChange(next);
    },
    [assignedIniciadorIds, onSelectionChange, selectedIds, selectedSet]
  );

  if (rows.length === 0) {
    return (
      <Typography sx={{ fontFamily: FONT_FAMILY_UI, fontSize: "0.8125rem", color: GLASS_COLORS.textMuted, py: 1 }}>
        Ningún ítem visible con los filtros actuales.
      </Typography>
    );
  }

  return (
    <Stack spacing={1} data-testid="asignacion-pool-mobile-list" sx={{ width: "100%", minWidth: 0 }}>
      {rows.map((row) => {
        const selectable = !assignedIniciadorIds.has(row.id);
        const checked = selectable && selectedSet.has(row.id);
        const tipo = tipoLabelOperativo(row);
        const prioridad = prioridadDisplayOperativo(row);
        const domicilio = domicilioLineaAsignacion(row);
        const rubro = rubroLineaAsignacion(row);
        const detalle = detalleOperativoTexto(row);

        return (
          <Box
            key={row.id}
            component="label"
            data-testid={`asignacion-pool-mobile-card-${row.id}`}
            sx={{
              ...rutasInstitutionalItemPaperSx,
              display: "flex",
              gap: 1,
              alignItems: "flex-start",
              minWidth: 0,
              cursor: selectable ? "pointer" : "default",
              opacity: selectable ? 1 : 0.55,
            }}
          >
            <Checkbox
              checked={checked}
              disabled={!selectable}
              onChange={() => toggleRow(row)}
              sx={{ p: 0.25, mt: 0.15, flexShrink: 0 }}
              inputProps={{ "aria-label": `Seleccionar ${domicilio}` }}
            />
            <Stack spacing={0.5} sx={{ minWidth: 0, flex: 1 }}>
              <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap alignItems="center">
                <Typography
                  sx={{
                    fontFamily: FONT_FAMILY_UI,
                    fontSize: "0.8125rem",
                    fontWeight: 600,
                    lineHeight: 1.35,
                    color: GLASS_COLORS.textPrimary,
                    wordBreak: "break-word",
                  }}
                >
                  {tipo}
                </Typography>
                {prioridad ? (
                  <Chip
                    label={prioridad.label}
                    size="small"
                    variant="outlined"
                    sx={{
                      ...rutasOperativaChipSx,
                      height: 24,
                      backgroundColor: prioridad.bg,
                      color: prioridad.color,
                      borderColor: prioridad.color,
                      "& .MuiChip-label": { fontWeight: 700, color: prioridad.color },
                    }}
                  />
                ) : null}
              </Stack>
              <Typography
                sx={{
                  fontFamily: FONT_FAMILY_UI,
                  fontSize: "0.8125rem",
                  fontWeight: 600,
                  lineHeight: 1.35,
                  color: GLASS_COLORS.textPrimary,
                  wordBreak: "break-word",
                }}
              >
                {domicilio}
              </Typography>
              {rubro ? (
                <Typography sx={{ fontFamily: FONT_FAMILY_UI, fontSize: "0.75rem", color: GLASS_COLORS.textMuted, lineHeight: 1.3 }}>
                  {rubro}
                </Typography>
              ) : null}
              {detalle ? (
                <Typography
                  sx={{
                    fontFamily: FONT_FAMILY_UI,
                    fontSize: "0.75rem",
                    color: GLASS_COLORS.textSecondary,
                    lineHeight: 1.35,
                    wordBreak: "break-word",
                  }}
                >
                  {detalle}
                </Typography>
              ) : null}
            </Stack>
          </Box>
        );
      })}
    </Stack>
  );
}
