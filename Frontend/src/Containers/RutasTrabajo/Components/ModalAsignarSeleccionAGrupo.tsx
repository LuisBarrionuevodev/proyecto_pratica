import { useMemo, useState } from "react";
import { Box, Typography } from "@mui/material";

import { dialogFormActionsRowSx, formDialogContentStackSx } from "../../../styles/formDialogStyles";
import { AppButton, AppDialog, AppSelect } from "../../../ui";
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
    <AppDialog
      open={open}
      // eslint-disable-next-line @typescript-eslint/no-unused-vars -- MUI Dialog onClose(event, reason)
      onClose={(_event, _reason) => handleClose()}
      onCloseButtonClick={() => handleClose()}
      title="Asignar selección a grupo"
      contentDividers
      contentSx={formDialogContentStackSx}
      actions={
        <Box sx={dialogFormActionsRowSx}>
          <AppButton dsVariant="ghost" onClick={handleClose} disabled={saving}>
            Cancelar
          </AppButton>
          <AppButton
            dsVariant="primary"
            onClick={handleConfirm}
            disabled={saving || !grupoId}
            loading={saving}
          >
            Asignar
          </AppButton>
        </Box>
      }
    >
      <Typography variant="body2" color="text.secondary">
        Se asignarán {selectedCount} iniciadores seleccionados.
      </Typography>
      <AppSelect
        appearance="glass"
        label="Grupo destino"
        value={grupoId}
        onChange={(e) => setGrupoId(Number(e.target.value))}
        fullWidth
        variant="outlined"
        options={gruposOrdenados.map((g) => ({ value: g.id, label: g.nombre }))}
      />
    </AppDialog>
  );
};

export default ModalAsignarSeleccionAGrupo;
