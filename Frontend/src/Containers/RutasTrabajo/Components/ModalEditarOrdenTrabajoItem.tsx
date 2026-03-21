import { useEffect, useState } from "react";
import { Alert } from "@mui/material";

import type { IRutaItemMin } from "../../../api/rutasTrabajoApi";
import { AppButton, AppDialog, AppTextField } from "../../../ui";

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
    <AppDialog
      open={open}
      // eslint-disable-next-line @typescript-eslint/no-unused-vars -- MUI Dialog onClose(event, reason)
      onClose={(_event, _reason) => handleClose()}
      onCloseButtonClick={() => handleClose()}
      title="Definir orden de trabajo"
      maxWidth="xs"
      contentSx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}
      actions={
        <>
          <AppButton dsVariant="ghost" onClick={handleClose} disabled={saving}>
            Cancelar
          </AppButton>
          <AppButton dsVariant="primary" onClick={handleConfirm} disabled={saving} loading={saving}>
            Guardar OT
          </AppButton>
        </>
      }
    >
      {error && <Alert severity="error">{error}</Alert>}
      <AppTextField
        label="Número OT"
        value={numero}
        onChange={(e) => setNumero(e.target.value)}
        fullWidth
        autoFocus
      />
    </AppDialog>
  );
};

export default ModalEditarOrdenTrabajoItem;
