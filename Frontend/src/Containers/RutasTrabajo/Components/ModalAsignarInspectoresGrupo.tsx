import { useEffect, useMemo, useState } from "react";
import {
  Checkbox,
  FormControl,
  InputLabel,
  ListItemText,
  MenuItem,
  Select,
  Typography,
} from "@mui/material";

import type { CatalogItem } from "../../../api/gridApi";
import type { IRutaGrupoMin } from "../../../api/rutasTrabajoApi";
import { AppButton, AppDialog, AppTextField } from "../../../ui";

interface Props {
  open: boolean;
  onClose: () => void;
  onSubmit: (inspectorIds: number[]) => Promise<void>;
  grupo: IRutaGrupoMin | null;
  inspectoresCatalogo: CatalogItem[];
  grupos: IRutaGrupoMin[];
}

const ModalAsignarInspectoresGrupo = ({ open, onClose, onSubmit, grupo, inspectoresCatalogo, grupos }: Props) => {
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [saving, setSaving] = useState(false);

  const selectedIdsSafe = useMemo(() => selectedIds.filter((id) => Number.isFinite(id) && id > 0), [selectedIds]);
  const availableInspectores = useMemo(() => {
    if (!grupo) return inspectoresCatalogo;
    const usedInOtherGroups = new Set(
      grupos
        .filter((g) => g.id !== grupo.id)
        .flatMap((g) => g.inspectores.map((i) => i.inspector_id))
    );
    const selectedInCurrent = new Set(grupo.inspectores.map((i) => i.inspector_id));
    return inspectoresCatalogo.filter((i) => !usedInOtherGroups.has(i.id) || selectedInCurrent.has(i.id));
  }, [grupo, grupos, inspectoresCatalogo]);

  useEffect(() => {
    if (!open || !grupo) return;
    setSelectedIds(grupo.inspectores.map((i) => i.inspector_id));
  }, [open, grupo]);

  const handleClose = () => {
    if (saving) return;
    onClose();
  };

  const handleSubmit = async () => {
    if (!grupo) return;
    setSaving(true);
    try {
      await onSubmit(selectedIdsSafe);
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
      title="Asignar/Reemplazar inspectores"
      contentSx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}
      actions={
        <>
          <AppButton dsVariant="ghost" onClick={handleClose} disabled={saving}>
            Cancelar
          </AppButton>
          <AppButton
            dsVariant="primary"
            onClick={handleSubmit}
            disabled={saving || !grupo}
            loading={saving}
          >
            Guardar inspectores
          </AppButton>
        </>
      }
    >
      <AppTextField
        label="Grupo"
        value={grupo?.nombre ?? "-"}
        fullWidth
        InputProps={{ readOnly: true }}
      />
      <FormControl fullWidth>
        <InputLabel id="inspectores-multiple-label">Inspectores</InputLabel>
        <Select
          labelId="inspectores-multiple-label"
          multiple
          value={selectedIdsSafe}
          label="Inspectores"
          onChange={(e) => setSelectedIds((e.target.value as number[]).map((v) => Number(v)))}
          renderValue={(selected) => {
            const set = new Set(selected as number[]);
            return inspectoresCatalogo
              .filter((i) => set.has(i.id))
              .map((i) => i.nombre)
              .join(", ");
          }}
        >
          {availableInspectores.map((inspector) => (
            <MenuItem key={inspector.id} value={inspector.id}>
              <Checkbox checked={selectedIdsSafe.includes(inspector.id)} />
              <ListItemText
                primary={inspector.nombre}
                secondary={inspector.legajo ? `Legajo: ${inspector.legajo}` : undefined}
              />
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      <Typography variant="caption" color="text.secondary">
        Esta acción reemplaza completamente la lista de inspectores del grupo. No se muestran inspectores ocupados por otros grupos.
      </Typography>
    </AppDialog>
  );
};

export default ModalAsignarInspectoresGrupo;
