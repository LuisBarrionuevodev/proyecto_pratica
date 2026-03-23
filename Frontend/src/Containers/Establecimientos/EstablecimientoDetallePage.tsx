import { useMemo, useState } from "react";
import { Link as RouterLink, useNavigate, useParams } from "react-router-dom";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import DescriptionIcon from "@mui/icons-material/Description";
import LocationOnIcon from "@mui/icons-material/LocationOn";
import StorefrontIcon from "@mui/icons-material/Storefront";
import AddIcon from "@mui/icons-material/Add";
import VisibilityIcon from "@mui/icons-material/Visibility";
import { Box, Grid, Link, Paper, Stack, Tab, Tabs, Typography } from "@mui/material";
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
} from "material-react-table";

import { AppButton } from "../../ui";
import { COLORS, gridContainerStyles } from "../CargarActuaciones/styles/cargarActuacionesStyles";
import { DARK_TABLE_CONFIG } from "../Actuaciones/styles/actuacionesTableStyles";
import { glassCard } from "../../styles/GlassStyles";
import { getMockEstablecimientoById } from "./mocks/establecimientosMock";
import type { IHistorialInspeccionRow } from "./types/establecimientos.types";
import { ResultadoInspeccionChip } from "./components/ResultadoInspeccionChip";

/**
 * Ficha de establecimiento (mock): encabezado + pestañas Información / Actuaciones (historial de inspecciones).
 */
export default function EstablecimientoDetallePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [tab, setTab] = useState<"info" | "actuaciones">("info");

  const detalle = id ? getMockEstablecimientoById(id) : undefined;

  const colsHistorial = useMemo<MRT_ColumnDef<IHistorialInspeccionRow>[]>(
    () => [
      { accessorKey: "fecha", header: "FECHA", size: 150 },
      { accessorKey: "tipoInspeccion", header: "TIPO DE INSPECCIÓN", size: 220 },
      { accessorKey: "ordenTrabajo", header: "ORDEN DE TRABAJO", size: 140 },
      { accessorKey: "inspectoresIniciales", header: "INSPECTORES", size: 100 },
      {
        accessorKey: "resultado",
        header: "RESULTADO",
        size: 130,
        Cell: ({ cell }) => (
          <ResultadoInspeccionChip resultado={cell.getValue() as IHistorialInspeccionRow["resultado"]} />
        ),
      },
    ],
    []
  );

  const tableHistorial = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    columns: colsHistorial,
    data: detalle?.historialInspecciones ?? [],
    getRowId: (r) => r.id,
    enableEditing: false,
    enableRowSelection: false,
    enableColumnFilters: false,
    enableGlobalFilter: false,
    enablePagination: false,
    enableBottomToolbar: false,
    initialState: { density: "compact" },
    enableRowActions: true,
    positionActionsColumn: "last",
    displayColumnDefOptions: { "mrt-row-actions": { header: "", size: 56 } },
    renderRowActions: () => (
      <AppButton dsVariant="ghost" dsSize="sm" aria-label="Ver" sx={{ minWidth: 0, p: 0.5 }}>
        <VisibilityIcon sx={{ fontSize: 20, color: COLORS.primary }} />
      </AppButton>
    ),
  });

  if (!detalle) {
    return (
      <Stack spacing={2} sx={{ p: 1 }}>
        <AppButton
          dsVariant="secondary"
          startIcon={<ArrowBackIcon />}
          component={RouterLink}
          to="/establecimientos"
        >
          Volver al listado
        </AppButton>
        <Typography sx={{ color: COLORS.white, fontFamily: '"Tactic Sans", sans-serif' }}>
          No se encontró el establecimiento (mock).
        </Typography>
      </Stack>
    );
  }

  const estadoColor =
    detalle.estadoAdmin === "HABILITADO"
      ? COLORS.successText
      : detalle.estadoAdmin === "PENDIENTE"
        ? COLORS.warningText
        : COLORS.errorText;

  return (
    <Stack spacing={2} sx={{ width: "100%", maxWidth: "100%" }}>
      <AppButton
        dsVariant="ghost"
        startIcon={<ArrowBackIcon />}
        onClick={() => navigate("/establecimientos")}
        sx={{ color: "rgba(255,255,255,0.75)", alignSelf: "flex-start" }}
      >
        Volver
      </AppButton>

      <Paper elevation={0} sx={{ ...glassCard, p: 2.5 }}>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems={{ sm: "flex-start" }}>
          <Box
            sx={{
              width: 72,
              height: 72,
              borderRadius: "8px",
              border: `1px solid ${COLORS.border}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              backgroundColor: "rgba(1, 102, 255, 0.12)",
              flexShrink: 0,
            }}
          >
            <StorefrontIcon sx={{ fontSize: 40, color: COLORS.primary }} />
          </Box>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography
              sx={{
                fontFamily: '"Tactic Sans", sans-serif',
                fontWeight: 700,
                fontSize: { xs: "16px", sm: "20px" },
                color: COLORS.white,
                letterSpacing: "0.04em",
                lineHeight: 1.25,
              }}
            >
              {detalle.razonSocial}
            </Typography>
            <Typography
              sx={{
                mt: 0.75,
                fontFamily: '"Tactic Sans", sans-serif',
                fontSize: "12px",
                fontWeight: 600,
                color: COLORS.primary,
                letterSpacing: "0.06em",
              }}
            >
              RUBRO: {detalle.rubroDetalle}
            </Typography>
            <Grid container spacing={2} sx={{ mt: 1.5 }}>
              <Grid size={{ xs: 12, sm: 4 }}>
                <Meta label="Titular del establecimiento" value={`${detalle.nombre} ${detalle.apellido}`} />
              </Grid>
              <Grid size={{ xs: 12, sm: 4 }}>
                <Meta label="Documento de identidad" value={`DNI ${detalle.dni}`} />
              </Grid>
              <Grid size={{ xs: 12, sm: 4 }}>
                <Stack direction="row" spacing={1} alignItems="center">
                  <Typography
                    sx={{
                      fontSize: "10px",
                      fontWeight: 600,
                      letterSpacing: "0.08em",
                      color: "rgba(255,255,255,0.45)",
                    }}
                  >
                    ESTADO ADMINISTRATIVO
                  </Typography>
                  <Box
                    sx={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      bgcolor: estadoColor,
                    }}
                  />
                  <Typography sx={{ fontSize: "13px", fontWeight: 600, color: COLORS.white }}>
                    {detalle.estadoAdmin}
                  </Typography>
                </Stack>
              </Grid>
            </Grid>
          </Box>
        </Stack>
      </Paper>

      <Paper elevation={0} sx={{ ...glassCard, overflow: "hidden" }}>
        <Tabs
          value={tab}
          onChange={(_, v) => setTab(v)}
          sx={{
            borderBottom: `1px solid ${COLORS.border}`,
            px: 1,
            "& .MuiTab-root": {
              fontFamily: '"Tactic Sans", sans-serif',
              fontSize: "11px",
              fontWeight: 600,
              letterSpacing: "0.08em",
              color: "rgba(255,255,255,0.55)",
            },
            "& .Mui-selected": { color: `${COLORS.primary} !important` },
          }}
        >
          <Tab value="info" label="Información" />
          <Tab value="actuaciones" label="Actuaciones" />
        </Tabs>

        <Box sx={{ p: 2 }}>
          {tab === "info" && (
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, md: 6 }}>
                <Paper elevation={0} sx={{ ...gridContainerStyles, p: 2, height: "100%" }}>
                  <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5 }}>
                    <LocationOnIcon sx={{ color: COLORS.primary, fontSize: 22 }} />
                    <Typography
                      sx={{
                        fontSize: "11px",
                        fontWeight: 700,
                        letterSpacing: "0.1em",
                        color: COLORS.white,
                      }}
                    >
                      UBICACIÓN
                    </Typography>
                  </Stack>
                  <Box
                    sx={{
                      height: 200,
                      borderRadius: "8px",
                      border: `1px solid ${COLORS.border}`,
                      background:
                        "linear-gradient(145deg, rgba(30,33,39,1) 0%, rgba(43,46,52,1) 100%)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      mb: 1.5,
                    }}
                  >
                    <LocationOnIcon sx={{ fontSize: 48, color: COLORS.primary, opacity: 0.85 }} />
                  </Box>
                  <Typography sx={{ fontSize: "12px", color: "rgba(255,255,255,0.75)", lineHeight: 1.5 }}>
                    {detalle.direccionCompleta}
                  </Typography>
                </Paper>
              </Grid>
              <Grid size={{ xs: 12, md: 6 }}>
                <Paper elevation={0} sx={{ ...gridContainerStyles, p: 2, height: "100%" }}>
                  <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5 }}>
                    <DescriptionIcon sx={{ color: COLORS.primary, fontSize: 22 }} />
                    <Typography
                      sx={{
                        fontSize: "11px",
                        fontWeight: 700,
                        letterSpacing: "0.1em",
                        color: COLORS.white,
                      }}
                    >
                      DOCUMENTOS ÚLTIMA INSPECCIÓN
                    </Typography>
                  </Stack>
                  <Typography sx={{ fontSize: "13px", color: "rgba(255,255,255,0.55)", lineHeight: 1.6 }}>
                    Próximamente podrás consultar y descargar los documentos asociados a la última inspección del
                    establecimiento.
                  </Typography>
                </Paper>
              </Grid>
            </Grid>
          )}

          {tab === "actuaciones" && (
            <Stack spacing={1.5}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={1}>
                <Typography
                  sx={{
                    fontFamily: '"Tactic Sans", sans-serif',
                    fontSize: "12px",
                    fontWeight: 700,
                    letterSpacing: "0.08em",
                    color: COLORS.white,
                  }}
                >
                  Actuaciones e inspecciones
                </Typography>
                <AppButton
                  dsVariant="primary"
                  dsSize="sm"
                  startIcon={<AddIcon />}
                  onClick={() => {}}
                  sx={{ fontWeight: 700, letterSpacing: "0.06em" }}
                >
                  Nueva inspección
                </AppButton>
              </Stack>
              {detalle.historialInspecciones.length === 0 ? (
                <Typography sx={{ color: "rgba(255,255,255,0.5)", fontSize: "13px" }}>
                  No hay registros en este mock.
                </Typography>
              ) : (
                <MaterialReactTable table={tableHistorial} />
              )}
              <Typography sx={{ fontSize: "11px", color: COLORS.primary }}>
                <Link
                  component="button"
                  type="button"
                  underline="hover"
                  onClick={() => {}}
                  sx={{ fontFamily: '"Tactic Sans", sans-serif', cursor: "pointer" }}
                >
                  Ver historial completo (mock)
                </Link>
              </Typography>
            </Stack>
          )}
        </Box>
      </Paper>
    </Stack>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <Box>
      <Typography
        sx={{
          fontSize: "10px",
          fontWeight: 600,
          letterSpacing: "0.08em",
          color: "rgba(255,255,255,0.45)",
          mb: 0.5,
        }}
      >
        {label}
      </Typography>
      <Typography sx={{ fontSize: "13px", fontWeight: 600, color: COLORS.white }}>{value}</Typography>
    </Box>
  );
}
