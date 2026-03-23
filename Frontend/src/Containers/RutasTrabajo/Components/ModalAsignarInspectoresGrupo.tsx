import { useEffect, useMemo, useState } from "react";
import {
  Box,
  Checkbox,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
} from "@mui/material";

import type { CatalogItem } from "../../../api/gridApi";
import type { IRutaGrupoMin } from "../../../api/rutasTrabajoApi";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { AppButton, AppDialog, AppTextField } from "../../../ui";

interface Props {
  open: boolean;
  onClose: () => void;
  onSubmit: (inspectorIds: number[]) => Promise<void>;
  grupo: IRutaGrupoMin | null;
  inspectoresCatalogo: CatalogItem[];
  grupos: IRutaGrupoMin[];
}

/**
 * Asignación de inspectores al grupo: rejilla de filas seleccionables y confirmación principal “Listo”.
 */
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

  const toggleInspector = (id: number) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
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
      maxWidth="md"
      fullWidth
      // eslint-disable-next-line @typescript-eslint/no-unused-vars -- MUI Dialog onClose(event, reason)
      onClose={(_event, _reason) => handleClose()}
      onCloseButtonClick={() => handleClose()}
      title="Asignar/Reemplazar inspectores"
      actions={
        <AppButton dsVariant="ghost" onClick={handleClose} disabled={saving}>
          Cancelar
        </AppButton>
      }
      contentSx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}
    >
      <AppTextField
        label="Grupo"
        value={grupo?.nombre ?? "-"}
        fullWidth
        appearance="glass"
        InputProps={{ readOnly: true }}
      />
      <Typography variant="body2" sx={{ color: GLASS_COLORS.textSecondary, fontFamily: '"Tactic Sans", sans-serif' }}>
        Tocá una fila para incluir o quitar. Esta acción reemplaza la lista del grupo. No se listan inspectores ya
        asignados a otros grupos.
      </Typography>
      <List
        dense
        sx={{
          maxHeight: 360,
          overflow: "auto",
          border: `1px solid ${GLASS_COLORS.borderMedium}`,
          borderRadius: "12px",
          bgcolor: "rgba(0,0,0,0.2)",
          py: 0,
        }}
      >
        {availableInspectores.map((inspector) => {
          const checked = selectedIdsSafe.includes(inspector.id);
          return (
            <ListItemButton
              key={inspector.id}
              selected={checked}
              onClick={() => toggleInspector(inspector.id)}
              sx={{
                borderBottom: `1px solid ${GLASS_COLORS.borderLight}`,
                "&.Mui-selected": {
                  backgroundColor: "rgba(1, 102, 255, 0.12)",
                },
                "&.Mui-selected:hover": {
                  backgroundColor: "rgba(1, 102, 255, 0.18)",
                },
              }}
            >
              <ListItemIcon sx={{ minWidth: 42 }}>
                <Checkbox
                  edge="start"
                  checked={checked}
                  tabIndex={-1}
                  disableRipple
                  sx={{ color: GLASS_COLORS.textMuted, "&.Mui-checked": { color: GLASS_COLORS.primary } }}
                />
              </ListItemIcon>
              <ListItemText
                primary={inspector.nombre}
                secondary={inspector.legajo ? `Legajo: ${inspector.legajo}` : undefined}
                primaryTypographyProps={{
                  sx: { fontFamily: '"Tactic Sans", sans-serif', fontWeight: 600, color: GLASS_COLORS.textPrimary },
                }}
                secondaryTypographyProps={{ sx: { color: GLASS_COLORS.textMuted } }}
              />
            </ListItemButton>
          );
        })}
      </List>
      <Box sx={{ pt: 0.5 }}>
        <AppButton
          dsVariant="primary"
          fullWidth
          onClick={handleSubmit}
          disabled={saving || !grupo}
          loading={saving}
          sx={{ py: 1.25, fontWeight: 700, letterSpacing: "0.06em" }}
        >
          Listo
        </AppButton>
      </Box>
    </AppDialog>
  );
};

export default ModalAsignarInspectoresGrupo;
