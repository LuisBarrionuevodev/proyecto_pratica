import { useVirtualizer } from "@tanstack/react-virtual";
import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Box,
  Button,
  Checkbox,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
} from "@mui/material";

import type { CatalogItem } from "../../../api/gridApi";
import type { IRutaGrupoMin } from "../../../api/rutasTrabajoApi";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { dialogFormActionsRowSx, formDialogContentStackSx } from "../../../styles/formDialogStyles";
import { AppButton, AppDialog, AppTextField } from "../../../ui";
import { rutasAsignacionNeutralContainedButtonSx } from "../styles/institutionalVisual";

/** Transición más corta + sin autofocus agresivo al abrir (menos trabajo en el frame de apertura). */
const DIALOG_OPEN_PERF = {
  transitionDuration: { enter: 120, exit: 90 },
  disableAutoFocus: true,
} as const;

/** Altura fija del viewport: el virtualizer necesita clientHeight > 0; solo maxHeight en flex + `contain` rompía el layout. */
const LIST_VIEWPORT_HEIGHT_PX = 360;

const LIST_VIEWPORT_SX = {
  height: LIST_VIEWPORT_HEIGHT_PX,
  maxHeight: LIST_VIEWPORT_HEIGHT_PX,
  minHeight: LIST_VIEWPORT_HEIGHT_PX,
  flexShrink: 0,
  overflow: "auto" as const,
  border: `1px solid ${GLASS_COLORS.borderMedium}`,
  borderRadius: "12px",
  bgcolor: "rgba(0,0,0,0.2)",
};

const INSPECTOR_LIST_ITEM_SX = {
  borderBottom: `1px solid ${GLASS_COLORS.borderLight}`,
  minHeight: 52,
  py: 0.75,
  transition: "none",
  "&.Mui-selected": {
    backgroundColor: "rgba(1, 102, 255, 0.12)",
  },
  "&.Mui-selected:hover": {
    backgroundColor: "rgba(1, 102, 255, 0.18)",
  },
  "&:hover": {
    backgroundColor: "rgba(255,255,255,0.05)",
  },
};

const CHECKBOX_SX = {
  color: GLASS_COLORS.textMuted,
  "&.Mui-checked": { color: GLASS_COLORS.primary },
};

const PRIMARY_TYPO = {
  fontFamily: '"Tactic Sans", sans-serif',
  fontWeight: 600,
  color: GLASS_COLORS.textPrimary,
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
};

interface Props {
  open: boolean;
  onClose: () => void;
  onSubmit: (inspectorIds: number[]) => Promise<void>;
  grupo: IRutaGrupoMin | null;
  inspectoresCatalogo: CatalogItem[];
  grupos: IRutaGrupoMin[];
}

type InspectorRowProps = {
  inspector: CatalogItem;
  checked: boolean;
  onToggle: (id: number) => void;
};

const InspectorOptionRow = memo(function InspectorOptionRow({ inspector, checked, onToggle }: InspectorRowProps) {
  return (
    <ListItemButton
      disableRipple
      selected={checked}
      onClick={() => onToggle(inspector.id)}
      sx={INSPECTOR_LIST_ITEM_SX}
    >
      <ListItemIcon sx={{ minWidth: 42 }}>
        <Checkbox edge="start" checked={checked} tabIndex={-1} disableRipple sx={CHECKBOX_SX} />
      </ListItemIcon>
      <ListItemText
        primary={inspector.nombre}
        secondary={inspector.legajo ? `Legajo: ${inspector.legajo}` : undefined}
        primaryTypographyProps={{ sx: PRIMARY_TYPO, title: inspector.nombre }}
        secondaryTypographyProps={{
          sx: { color: GLASS_COLORS.textMuted, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" },
        }}
      />
    </ListItemButton>
  );
});

const ESTIMATE_ROW_PX = 56;

/**
 * Asignación de inspectores: lista virtualizada para pocas filas en DOM y hover más liviano.
 */
function ModalAsignarInspectoresGrupoInner({ open, onClose, onSubmit, grupo, inspectoresCatalogo, grupos }: Props) {
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [saving, setSaving] = useState(false);
  const listParentRef = useRef<HTMLDivElement>(null);

  const selectedIdsSafe = useMemo(() => selectedIds.filter((id) => Number.isFinite(id) && id > 0), [selectedIds]);
  const selectedSet = useMemo(() => new Set(selectedIdsSafe), [selectedIdsSafe]);

  const availableInspectores = useMemo(() => {
    if (!open || !grupo) return [];
    const usedInOtherGroups = new Set(
      grupos
        .filter((g) => g.id !== grupo.id)
        .flatMap((g) => g.inspectores.map((i) => i.inspector_id))
    );
    const selectedInCurrent = new Set(grupo.inspectores.map((i) => i.inspector_id));
    return inspectoresCatalogo.filter((i) => !usedInOtherGroups.has(i.id) || selectedInCurrent.has(i.id));
  }, [open, grupo, grupos, inspectoresCatalogo]);

  const rowVirtualizer = useVirtualizer({
    count: availableInspectores.length,
    getScrollElement: () => listParentRef.current,
    estimateSize: () => ESTIMATE_ROW_PX,
    overscan: 6,
  });

  useEffect(() => {
    if (!open || !grupo) return;
    setSelectedIds(grupo.inspectores.map((i) => i.inspector_id));
  }, [open, grupo]);

  const handleClose = useCallback(() => {
    if (saving) return;
    onClose();
  }, [saving, onClose]);

  const toggleInspector = useCallback((id: number) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!grupo) return;
    setSaving(true);
    try {
      await onSubmit(selectedIdsSafe);
    } finally {
      setSaving(false);
    }
  }, [grupo, onSubmit, selectedIdsSafe]);

  return (
    <AppDialog
      open={open}
      keepMounted={false}
      maxWidth="md"
      fullWidth
      {...DIALOG_OPEN_PERF}
      // eslint-disable-next-line @typescript-eslint/no-unused-vars -- MUI Dialog onClose(event, reason)
      onClose={(_event, _reason) => handleClose()}
      onCloseButtonClick={handleClose}
      title="Inspectores del grupo"
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
        </Box>
      }
    >
      {open && grupo ? (
        <>
          <AppTextField
            label="Grupo"
            value={grupo.nombre}
            fullWidth
            appearance="glass"
            InputProps={{ readOnly: true }}
          />
          <Typography
            variant="caption"
            sx={{
              color: GLASS_COLORS.textMuted,
              fontFamily: '"Tactic Sans", sans-serif',
              display: "block",
              lineHeight: 1.4,
            }}
          >
            Selección reemplaza el equipo del grupo. Excluye inspectores ya asignados a otros grupos.
          </Typography>
          <Box ref={listParentRef} sx={LIST_VIEWPORT_SX}>
            <Box
              sx={{
                height: `${rowVirtualizer.getTotalSize()}px`,
                width: "100%",
                position: "relative",
              }}
            >
              {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                const inspector = availableInspectores[virtualRow.index];
                if (!inspector) return null;
                return (
                  <Box
                    key={virtualRow.key}
                    data-index={virtualRow.index}
                    ref={rowVirtualizer.measureElement}
                    sx={{
                      position: "absolute",
                      top: 0,
                      left: 0,
                      width: "100%",
                      transform: `translateY(${virtualRow.start}px)`,
                    }}
                  >
                    <InspectorOptionRow
                      inspector={inspector}
                      checked={selectedSet.has(inspector.id)}
                      onToggle={toggleInspector}
                    />
                  </Box>
                );
              })}
            </Box>
          </Box>
          <Box sx={{ pt: 0.5 }}>
            <AppButton
              dsVariant="primary"
              fullWidth
              onClick={handleSubmit}
              disabled={saving}
              loading={saving}
              sx={{ py: 1.25, fontWeight: 700, letterSpacing: "0.06em" }}
            >
              Listo
            </AppButton>
          </Box>
        </>
      ) : null}
    </AppDialog>
  );
}

const ModalAsignarInspectoresGrupo = memo(ModalAsignarInspectoresGrupoInner);
export default ModalAsignarInspectoresGrupo;
