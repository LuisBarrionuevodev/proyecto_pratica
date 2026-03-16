import { useEffect, useState } from "react";
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, TextField } from "@mui/material";

import type { IRutaItemMin } from "../../../api/rutasTrabajoApi";

interface Props {
  open: boolean;
  onClose: () => void;
  item: IRutaItemMin | null;
  onConfirm: (numeroOt: string) => Promise<void>;
}

const ModalEditarOrdenTrabajoItem = ({ open, onClose, item, onConfirm }: Props) => {
  const [numero, setNumero] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setNumero(item?.orden_trabajo?.numero_acta ?? "");
    setError(null);
  }, [open, item]);

  const handleClose = () => {
    if (saving) return;
    onClose();
  };

  const handleConfirm = async () => {
    const value = numero.trim();
    if (!value || !/^\d+$/.test(value)) {
      setError("La orden de trabajo debe ser numérica.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onConfirm(value);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="xs">
      <DialogTitle>Definir orden de trabajo</DialogTitle>
      <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
        {error && <Alert severity="error">{error}</Alert>}
        <TextField
          label="Número OT"
          value={numero}
          onChange={(e) => setNumero(e.target.value)}
          fullWidth
          autoFocus
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={saving}>
          Cancelar
        </Button>
        <Button variant="contained" onClick={handleConfirm} disabled={saving}>
          {saving ? "Guardando..." : "Guardar OT"}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ModalEditarOrdenTrabajoItem;
