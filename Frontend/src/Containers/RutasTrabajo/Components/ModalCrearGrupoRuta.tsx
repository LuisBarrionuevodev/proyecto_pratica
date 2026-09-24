import { useState } from "react";
import { Box, Button, Typography } from "@mui/material";

import { dialogFormActionsRowSx, formDialogContentStackSx } from "../../../styles/formDialogStyles";
import { AppButton, AppDialog } from "../../../ui";
import { rutasAsignacionNeutralContainedButtonSx } from "../styles/institutionalVisual";

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
      contentDividers
      contentSx={formDialogContentStackSx}
      actions={
        <Box sx={dialogFormActionsRowSx}>
          <Button
            variant="contained"
            size="small"
            disableElevation
            onClick={handleClose}
            disabled={saving}
            sx={rutasAsignacionNeutralContainedButtonSx}
          >
            Cancelar
          </Button>
          <AppButton
            dsVariant="primary"
            onClick={handleSubmit}
            disabled={saving || disabled}
            loading={saving}
          >
            Crear grupo
          </AppButton>
        </Box>
      }
    >
      <Typography variant="body2" color="text.secondary">
        El nombre se genera automáticamente siguiendo la secuencia del día (Grupo N).
      </Typography>
    </AppDialog>
  );
};

export default ModalCrearGrupoRuta;
