import { Box, Typography } from "@mui/material";
import type { IRelevamientoListItem } from "../../../api/relevamientosListApi";
import NumeroEsquinaEditor from "../../../components/shared/NumeroEsquinaEditor";
import { formDialogContentStackSx } from "../../../styles/formDialogStyles";
import { AppButton, AppDialog, AppSelect, AppTextField } from "../../../ui";

export type RelevamientoEditCatalogs = {
  inspectores: string[];
  rubros: string[];
};

export type RelevamientoEditDialogProps = {
  open: boolean;
  draft: IRelevamientoListItem;
  fieldErrors: Record<string, string>;
  saving: boolean;
  catalogs: RelevamientoEditCatalogs;
  readOnlyColumns: string[];
  numeroCallesOptions?: string[];
  numeroEditorLabel: string;
  numeroAllowFreeSolo?: boolean;
  onClose: () => void;
  onDraftChange: (patch: Partial<IRelevamientoListItem>) => void;
  onSave: () => void | Promise<void>;
};

function opts(strings: string[]) {
  return strings.map((s) => ({ value: s, label: s || "—" }));
}

/**
 * Formulario de edición de relevamiento en `AppDialog` (Digitaliza glass).
 * El padre mantiene el draft completo y el guardado vía `submitRelevamientoRow`.
 */
export function RelevamientoEditDialog({
  open,
  draft,
  fieldErrors,
  saving,
  catalogs,
  readOnlyColumns,
  numeroCallesOptions,
  numeroEditorLabel,
  numeroAllowFreeSolo = false,
  onClose,
  onDraftChange,
  onSave,
}: RelevamientoEditDialogProps) {
  const e = (key: string) => fieldErrors[key] ?? "";
  const ro = (key: string) => readOnlyColumns.includes(key);

  const estaAbiertoValue =
    draft.esta_abierto === true ? "Sí" : draft.esta_abierto === false ? "No" : "";

  const handleClose = () => {
    if (saving) return;
    onClose();
  };

  return (
    <AppDialog
      open={open}
      onClose={(_ev, _reason) => handleClose()}
      onCloseButtonClick={handleClose}
      title="Editar relevamiento"
      maxWidth="md"
      fullWidth
      contentDividers
      contentSx={[
        formDialogContentStackSx,
        { maxHeight: "min(72vh, 720px)", overflowY: "auto" },
      ]}
      showCloseButton
      actions={
        <Box sx={{ display: "flex", gap: 1.5, justifyContent: "flex-end", flexWrap: "wrap", width: "100%" }}>
          <AppButton dsVariant="ghost" onClick={handleClose} disabled={saving}>
            Cancelar
          </AppButton>
          <AppButton dsVariant="primary" onClick={() => void onSave()} loading={saving} disabled={saving}>
            Guardar
          </AppButton>
        </Box>
      }
    >
      <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.55)", fontFamily: '"Tactic Sans", sans-serif' }}>
        ID: {draft.id}
      </Typography>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)" },
          gap: 2,
          width: "100%",
        }}
      >
        <AppTextField
          appearance="glass"
          label="Fecha"
          type="date"
          value={draft.fecha ?? ""}
          onChange={(ev) => onDraftChange({ fecha: ev.target.value })}
          disabled={ro("fecha")}
          InputLabelProps={{ shrink: true }}
          error={!!e("fecha")}
          helperText={e("fecha")}
          fullWidth
          required
        />
        <AppSelect
          appearance="glass"
          label="Inspector"
          value={draft.inspector ?? ""}
          onChange={(ev) => onDraftChange({ inspector: ev.target.value as string })}
          options={opts(["", ...catalogs.inspectores])}
          fullWidth
          disabled={ro("inspector")}
          error={!!e("inspector")}
          helperText={e("inspector")}
          required
        />
        <AppTextField
          appearance="glass"
          label="Calle"
          value={draft.calle ?? ""}
          onChange={(ev) => onDraftChange({ calle: ev.target.value })}
          fullWidth
          disabled={ro("calle")}
          error={!!e("calle")}
          helperText={e("calle")}
          required
        />
        <AppSelect
          appearance="glass"
          label="Rubro"
          value={draft.rubro ?? ""}
          onChange={(ev) => onDraftChange({ rubro: ev.target.value as string })}
          options={opts(["", ...catalogs.rubros])}
          fullWidth
          error={!!e("rubro")}
          helperText={e("rubro")}
          required
        />
        <AppSelect
          appearance="glass"
          label="Turno carga"
          value={draft.turno ?? ""}
          onChange={(ev) => {
            const v = ev.target.value as string;
            onDraftChange({ turno: v === "" ? null : v });
          }}
          options={opts(["", "MANIANA", "TARDE"])}
          fullWidth
          error={!!e("turno")}
          helperText={e("turno")}
        />
        <AppSelect
          appearance="glass"
          label="Está abierto"
          value={estaAbiertoValue}
          onChange={(ev) => {
            const v = ev.target.value as string;
            if (v === "Sí") onDraftChange({ esta_abierto: true });
            else if (v === "No") onDraftChange({ esta_abierto: false });
            else onDraftChange({ esta_abierto: null });
          }}
          options={opts(["", "Sí", "No"])}
          fullWidth
          error={!!e("esta_abierto")}
          helperText={e("esta_abierto")}
        />
      </Box>

      <Typography variant="subtitle2" sx={{ color: "rgba(255,255,255,0.8)", fontFamily: '"Tactic Sans", sans-serif', pt: 1 }}>
        Número / esquina
      </Typography>
      <NumeroEsquinaEditor
        value={draft.numero ?? null}
        onChange={(newValue) => onDraftChange({ numero: newValue })}
        onModeChange={(mode) => onDraftChange({ numero_tipo: mode })}
        extraCalles={numeroCallesOptions}
        label={numeroEditorLabel}
        error={!!e("numero")}
        helperText={e("numero")}
        allowFreeSolo={numeroAllowFreeSolo}
        initialMode={draft.numero_tipo === "ESQUINA" ? "ESQUINA" : "NUMERO"}
      />
    </AppDialog>
  );
}
