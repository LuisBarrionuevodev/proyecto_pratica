import { Box, Typography } from "@mui/material";

import { AppButton } from "../../../ui";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { FONT_FAMILY_UI } from "../../../theme/typography";

export type ActuacionesGestionListPaginationProps = {
  page: number;
  pageSize: number;
  totalRowCount: number;
  loading?: boolean;
  onPageChange: (page: number, pageSize: number) => void;
};

/**
 * Pie de paginación servidor (misma semántica que MRT `manualPagination` en desktop).
 */
export function ActuacionesGestionListPagination({
  page,
  pageSize,
  totalRowCount,
  loading = false,
  onPageChange,
}: ActuacionesGestionListPaginationProps) {
  const pageCount = Math.max(1, Math.ceil(totalRowCount / Math.max(pageSize, 1)));
  const canPrev = page > 1;
  const canNext = page < pageCount;

  return (
    <Box
      data-testid="actuaciones-gestion-pagination"
      sx={{
        width: "100%",
        minWidth: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "stretch",
        gap: 1,
        py: 0.5,
      }}
    >
      <Typography
        variant="body2"
        sx={{
          color: GLASS_COLORS.textMuted,
          fontFamily: FONT_FAMILY_UI,
          textAlign: { xs: "center", sm: "left" },
          fontSize: { xs: "0.8125rem", sm: "0.875rem" },
          lineHeight: 1.4,
        }}
      >
        Página {page} de {pageCount}
        <Typography component="span" sx={{ display: { xs: "block", sm: "inline" } }}>
          {" "}
          · {totalRowCount} actuaciones
        </Typography>
      </Typography>
      <Box
        sx={{
          display: "flex",
          flexDirection: { xs: "column", sm: "row" },
          gap: 1,
          width: "100%",
          minWidth: 0,
        }}
      >
        <AppButton
          dsVariant="secondary"
          dsSize="sm"
          fullWidth
          disabled={loading || !canPrev}
          onClick={() => onPageChange(page - 1, pageSize)}
        >
          Anterior
        </AppButton>
        <AppButton
          dsVariant="secondary"
          dsSize="sm"
          fullWidth
          disabled={loading || !canNext}
          onClick={() => onPageChange(page + 1, pageSize)}
        >
          Siguiente
        </AppButton>
      </Box>
    </Box>
  );
}
