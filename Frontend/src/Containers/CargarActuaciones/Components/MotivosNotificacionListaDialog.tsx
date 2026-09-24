import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Autocomplete,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
  Typography,
} from "@mui/material";

import { MOTIVOS_NOTIFICACION_MAX, orderedMotivosNotificacion } from "../../../utils/motivosNotificacionSlots";

export type MotivosNotificacionListaDialogProps = {
  open: boolean;
  initialMotivos: string[];
  catalogMotivos: string[];
  onClose: () => void;
  onSave: (motivos: string[]) => void;
};

/**
 * Editor modal: hasta tres motivos de notificación desde un solo catálogo (sin duplicados).
 */
export function MotivosNotificacionListaDialog({
  open,
  initialMotivos,
  catalogMotivos,
  onClose,
  onSave,
}: MotivosNotificacionListaDialogProps) {
  const [selected, setSelected] = useState<string[]>([]);

  useEffect(() => {
    if (open) {
      setSelected(orderedMotivosNotificacion(initialMotivos));
    }
  }, [open, initialMotivos]);

  const options = useMemo(
    () => [...catalogMotivos].sort((a, b) => a.localeCompare(b, "es", { sensitivity: "base" })),
    [catalogMotivos]
  );

  const availableToAdd = useMemo(
    () => options.filter((o) => !selected.includes(o)),
    [options, selected]
  );

  const handleAdd = useCallback(
    (_: unknown, value: string | null) => {
      if (!value || selected.includes(value)) return;
      if (selected.length >= MOTIVOS_NOTIFICACION_MAX) return;
      setSelected((prev) => orderedMotivosNotificacion([...prev, value]));
    },
    [selected]
  );

  const handleRemove = useCallback((name: string) => {
    setSelected((prev) => prev.filter((x) => x !== name));
  }, []);

  const handleSave = useCallback(() => {
    onSave(orderedMotivosNotificacion(selected));
  }, [onSave, selected]);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Motivos de notificación</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
          Elegí del catálogo (máximo {MOTIVOS_NOTIFICACION_MAX}). Doble clic en la celda de la grilla para volver a
          abrir.
        </Typography>
        <Autocomplete
          options={availableToAdd}
          value={null}
          onChange={handleAdd}
          renderInput={(params) => (
            <TextField {...params} label="Agregar motivo" placeholder="Buscar…" size="small" />
          )}
          disabled={availableToAdd.length === 0 || selected.length >= MOTIVOS_NOTIFICACION_MAX}
        />
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, mt: 2, minHeight: 40 }}>
          {selected.length === 0 ? (
            <Typography variant="body2" color="text.disabled">
              Ninguno seleccionado
            </Typography>
          ) : (
            selected.map((name) => (
              <Chip key={name} label={name} onDelete={() => handleRemove(name)} size="small" />
            ))
          )}
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose}>Cancelar</Button>
        <Button variant="contained" onClick={handleSave}>
          Guardar
        </Button>
      </DialogActions>
    </Dialog>
  );
}
