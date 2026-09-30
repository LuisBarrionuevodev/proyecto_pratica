import Box from "@mui/material/Box";
import type { SxProps, Theme } from "@mui/material/styles";

import {
    responsiveFormControlSpacingSx,
    responsiveFormFieldFullWidthSx,
    responsiveFormGridSx,
} from "../styles/responsivePatterns";
import { mergeSx } from "../utils/muiSx";

export type ResponsiveFormGridProps = {
    children: React.ReactNode;
    sx?: SxProps<Theme>;
    /** Aplica min-height táctil en inputs/botones del grid. */
    touchSpacing?: boolean;
};

/**
 * Grid de formulario compartido: 1 columna en xs, 2 en sm, 3 en md+ (`dialogFormGridSx`).
 */
export function ResponsiveFormGrid({ children, sx, touchSpacing = true }: ResponsiveFormGridProps) {
    return (
        <Box
            sx={mergeSx(
                responsiveFormGridSx,
                responsiveFormFieldFullWidthSx,
                touchSpacing ? responsiveFormControlSpacingSx : undefined,
                sx
            )}
        >
            {children}
        </Box>
    );
}
