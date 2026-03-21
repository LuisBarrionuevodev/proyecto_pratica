import { useState } from "react";
import { Typography } from "@mui/material";

import { AppButton, AppDialog } from "../../../ui";

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
    <AppDialog
      open={open}
      // eslint-disable-next-line @typescript-eslint/no-unused-vars -- MUI Dialog onClose(event, reason)
      onClose={(_event, _reason) => handleClose()}
      onCloseButtonClick={() => handleClose()}
      title="Crear grupo"
      contentSx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}
      actions={
        <>
          <AppButton dsVariant="ghost" onClick={handleClose} disabled={saving}>
            Cancelar
          </AppButton>
          <AppButton
            dsVariant="primary"
            onClick={handleSubmit}
            disabled={saving || disabled}
            loading={saving}
          >
            Crear grupo
          </AppButton>
        </>
      }
    >
      <Typography variant="body2" color="text.secondary">
        El nombre se genera automáticamente siguiendo la secuencia del día (Grupo N).
      </Typography>
    </AppDialog>
  );
};

export default ModalCrearGrupoRuta;
