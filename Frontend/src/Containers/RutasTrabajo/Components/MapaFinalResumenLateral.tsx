import { Box, Stack, Typography } from "@mui/material";

import { GLASS_COLORS } from "../../../styles/GlassStyles";
import type { RutaMapaGrupoVista } from "../types/rutasTrabajoMapa.types";

function distritosDelGrupo(gv: RutaMapaGrupoVista): string[] {
  const s = new Set<string>();
  for (const it of gv.items) {
    const d = it.distritoNombre?.trim();
    if (d) s.add(d);
  }
  return Array.from(s).sort((a, b) => a.localeCompare(b, "es"));
}

/** Máx. caracteres de inspectores antes de truncar (densidad en panel angosto). */
const INSPECTORES_MAX = 72;

function recorteInspectores(s: string): string {
  const t = s.trim();
  if (t.length <= INSPECTORES_MAX) return t;
  return `${t.slice(0, INSPECTORES_MAX - 1)}…`;
}

export type MapaFinalResumenLateralProps = {
  gruposVista: RutaMapaGrupoVista[];
};

/**
 * Panel de solo lectura para Mapa final: leyenda compacta por grupo (color, ítems, inspectores, distritos).
 */
export function MapaFinalResumenLateral({ gruposVista }: MapaFinalResumenLateralProps) {
  if (gruposVista.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.45, fontSize: "0.8125rem" }}>
        No hay grupos en esta ruta. Volvé a <strong>Asignación</strong> para armar equipos y cargar trabajos.
      </Typography>
    );
  }

  return (
    <Stack spacing={1} sx={{ pb: 0.25 }}>
      {gruposVista.map((gv) => {
        const distritos = distritosDelGrupo(gv);
        const distritosTxt =
          distritos.length > 0
            ? distritos.length <= 2
              ? distritos.join(" · ")
              : `${distritos.slice(0, 2).join(" · ")} +${distritos.length - 2}`
            : null;

        return (
          <Box
            key={gv.id}
            sx={{
              borderRadius: 1.5,
              pl: 1.25,
              py: 0.875,
              pr: 1,
              borderLeft: `3px solid ${gv.color}`,
              backgroundColor: "rgba(0,0,0,0.18)",
              border: `1px solid ${GLASS_COLORS.borderLight}`,
              borderLeftWidth: 3,
              borderLeftColor: gv.color,
            }}
          >
            <Stack direction="row" alignItems="baseline" justifyContent="space-between" gap={0.75} sx={{ flexWrap: "nowrap" }}>
              <Typography
                variant="body2"
                sx={{
                  fontWeight: 700,
                  fontSize: "0.8125rem",
                  lineHeight: 1.35,
                  flex: 1,
                  minWidth: 0,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
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
                  color: "text.secondary",
                  flexShrink: 0,
                }}
              >
                ×{gv.itemCount}
              </Typography>
            </Stack>
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ display: "block", mt: 0.35, lineHeight: 1.35, fontSize: "0.7rem" }}
              title={gv.inspectoresResumen}
            >
              {recorteInspectores(gv.inspectoresResumen)}
            </Typography>
            {distritosTxt ? (
              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.25, lineHeight: 1.35, fontSize: "0.7rem", opacity: 0.95 }} title={distritos.join(" · ")}>
                {distritosTxt}
              </Typography>
            ) : (
              <Typography variant="caption" sx={{ display: "block", mt: 0.25, fontSize: "0.68rem", opacity: 0.75 }}>
                Sin distrito en datos
              </Typography>
            )}
          </Box>
        );
      })}

      <Typography variant="caption" color="text.secondary" sx={{ lineHeight: 1.4, fontSize: "0.68rem", pt: 0.5, opacity: 0.88 }}>
        ¿Cambios de grupo u OT? <strong>Asignación</strong>
      </Typography>
    </Stack>
  );
}
