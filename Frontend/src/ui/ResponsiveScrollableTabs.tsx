import type { ReactNode } from "react";
import Paper from "@mui/material/Paper";
import Tabs, { type TabsProps } from "@mui/material/Tabs";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useTheme } from "@mui/material/styles";
import type { SxProps, Theme } from "@mui/material/styles";

import { glassTabsSecondaryPanelBarSx } from "../styles/GlassStyles";
import { mergeResponsiveTabsSx } from "../styles/responsivePatterns";
import { responsiveLayout } from "../theme/tokens";
import { mergeSx } from "../utils/muiSx";

export type ResponsiveScrollableTabsProps = TabsProps & {
    /** Envoltorio glass secundario (como Relevamientos / planificación). Default true. */
    withGlassBar?: boolean;
    barSx?: SxProps<Theme>;
    children: ReactNode;
};

/**
 * Tabs institucionales con scroll horizontal en viewports &lt; md.
 * Reutiliza `glassSecondaryTabsSx` sin duplicar estilos por módulo.
 */
export function ResponsiveScrollableTabs({
    withGlassBar = true,
    barSx,
    sx,
    children,
    variant,
    scrollButtons = "auto",
    allowScrollButtonsMobile = true,
    ...rest
}: ResponsiveScrollableTabsProps) {
    const theme = useTheme();
    const isDesktop = useMediaQuery(theme.breakpoints.up(responsiveLayout.desktopMinBreakpoint));

    const tabsVariant = variant ?? (isDesktop ? "standard" : "scrollable");
    const mergedTabsSx = mergeResponsiveTabsSx(sx);

    const tabs = (
        <Tabs
            variant={tabsVariant}
            scrollButtons={scrollButtons}
            allowScrollButtonsMobile={allowScrollButtonsMobile}
            sx={mergedTabsSx}
            {...rest}
        >
            {children}
        </Tabs>
    );

    if (!withGlassBar) {
        return tabs;
    }

    return (
        <Paper elevation={0} sx={mergeSx(glassTabsSecondaryPanelBarSx, { width: "100%" }, barSx)}>
            {tabs}
        </Paper>
    );
}
