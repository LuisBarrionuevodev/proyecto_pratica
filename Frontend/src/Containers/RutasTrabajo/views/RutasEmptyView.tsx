import AddIcon from "@mui/icons-material/Add";
import FactCheckIcon from "@mui/icons-material/FactCheck";
import FolderOpenIcon from "@mui/icons-material/FolderOpen";
import PublishedWithChangesIcon from "@mui/icons-material/PublishedWithChanges";
import { Box, CircularProgress, Divider, Stack, TextField, ToggleButton, ToggleButtonGroup, Typography } from "@mui/material";
import { useEffect, useMemo, useState } from "react";

import { listRutasBorrador, listRutasTrabajo, type IRutaTrabajo } from "../../../api/rutasTrabajoApi";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { AppButton, CardGlass } from "../../../ui";

const tactic = '"Tactic Sans", sans-serif' as const;

function toIsoDateLocal(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function labelTurno(t: IRutaTrabajo["turno"]): string {
  if (t === "MANIANA") return "Mañana";
  if (t === "TARDE") return "Tarde";
  return t;
}

function labelFilaRuta(r: IRutaTrabajo): string {
  const fecha = r.fecha
    ? new Date(r.fecha + "T12:00:00").toLocaleDateString("es-AR", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
      })
    : "—";
  const estado = r.estado_ruta === "PUBLICADA" ? "" : ` · ${r.estado_ruta}`;
  return `Ruta ${r.numero} · ${fecha} · ${labelTurno(r.turno)}${estado}`;
}

export type RutasListaTab = "borradores" | "publicadas";

export type RutasEmptyViewProps = {
  /** Abre el modal de creación de ruta (BORRADOR). */
  onCrearBorrador: () => void;
  /** Carga detalle por id (`getRutaTrabajoDetail`): borrador desde listado por defecto o publicada desde pestaña Publicadas. */
  onAbrirRuta: (rutaId: number) => void;
};

/**
 * Vista inicial cuando no hay ruta en sesión: borradores o publicadas con filtro por día, y CTA crear ruta.
 */
export function RutasEmptyView({ onCrearBorrador, onAbrirRuta }: RutasEmptyViewProps) {
  const fechaHoyLegible = useMemo(
    () =>
      new Date().toLocaleDateString("es-AR", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
      }),
    []
  );

  const [tab, setTab] = useState<RutasListaTab>("borradores");
  const [fechaPublicadas, setFechaPublicadas] = useState(() => toIsoDateLocal(new Date()));

  const [borradores, setBorradores] = useState<IRutaTrabajo[]>([]);
  const [publicadas, setPublicadas] = useState<IRutaTrabajo[]>([]);
  const [loadingLista, setLoadingLista] = useState(true);
  const [errorLista, setErrorLista] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      setLoadingLista(true);
      setErrorLista(null);
      try {
        if (tab === "borradores") {
          const resp = await listRutasBorrador({ per_page: 50, page: 1 });
          if (!cancelled) setBorradores(resp.items ?? []);
        } else {
          const resp = await listRutasTrabajo({
            estado_ruta: "PUBLICADA",
            fecha: fechaPublicadas,
            per_page: 50,
            page: 1,
          });
          if (!cancelled) setPublicadas(resp.items ?? []);
        }
      } catch {
        if (!cancelled) {
          if (tab === "borradores") setBorradores([]);
          else setPublicadas([]);
          setErrorLista(
            tab === "borradores" ? "No se pudo cargar la lista de borradores." : "No se pudo cargar la lista de rutas publicadas."
          );
        }
      } finally {
        if (!cancelled) setLoadingLista(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [tab, fechaPublicadas]);

  const listaActual = tab === "borradores" ? borradores : publicadas;

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
          maxWidth: tab === "publicadas" ? 560 : 520,
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

          <ToggleButtonGroup
            exclusive
            value={tab}
            onChange={(_, v: RutasListaTab | null) => {
              if (v != null) setTab(v);
            }}
            aria-label="Tipo de listado de rutas"
            fullWidth
            sx={{
              alignSelf: "stretch",
              maxWidth: 420,
              "& .MuiToggleButton-root": {
                fontFamily: tactic,
                fontWeight: 600,
                fontSize: "0.8125rem",
                textTransform: "none",
                flex: 1,
                py: 1,
              },
            }}
          >
            <ToggleButton value="borradores">Borradores</ToggleButton>
            <ToggleButton value="publicadas">Publicadas</ToggleButton>
          </ToggleButtonGroup>

          {tab === "borradores" && (
            <>
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
                Podés reabrir un <strong>borrador</strong> guardado o crear una ruta nueva. Usá{" "}
                <strong>Publicadas</strong> para ver rutas ya publicadas por día.
              </Typography>
            </>
          )}

          {tab === "publicadas" && (
            <>
              <Typography
                variant="body2"
                sx={{
                  fontFamily: tactic,
                  color: GLASS_COLORS.textSecondary,
                  maxWidth: 440,
                  mx: "auto",
                  lineHeight: 1.55,
                }}
              >
                Rutas en estado <strong>PUBLICADA</strong> para el día elegido. Al abrir una verás la{" "}
                <strong>consulta histórica</strong> (solo lectura: mapa y resumen operativo, sin edición).
              </Typography>
              <TextField
                label="Día"
                type="date"
                value={fechaPublicadas}
                onChange={(e) => setFechaPublicadas(e.target.value)}
                InputLabelProps={{ shrink: true }}
                size="small"
                sx={{
                  alignSelf: "stretch",
                  maxWidth: 280,
                  "& .MuiInputBase-root": { fontFamily: tactic },
                  "& .MuiInputLabel-root": { fontFamily: tactic },
                }}
              />
            </>
          )}

          {loadingLista && (
            <CircularProgress size={28} sx={{ color: GLASS_COLORS.primary }} aria-label="Cargando listado" />
          )}

          {!loadingLista && errorLista && (
            <Typography variant="body2" sx={{ fontFamily: tactic, color: GLASS_COLORS.textMuted }}>
              {errorLista}
            </Typography>
          )}

          {!loadingLista && !errorLista && tab === "publicadas" && publicadas.length === 0 && (
            <Typography variant="body2" sx={{ fontFamily: tactic, color: GLASS_COLORS.textMuted, px: 1 }}>
              No hay rutas publicadas para esta fecha.
            </Typography>
          )}

          {!loadingLista && listaActual.length > 0 && (
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
                {tab === "borradores" ? "Borradores pendientes" : "Rutas publicadas"}
              </Typography>
              <Stack spacing={1} alignItems="stretch" sx={{ width: "100%", maxHeight: 280, overflowY: "auto" }}>
                {listaActual.map((r) => (
                  <AppButton
                    key={r.id}
                    dsVariant="secondary"
                    dsSize="md"
                    fullWidth
                    startIcon={tab === "borradores" ? <FolderOpenIcon /> : <PublishedWithChangesIcon />}
                    onClick={() => onAbrirRuta(r.id)}
                    sx={{
                      fontFamily: tactic,
                      fontWeight: 600,
                      justifyContent: "flex-start",
                      textAlign: "left",
                    }}
                  >
                    {labelFilaRuta(r)}
                  </AppButton>
                ))}
              </Stack>
            </>
          )}

          {tab === "borradores" && (
            <>
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
            </>
          )}
        </Stack>
      </CardGlass>
    </Box>
  );
}
