import { Autocomplete, Box, Chip, TextField } from "@mui/material";

import type { CatalogItem } from "../../../api/gridApi";
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
  domicilioCalleValorEdicion,
  domicilioNumeroValorEdicion,
} from "../../../utils/domicilioCalleUi";
import {
  relevamientoAnguloEsquinaDisplay,
  relevamientoCalleDisplay,
  relevamientoEstaAbiertoDisplay,
  relevamientoNombreFantasiaDisplay,
  relevamientoNumeroDisplay,
  relevamientoTurnoDisplay,
} from "../utils/relevamientoCrudDisplay";

export type RelevamientoEditCatalogs = {
  relevadores: CatalogItem[];
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
  numeroEditorLabel: _numeroEditorLabel,
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

  const numeroModoEsquina = (draft.numero_tipo ?? "").toUpperCase() === "ESQUINA";
  const numeroFieldLabel = numeroModoEsquina ? "Calle de esquina" : "Número";

  const handleClose = () => {
    if (saving) return;
    onClose();
  };

  const titulo = isView ? "Relevamiento" : "Editar relevamiento";
  const subtitulo =
    [draft.fecha, draft.relevadores_label ?? draft.relevadores?.map((r) => r.nombre).join(" · ")]
      .filter(Boolean)
      .join(" · ") || undefined;

  const selectedRelevadores = catalogs.relevadores.filter((r) =>
    (draft.relevador_ids ?? draft.relevadores?.map((x) => x.id) ?? []).includes(r.id)
  );

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
            label="Relevador"
            mode={mode}
            value={draft.relevadores_label ?? draft.relevadores?.map((r) => r.nombre).join(" · ")}
            required
            error={!!e("relevador") || !!e("relevador_ids")}
            helperText={e("relevador") || e("relevador_ids")}
            sx={{ gridColumn: { sm: "1 / -1" } }}
          >
            <Autocomplete
              multiple
              options={catalogs.relevadores}
              getOptionLabel={(o) => o.nombre}
              value={selectedRelevadores}
              onChange={(_ev, value) => {
                onDraftChange({
                  relevador_ids: value.map((v) => v.id),
                  relevadores: value.map((v) => ({ id: v.id, nombre: v.nombre })),
                  relevadores_label: value.map((v) => v.nombre).join(" · "),
                });
              }}
              disabled={ro("relevador_ids")}
              renderTags={(value, getTagProps) =>
                value.map((option, index) => (
                  <Chip {...getTagProps({ index })} key={option.id} label={option.nombre} size="small" />
                ))
              }
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Relevador"
                  required
                  error={!!e("relevador") || !!e("relevador_ids")}
                  helperText={e("relevador") || e("relevador_ids") || undefined}
                />
              )}
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
              value={domicilioCalleValorEdicion(draft)}
              onChange={(ev) => onDraftChange({ calle: ev.target.value })}
              fullWidth
              disabled={ro("calle")}
              error={!!e("calle")}
              helperText={e("calle") || undefined}
              required
            />
          </CrudFormSlot>
          <CrudFormSlot
            label={numeroFieldLabel}
            mode={mode}
            value={relevamientoNumeroDisplay(draft)}
            error={!!e("numero")}
            helperText={e("numero")}
          >
            <NumeroEsquinaEditor
              value={domicilioNumeroValorEdicion(draft) || null}
              onChange={(newValue) => onDraftChange({ numero: newValue })}
              onModeChange={(editorMode) =>
                onDraftChange(buildNumeroTipoDraftPatch(editorMode, draft))
              }
              extraCalles={numeroCallesOptions}
              label={numeroFieldLabel}
              error={!!e("numero")}
              helperText={e("numero")}
              allowFreeSolo={numeroAllowFreeSolo}
              initialMode={draft.numero_tipo === "ESQUINA" ? "ESQUINA" : "NUMERO"}
            />
          </CrudFormSlot>
          {anguloAplica ? (
            <CrudFormSlot
              label="Orientación"
              mode={mode}
              value={relevamientoAnguloEsquinaDisplay(draft)}
              error={!!e("angulo_esquina")}
              helperText={
                e("angulo_esquina") || "Ubicación del local en la esquina: NE, NO, SE o SO."
              }
            >
              <AppSelect
                appearance="glass"
                label="Orientación"
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
                helperText={
                  e("angulo_esquina") || "Ubicación del local en la esquina: NE, NO, SE o SO."
                }
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
