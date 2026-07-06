import { Chip, Stack } from "@mui/material";
import { sliceLabel } from "../domicilioSliceTabs";
import { SECONDARY_FILTERS_FOR_VIEW } from "../domicilioViewTabs";
import type { DomiciliosViewTab } from "../domicilioViewTabs";
import type { DomiciliosSlice } from "../types";

type Props = {
  view: DomiciliosViewTab;
  value: DomiciliosSlice | "all";
  onChange: (value: DomiciliosSlice | "all") => void;
};

/** Filtros secundarios por slice interno (legacy seguro PR6B). */
export function DomicilioSliceFilterChips({ view, value, onChange }: Props) {
  const options = SECONDARY_FILTERS_FOR_VIEW[view];
  if (options.length <= 1) return null;

  return (
    <Stack direction="row" flexWrap="wrap" gap={0.75} useFlexGap sx={{ mb: 1.5 }}>
      {options.map((opt) => {
        const label = opt === "all" ? "Todos" : sliceLabel(opt);
        const selected = value === opt;
        return (
          <Chip
            key={opt}
            label={label}
            size="small"
            variant={selected ? "filled" : "outlined"}
            color={selected ? "primary" : "default"}
            onClick={() => onChange(opt)}
          />
        );
      })}
    </Stack>
  );
}
