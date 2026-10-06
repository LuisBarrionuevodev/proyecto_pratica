import AssignmentTurnedInIcon from "@mui/icons-material/AssignmentTurnedIn";
import { Box, CircularProgress, Stack, Typography } from "@mui/material";

import type { ICompletarTrabajoPendienteRow } from "../../../api/completarTrabajoApi";
import { formatCrudDialogOtReference } from "../../../components/crudDialog/crudDialogReference";
import { AppButton } from "../../../ui";
import { GLASS_COLORS, moduleContentPanelPaperSx } from "../../../styles/GlassStyles";
import { FONT_FAMILY_UI } from "../../../theme/typography";
import {
  completarTrabajoDomicilioLinea,
  completarTrabajoEstadoLabel,
  completarTrabajoOrigenTipoSegments,
  completarTrabajoTitularLinea,
} from "../utils/completarTrabajosListDisplay";
import {
  lineasEvidenciasPendientes,
  mediaResumenFromRow,
  rowTieneEvidenciasPendientes,
} from "../utils/completarTrabajoMediaPendingDisplay";

export type CompletarTrabajosMobileCardListProps = {
  rows: ICompletarTrabajoPendienteRow[];
  loading: boolean;
  total: number;
  page: number;
  perPage: number;
  onPageChange: (nextPage: number) => void;
  onOpenCompletarModal: (row: ICompletarTrabajoPendienteRow) => void;
};

const labelSx = {
  fontFamily: FONT_FAMILY_UI,
  fontSize: "0.6875rem",
  fontWeight: 700,
  letterSpacing: "0.06em",
  textTransform: "uppercase" as const,
  color: GLASS_COLORS.textMuted,
};

const valueSx = {
  fontFamily: FONT_FAMILY_UI,
  fontSize: "0.875rem",
  fontWeight: 500,
  color: GLASS_COLORS.textPrimary,
  lineHeight: 1.4,
  wordBreak: "break-word" as const,
};

/**
 * Listado móvil de trabajos pendientes (misma data y acción que `CompletarTrabajosMRT`).
 */
export function CompletarTrabajosMobileCardList({
  rows,
  loading,
  total,
  page,
  perPage,
  onPageChange,
  onOpenCompletarModal,
}: CompletarTrabajosMobileCardListProps) {
  const pageCount = Math.max(1, Math.ceil(total / perPage));

  return (
    <Stack spacing={1.5} sx={{ width: "100%", minWidth: 0 }}>
      {loading && rows.length === 0 ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
          <CircularProgress size={32} sx={{ color: GLASS_COLORS.textSecondary }} />
        </Box>
      ) : null}

      {rows.map((row) => {
        const otRef = formatCrudDialogOtReference(row.orden_trabajo_numero) ?? "OT —";
        const origen = completarTrabajoOrigenTipoSegments(row).join(" · ") || "—";
        const evidenciasPendientes = rowTieneEvidenciasPendientes(row);
        const lineasPend = lineasEvidenciasPendientes(mediaResumenFromRow(row));
        return (
          <Box
            key={row.ruta_item_id}
            sx={{
              ...moduleContentPanelPaperSx,
              p: 1.5,
              display: "flex",
              flexDirection: "column",
              gap: 1,
              minWidth: 0,
            }}
          >
            <Box sx={{ minWidth: 0 }}>
              <Typography sx={{ ...valueSx, fontWeight: 700, fontSize: "0.95rem" }}>{otRef}</Typography>
              <Typography sx={{ ...valueSx, color: GLASS_COLORS.textSecondary, fontSize: "0.8125rem", mt: 0.25 }}>
                {origen}
              </Typography>
            </Box>

            <Box>
              <Typography sx={labelSx}>Domicilio</Typography>
              <Typography sx={valueSx}>{completarTrabajoDomicilioLinea(row)}</Typography>
            </Box>
            <Box>
              <Typography sx={labelSx}>Rubro / titular</Typography>
              <Typography sx={valueSx}>{completarTrabajoTitularLinea(row)}</Typography>
            </Box>
            <Box>
              <Typography sx={labelSx}>Estado</Typography>
              <Typography sx={valueSx}>{completarTrabajoEstadoLabel(row)}</Typography>
            </Box>

            {evidenciasPendientes ? (
              <Box sx={{ borderTop: `1px solid ${GLASS_COLORS.borderLight}`, pt: 1 }}>
                <Typography sx={{ ...labelSx, color: GLASS_COLORS.primary }}>
                  TRABAJO GUARDADO · FOTOS PENDIENTES
                </Typography>
                {lineasPend.map((line) => (
                  <Typography key={line} sx={{ ...valueSx, fontSize: "0.8125rem" }}>
                    {line}
                  </Typography>
                ))}
              </Box>
            ) : null}

            <AppButton
              dsVariant="primary"
              dsSize="sm"
              fullWidth
              disabled={loading}
              onClick={() => onOpenCompletarModal(row)}
              startIcon={<AssignmentTurnedInIcon />}
            >
              {evidenciasPendientes ? "SUBIR FOTOS" : "Completar"}
            </AppButton>
          </Box>
        );
      })}

      {total > perPage ? (
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 1,
            flexWrap: "wrap",
          }}
        >
          <Typography variant="caption" sx={{ color: GLASS_COLORS.textMuted, fontFamily: FONT_FAMILY_UI }}>
            Página {page} de {pageCount} · {total} trabajos
          </Typography>
          <Box sx={{ display: "flex", gap: 1 }}>
            <AppButton
              dsVariant="secondary"
              dsSize="sm"
              disabled={loading || page <= 1}
              onClick={() => onPageChange(page - 1)}
            >
              Anterior
            </AppButton>
            <AppButton
              dsVariant="secondary"
              dsSize="sm"
              disabled={loading || page >= pageCount}
              onClick={() => onPageChange(page + 1)}
            >
              Siguiente
            </AppButton>
          </Box>
        </Box>
      ) : null}
    </Stack>
  );
}
