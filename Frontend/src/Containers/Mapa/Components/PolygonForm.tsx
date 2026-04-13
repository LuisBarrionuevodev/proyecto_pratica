import { Box } from "@mui/material";
import { useState } from "react";

import { dialogFormActionsRowSx, formDialogContentStackSx } from "../../../styles/formDialogStyles";
import { AppButton, AppDialog, AppTextField } from "../../../ui";

interface PolygonFormProps {
  open: boolean;
  onClose: () => void;
  onSave: (data: { nombre: string; descripcion: string }) => void;
}

export default function PolygonForm({ open, onClose, onSave }: PolygonFormProps) {
  const [nombre, setNombre] = useState("");
  const [descripcion, setDescripcion] = useState("");

  const handleClose = () => {
    onClose();
  };

  const handleSubmit = () => {
    onSave({ nombre, descripcion });
    setNombre("");
    setDescripcion("");
  };

  return (
    <AppDialog
      open={open}
      onClose={(_event, _reason) => handleClose()}
      onCloseButtonClick={handleClose}
      title="Nuevo Distrito"
      contentDividers
      contentSx={formDialogContentStackSx}
      actions={
        <Box sx={dialogFormActionsRowSx}>
          <AppButton dsVariant="ghost" onClick={handleClose}>
            Cancelar
          </AppButton>
          <AppButton dsVariant="primary" onClick={handleSubmit}>
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
    </AppDialog>
  );
}
