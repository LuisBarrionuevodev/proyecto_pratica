import AddIcon from "@mui/icons-material/Add";
import FactCheckIcon from "@mui/icons-material/FactCheck";
import FolderOpenIcon from "@mui/icons-material/FolderOpen";
import { Box, CircularProgress, Divider, Stack, Typography } from "@mui/material";
import { useEffect, useMemo, useState } from "react";

import { listRutasBorrador, type IRutaTrabajo } from "../../../api/rutasTrabajoApi";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { AppButton, CardGlass } from "../../../ui";

const tactic = '"Tactic Sans", sans-serif' as const;

function labelTurno(t: IRutaTrabajo["turno"]): string {
  if (t === "MANIANA") return "Mañana";
  if (t === "TARDE") return "Tarde";
  return t;
}

function labelBorrador(r: IRutaTrabajo): string {
  const fecha = r.fecha
    ? new Date(r.fecha + "T12:00:00").toLocaleDateString("es-AR", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
      })
    : "—";
  return `Ruta ${r.numero} · ${fecha} · ${labelTurno(r.turno)}`;
}

export type RutasEmptyViewProps = {
  /** Abre el modal de creación de ruta (BORRADOR). */
  onCrearBorrador: () => void;
  /** Carga el detalle de un borrador existente (solo BORRADOR desde API). */
  onAbrirBorrador: (rutaId: number) => void;
};

/**
 * Vista inicial cuando no hay borrador en sesión: lista borradores en DB, fecha de hoy y CTA para crear ruta.
 */
export function RutasEmptyView({ onCrearBorrador, onAbrirBorrador }: RutasEmptyViewProps) {
  const fechaHoyLegible = useMemo(
    () =>
      new Date().toLocaleDateString("es-AR", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
      }),
    []
  );

  const [borradores, setBorradores] = useState<IRutaTrabajo[]>([]);
  const [loadingLista, setLoadingLista] = useState(true);
  const [errorLista, setErrorLista] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoadingLista(true);
    setErrorLista(null);
    void listRutasBorrador({ per_page: 50, page: 1 })
      .then((resp) => {
        if (!cancelled) setBorradores(resp.items ?? []);
      })
      .catch(() => {
        if (!cancelled) {
          setBorradores([]);
          setErrorLista("No se pudo cargar la lista de borradores.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingLista(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Box
      sx={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        py: { xs: 2, sm: 4 },
        px: 1,
        minHeight: { xs: "auto", sm: "min(52vh, 420px)" },
      }}
    >
      <CardGlass
        sx={{
          maxWidth: 520,
          width: "100%",
          textAlign: "center",
        }}
        contentPadding="md"
      >
        <Stack spacing={2.25} alignItems="center">
          <Box
            sx={{
              width: 76,
              height: 76,
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              backgroundColor: "rgba(1, 102, 255, 0.1)",
              border: `1px solid ${GLASS_COLORS.borderActive}`,
              boxShadow: `0 0 24px ${GLASS_COLORS.primaryGlow}`,
            }}
            aria-hidden
          >
            <FactCheckIcon sx={{ fontSize: 38, color: GLASS_COLORS.primary }} />
          </Box>

          <Typography
            component="p"
            sx={{
              fontFamily: tactic,
              fontSize: "0.6875rem",
              fontWeight: 600,
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              color: GLASS_COLORS.textMuted,
              m: 0,
            }}
          >
            Planificación diaria
          </Typography>

          <Typography
            variant="h5"
            component="h2"
            sx={{
              fontFamily: tactic,
              fontWeight: 700,
              color: GLASS_COLORS.textPrimary,
              lineHeight: 1.25,
              m: 0,
            }}
          >
            Rutas de trabajo
          </Typography>

          <Typography
            sx={{
              fontFamily: tactic,
              fontSize: "1.375rem",
              fontWeight: 700,
              color: GLASS_COLORS.primary,
              lineHeight: 1.2,
              m: 0,
            }}
          >
            {fechaHoyLegible}
          </Typography>

          <Typography
            variant="body2"
            sx={{
              fontFamily: tactic,
              color: GLASS_COLORS.textSecondary,
              maxWidth: 400,
              mx: "auto",
              lineHeight: 1.55,
            }}
          >
            Podés reabrir un <strong>borrador</strong> guardado o crear una ruta nueva para hoy. Los borradores
            publicados no aparecen aquí.
          </Typography>

          {loadingLista && (
            <CircularProgress size={28} sx={{ color: GLASS_COLORS.primary }} aria-label="Cargando borradores" />
          )}

          {!loadingLista && errorLista && (
            <Typography variant="body2" sx={{ fontFamily: tactic, color: GLASS_COLORS.textMuted }}>
              {errorLista}
            </Typography>
          )}

          {!loadingLista && borradores.length > 0 && (
            <>
              <Divider
                flexItem
                sx={{ borderColor: GLASS_COLORS.borderMedium, opacity: 0.6, width: "100%", maxWidth: 420 }}
              />
              <Typography
                variant="subtitle2"
                sx={{
                  fontFamily: tactic,
                  fontWeight: 700,
                  color: GLASS_COLORS.textPrimary,
                  alignSelf: "stretch",
                  textAlign: "left",
                }}
              >
                Borradores pendientes
              </Typography>
              <Stack spacing={1} alignItems="stretch" sx={{ width: "100%", maxHeight: 280, overflowY: "auto" }}>
                {borradores.map((r) => (
                  <AppButton
                    key={r.id}
                    dsVariant="secondary"
                    dsSize="md"
                    fullWidth
                    startIcon={<FolderOpenIcon />}
                    onClick={() => onAbrirBorrador(r.id)}
                    sx={{
                      fontFamily: tactic,
                      fontWeight: 600,
                      justifyContent: "flex-start",
                      textAlign: "left",
                    }}
                  >
                    {labelBorrador(r)}
                  </AppButton>
                ))}
              </Stack>
            </>
          )}

          <Divider
            flexItem
            sx={{ borderColor: GLASS_COLORS.borderMedium, opacity: 0.6, width: "100%", maxWidth: 420 }}
          />

          <AppButton
            dsVariant="primary"
            dsSize="lg"
            fullWidth
            startIcon={<AddIcon />}
            onClick={onCrearBorrador}
            sx={{
              fontFamily: tactic,
              fontWeight: 700,
              mt: 0.5,
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            Crear nueva ruta
          </AppButton>
        </Stack>
      </CardGlass>
    </Box>
  );
}
