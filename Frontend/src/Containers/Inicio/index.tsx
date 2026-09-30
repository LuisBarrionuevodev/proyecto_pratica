import { type JSX, useEffect } from "react";
import InicioOperacionesGrid from "./Components/InicioOperacionesGrid";
import TopBar from "../../Componets/TopBar";
import { Box, Grid, Skeleton, Typography } from "@mui/material";
import { GLASS_COLORS } from "../../styles/GlassStyles";
import { useAppSession } from "../../auth/AppSessionProvider";
import { FONT_FAMILY_UI } from "../../theme/typography";
import { setBodyAuthenticatedRoute } from "../../theme/bodyRouteClass";
import { CSS_VAR_NAMES } from "../../theme/applyCssVariables";

function formatFechaHoy(): string {
  return new Intl.DateTimeFormat("es-AR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date());
}

/**
 * Inicio — panel bajo TopBar: bienvenida + fecha, accesos filtrados por rol.
 */
const Inicio = (): JSX.Element => {
  const session = useAppSession();
  const welcomeName =
    session.status === "loading"
      ? null
      : session.displayName ?? session.toolbarPrimary;

  useEffect(() => {
    setBodyAuthenticatedRoute(true);
    return () => setBodyAuthenticatedRoute(false);
  }, []);

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        width: "100vw",
        overflow: "hidden",
        bgcolor: "transparent",
      }}
    >
      <Box
        component="header"
        sx={{
          height: "56px",
          flexShrink: 0,
          bgcolor: "transparent",
        }}
      >
        <TopBar />
      </Box>

      <Box
        sx={{
          flex: 1,
          minHeight: 0,
          overflow: "auto",
          backgroundColor: "transparent",
          border: "none",
          boxShadow: "none",
          backdropFilter: "none",
          WebkitBackdropFilter: "none",
          "&::-webkit-scrollbar": {
            width: "6px",
          },
          "&::-webkit-scrollbar-thumb": {
            backgroundColor: `var(${CSS_VAR_NAMES.scrollbarThumb})`,
            borderRadius: "3px",
          },
          "&::-webkit-scrollbar-thumb:hover": {
            backgroundColor: `var(${CSS_VAR_NAMES.scrollbarThumbHover})`,
          },
        }}
      >
        <Box sx={{ p: { xs: 2, sm: 3, md: 4 } }}>
            <Box
              sx={{
                display: "flex",
                flexDirection: { xs: "column", sm: "row" },
                alignItems: { xs: "flex-start", sm: "flex-start" },
                justifyContent: "space-between",
                gap: { xs: 1.5, sm: 2 },
                mb: { xs: 2.5, md: 3 },
              }}
            >
              <Box sx={{ maxWidth: { sm: "65%", md: "70%" } }}>
                <Typography
                  sx={{
                    fontFamily: FONT_FAMILY_UI,
                    fontSize: { xs: "22px", sm: "26px", md: "28px" },
                    fontWeight: 600,
                    color: GLASS_COLORS.textPrimary,
                    mb: 0.75,
                  }}
                >
                  {session.status === "loading" ? (
                    <Skeleton variant="text" width={280} sx={{ fontSize: "inherit" }} />
                  ) : (
                    <>Bienvenido, {welcomeName}</>
                  )}
                </Typography>
                <Typography
                  sx={{
                    fontFamily: FONT_FAMILY_UI,
                    fontSize: { xs: "13px", sm: "14px" },
                    fontWeight: 400,
                    color: GLASS_COLORS.textMuted,
                    lineHeight: 1.45,
                  }}
                >
                  Accesos rápidos al operativo: rutas, relevamientos, actuaciones y mapa territorial.
                </Typography>
              </Box>
              <Typography
                sx={{
                  fontFamily: FONT_FAMILY_UI,
                  fontSize: { xs: "13px", sm: "14px" },
                  fontWeight: 500,
                  color: GLASS_COLORS.textPrimary,
                  textTransform: "capitalize",
                  whiteSpace: { sm: "nowrap" },
                  alignSelf: { xs: "flex-start", sm: "flex-start" },
                  pt: { sm: 0.5 },
                }}
              >
                {formatFechaHoy()}
              </Typography>
            </Box>

            <Grid container spacing={2}>
              <Grid size={{ xs: 12 }}>
                <InicioOperacionesGrid />
              </Grid>
            </Grid>
        </Box>
      </Box>
    </Box>
  );
};

export default Inicio;
