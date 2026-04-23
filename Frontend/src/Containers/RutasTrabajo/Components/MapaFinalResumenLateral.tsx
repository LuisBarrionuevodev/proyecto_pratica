import { Box, Button, Chip, Divider, Stack, Tooltip, Typography } from "@mui/material";

import type { IRutaGrupoMin } from "../../../api/rutasTrabajoApi";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import {
  planificacionPanelSubtitleSx,
  planificacionPanelTitleSx,
  rutasAsignacionNeutralContainedButtonSx,
} from "../styles/institutionalVisual";
import type { RutaMapaGrupoVista, RutaMapaItemVista } from "../types/rutasTrabajoMapa.types";

const EM = "—";

function distritosDelGrupo(gv: RutaMapaGrupoVista): string[] {
  const s = new Set<string>();
  for (const it of gv.items) {
    const d = it.distritoNombre?.trim();
    if (d) s.add(d);
  }
  return Array.from(s).sort((a, b) => a.localeCompare(b, "es"));
}

function chipLabelInspector(fila: { nombre: string; legajo: string | null }): string {
  if (fila.legajo) return `${fila.nombre} · Leg. ${fila.legajo}`;
  return fila.nombre;
}

function DireccionRow({ it }: { it: RutaMapaItemVista }) {
  const sinMapa = it.lat == null || it.lng == null;
  const tipoTxt = it.tipoIniciadorLabel ?? EM;
  const rubroTxt = it.rubroNombre?.trim() || null;
  const otTxt = it.ordenTrabajoLabel?.trim() || null;

  return (
    <Box
      sx={{
        pl: 1,
        py: 0.75,
        borderLeft: `2px solid ${GLASS_COLORS.borderMedium}`,
        bgcolor: "rgba(0,0,0,0.12)",
        borderRadius: "0 8px 8px 0",
      }}
    >
      <Typography
        variant="body2"
        sx={{
          fontWeight: 600,
          color: GLASS_COLORS.textPrimary,
          lineHeight: 1.35,
          fontSize: "0.8125rem",
        }}
      >
        {it.orden}. {it.etiqueta}
      </Typography>
      <Stack spacing={0.25} sx={{ mt: 0.5 }}>
        {rubroTxt ? (
          <Typography variant="caption" sx={{ color: GLASS_COLORS.textSecondary, lineHeight: 1.35, fontSize: "0.72rem" }}>
            Rubro: {rubroTxt}
          </Typography>
        ) : null}
        <Typography variant="caption" sx={{ color: GLASS_COLORS.textSecondary, lineHeight: 1.35, fontSize: "0.72rem" }}>
          Tipo: {tipoTxt}
        </Typography>
        {otTxt ? (
          <Typography variant="caption" sx={{ color: GLASS_COLORS.textSecondary, lineHeight: 1.35, fontSize: "0.72rem" }}>
            {otTxt}
          </Typography>
        ) : null}
        {sinMapa ? (
          <Typography variant="caption" sx={{ color: "warning.light", lineHeight: 1.35, fontSize: "0.68rem" }}>
            Sin ubicación en mapa
          </Typography>
        ) : it.geoStatusLabel && String(it.geoStatus ?? "").toUpperCase() !== "OK" ? (
          <Typography variant="caption" sx={{ color: GLASS_COLORS.textMuted, lineHeight: 1.35, fontSize: "0.68rem" }}>
            {it.geoStatusLabel}
          </Typography>
        ) : null}
      </Stack>
    </Box>
  );
}

export type MapaFinalResumenLateralProps = {
  gruposVista: RutaMapaGrupoVista[];
  /** Grupos del borrador (API) para abrir el modal con el objeto completo. */
  gruposModelo?: IRutaGrupoMin[];
  /** Mismo handler que Asignación → `ModalAsignarInspectoresGrupo`. */
  onEditarInspectores?: (grupo: IRutaGrupoMin) => void;
  /** `false` si la ruta no es editable (p. ej. no BORRADOR) o hay carga de detalle. */
  puedeEditarEquipos?: boolean;
  /** Oculta por completo acciones de equipo (no solo deshabilitadas). */
  readOnly?: boolean;
};

const BOTON_EQUIPO_SX = {
  ...rutasAsignacionNeutralContainedButtonSx,
  minHeight: 26,
  minWidth: 0,
  py: 0.25,
  px: 1,
  fontSize: "0.68rem",
  lineHeight: 1.2,
} as const;

/**
 * Panel operativo Mapa final: grupos con inspectores y listado numerado de direcciones (domicilio, rubro, tipo, OT).
 */
export function MapaFinalResumenLateral({
  gruposVista,
  gruposModelo = [],
  onEditarInspectores,
  puedeEditarEquipos = false,
  readOnly = false,
}: MapaFinalResumenLateralProps) {
  if (gruposVista.length === 0) {
    return (
      <Typography sx={{ ...planificacionPanelSubtitleSx, fontSize: "0.8125rem", lineHeight: 1.45, color: GLASS_COLORS.textSecondary }}>
        {readOnly ? (
          "No hay grupos con datos en esta ruta (consulta histórica)."
        ) : (
          <>
            No hay grupos. Usá <strong style={{ color: GLASS_COLORS.textPrimary }}>Asignación</strong> para armar equipos.
          </>
        )}
      </Typography>
    );
  }

  return (
    <Stack spacing={1.5} sx={{ pb: 0.5 }}>
      {gruposVista.map((gv) => {
        const distritos = distritosDelGrupo(gv);
        const distritosLine =
          distritos.length === 0 ? EM : distritos.length <= 2 ? distritos.join(" · ") : `${distritos.slice(0, 2).join(" · ")} +${distritos.length - 2}`;
        const grupoMin = gruposModelo.find((g) => g.id === gv.id);

        return (
          <Box
            key={gv.id}
            sx={{
              borderRadius: 1.5,
              p: 1.25,
              border: `1px solid ${GLASS_COLORS.borderLight}`,
              borderLeft: `4px solid ${gv.color}`,
              backgroundColor: "rgba(0,0,0,0.2)",
            }}
          >
            <Stack spacing={1.25}>
              <Box>
                <Stack direction="row" alignItems="flex-start" justifyContent="space-between" gap={1} sx={{ flexWrap: "nowrap" }}>
                  <Typography
                    sx={{
                      ...planificacionPanelTitleSx,
                      fontSize: "0.875rem",
                      lineHeight: 1.3,
                      flex: 1,
                      minWidth: 0,
                    }}
                    title={gv.nombre}
                  >
                    {gv.nombre}
                  </Typography>
                  <Typography
                    component="span"
                    variant="caption"
                    sx={{
                      fontWeight: 700,
                      fontVariantNumeric: "tabular-nums",
                      color: GLASS_COLORS.textSecondary,
                      flexShrink: 0,
                      fontSize: "0.7rem",
                    }}
                  >
                    {gv.itemCount} {gv.itemCount === 1 ? "dirección" : "direcciones"}
                  </Typography>
                </Stack>
                <Typography
                  variant="caption"
                  sx={{ display: "block", mt: 0.5, color: GLASS_COLORS.textMuted, fontSize: "0.68rem", lineHeight: 1.35 }}
                >
                  Distrito: {distritosLine}
                </Typography>
              </Box>

              <Box>
                <Stack direction="row" alignItems="center" justifyContent="space-between" gap={0.75} sx={{ mb: 0.5 }}>
                  <Typography
                    variant="caption"
                    sx={{
                      color: GLASS_COLORS.textMuted,
                      fontSize: "0.65rem",
                      letterSpacing: "0.06em",
                      textTransform: "uppercase",
                    }}
                  >
                    Inspectores
                  </Typography>
                  {!readOnly && onEditarInspectores && grupoMin ? (
                    <Tooltip title={puedeEditarEquipos ? "Editar inspectores" : "Solo con borrador."}>
                      <span>
                        <Button
                          type="button"
                          size="small"
                          variant="contained"
                          disableElevation
                          disabled={!puedeEditarEquipos}
                          onClick={() => onEditarInspectores(grupoMin)}
                          sx={BOTON_EQUIPO_SX}
                        >
                          Equipo
                        </Button>
                      </span>
                    </Tooltip>
                  ) : null}
                </Stack>
                {gv.inspectoresFilas.length === 0 ? (
                  <Typography variant="caption" sx={{ color: GLASS_COLORS.textSecondary, fontSize: "0.75rem" }}>
                    {EM}
                  </Typography>
                ) : (
                  <Stack direction="row" flexWrap="wrap" gap={0.5} useFlexGap>
                    {gv.inspectoresFilas.map((f) => (
                      <Chip
                        key={`${gv.id}-insp-${f.inspectorId}`}
                        size="small"
                        variant="outlined"
                        label={chipLabelInspector(f)}
                        sx={{
                          height: "auto",
                          py: 0.35,
                          "& .MuiChip-label": {
                            whiteSpace: "normal",
                            fontSize: "0.7rem",
                            lineHeight: 1.25,
                            color: GLASS_COLORS.textPrimary,
                          },
                          borderColor: GLASS_COLORS.borderLight,
                          bgcolor: "rgba(255,255,255,0.04)",
                        }}
                      />
                    ))}
                  </Stack>
                )}
              </Box>

              <Divider sx={{ borderColor: GLASS_COLORS.borderLight, opacity: 0.6 }} />

              <Box>
                <Typography
                  variant="caption"
                  sx={{
                    display: "block",
                    mb: 0.75,
                    color: GLASS_COLORS.textMuted,
                    fontSize: "0.65rem",
                    letterSpacing: "0.06em",
                    textTransform: "uppercase",
                  }}
                >
                  Direcciones
                </Typography>
                <Stack spacing={0.75}>
                  {gv.items.map((it) => (
                    <DireccionRow key={it.itemId} it={it} />
                  ))}
                </Stack>
              </Box>
            </Stack>
          </Box>
        );
      })}
    </Stack>
  );
}
