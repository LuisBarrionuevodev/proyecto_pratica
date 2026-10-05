import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
} from "@mui/material";
import { useEffect, useMemo, useState } from "react";

import type { IndicadoresMonthSelection } from "../utils/indicadoresMonthYearRange";
import {
  MESES_ES,
  formatIndicadoresMonthYearLabel,
  indicadoresYearOptions,
  isFutureIndicadoresMonth,
} from "../utils/indicadoresMonthYearRange";

export type IndicadoresMonthPickerDialogProps = {
  open: boolean;
  initialSelection: IndicadoresMonthSelection | null;
  onClose: () => void;
  onApply: (selection: IndicadoresMonthSelection) => void;
};

export function IndicadoresMonthPickerDialog({
  open,
  initialSelection,
  onClose,
  onApply,
}: IndicadoresMonthPickerDialogProps) {
  const now = useMemo(() => new Date(), [open]);
  const yearOptions = useMemo(() => indicadoresYearOptions(now), [now]);

  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);

  useEffect(() => {
    if (!open) return;
    const base = initialSelection ?? {
      year: now.getFullYear(),
      month: now.getMonth() + 1,
    };
    setYear(base.year);
    setMonth(base.month);
  }, [open, initialSelection, now]);

  const previewLabel = formatIndicadoresMonthYearLabel({ year, month });
  const selectionValid = !isFutureIndicadoresMonth(year, month, now);

  const handleApply = () => {
    if (!selectionValid) return;
    onApply({ year, month });
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>Elegir mes</DialogTitle>
      <DialogContent>
        <FormControl fullWidth size="small" sx={{ mt: 0.5, mb: 2 }}>
          <InputLabel id="indicadores-month-year-label">Año</InputLabel>
          <Select
            labelId="indicadores-month-year-label"
            label="Año"
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
          >
            {yearOptions.map((y) => (
              <MenuItem key={y} value={y}>
                {y}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <Stack direction="row" flexWrap="wrap" gap={1} useFlexGap>
          {MESES_ES.map((label, idx) => {
            const m = idx + 1;
            const disabled = isFutureIndicadoresMonth(year, m, now);
            const selected = month === m;
            return (
              <Button
                key={label}
                variant={selected ? "contained" : "outlined"}
                size="small"
                disabled={disabled}
                onClick={() => setMonth(m)}
                sx={{ flex: "1 1 calc(33.33% - 8px)", minWidth: 88, textTransform: "none" }}
              >
                {label.slice(0, 3)}
              </Button>
            );
          })}
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} color="inherit">
          Cancelar
        </Button>
        <Button variant="contained" onClick={handleApply} disabled={!selectionValid}>
          Aplicar ({previewLabel})
        </Button>
      </DialogActions>
    </Dialog>
  );
}
