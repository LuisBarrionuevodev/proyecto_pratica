import { useMemo, useState } from "react";

import { getCurrentMonthRange } from "../../../utils/dateRange";
import { AppButton, AppDialog, AppSelect, AppTextField } from "../../../ui";

interface Props {
  open: boolean;
  onClose: () => void;
  onSubmit: (payload: { fecha: string; turno: "MANIANA" | "TARDE"; observaciones?: string }) => Promise<void>;
}

const ModalCrearRutaTrabajo = ({ open, onClose, onSubmit }: Props) => {
  const defaultRange = useMemo(() => getCurrentMonthRange(), []);
  const [fecha, setFecha] = useState(defaultRange.hasta);
  const [turno, setTurno] = useState<"MANIANA" | "TARDE">("MANIANA");
  const [observaciones, setObservaciones] = useState("");
  const [saving, setSaving] = useState(false);

  const handleClose = () => {
    if (saving) return;
    onClose();
  };

  const handleSubmit = async () => {
    if (!fecha) return;
    setSaving(true);
    try {
      await onSubmit({
        fecha,
        turno,
        observaciones: observaciones.trim() || undefined,
      });
      setObservaciones("");
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
      title="Crear ruta de trabajo"
      contentSx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}
      actions={
        <>
          <AppButton dsVariant="ghost" onClick={handleClose} disabled={saving}>
            Cancelar
          </AppButton>
          <AppButton
            dsVariant="primary"
            onClick={handleSubmit}
            disabled={saving || !fecha}
            loading={saving}
          >
            Crear ruta
          </AppButton>
        </>
      }
    >
      <AppTextField
        label="Fecha"
        type="date"
        value={fecha}
        onChange={(e) => setFecha(e.target.value)}
        InputLabelProps={{ shrink: true }}
        fullWidth
        required
      />
      <AppSelect
        label="Turno"
        value={turno}
        onChange={(e) => setTurno(e.target.value as "MANIANA" | "TARDE")}
        fullWidth
        options={[
          { value: "MANIANA", label: "Mañana" },
          { value: "TARDE", label: "Tarde" },
        ]}
      />
      <AppTextField
        label="Observaciones"
        value={observaciones}
        onChange={(e) => setObservaciones(e.target.value)}
        fullWidth
        multiline
        minRows={3}
      />
    </AppDialog>
  );
};

export default ModalCrearRutaTrabajo;
