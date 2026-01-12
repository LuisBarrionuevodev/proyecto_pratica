import { Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField } from "@mui/material";
import { useState } from "react";

interface PolygonFormProps {
  open: boolean;
  onClose: () => void;
  onSave: (data: { nombre: string; descripcion: string }) => void;
}

export default function PolygonForm({ open, onClose, onSave }: PolygonFormProps) {
  const [nombre, setNombre] = useState("");
  const [descripcion, setDescripcion] = useState("");

  const handleSubmit = () => {
    onSave({ nombre, descripcion });
    setNombre("");
    setDescripcion("");
  };

  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>Nuevo Distrito</DialogTitle>

      <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}>
        <TextField label="Nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} />
        <TextField label="Descripción" value={descripcion} onChange={(e) => setDescripcion(e.target.value)} multiline rows={3} />
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>Cancelar</Button>
        <Button variant="contained" onClick={handleSubmit}>Guardar</Button>
      </DialogActions>
    </Dialog>
  );
}
