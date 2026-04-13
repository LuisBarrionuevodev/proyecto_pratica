import type { DialogProps } from "@mui/material/Dialog";
import { Box, Typography } from "@mui/material";
import { useMemo, useState } from "react";

import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { dialogFormActionsRowSx, formDialogContentStackSx } from "../../../styles/formDialogStyles";
import { AppButton, AppDialog, AppSelect, AppTextField } from "../../../ui";

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

  const distritoOptions = useMemo(
    () => [
      { value: "", label: "-- sin seleccionar --" },
      ...distritos.map((d) => ({ value: d, label: d })),
    ],
    [distritos]
  );

  const handleDialogClose: DialogProps["onClose"] = (_event, _reason) => {
    if (saving) return;
    onClose();
  };

  const handleCloseButton = () => {
    if (saving) return;
    onClose();
  };

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
    <AppDialog
      open={open}
      onClose={handleDialogClose}
      onCloseButtonClick={handleCloseButton}
      title="Agregar local"
      maxWidth="sm"
      fullWidth
      contentDividers
      contentSx={formDialogContentStackSx}
      disableEscapeKeyDown={saving}
      disableBackdropClick={saving}
      actions={
        <Box sx={dialogFormActionsRowSx}>
          <AppButton dsVariant="ghost" onClick={handleCloseButton} disabled={saving}>
            Cancelar
          </AppButton>
          <AppButton
            dsVariant="primary"
            onClick={() => void handleSave()}
            disabled={saving || !nombre}
            loading={saving}
          >
            Guardar
          </AppButton>
        </Box>
      }
    >
      <AppTextField
        appearance="glass"
        label="Nombre"
        value={nombre}
        onChange={(e) => setNombre(e.target.value)}
        fullWidth
        variant="outlined"
      />
      <AppTextField
        appearance="glass"
        label="Descripción"
        value={descripcion}
        onChange={(e) => setDescripcion(e.target.value)}
        fullWidth
        multiline
        minRows={3}
        variant="outlined"
      />
      <AppSelect
        appearance="glass"
        label="Distrito"
        value={distrito}
        onChange={(e) => setDistrito(e.target.value)}
        fullWidth
        variant="outlined"
        options={distritoOptions}
      />
      <Box sx={{ mt: 0.5 }}>
        <Typography
          component="label"
          htmlFor="add-local-files"
          sx={{ fontFamily: '"Tactic Sans", sans-serif', fontSize: "0.75rem", color: GLASS_COLORS.textSecondary }}
        >
          Archivos
        </Typography>
        <input
          id="add-local-files"
          style={{ display: "block", marginTop: 8 }}
          type="file"
          multiple
          onChange={(e) => setFiles(e.target.files)}
        />
      </Box>
      <Typography
        sx={{
          mt: 1.5,
          fontFamily: '"Tactic Sans", sans-serif',
          fontSize: "0.875rem",
          color: GLASS_COLORS.textSecondary,
        }}
      >
        <Box component="span" sx={{ color: GLASS_COLORS.textPrimary, fontWeight: 600 }}>
          Lat:
        </Box>{" "}
        {lat.toFixed(6)}{" "}
        <Box component="span" sx={{ color: GLASS_COLORS.textPrimary, fontWeight: 600 }}>
          Lng:
        </Box>{" "}
        {lng.toFixed(6)}
      </Typography>
    </AppDialog>
  );
}
