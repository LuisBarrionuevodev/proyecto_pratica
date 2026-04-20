import { memo, useCallback, useEffect, useMemo, useState } from "react";
import { Box, Button, Typography } from "@mui/material";
import type { SelectChangeEvent } from "@mui/material/Select";

import { dialogFormActionsRowSx, formDialogContentStackSx } from "../../../styles/formDialogStyles";
import { AppButton, AppDialog, AppSelect } from "../../../ui";
import type { IRutaGrupoMin } from "../../../api/rutasTrabajoApi";
import { rutasAsignacionNeutralContainedButtonSx } from "../styles/institutionalVisual";

interface Props {
  open: boolean;
  onClose: () => void;
  grupos: IRutaGrupoMin[];
  selectedCount: number;
  onConfirm: (grupoId: number) => Promise<void>;
}

/** Menos trabajo en el primer frame de apertura del Dialog. */
const DIALOG_OPEN_PERF = {
  transitionDuration: { enter: 120, exit: 90 },
  disableAutoFocus: true,
} as const;

/**
 * Asignar iniciadores seleccionados a un grupo.
 * Contenido pesado (select + opciones) solo se monta con `open` para no pagar costo en cada render del padre.
 */
function ModalAsignarSeleccionAGrupoInner({ open, onClose, grupos, selectedCount, onConfirm }: Props) {
  const [grupoId, setGrupoId] = useState<number | "">("");
  const [saving, setSaving] = useState(false);

  const gruposOrdenados = useMemo(() => [...grupos].sort((a, b) => a.nombre.localeCompare(b.nombre)), [grupos]);

  const selectOptions = useMemo(
    () => gruposOrdenados.map((g) => ({ value: g.id, label: g.nombre })),
    [gruposOrdenados]
  );

  useEffect(() => {
    if (open) setGrupoId("");
  }, [open]);

  const handleClose = useCallback(() => {
    if (saving) return;
    onClose();
  }, [saving, onClose]);

  const handleConfirm = useCallback(async () => {
    if (!grupoId) return;
    setSaving(true);
    try {
      await onConfirm(Number(grupoId));
      setGrupoId("");
    } finally {
      setSaving(false);
    }
  }, [grupoId, onConfirm]);

  const handleSelectChange = useCallback((e: SelectChangeEvent<string | number>) => {
    setGrupoId(Number(e.target.value));
  }, []);

  return (
    <AppDialog
      open={open}
      keepMounted={false}
      {...DIALOG_OPEN_PERF}
      // eslint-disable-next-line @typescript-eslint/no-unused-vars -- MUI Dialog onClose(event, reason)
      onClose={(_event, _reason) => handleClose()}
      onCloseButtonClick={handleClose}
      title="Asignar selección a grupo"
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
          <AppButton dsVariant="primary" onClick={handleConfirm} disabled={saving || !grupoId} loading={saving}>
            Asignar
          </AppButton>
        </Box>
      }
    >
      {open ? (
        <>
          <Typography variant="body2" color="text.secondary">
            Se asignarán {selectedCount} iniciadores seleccionados.
          </Typography>
          <AppSelect
            appearance="glass"
            label="Grupo destino"
            value={grupoId}
            onChange={handleSelectChange}
            fullWidth
            variant="outlined"
            options={selectOptions}
          />
        </>
      ) : null}
    </AppDialog>
  );
}

const ModalAsignarSeleccionAGrupo = memo(ModalAsignarSeleccionAGrupoInner);
export default ModalAsignarSeleccionAGrupo;
