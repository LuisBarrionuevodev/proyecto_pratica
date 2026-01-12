import { useState } from "react";
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField, MenuItem } from "@mui/material";

type Props = {
  open: boolean;
  onClose: () => void;
  onSave: (form: FormData) => Promise<void>;
  lat: number;
  lng: number;
  distritos: string[];
};

export default function AddLocalForm({ open, onClose, onSave, lat, lng, distritos }: Props) {
  const [nombre, setNombre] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [distrito, setDistrito] = useState<string | "">("");
  const [files, setFiles] = useState<FileList | null>(null);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    const fd = new FormData();
    fd.append("nombre", nombre);
    fd.append("descripcion", descripcion);
    fd.append("lat", String(lat));
    fd.append("lng", String(lng));
    fd.append("distrito", distrito || "");
    if (files) {
      Array.from(files).forEach((f) => fd.append("files[]", f));
    }
    setSaving(true);
    try {
      await onSave(fd);
      setNombre("");
      setDescripcion("");
      setDistrito("");
      setFiles(null);
      onClose();
    } catch (err) {
      console.error(err);
      alert("Error al guardar");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>Agregar local</DialogTitle>
      <DialogContent>
        <TextField margin="dense" fullWidth label="Nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} />
        <TextField margin="dense" fullWidth label="Descripción" value={descripcion} onChange={(e) => setDescripcion(e.target.value)} multiline rows={3} />
        <TextField select margin="dense" fullWidth label="Distrito" value={distrito} onChange={(e) => setDistrito(e.target.value)}>
          <MenuItem value="">-- sin seleccionar --</MenuItem>
          {distritos.map((d) => <MenuItem value={d} key={d}>{d}</MenuItem>)}
        </TextField>
        <input style={{ marginTop: 12 }} type="file" multiple onChange={(e) => setFiles(e.target.files)} />
        <div style={{ marginTop: 12 }}>
          <strong>Lat:</strong> {lat.toFixed(6)} <strong>Lng:</strong> {lng.toFixed(6)}
        </div>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={saving}>Cancelar</Button>
        <Button onClick={handleSave} variant="contained" disabled={saving || !nombre}>
          {saving ? "Guardando..." : "Guardar"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
