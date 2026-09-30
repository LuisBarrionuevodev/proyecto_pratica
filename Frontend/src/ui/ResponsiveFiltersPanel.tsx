import { useState, type ReactNode } from "react";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useTheme } from "@mui/material/styles";
import type { SxProps, Theme } from "@mui/material/styles";

import {
    responsiveFiltersSurfaceSx,
    responsiveFiltersToolbarSx,
} from "../styles/responsivePatterns";
import { responsiveLayout } from "../theme/tokens";
import { mergeSx } from "../utils/muiSx";
import { AppButton } from "./AppButton";

export type ResponsiveFiltersPanelProps = {
    children: ReactNode;
    /** Chips o resumen de filtros activos (siempre visible en mobile). */
    activeFiltersSlot?: ReactNode;
    surfaceSx?: SxProps<Theme>;
    /** Estado inicial del panel en mobile (desktop siempre expandido). */
    defaultMobileExpanded?: boolean;
    showFiltersLabel?: string;
    hideFiltersLabel?: string;
};

/**
 * Contenedor de filtros: desktop sin cambios; mobile con toggle Mostrar/Ocultar.
 * El contenido permanece montado (Collapse) para no perder estado.
 */
export function ResponsiveFiltersPanel({
    children,
    activeFiltersSlot,
    surfaceSx,
    defaultMobileExpanded = false,
    showFiltersLabel = "Mostrar filtros",
    hideFiltersLabel = "Ocultar filtros",
}: ResponsiveFiltersPanelProps) {
    const theme = useTheme();
    const isDesktop = useMediaQuery(theme.breakpoints.up(responsiveLayout.desktopMinBreakpoint));
    const [mobileExpanded, setMobileExpanded] = useState(defaultMobileExpanded);

    const expanded = isDesktop || mobileExpanded;

    return (
        <Box sx={mergeSx(responsiveFiltersSurfaceSx, surfaceSx)}>
            <Box sx={responsiveFiltersToolbarSx}>
                {!isDesktop ? (
                    <AppButton
                        type="button"
                        dsVariant="secondary"
                        dsSize="sm"
                        onClick={() => setMobileExpanded((v) => !v)}
                        aria-expanded={expanded}
                    >
                        {expanded ? hideFiltersLabel : showFiltersLabel}
                    </AppButton>
                ) : null}
                {activeFiltersSlot ? (
                    <Box sx={{ flex: 1, minWidth: 0, display: "flex", flexWrap: "wrap", gap: 0.75 }}>
                        {activeFiltersSlot}
                    </Box>
                ) : null}
            </Box>

            {isDesktop ? (
                <Box sx={{ width: "100%", minWidth: 0, mt: 1 }}>{children}</Box>
            ) : (
                <Collapse in={mobileExpanded}>
                    <Box sx={{ width: "100%", minWidth: 0, pt: 1 }}>{children}</Box>
                </Collapse>
            )}
        </Box>
    );
}
