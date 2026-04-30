import { useEffect, useState } from "react";
import { Box } from "@mui/material";

import { fechaLocalHoyIso } from "../../../utils/dateRange";
import { dialogFormActionsRowSx, formDialogShortContentSx } from "../../../styles/formDialogStyles";
import { AppButton, AppDialog, AppSelect, AppTextField } from "../../../ui";

interface Props {
  open: boolean;
  onClose: () => void;
  /** Si se informa al abrir, precarga el campo fecha (p. ej. día elegido en el almanaque). */
  fechaSugeridaAlAbrir?: string | null;
  onSubmit: (payload: { fecha: string; turno: "MANIANA" | "TARDE"; observaciones?: string }) => Promise<void>;
}

const ModalCrearRutaTrabajo = ({ open, onClose, fechaSugeridaAlAbrir, onSubmit }: Props) => {
  const [fecha, setFecha] = useState(() => fechaLocalHoyIso());
  const [turno, setTurno] = useState<"MANIANA" | "TARDE">("MANIANA");
  const [observaciones, setObservaciones] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    const raw = fechaSugeridaAlAbrir?.trim();
    if (raw && /^\d{4}-\d{2}-\d{2}$/.test(raw)) {
      setFecha(raw);
    } else {
      setFecha(fechaLocalHoyIso());
    }
  }, [open, fechaSugeridaAlAbrir]);

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
      contentDividers
      contentSx={formDialogShortContentSx}
      actions={
        <Box sx={dialogFormActionsRowSx}>
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
        </Box>
      }
    >
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
          gap: 2,
          width: "100%",
        }}
      >
        <AppTextField
          appearance="glass"
          label="Fecha"
          type="date"
          value={fecha}
          onChange={(e) => setFecha(e.target.value)}
          InputLabelProps={{ shrink: true }}
          fullWidth
          required
          variant="outlined"
        />
        <AppSelect
          appearance="glass"
          label="Turno"
          value={turno}
          onChange={(e) => setTurno(e.target.value as "MANIANA" | "TARDE")}
          fullWidth
          variant="outlined"
          options={[
            { value: "MANIANA", label: "Mañana" },
            { value: "TARDE", label: "Tarde" },
          ]}
        />
      </Box>
      <AppTextField
        appearance="glass"
        label="Observaciones"
        value={observaciones}
        onChange={(e) => setObservaciones(e.target.value)}
        fullWidth
        multiline
        minRows={3}
        variant="outlined"
      />
    </AppDialog>
  );
};

export default ModalCrearRutaTrabajo;
