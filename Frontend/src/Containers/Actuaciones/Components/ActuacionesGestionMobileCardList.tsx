import VisibilityIcon from "@mui/icons-material/Visibility";
import { Box, CircularProgress, Stack, Typography } from "@mui/material";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import { AppButton } from "../../../ui";
import { GLASS_COLORS, moduleContentPanelPaperSx } from "../../../styles/GlassStyles";
import { FONT_FAMILY_UI } from "../../../theme/typography";
import {
  actuacionGestionMobileDomicilio,
  actuacionGestionMobileEstado,
  actuacionGestionMobileFecha,
  actuacionGestionMobileIdentificador,
  actuacionGestionMobileOrigen,
  actuacionGestionMobileTitular,
} from "../utils/actuacionGestionMobileDisplay";
import { ActuacionesGestionListPagination } from "./ActuacionesGestionListPagination";

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

export type ActuacionesGestionMobileCardListProps = {
  rows: IActuacionListItem[];
  loading: boolean;
  hideRowActions?: boolean;
  listadoServidor?: {
    totalRowCount: number;
    page: number;
    pageSize: number;
    onPageChange: (page: number, pageSize: number) => void;
  };
  onOpenDetalle: (row: IActuacionListItem) => void;
};

/**
 * Vista móvil de Gestión de Actuaciones (misma data y modal CRUD que la tabla MRT).
 * Con `listadoServidor`, solo muestra la página vigente devuelta por el padre.
 */
export function ActuacionesGestionMobileCardList({
  rows,
  loading,
  hideRowActions = false,
  listadoServidor,
  onOpenDetalle,
}: ActuacionesGestionMobileCardListProps) {
  const paginationBar =
    listadoServidor != null ? (
      <ActuacionesGestionListPagination
        page={listadoServidor.page}
        pageSize={listadoServidor.pageSize}
        totalRowCount={listadoServidor.totalRowCount}
        loading={loading}
        onPageChange={listadoServidor.onPageChange}
      />
    ) : null;

  return (
    <Stack spacing={1.5} sx={{ width: "100%", minWidth: 0 }} data-testid="actuaciones-gestion-mobile-cards">
      {paginationBar}

      {loading && rows.length === 0 ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
          <CircularProgress size={32} sx={{ color: GLASS_COLORS.textSecondary }} />
        </Box>
      ) : null}

      {!loading && rows.length === 0 ? (
        <Typography
          variant="body2"
          sx={{ color: GLASS_COLORS.textMuted, fontFamily: FONT_FAMILY_UI, textAlign: "center", py: 2 }}
        >
          Sin actuaciones en esta página.
        </Typography>
      ) : null}

      {rows.map((row) => (
        <Box
          key={row.id}
          sx={{
            ...moduleContentPanelPaperSx,
            p: 1.5,
            display: "flex",
            flexDirection: "column",
            gap: 1,
            minWidth: 0,
            opacity: loading ? 0.72 : 1,
            pointerEvents: loading ? "none" : "auto",
          }}
        >
          <Box sx={{ minWidth: 0 }}>
            <Typography sx={{ ...valueSx, fontWeight: 700, fontSize: "0.95rem" }}>
              {actuacionGestionMobileIdentificador(row)}
            </Typography>
            <Typography sx={{ ...valueSx, color: GLASS_COLORS.textSecondary, fontSize: "0.8125rem", mt: 0.25 }}>
              {actuacionGestionMobileFecha(row)} · {actuacionGestionMobileOrigen(row)}
            </Typography>
          </Box>

          <Box>
            <Typography sx={labelSx}>Titular</Typography>
            <Typography sx={valueSx}>{actuacionGestionMobileTitular(row)}</Typography>
          </Box>
          <Box>
            <Typography sx={labelSx}>Domicilio</Typography>
            <Typography sx={valueSx}>{actuacionGestionMobileDomicilio(row)}</Typography>
          </Box>
          <Box>
            <Typography sx={labelSx}>Estado</Typography>
            <Typography sx={valueSx}>{actuacionGestionMobileEstado(row)}</Typography>
          </Box>

          {!hideRowActions ? (
            <AppButton
              dsVariant="primary"
              dsSize="sm"
              fullWidth
              disabled={loading}
              onClick={() => onOpenDetalle(row)}
              startIcon={<VisibilityIcon />}
            >
              Ver / editar
            </AppButton>
          ) : null}
        </Box>
      ))}

      {paginationBar}
    </Stack>
  );
}
