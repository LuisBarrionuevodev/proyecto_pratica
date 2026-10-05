import type { ReactNode } from "react";
import { Box, Typography } from "@mui/material";

import { FONT_FAMILY_UI } from "../../../theme/typography";
import { recuperarCardShellSx } from "../../../styles/RecuperarCuentaStyles";

type RecuperarCuentaStepShellProps = {
  title: string;
  subtitle?: ReactNode;
  children: ReactNode;
};

/** Caja neo-brutalista compartida por las tres etapas de recuperación. */
export function RecuperarCuentaStepShell({
  title,
  subtitle,
  children,
}: RecuperarCuentaStepShellProps) {
  return (
    <Box
      sx={{
        width: "100%",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        minWidth: 0,
      }}
    >
      <Box sx={recuperarCardShellSx}>
        <Typography
          sx={{
            fontFamily: FONT_FAMILY_UI,
            fontWeight: 500,
            fontSize: { xs: "1.75rem", sm: "2rem" },
            textAlign: "center",
            lineHeight: 1.2,
          }}
        >
          {title}
        </Typography>
        {subtitle ? (
          <Typography
            sx={{
              fontFamily: FONT_FAMILY_UI,
              fontSize: { xs: "0.9375rem", sm: "1rem" },
              fontWeight: 500,
              textAlign: "center",
              px: { xs: 0, sm: 1 },
            }}
          >
            {subtitle}
          </Typography>
        ) : null}
        <Box
          sx={{
            width: "100%",
            display: "flex",
            flexDirection: "column",
            alignItems: "stretch",
            gap: { xs: 2, sm: 2.5 },
            minWidth: 0,
          }}
        >
          {children}
        </Box>
      </Box>
    </Box>
  );
}
