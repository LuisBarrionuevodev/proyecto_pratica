import { useMemo, type JSX } from "react";
import { Box, Grid, Skeleton, Stack } from "@mui/material";
import { Navigate } from "react-router-dom";

import { getVisibleHomeCards } from "../../../auth/accessConfig";
import { useAppSession } from "../../../auth/AppSessionProvider";
import InicioAccesoCard from "./InicioAccesoCard";

const GAP = 2;
const SKELETON_COUNT = 4;

/**
 * Accesos rápidos filtrados por rol (fuente única con NavLeft).
 * Default deny: skeleton hasta resolver sesión.
 */
export default function InicioOperacionesGrid(): JSX.Element {
  const { status, role } = useAppSession();

  const cards = useMemo(() => {
    if (status !== "ready" || !role) return [];
    return getVisibleHomeCards(role);
  }, [status, role]);

  if (status === "loading") {
    return (
      <Stack spacing={GAP}>
        <Grid container spacing={GAP}>
          {Array.from({ length: SKELETON_COUNT }, (_, i) => (
            <Grid key={i} size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
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
      <Grid container spacing={GAP}>
        {cards.map((item) => (
          <Grid key={item.to} size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
            <InicioAccesoCard item={item} />
          </Grid>
        ))}
      </Grid>
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
