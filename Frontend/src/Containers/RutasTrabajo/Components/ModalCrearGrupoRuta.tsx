import { useState } from "react";
import { Button, Dialog, DialogActions, DialogContent, DialogTitle, Typography } from "@mui/material";

interface Props {
  open: boolean;
  onClose: () => void;
  onSubmit: () => Promise<void>;
  disabled?: boolean;
}

const ModalCrearGrupoRuta = ({ open, onClose, onSubmit, disabled = false }: Props) => {
  const [saving, setSaving] = useState(false);

  const handleClose = () => {
    if (saving) return;
    onClose();
  };

  const handleSubmit = async () => {
    if (disabled) return;
    setSaving(true);
    try {
      await onSubmit();
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="sm">
      <DialogTitle>Crear grupo</DialogTitle>
      <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
        <Typography variant="body2" color="text.secondary">
          El nombre se genera automáticamente siguiendo la secuencia del día (Grupo N).
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={saving}>
          Cancelar
        </Button>
        <Button variant="contained" onClick={handleSubmit} disabled={saving || disabled}>
          {saving ? "Guardando..." : "Crear grupo"}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ModalCrearGrupoRuta;
