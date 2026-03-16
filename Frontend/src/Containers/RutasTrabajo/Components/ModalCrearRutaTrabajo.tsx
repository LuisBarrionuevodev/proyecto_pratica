import { useMemo, useState } from "react";
import { Button, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, TextField } from "@mui/material";

import { getCurrentMonthRange } from "../../../utils/dateRange";

interface Props {
  open: boolean;
  onClose: () => void;
  onSubmit: (payload: { fecha: string; turno: "MANIANA" | "TARDE"; observaciones?: string }) => Promise<void>;
}

const ModalCrearRutaTrabajo = ({ open, onClose, onSubmit }: Props) => {
  const defaultRange = useMemo(() => getCurrentMonthRange(), []);
  const [fecha, setFecha] = useState(defaultRange.hasta);
  const [turno, setTurno] = useState<"MANIANA" | "TARDE">("MANIANA");
  const [observaciones, setObservaciones] = useState("");
  const [saving, setSaving] = useState(false);

  const handleClose = () => {
    if (saving) return;
    onClose();
  };

  const handleSubmit = async () => {
    if (!fecha) return;
    setSaving(true);
    try {
      await onSubmit({
        fecha,
        turno,
        observaciones: observaciones.trim() || undefined,
      });
      setObservaciones("");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="sm">
      <DialogTitle>Crear ruta de trabajo</DialogTitle>
      <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
        <TextField
          label="Fecha"
          type="date"
          value={fecha}
          onChange={(e) => setFecha(e.target.value)}
          InputLabelProps={{ shrink: true }}
          fullWidth
          required
        />
        <TextField select label="Turno" value={turno} onChange={(e) => setTurno(e.target.value as "MANIANA" | "TARDE")} fullWidth>
          <MenuItem value="MANIANA">Mañana</MenuItem>
          <MenuItem value="TARDE">Tarde</MenuItem>
        </TextField>
        <TextField
          label="Observaciones"
          value={observaciones}
          onChange={(e) => setObservaciones(e.target.value)}
          fullWidth
          multiline
          minRows={3}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={saving}>
          Cancelar
        </Button>
        <Button variant="contained" onClick={handleSubmit} disabled={saving || !fecha}>
          {saving ? "Guardando..." : "Crear ruta"}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ModalCrearRutaTrabajo;
