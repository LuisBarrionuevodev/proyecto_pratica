import { Box } from "@mui/material";

import type { IRelevamientoListItem } from "../../../api/relevamientosListApi";
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
import { TURNO_CANON } from "../../CargarRelevamientos/config/relevamientoTurnOptions";
import {
  ANGULO_ESQUINA_VALUES,
  buildNumeroTipoDraftPatch,
  relevamientoAnguloEsAplicable,
} from "../utils/relevamientoCamposForm";
import {
  relevamientoAnguloEsquinaDisplay,
  relevamientoCalleDisplay,
  relevamientoEstaAbiertoDisplay,
  relevamientoNombreFantasiaDisplay,
  relevamientoNumeroDisplay,
  relevamientoTurnoDisplay,
} from "../utils/relevamientoCrudDisplay";

export type RelevamientoEditCatalogs = {
  inspectores: string[];
  rubros: string[];
};

export type RelevamientoCrudDialogProps = {
  open: boolean;
  mode: "view" | "edit";
  draft: IRelevamientoListItem;
  fieldErrors: Record<string, string>;
  saving: boolean;
  catalogs: RelevamientoEditCatalogs;
  readOnlyColumns: string[];
  numeroCallesOptions?: string[];
  numeroEditorLabel: string;
  numeroAllowFreeSolo?: boolean;
  globalError?: string | null;
  canEdit?: boolean;
  showDelete?: boolean;
  onClose: () => void;
  onModeChange?: (mode: "view" | "edit") => void;
  onDelete?: () => void;
  onDraftChange: (patch: Partial<IRelevamientoListItem>) => void;
  onSave: () => void | Promise<void>;
  disablePortal?: boolean;
};

function opts(strings: string[]) {
  return strings.map((s) => ({ value: s, label: s || "—" }));
}

const fieldGridSx = {
  display: "grid",
  gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)" },
  gap: 2,
  width: "100%",
} as const;

/**
 * Modal CRUD glass para relevamiento (referencia visual del sistema CRUD unificado).
 */
export function RelevamientoCrudDialog({
  open,
  mode,
  draft,
  fieldErrors,
  saving,
  catalogs,
  readOnlyColumns,
  numeroCallesOptions,
  numeroEditorLabel,
  numeroAllowFreeSolo = false,
  globalError = null,
  canEdit = true,
  showDelete = false,
  onClose,
  onModeChange,
  onDelete,
  onDraftChange,
  onSave,
  disablePortal,
}: RelevamientoCrudDialogProps) {
  const isView = mode === "view";
  const e = (key: string) => fieldErrors[key] ?? "";
  const ro = (key: string) => readOnlyColumns.includes(key);

  const estaAbiertoValue =
    draft.esta_abierto === true ? "Sí" : draft.esta_abierto === false ? "No" : "";

  const anguloAplica = relevamientoAnguloEsAplicable({
    numero_tipo: draft.numero_tipo,
    numero: draft.numero,
  });

  const handleClose = () => {
    if (saving) return;
    onClose();
  };

  const titulo = isView ? "Relevamiento" : "Editar relevamiento";
  const subtitulo = [draft.fecha, draft.inspector].filter(Boolean).join(" · ") || undefined;

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
          domainChip="Relevamientos"
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

      <CrudDialogSection title="Datos del relevamiento" variant="plain">
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
              disabled={ro("fecha")}
              InputLabelProps={{ shrink: true }}
              error={!!e("fecha")}
              helperText={e("fecha") || undefined}
              fullWidth
              required
            />
          </CrudFormSlot>
          <CrudFormSlot
            label="Turno carga"
            mode={mode}
            value={relevamientoTurnoDisplay(draft.turno)}
            error={!!e("turno")}
            helperText={e("turno")}
          >
            <AppSelect
              appearance="glass"
              label="Turno carga"
              value={draft.turno ?? ""}
              onChange={(ev) => {
                const v = ev.target.value as string;
                onDraftChange({ turno: v === "" ? null : v });
              }}
              options={[
                { value: "", label: "—" },
                { value: TURNO_CANON.MANIANA, label: "Mañana" },
                { value: TURNO_CANON.TARDE, label: "Tarde" },
              ]}
              fullWidth
              error={!!e("turno")}
              helperText={e("turno") || undefined}
            />
          </CrudFormSlot>
          <CrudFormSlot
            label="Inspector"
            mode={mode}
            value={draft.inspector}
            required
            error={!!e("inspector")}
            helperText={e("inspector")}
            sx={{ gridColumn: { sm: "1 / -1" } }}
          >
            <AppSelect
              appearance="glass"
              label="Inspector"
              value={draft.inspector ?? ""}
              onChange={(ev) => onDraftChange({ inspector: ev.target.value as string })}
              options={opts(["", ...catalogs.inspectores])}
              fullWidth
              disabled={ro("inspector")}
              error={!!e("inspector")}
              helperText={e("inspector") || undefined}
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
            value={relevamientoCalleDisplay(draft)}
            required
            error={!!e("calle")}
            helperText={e("calle")}
          >
            <AppTextField
              appearance="glass"
              label="Calle"
              value={draft.calle ?? ""}
              onChange={(ev) => onDraftChange({ calle: ev.target.value })}
              fullWidth
              disabled={ro("calle")}
              error={!!e("calle")}
              helperText={e("calle") || undefined}
              required
            />
          </CrudFormSlot>
          <CrudFormSlot
            label={numeroEditorLabel}
            mode={mode}
            value={relevamientoNumeroDisplay(draft)}
            error={!!e("numero")}
            helperText={e("numero")}
          >
            <NumeroEsquinaEditor
              value={draft.numero ?? null}
              onChange={(newValue) => onDraftChange({ numero: newValue })}
              onModeChange={(editorMode) => onDraftChange(buildNumeroTipoDraftPatch(editorMode))}
              extraCalles={numeroCallesOptions}
              label={numeroEditorLabel}
              error={!!e("numero")}
              helperText={e("numero")}
              allowFreeSolo={numeroAllowFreeSolo}
              initialMode={draft.numero_tipo === "ESQUINA" ? "ESQUINA" : "NUMERO"}
            />
          </CrudFormSlot>
          {anguloAplica ? (
            <CrudFormSlot
              label="Ángulo esquina"
              mode={mode}
              value={relevamientoAnguloEsquinaDisplay(draft)}
              error={!!e("angulo_esquina")}
              helperText={e("angulo_esquina") || "Solo para esquinas/intersecciones."}
            >
              <AppSelect
                appearance="glass"
                label="Ángulo esquina"
                value={draft.angulo_esquina ?? ""}
                onChange={(ev) => {
                  const v = ev.target.value as string;
                  onDraftChange({ angulo_esquina: v === "" ? null : (v as typeof draft.angulo_esquina) });
                }}
                options={[
                  { value: "", label: "—" },
                  ...ANGULO_ESQUINA_VALUES.map((a) => ({ value: a, label: a })),
                ]}
                fullWidth
                error={!!e("angulo_esquina")}
                helperText={e("angulo_esquina") || "Solo para esquinas/intersecciones."}
              />
            </CrudFormSlot>
          ) : null}
        </Box>
      </CrudDialogSection>

      <CrudDialogSection title="Actividad" variant="plain">
        <Box sx={fieldGridSx}>
          <CrudFormSlot
            label="Rubro"
            mode={mode}
            value={draft.rubro}
            required
            error={!!e("rubro")}
            helperText={e("rubro")}
          >
            <AppSelect
              appearance="glass"
              label="Rubro"
              value={draft.rubro ?? ""}
              onChange={(ev) => onDraftChange({ rubro: ev.target.value as string })}
              options={opts(["", ...catalogs.rubros])}
              fullWidth
              error={!!e("rubro")}
              helperText={e("rubro") || undefined}
              required
            />
          </CrudFormSlot>
          <CrudFormSlot
            label="Nombre fantasía"
            mode={mode}
            value={relevamientoNombreFantasiaDisplay(draft)}
            error={!!e("nombre_fantasia")}
            helperText={e("nombre_fantasia") || "Opcional. Sirve para distinguir locales en una misma esquina."}
          >
            <AppTextField
              appearance="glass"
              label="Nombre fantasía"
              value={draft.nombre_fantasia ?? ""}
              onChange={(ev) => onDraftChange({ nombre_fantasia: ev.target.value })}
              fullWidth
              inputProps={{ maxLength: 255 }}
              error={!!e("nombre_fantasia")}
              helperText={
                e("nombre_fantasia") || "Opcional. Sirve para distinguir locales en una misma esquina."
              }
            />
          </CrudFormSlot>
          <CrudFormSlot
            label="Está abierto"
            mode={mode}
            value={relevamientoEstaAbiertoDisplay(draft.esta_abierto)}
            error={!!e("esta_abierto")}
            helperText={e("esta_abierto")}
          >
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
              helperText={e("esta_abierto") || undefined}
            />
          </CrudFormSlot>
        </Box>
      </CrudDialogSection>
    </CrudGlassDialog>
  );
}
