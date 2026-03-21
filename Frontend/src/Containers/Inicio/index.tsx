import { useEffect, useState, type JSX } from "react";
import InicioMapaResumenCard from "./Components/InicioMapaResumenCard";
import InicioOperacionesGrid from "./Components/InicioOperacionesGrid";
import TopBar from "../../Componets/TopBar";
import { Box, Grid, Typography } from "@mui/material";
import { GLASS_COLORS, glassContent } from "../../styles/GlassStyles";
import { apiClient } from "../../api/apiClient";

type MeResponse = {
  user: {
    username: string;
  };
  profile: {
    nickname: string | null;
  };
};

function formatFechaHoy(): string {
  return new Intl.DateTimeFormat("es-AR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date());
}

/**
 * Inicio — panel bajo TopBar: bienvenida + fecha, accesos, ruta, actas pendientes, indicadores y mapa.
 */
const Inicio = (): JSX.Element => {
  const [displayName, setDisplayName] = useState("Usuario");

  useEffect(() => {
    const fetchMe = async () => {
      try {
        const res = await apiClient.get<MeResponse>("/api/profile/me");
        setDisplayName(res.data.profile.nickname || res.data.user.username || "Usuario");
      } catch {
        setDisplayName("Usuario");
      }
    };
    fetchMe();
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
        sx={[
          glassContent,
          {
            flex: 1,
            minHeight: 0,
            borderTopLeftRadius: 0,
            borderTopRightRadius: 0,
            borderBottom: "none",
            overflow: "auto",
            // Sin backdrop-filter en el scroll: el blur recalcula cada frame y encarece el scroll (Chrome/Edge).
            backdropFilter: "none",
            WebkitBackdropFilter: "none",
            // Capa sólida equivalente al glass sin depender del fondo detrás del panel.
            backgroundColor: GLASS_COLORS.contentBg,
            "&::-webkit-scrollbar": {
              width: "6px",
            },
            "&::-webkit-scrollbar-thumb": {
              backgroundColor: "rgba(255, 255, 255, 0.1)",
              borderRadius: "3px",
            },
          },
        ]}
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
                    fontFamily: '"Tactic Sans", sans-serif',
                    fontSize: { xs: "22px", sm: "26px", md: "28px" },
                    fontWeight: 600,
                    color: GLASS_COLORS.textPrimary,
                    mb: 0.75,
                  }}
                >
                  Bienvenido, {displayName}
                </Typography>
                <Typography
                  sx={{
                    fontFamily: '"Tactic Sans", sans-serif',
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
                  fontFamily: '"Tactic Sans", sans-serif',
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
              <Grid size={{ xs: 12 }}>
                <InicioMapaResumenCard />
              </Grid>
            </Grid>
        </Box>
      </Box>
    </Box>
  );
};

export default Inicio;
