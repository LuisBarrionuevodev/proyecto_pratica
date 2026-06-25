import { Box } from "@mui/material";

import type { IDenunciaGestionItem } from "../../../api/denunciasApi";
import NumeroEsquinaEditor from "../../../components/shared/NumeroEsquinaEditor";
import {
  CrudDialogActions,
  CrudDialogHeader,
  CrudDialogSection,
  CrudFormErrorSummary,
  CrudFormSlot,
  CrudGlassDialog,
} from "../../../components/crudDialog";
import { AppSelect, AppTextField } from "../../../ui";

export type DenunciaCrudDialogProps = {
  open: boolean;
  mode: "view" | "edit";
  draft: IDenunciaGestionItem;
  fieldErrors: Record<string, string>;
  saving: boolean;
  globalError?: string | null;
  canEdit?: boolean;
  showDelete?: boolean;
  onClose: () => void;
  onModeChange?: (mode: "view" | "edit") => void;
  onDelete?: () => void;
  onDraftChange: (patch: Partial<IDenunciaGestionItem>) => void;
  onSave: () => void | Promise<void>;
  disablePortal?: boolean;
};

const fieldGridSx = {
  display: "grid",
  gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)" },
  gap: 2,
  width: "100%",
} as const;

const ESTADO_OPTIONS = ["ABIERTA", "CERRADA", "DESCARTADA"] as const;

function denunciaNumeroDisplay(row: IDenunciaGestionItem): string | null {
  if (row.numero_tipo === "ESQUINA" && row.numero) return row.numero;
  return row.numero ?? null;
}

/** Modal CRUD glass para denuncia (mismo patrón que Relevamientos). */
export function DenunciaCrudDialog({
  open,
  mode,
  draft,
  fieldErrors,
  saving,
  globalError = null,
  canEdit = true,
  showDelete = false,
  onClose,
  onModeChange,
  onDelete,
  onDraftChange,
  onSave,
  disablePortal,
}: DenunciaCrudDialogProps) {
  const isView = mode === "view";
  const e = (key: string) => fieldErrors[key] ?? "";

  const handleClose = () => {
    if (saving) return;
    onClose();
  };

  const titulo = isView ? "Denuncia" : "Editar denuncia";
  const subtitulo = [draft.fecha, draft.estado].filter(Boolean).join(" · ") || undefined;

  return (
    <CrudGlassDialog
      open={open}
      disablePortal={disablePortal}
      hideBackdrop={disablePortal}
      onClose={(_ev, _reason) => handleClose()}
      onCloseButtonClick={handleClose}
      maxWidth="md"
      title={
        <CrudDialogHeader
          domainChip="Denuncias"
          mode={isView ? "view" : "edit"}
          titulo={titulo}
          subtitulo={subtitulo}
          statusChip={draft.editable === false ? "No editable" : undefined}
        />
      }
      actions={
        <CrudDialogActions
          mode={isView ? "view" : "edit"}
          onEdit={canEdit && onModeChange ? () => onModeChange("edit") : undefined}
          onSave={() => void onSave()}
          onDelete={onDelete}
          loading={saving}
          canEdit={canEdit}
          showDelete={showDelete && !isView}
          saveLabel="Guardar cambios"
        />
      }
    >
      <CrudFormErrorSummary message={globalError} />

      <CrudDialogSection title="Datos de la denuncia" variant="plain">
        <Box sx={fieldGridSx}>
          <CrudFormSlot
            label="Fecha"
            mode={mode}
            value={draft.fecha}
            required
            error={!!e("fecha")}
            helperText={e("fecha")}
          >
            <AppTextField
              appearance="glass"
              label="Fecha"
              type="date"
              value={draft.fecha ?? ""}
              onChange={(ev) => onDraftChange({ fecha: ev.target.value })}
              InputLabelProps={{ shrink: true }}
              error={!!e("fecha")}
              helperText={e("fecha") || undefined}
              fullWidth
              required
            />
          </CrudFormSlot>
          <CrudFormSlot
            label="Estado"
            mode={mode}
            value={draft.estado}
            error={!!e("estado")}
            helperText={e("estado")}
          >
            <AppSelect
              appearance="glass"
              label="Estado"
              value={draft.estado ?? ""}
              onChange={(ev) => onDraftChange({ estado: ev.target.value as string })}
              options={[{ value: "", label: "—" }, ...ESTADO_OPTIONS.map((v) => ({ value: v, label: v }))]}
              fullWidth
              error={!!e("estado")}
              helperText={e("estado") || undefined}
            />
          </CrudFormSlot>
          <CrudFormSlot
            label="Motivo"
            mode={mode}
            value={draft.motivo}
            required
            error={!!e("motivo")}
            helperText={e("motivo")}
            sx={{ gridColumn: { sm: "1 / -1" } }}
          >
            <AppTextField
              appearance="glass"
              label="Motivo"
              value={draft.motivo ?? ""}
              onChange={(ev) => onDraftChange({ motivo: ev.target.value })}
              error={!!e("motivo")}
              helperText={e("motivo") || undefined}
              fullWidth
              required
            />
          </CrudFormSlot>
        </Box>
      </CrudDialogSection>

      <CrudDialogSection title="Domicilio" variant="plain">
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <CrudFormSlot
            label="Calle"
            mode={mode}
            value={draft.calle}
            required
            error={!!e("calle")}
            helperText={e("calle")}
          >
            <AppTextField
              appearance="glass"
              label="Calle"
              value={draft.calle ?? ""}
              onChange={(ev) => onDraftChange({ calle: ev.target.value })}
              error={!!e("calle")}
              helperText={e("calle") || undefined}
              fullWidth
              required
            />
          </CrudFormSlot>
          <CrudFormSlot
            label="Número/Esquina"
            mode={mode}
            value={denunciaNumeroDisplay(draft)}
            error={!!e("numero")}
            helperText={e("numero")}
          >
            <NumeroEsquinaEditor
              value={draft.numero ?? null}
              onChange={(newValue) => onDraftChange({ numero: newValue })}
              onModeChange={(editorMode) => onDraftChange({ numero_tipo: editorMode })}
              label="Número/Esquina"
              error={!!e("numero")}
              helperText={e("numero")}
              allowFreeSolo
              initialMode={draft.numero_tipo === "ESQUINA" ? "ESQUINA" : "NUMERO"}
            />
          </CrudFormSlot>
        </Box>
      </CrudDialogSection>
    </CrudGlassDialog>
  );
}
