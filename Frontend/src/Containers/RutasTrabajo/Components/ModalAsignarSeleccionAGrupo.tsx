import { useMemo, useState } from "react";
import { Button, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, TextField, Typography } from "@mui/material";

import type { IRutaGrupoMin } from "../../../api/rutasTrabajoApi";

interface Props {
  open: boolean;
  onClose: () => void;
  grupos: IRutaGrupoMin[];
  selectedCount: number;
  onConfirm: (grupoId: number) => Promise<void>;
}

const ModalAsignarSeleccionAGrupo = ({ open, onClose, grupos, selectedCount, onConfirm }: Props) => {
  const [grupoId, setGrupoId] = useState<number | "">("");
  const [saving, setSaving] = useState(false);

  const gruposOrdenados = useMemo(() => [...grupos].sort((a, b) => a.nombre.localeCompare(b.nombre)), [grupos]);

  const handleClose = () => {
    if (saving) return;
    onClose();
  };

  const handleConfirm = async () => {
    if (!grupoId) return;
    setSaving(true);
    try {
      await onConfirm(Number(grupoId));
      setGrupoId("");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="sm">
      <DialogTitle>Asignar selección a grupo</DialogTitle>
      <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
        <Typography variant="body2" color="text.secondary">
          Se asignarán {selectedCount} iniciadores seleccionados.
        </Typography>
        <TextField
          select
          label="Grupo destino"
          value={grupoId}
          onChange={(e) => setGrupoId(Number(e.target.value))}
          fullWidth
        >
          {gruposOrdenados.map((g) => (
            <MenuItem key={g.id} value={g.id}>
              {g.nombre}
            </MenuItem>
          ))}
        </TextField>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={saving}>
          Cancelar
        </Button>
        <Button variant="contained" onClick={handleConfirm} disabled={saving || !grupoId}>
          {saving ? "Asignando..." : "Asignar"}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ModalAsignarSeleccionAGrupo;
