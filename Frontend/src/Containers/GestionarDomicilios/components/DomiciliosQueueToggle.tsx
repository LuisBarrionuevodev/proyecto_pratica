import { Box, ToggleButton, ToggleButtonGroup, Typography } from "@mui/material";

import { GLASS_COLORS, glassCard } from "../../../styles/GlassStyles";

export type DomiciliosQueueFocus = "all" | "nomenclatura" | "geolocalizacion";

type Props = {
  value: DomiciliosQueueFocus;
  onChange: (next: DomiciliosQueueFocus) => void;
  nomenclaturaCount: number;
  geolocalizacionCount: number;
  pendingQuery: boolean;
};

/**
 * Selector de cola de trabajo con conteos en vivo (sustituye tarjetas KPI superiores).
 *
 * Total = suma nomenclatura + geolocalización; un mismo domicilio puede aparecer en ambas colas.
 */
const DomiciliosQueueToggle = ({
  value,
  onChange,
  nomenclaturaCount,
  geolocalizacionCount,
  pendingQuery,
}: Props) => {
  const totalSum = nomenclaturaCount + geolocalizacionCount;
  const dash = pendingQuery ? "—" : null;
  const t = dash ?? totalSum;
  const n = dash ?? nomenclaturaCount;
  const g = dash ?? geolocalizacionCount;

  return (
    <Box
      sx={{
        ...glassCard,
        p: 2,
        mb: 2,
      }}
    >
      <Typography
        sx={{
          fontFamily: '"Tactic Sans", sans-serif',
          fontSize: "11px",
          fontWeight: 600,
          letterSpacing: "0.1em",
          color: GLASS_COLORS.textMuted,
          mb: 1.5,
        }}
      >
        Pendientes por cola
      </Typography>
      <ToggleButtonGroup
        exclusive
        value={value}
        onChange={(_, v) => {
          if (v != null) onChange(v);
        }}
        fullWidth
        sx={{
          flexWrap: "wrap",
          gap: 1,
          "& .MuiToggleButtonGroup-grouped": {
            border: `1px solid ${GLASS_COLORS.borderMedium} !important`,
            borderRadius: "10px !important",
            fontFamily: '"Tactic Sans", sans-serif',
            fontSize: "12px",
            fontWeight: 600,
            color: GLASS_COLORS.textSecondary,
            textTransform: "none",
            py: 1.25,
            flex: "1 1 200px",
            "&.Mui-selected": {
              color: GLASS_COLORS.primary,
              backgroundColor: "rgba(1, 102, 255, 0.12) !important",
            },
          },
        }}
      >
        <ToggleButton value="all">
          Todos ({t})
        </ToggleButton>
        <ToggleButton value="nomenclatura">
          Nomenclatura ({n})
        </ToggleButton>
        <ToggleButton value="geolocalizacion">
          Geolocalización ({g})
        </ToggleButton>
      </ToggleButtonGroup>
      <Typography variant="caption" sx={{ display: "block", mt: 1.25, color: GLASS_COLORS.textMuted }}>
        El total es la suma de ambas colas; un mismo domicilio puede figurar en nomenclatura y en geolocalización.
      </Typography>
    </Box>
  );
};

export default DomiciliosQueueToggle;
