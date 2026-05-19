import type { ReactNode } from "react";
import { Box, CircularProgress, Typography } from "@mui/material";

import {
  DATA_TABLE_MRT_GLASS_COLORS,
  dataTableMrtContentReadySx,
  dataTableMrtContentWhileLoadingSx,
  dataTableMrtLoadingOverlayMessageSx,
  dataTableMrtLoadingOverlaySx,
  dataTableMrtTypographyScopeSx,
  dataTableShellSx,
} from "../../styles/mrtGlassDataTablePreset";

/** Cómo muestra loading el shell (F3.10 / F3.10e). */
export type DataTableMrtLoadingMode =
  /** Spinner + overlay + atenuación (usar solo si la vista no tiene otro loading). */
  | "overlay"
  /** Wrapper tipográfico; el loading visible lo maneja MRT (`showProgressBars`). Default F3.10e. */
  | "progress"
  /** Sin indicador de carga en el shell. */
  | "none";

export type DataTableMrtShellProps = {
  /** Estado de carga (afecta overlay/fade solo en modo `overlay`). */
  loading?: boolean;
  loadingMessage?: string;
  /**
   * `progress` (default): evita doble animación con `state.isLoading` + `showProgressBars` de MRT.
   * `overlay`: spinner + fade sobre la tabla.
   * `none`: contenedor visual sin feedback de carga.
   */
  loadingMode?: DataTableMrtLoadingMode;
  children: ReactNode;
  footer?: ReactNode;
};

/**
 * Contenedor estándar F3.10 para tablas MRT: shell glass + tipografía unificada.
 * Combinar modo `progress` con `state.showProgressBars` en `useMaterialReactTable`.
 */
export function DataTableMrtShell({
  loading = false,
  loadingMessage = "Cargando…",
  loadingMode = "progress",
  children,
  footer,
}: DataTableMrtShellProps) {
  const showOverlay = loadingMode === "overlay" && loading;
  const dimContent = showOverlay;

  return (
    <Box sx={{ position: "relative", display: "flex", flexDirection: "column", gap: footer ? 1 : 0 }}>
      <Box sx={{ position: "relative" }}>
        {showOverlay ? (
          <Box sx={dataTableMrtLoadingOverlaySx} aria-hidden>
            <CircularProgress size={28} sx={{ color: DATA_TABLE_MRT_GLASS_COLORS.primary }} />
            <Typography variant="body2" sx={dataTableMrtLoadingOverlayMessageSx}>
              {loadingMessage}
            </Typography>
          </Box>
        ) : null}
        <Box
          sx={{
            ...(dimContent ? dataTableMrtContentWhileLoadingSx : dataTableMrtContentReadySx),
            ...dataTableShellSx,
            ...dataTableMrtTypographyScopeSx,
          }}
        >
          {children}
        </Box>
      </Box>
      {footer}
    </Box>
  );
}
