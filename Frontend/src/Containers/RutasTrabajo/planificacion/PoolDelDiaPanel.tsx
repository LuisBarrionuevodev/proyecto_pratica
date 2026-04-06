import { Box, Stack, Typography } from "@mui/material";
import type { IRutaIniciadorPendienteRow } from "../../../api/rutasTrabajoApi";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { AppButton } from "../../../ui";
import { rutasInstitutionalPanelPaperSx } from "../styles/institutionalVisual";

const tactic = '"Tactic Sans", sans-serif' as const;

export type PoolDelDiaPanelProps = {
  items: IRutaIniciadorPendienteRow[];
  onQuitar: (id: number) => void;
  onContinuarAsignacion: () => void;
};

/**
 * Pool local: lista con scroll; CTA fijo al pie.
 */
export function PoolDelDiaPanel({ items, onQuitar, onContinuarAsignacion }: PoolDelDiaPanelProps) {
  return (
    <Stack
      sx={{
        ...rutasInstitutionalPanelPaperSx,
        flexShrink: 0,
        minHeight: 0,
        maxHeight: "min(32vh, 320px)",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
      spacing={1}
    >
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ flexShrink: 0 }}>
        <Typography sx={{ fontFamily: tactic, fontWeight: 700, fontSize: "0.95rem", color: GLASS_COLORS.textPrimary }}>
          Pool del día
        </Typography>
        <Typography sx={{ fontFamily: tactic, fontSize: "0.8rem", color: GLASS_COLORS.textSecondary }}>Total: {items.length}</Typography>
      </Stack>

      <Box sx={{ flex: 1, minHeight: 0, overflow: "auto" }}>
        {items.length === 0 ? (
          <Typography sx={{ fontFamily: tactic, fontSize: "0.8rem", color: GLASS_COLORS.textSecondary }}>
            Agregá ítems desde pendientes o urgentes.
          </Typography>
        ) : (
          <Stack spacing={0.75}>
            {items.map((row) => (
              <Stack
                key={row.id}
                direction="row"
                alignItems="center"
                justifyContent="space-between"
                spacing={1}
                sx={{
                  py: 0.5,
                  borderBottom: `1px solid ${GLASS_COLORS.borderLight}`,
                }}
              >
                <Typography sx={{ fontFamily: tactic, fontSize: "0.78rem" }} noWrap title={row.domicilio_texto ?? ""}>
                  #{row.id} · {row.tipo_iniciador.replace(/_/g, " ")}
                </Typography>
                <AppButton dsVariant="ghost" dsSize="sm" onClick={() => onQuitar(row.id)}>
                  Quitar
                </AppButton>
              </Stack>
            ))}
          </Stack>
        )}
      </Box>

      <Box sx={{ flexShrink: 0, pt: 0.5 }}>
        <AppButton dsVariant="primary" fullWidth onClick={onContinuarAsignacion} disabled={items.length === 0}>
          Continuar a asignación
        </AppButton>
      </Box>
    </Stack>
  );
}
