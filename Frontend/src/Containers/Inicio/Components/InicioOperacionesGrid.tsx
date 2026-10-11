import { useMemo, type JSX } from "react";
import { Box, Grid, Skeleton, Stack } from "@mui/material";
import { Navigate } from "react-router-dom";

import { getVisibleHomeCards } from "../../../auth/accessConfig";
import { MAPA_PATH } from "../../../auth/roles";
import { useAppSession } from "../../../auth/AppSessionProvider";
import InicioAccesoCard from "./InicioAccesoCard";
import InicioAboutCard from "./InicioAboutCard";
import InicioMapaHeroCard from "./InicioMapaHeroCard";

const GAP = 2;
const SKELETON_COUNT = 4;

const MOBILE_GRID_SIZE = { xs: 12, sm: 6, md: 4, lg: 3 } as const;
const DESKTOP_GRID_SIZE = { xs: 12, sm: 6, md: 4, lg: 4 } as const;

/**
 * Accesos rápidos filtrados por rol (fuente única con NavLeft).
 * Desktop (md+): fila operativa → mapa hero → Acerca de. Mobile/tablet: grilla clásica.
 */
export default function InicioOperacionesGrid(): JSX.Element {
  const { status, role } = useAppSession();

  const cards = useMemo(() => {
    if (status !== "ready" || !role) return [];
    return getVisibleHomeCards(role);
  }, [status, role]);

  const mapCard = useMemo(() => cards.find((c) => c.to === MAPA_PATH), [cards]);
  const operationalCards = useMemo(
    () => cards.filter((c) => c.to !== MAPA_PATH),
    [cards]
  );

  if (status === "loading") {
    return (
      <Stack spacing={GAP}>
        <Grid container spacing={GAP}>
          {Array.from({ length: SKELETON_COUNT }, (_, i) => (
            <Grid key={i} size={MOBILE_GRID_SIZE}>
              <Skeleton variant="rounded" height={128} sx={{ borderRadius: "12px" }} />
            </Grid>
          ))}
        </Grid>
      </Stack>
    );
  }

  if (status === "unauthenticated") {
    return <Navigate to="/login" replace />;
  }

  if (status === "error" || !role) {
    return (
      <TypographyFallback message="No se pudo cargar tu perfil. Volvé a iniciar sesión." />
    );
  }

  return (
    <Stack spacing={GAP}>
      <Box sx={{ display: { xs: "block", md: "none" } }}>
        <Grid container spacing={GAP}>
          {cards.map((item) => (
            <Grid key={item.to} size={MOBILE_GRID_SIZE}>
              <InicioAccesoCard item={item} variant="compact" />
            </Grid>
          ))}
        </Grid>
        <Box sx={{ mt: GAP }}>
          <InicioAboutCard />
        </Box>
      </Box>

      <Box sx={{ display: { xs: "none", md: "flex" }, flexDirection: "column", gap: GAP }}>
        <Grid container spacing={GAP}>
          {operationalCards.map((item) => (
            <Grid key={item.to} size={DESKTOP_GRID_SIZE}>
              <InicioAccesoCard item={item} variant="desktop" />
            </Grid>
          ))}
        </Grid>
        {mapCard ? <InicioMapaHeroCard item={mapCard} /> : null}
        <InicioAboutCard />
      </Box>
    </Stack>
  );
}

function TypographyFallback({ message }: { message: string }): JSX.Element {
  return (
    <Box sx={{ py: 2 }}>
      <Box component="p" sx={{ m: 0, color: "rgba(255,255,255,0.55)", fontSize: "0.875rem" }}>
        {message}
      </Box>
    </Box>
  );
}
