import type { SxProps, Theme } from "@mui/material";

import { dialogFormGridSx } from "./formDialogStyles";
import { glassSecondaryTabsSx, moduleFiltersSurfaceSx } from "./GlassStyles";
import { responsiveLayout } from "../theme/tokens";
import { mergeSx } from "../utils/muiSx";

const MD = responsiveLayout.desktopMinBreakpoint;
const SM = responsiveLayout.dialogFullscreenMaxBreakpoint;

/**
 * Layout del paper de diálogo glass en viewports &lt; md (márgenes seguros, altura usable).
 * Componer sobre `glassDialogPaperSx` / `crudDialogPaperSx` — no redefine superficie glass.
 */
export const responsiveDialogPaperLayoutSx: SxProps<Theme> = {
    boxSizing: "border-box",
    [`@media (max-width: 899.95px)`]: {
        width: "calc(100% - 16px)",
        maxWidth: "calc(100% - 16px) !important",
        margin: "8px",
        maxHeight: "calc(100vh - 16px)",
    },
};

/** Layout fullscreen opcional en &lt; sm cuando `AppDialog` activa `mobileFullScreen`. */
export const responsiveDialogFullscreenPaperLayoutSx: SxProps<Theme> = {
    [`@media (max-width: 599.95px)`]: {
        width: "100%",
        maxWidth: "100%",
        height: "100dvh",
        maxHeight: "100dvh",
        minHeight: "100dvh",
        margin: 0,
        borderRadius: 0,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        boxSizing: "border-box",
    },
};

/** Contenido del diálogo en fullscreen móvil: solo el cuerpo interno hace scroll. */
export const responsiveDialogFullscreenContentLayoutSx: SxProps<Theme> = {
    [`@media (max-width: 599.95px)`]: {
        flex: "1 1 auto",
        minHeight: 0,
        maxHeight: "none",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
    },
};

/** Título y acciones fijos en fullscreen móvil. */
export const responsiveDialogFullscreenChromeSx: SxProps<Theme> = {
    [`@media (max-width: 599.95px)`]: {
        flexShrink: 0,
    },
};

/** Acciones del diálogo: envuelven en mobile sin cambiar tokens glass del pie. */
export const responsiveDialogActionsLayoutSx: SxProps<Theme> = {
    flexWrap: "wrap",
    [`@media (max-width: 899.95px)`]: {
        justifyContent: "flex-end",
        gap: 1,
    },
};

/**
 * Tabs glass existentes + scroll horizontal táctil en mobile (sin wrap).
 * Usar con `variant="scrollable"` en &lt; md vía `ResponsiveScrollableTabs`.
 */
export const responsiveScrollableTabsLayoutSx: SxProps<Theme> = {
    ...glassSecondaryTabsSx,
    minWidth: 0,
    "& .MuiTabs-scroller": {
        overflowX: "auto",
        WebkitOverflowScrolling: "touch",
    },
    [`@media (max-width: 899.95px)`]: {
        "& .MuiTabs-flexContainer": {
            flexWrap: "nowrap",
        },
    },
};

/** Superficie de filtros compartida (reexport composición existente). */
export const responsiveFiltersSurfaceSx: SxProps<Theme> = moduleFiltersSurfaceSx;

/** Cabecera compacta del panel de filtros en mobile. */
export const responsiveFiltersToolbarSx: SxProps<Theme> = {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    flexWrap: "wrap",
    gap: 1,
    width: "100%",
    minWidth: 0,
    boxSizing: "border-box",
};

/** Grid de formulario 1 columna en mobile (alias del patrón modal existente). */
export const responsiveFormGridSx: SxProps<Theme> = dialogFormGridSx;

/** Campos a ancho completo en mobile/desktop (controles MUI dentro del grid). */
export const responsiveFormFieldFullWidthSx: SxProps<Theme> = {
    width: "100%",
    minWidth: 0,
    maxWidth: "100%",
    boxSizing: "border-box",
    "& .MuiFormControl-root": {
        width: "100%",
    },
    "& .MuiAutocomplete-root": {
        width: "100%",
    },
};

/** Espaciado táctil mínimo en controles de formulario responsive. */
export const responsiveFormControlSpacingSx: SxProps<Theme> = {
    "& .MuiInputBase-root": {
        minHeight: 44,
    },
    "& .MuiButton-root": {
        minHeight: 44,
    },
};

export function mergeResponsiveTabsSx(extra?: SxProps<Theme>): SxProps<Theme> {
    return mergeSx(responsiveScrollableTabsLayoutSx, extra);
}

export const responsiveBreakpoints = {
    md: MD,
    sm: SM,
} as const;
