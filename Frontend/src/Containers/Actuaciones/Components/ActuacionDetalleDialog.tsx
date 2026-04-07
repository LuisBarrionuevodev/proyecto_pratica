import { Alert, Box, Typography } from "@mui/material";
import { useEffect, useState } from "react";
import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import { getDropdownOptions } from "../../CargarActuaciones/config/dropdownOptions";
import { formDialogContentStackSx } from "../../../styles/formDialogStyles";
import { AppButton, AppDialog, AppSelect, AppTextField } from "../../../ui";

export type ActuacionEditCatalogs = {
  inspectores: string[];
  motivos: string[];
  rubros: string[];
  tipos: string[];
  contraproducencias: string[];
  motivosComprobacion: string[];
};

export type ActuacionDetalleDialogProps = {
  open: boolean;
  draft: IActuacionListItem;
  fieldErrors: Record<string, string>;
  saving: boolean;
  catalogs: ActuacionEditCatalogs;
  readOnlyColumns: string[];
  /** Reservados para una futura edición de domicilio; no usados en el modo edición actual. */
  numeroCallesOptions?: string[];
  numeroEditorLabel?: string;
  numeroAllowFreeSolo?: boolean;
  /** Si es false, no se muestra el paso a edición (p. ej. bandejas restringidas). */
  canEdit?: boolean;
  onClose: () => void;
  onDraftChange: (patch: Partial<IActuacionListItem>) => void;
  onSave: () => void | Promise<void>;
};

function opts(strings: string[]) {
  return strings.map((s) => ({ value: s, label: s || "—" }));
}

const sectionTitleSx = {
  color: "rgba(255,255,255,0.88)",
  fontFamily: '"Tactic Sans", sans-serif',
  fontWeight: 600,
  mb: 1.5,
  display: "block" as const,
};

const blockShellSx = {
  p: 1.75,
  borderRadius: 2,
  bgcolor: "rgba(255,255,255,0.04)",
  border: "1px solid rgba(255,255,255,0.08)",
  fontFamily: '"Tactic Sans", sans-serif',
};

function dash(v: unknown): string {
  if (v === null || v === undefined || v === "") return "—";
  return String(v);
}

function domicilioTexto(row: IActuacionListItem): string {
  const calle =
    row.calle_estado === "OK" && row.calle_normalizada ? row.calle_normalizada : row.calle ?? "";
  let numero = "";
  if (row.numero_tipo === "ESQUINA" && (row.numero_esquina || row.esquina_normalizada)) {
    numero = row.numero_esquina || row.esquina_normalizada || "";
  } else {
    numero = row.numero ?? "";
  }
  const line = [calle, numero].filter(Boolean).join(" ").trim();
  return line || "—";
}

function inspectoresLinea(row: IActuacionListItem): string {
  const parts = [row.inspector1, row.inspector2, row.inspector3].filter((x) => x?.trim());
  return parts.length ? parts.join(", ") : "—";
}

function tieneReferenciaAdmin(row: IActuacionListItem): boolean {
  return !!(
    row.expediente_numero ||
    row.expediente_anio != null ||
    row.oficio_numero ||
    row.oficio_anio != null ||
    (row.oficio_causa != null && String(row.oficio_causa).trim() !== "")
  );
}

function BloqueIniciadorVacío() {
  return (
    <Box sx={blockShellSx}>
      <Typography variant="subtitle2" sx={{ ...sectionTitleSx, mt: 0 }}>
        3. Iniciador de la ruta
      </Typography>
      <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.62)", lineHeight: 1.5 }}>
        Los datos del iniciador de ruta no están disponibles desde este listado. Cuando el API los
        incluya, se mostrarán aquí sin mezclarlos con la actuación ni el local.
      </Typography>
    </Box>
  );
}

/**
 * Detalle de actuación (lectura por defecto) y edición parcial tras "Editar".
 * Guardado vía `submitActuacionRow` en el padre (canal actas: sin reenvío de expediente/oficio).
 */
export function ActuacionDetalleDialog({
  open,
  draft,
  fieldErrors,
  saving,
  catalogs,
  readOnlyColumns,
  canEdit = true,
  onClose,
  onDraftChange,
  onSave,
}: ActuacionDetalleDialogProps) {
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    if (open) setIsEditing(false);
  }, [open, draft.id]);

  const e = (key: string) => fieldErrors[key] ?? "";
  const ro = (key: string) => readOnlyColumns.includes(key);
  const lockedNotif = draft.notificacion_editable === false;
  const lockedComp = draft.comprobacion_editable === false;

  const mergedCatalogs = {
    inspectores: catalogs.inspectores,
    motivos: catalogs.motivos,
    rubros: catalogs.rubros,
    tipos: catalogs.tipos,
    contraproducencias: catalogs.contraproducencias,
    motivosComprobacion: catalogs.motivosComprobacion,
  };

  const handleClose = () => {
    if (saving) return;
    onClose();
  };

  const handleBackToDetail = () => {
    if (saving) return;
    setIsEditing(false);
  };

  const title = isEditing ? "Editar actuación" : "Detalle de actuación";

  const detalleVista = (
    <>
      <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.55)", fontFamily: '"Tactic Sans", sans-serif' }}>
        ID actuación: {draft.id}
      </Typography>

      <Box sx={blockShellSx}>
        <Typography variant="subtitle2" sx={{ ...sectionTitleSx, mt: 0 }}>
          1. Datos de la actuación actual
        </Typography>
        <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.78)", mb: 0.75 }}>
          OT: {dash(draft.orden_trabajo_numero)} · Fecha: {dash(draft.fecha_actuacion)}
        </Typography>
        <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.75)", mb: 0.75 }}>
          Tipo: {dash(draft.tipo_actuacion)} · Contraproducencia: {dash(draft.contraproducencia)}
        </Typography>
        {draft.resultado_cumplimiento_oficio != null &&
          String(draft.resultado_cumplimiento_oficio).trim() !== "" && (
            <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.75)", mb: 0.75 }}>
              Resultado (oficio / reinspección): {dash(draft.resultado_cumplimiento_oficio)}
            </Typography>
          )}
        <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.75)", mb: 1 }}>
          Inspectores: {inspectoresLinea(draft)}
        </Typography>
        <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.45)", display: "block", mb: 0.5 }}>
          Actas del día
        </Typography>
        <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.72)" }}>
          Inspección: {dash(draft.acta_inspeccion_num)} · Notificación: {dash(draft.acta_notificacion_num)} ·
          Comprobación: {dash(draft.acta_comprobacion_num)}
        </Typography>
        <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.72)", mt: 0.5 }}>
          Motivos notif.: {dash(draft.notificacion_motivo_1)} · {dash(draft.notificacion_motivo_2)} ·{" "}
          {dash(draft.notificacion_motivo_3)}
        </Typography>
        <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.72)", mt: 0.5 }}>
          Motivo comprob.: {dash(draft.comprobacion_motivo)}
        </Typography>
        <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.72)", mt: 0.5 }}>
          Clausura: {dash(draft.acta_clausura_num)} · Decomiso: {dash(draft.acta_decomiso_num)}
          {draft.decomiso_kilos_total != null ? ` (${draft.decomiso_kilos_total} kg)` : ""}
        </Typography>
        {tieneReferenciaAdmin(draft) && (
          <Box sx={{ mt: 1.5, pt: 1.5, borderTop: "1px solid rgba(255,255,255,0.08)" }}>
            <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.45)", display: "block", mb: 0.5 }}>
              Referencia administrativa (comprobación)
            </Typography>
            <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.68)" }}>
              Expediente: {dash(draft.expediente_numero)} / {dash(draft.expediente_anio)} · Oficio:{" "}
              {dash(draft.oficio_numero)} / {dash(draft.oficio_anio)}
            </Typography>
            {draft.oficio_causa != null && String(draft.oficio_causa).trim() !== "" && (
              <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.65)", mt: 0.5 }}>
                Causa oficio: {dash(draft.oficio_causa)}
              </Typography>
            )}
          </Box>
        )}
      </Box>

      <Box sx={blockShellSx}>
        <Typography variant="subtitle2" sx={{ ...sectionTitleSx, mt: 0 }}>
          2. Datos del local
        </Typography>
        <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.78)", mb: 0.75 }}>
          Domicilio: {domicilioTexto(draft)}
        </Typography>
        <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.75)", mb: 0.75 }}>
          Nombre del local: {dash(draft.nombre_local)}
        </Typography>
        <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.75)", mb: 0.75 }}>
          Rubro: {dash(draft.rubro_nombre)}
        </Typography>
        <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.75)" }}>
          Contribuyente: {dash(draft.contrib_apellido)} {dash(draft.contrib_nombre)} · Doc. {dash(draft.doc_nro)}
        </Typography>
      </Box>

      <BloqueIniciadorVacío />
    </>
  );

  const roFieldSx = { "& .MuiInputBase-input": { color: "rgba(255,255,255,0.72)" } };

  const edicionVista = (
    <>
      {(lockedNotif || lockedComp) && (
        <Alert severity="info" variant="outlined" sx={{ mb: 1 }}>
          {lockedNotif && "Algunos campos de notificación están bloqueados (expediente). "}
          {lockedComp && "Algunos campos de comprobación están bloqueados (expediente). "}
        </Alert>
      )}

      <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.55)", fontFamily: '"Tactic Sans", sans-serif' }}>
        ID actuación: {draft.id}
      </Typography>

      <Box sx={blockShellSx}>
        <Typography variant="subtitle2" sx={{ ...sectionTitleSx, mt: 0 }}>
          1. Datos de la actuación actual
        </Typography>
        <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.45)", display: "block", mb: 1 }}>
          Solo lectura: OT, fecha, tipo, contraproducencia e inspectores no se editan desde este canal.
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
            label="OT"
            value={draft.orden_trabajo_numero ?? ""}
            disabled
            sx={roFieldSx}
            fullWidth
          />
          <AppTextField
            appearance="glass"
            label="Fecha"
            type="date"
            value={draft.fecha_actuacion ?? ""}
            disabled
            sx={roFieldSx}
            InputLabelProps={{ shrink: true }}
            fullWidth
          />
          <AppTextField appearance="glass" label="Tipo" value={draft.tipo_actuacion ?? ""} disabled sx={roFieldSx} fullWidth />
          <AppTextField
            appearance="glass"
            label="Contraproducencia"
            value={draft.contraproducencia ?? ""}
            disabled
            sx={roFieldSx}
            fullWidth
          />
          {draft.resultado_cumplimiento_oficio != null &&
            String(draft.resultado_cumplimiento_oficio).trim() !== "" && (
              <AppTextField
                appearance="glass"
                label="Resultado (oficio / reinspección)"
                value={draft.resultado_cumplimiento_oficio ?? ""}
                disabled
                sx={{ ...roFieldSx, gridColumn: { xs: "1 / -1", sm: "1 / -1" } }}
                fullWidth
              />
            )}
          <AppSelect
            appearance="glass"
            label="Inspector 1"
            value={draft.inspector1 ?? ""}
            options={opts(["", ...catalogs.inspectores])}
            disabled
            sx={roFieldSx}
            fullWidth
          />
          <AppSelect
            appearance="glass"
            label="Inspector 2"
            value={draft.inspector2 ?? ""}
            options={opts(["", ...catalogs.inspectores])}
            disabled
            sx={roFieldSx}
            fullWidth
          />
          <AppSelect
            appearance="glass"
            label="Inspector 3"
            value={draft.inspector3 ?? ""}
            options={opts(["", ...catalogs.inspectores])}
            disabled
            sx={roFieldSx}
            fullWidth
          />
        </Box>

        <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.5)", display: "block", mt: 2, mb: 1 }}>
          Actas del día (editables)
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
            label="Acta inspección"
            value={draft.acta_inspeccion_num ?? ""}
            onChange={(ev) => onDraftChange({ acta_inspeccion_num: ev.target.value })}
            error={!!e("acta_inspeccion_num")}
            helperText={e("acta_inspeccion_num")}
            fullWidth
          />
        </Box>

        <Typography variant="subtitle2" sx={{ ...sectionTitleSx, mt: 2, mb: 1.5 }}>
          Notificación
        </Typography>
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)" }, gap: 2, width: "100%" }}>
          <AppTextField
            appearance="glass"
            label="Acta notificación"
            value={draft.acta_notificacion_num ?? ""}
            onChange={(ev) => onDraftChange({ acta_notificacion_num: ev.target.value })}
            disabled={lockedNotif}
            error={!!e("acta_notificacion_num")}
            helperText={lockedNotif ? "Notificación con expediente: no editable aquí." : e("acta_notificacion_num")}
            fullWidth
          />
          <AppSelect
            appearance="glass"
            label="Motivo notif. 1"
            value={draft.notificacion_motivo_1 ?? ""}
            onChange={(ev) => onDraftChange({ notificacion_motivo_1: ev.target.value as string })}
            options={opts(["", ...catalogs.motivos])}
            disabled={lockedNotif}
            error={!!e("notificacion_motivo_1")}
            helperText={lockedNotif ? "Notificación con expediente: no editable aquí." : e("notificacion_motivo_1")}
            fullWidth
          />
          <AppSelect
            appearance="glass"
            label="Motivo notif. 2"
            value={draft.notificacion_motivo_2 ?? ""}
            onChange={(ev) => onDraftChange({ notificacion_motivo_2: ev.target.value as string })}
            options={opts(["", ...catalogs.motivos])}
            disabled={lockedNotif}
            error={!!e("notificacion_motivo_2")}
            helperText={lockedNotif ? "Notificación con expediente: no editable aquí." : e("notificacion_motivo_2")}
            fullWidth
          />
          <AppSelect
            appearance="glass"
            label="Motivo notif. 3"
            value={draft.notificacion_motivo_3 ?? ""}
            onChange={(ev) => onDraftChange({ notificacion_motivo_3: ev.target.value as string })}
            options={opts(["", ...catalogs.motivos])}
            disabled={lockedNotif}
            error={!!e("notificacion_motivo_3")}
            helperText={lockedNotif ? "Notificación con expediente: no editable aquí." : e("notificacion_motivo_3")}
            fullWidth
          />
        </Box>

        <Typography variant="subtitle2" sx={{ ...sectionTitleSx, mt: 2, mb: 1.5 }}>
          Comprobación
        </Typography>
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)" }, gap: 2, width: "100%" }}>
          <AppTextField
            appearance="glass"
            label="Acta comprobación"
            value={draft.acta_comprobacion_num ?? ""}
            onChange={(ev) => onDraftChange({ acta_comprobacion_num: ev.target.value })}
            disabled={lockedComp}
            error={!!e("acta_comprobacion_num")}
            helperText={lockedComp ? "Comprobación con expediente: no editable aquí." : e("acta_comprobacion_num")}
            fullWidth
          />
          <AppSelect
            appearance="glass"
            label="Motivo comprobación"
            value={draft.comprobacion_motivo ?? ""}
            onChange={(ev) => onDraftChange({ comprobacion_motivo: ev.target.value as string })}
            options={opts(getDropdownOptions("Motivo comprobación", mergedCatalogs))}
            disabled={lockedComp}
            error={!!e("comprobacion_motivo")}
            helperText={lockedComp ? "Comprobación con expediente: no editable aquí." : e("comprobacion_motivo")}
            fullWidth
          />
        </Box>

        <Typography variant="subtitle2" sx={{ ...sectionTitleSx, mt: 2, mb: 1.5 }}>
          Clausura / decomiso
        </Typography>
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)" }, gap: 2, width: "100%" }}>
          <AppTextField
            appearance="glass"
            label="Acta clausura"
            value={draft.acta_clausura_num ?? ""}
            onChange={(ev) => onDraftChange({ acta_clausura_num: ev.target.value })}
            error={!!e("acta_clausura_num")}
            helperText={e("acta_clausura_num")}
            fullWidth
          />
          <AppTextField
            appearance="glass"
            label="Acta decomiso"
            value={draft.acta_decomiso_num ?? ""}
            onChange={(ev) => onDraftChange({ acta_decomiso_num: ev.target.value })}
            error={!!e("acta_decomiso_num")}
            helperText={e("acta_decomiso_num")}
            fullWidth
          />
          <AppTextField
            appearance="glass"
            label="Kilos decomisados"
            type="number"
            value={draft.decomiso_kilos_total ?? ""}
            onChange={(ev) => {
              const v = ev.target.value;
              onDraftChange({
                decomiso_kilos_total: v === "" ? null : Number(v),
              });
            }}
            error={!!e("decomiso_kilos_total")}
            helperText={e("decomiso_kilos_total")}
            fullWidth
          />
        </Box>

        {tieneReferenciaAdmin(draft) && (
          <Box sx={{ mt: 2, pt: 1.5, borderTop: "1px solid rgba(255,255,255,0.08)" }}>
            <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.45)", display: "block", mb: 0.75 }}>
              Referencia administrativa (solo lectura; no se envía por este canal de guardado)
            </Typography>
            <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.62)" }}>
              Expediente: {dash(draft.expediente_numero)} / {dash(draft.expediente_anio)} · Oficio:{" "}
              {dash(draft.oficio_numero)} / {dash(draft.oficio_anio)}
              {draft.oficio_causa != null && String(draft.oficio_causa).trim() !== ""
                ? ` · Causa: ${dash(draft.oficio_causa)}`
                : ""}
            </Typography>
          </Box>
        )}
      </Box>

      <Box sx={blockShellSx}>
        <Typography variant="subtitle2" sx={{ ...sectionTitleSx, mt: 0 }}>
          2. Datos del local
        </Typography>
        <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.45)", display: "block", mb: 1 }}>
          Domicilio y nombre de local son solo lectura. Podés corregir rubro y contribuyente.
        </Typography>
        <AppTextField
          appearance="glass"
          label="Domicilio"
          value={domicilioTexto(draft)}
          disabled
          sx={roFieldSx}
          fullWidth
        />
        <AppTextField
          appearance="glass"
          label="Nombre del local"
          value={draft.nombre_local ?? ""}
          disabled
          sx={{ ...roFieldSx, mt: 2 }}
          fullWidth
        />
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)" },
            gap: 2,
            width: "100%",
            mt: 2,
          }}
        >
          <AppSelect
            appearance="glass"
            label="Rubro"
            value={draft.rubro_nombre ?? ""}
            onChange={(ev) => onDraftChange({ rubro_nombre: ev.target.value as string })}
            options={opts(["", ...catalogs.rubros])}
            disabled={ro("rubro_nombre")}
            error={!!e("rubro_nombre")}
            helperText={e("rubro_nombre")}
            fullWidth
          />
          <AppTextField
            appearance="glass"
            label="Doc. Nro"
            value={draft.doc_nro ?? ""}
            onChange={(ev) => onDraftChange({ doc_nro: ev.target.value })}
            error={!!e("doc_nro")}
            helperText={e("doc_nro")}
            fullWidth
          />
          <AppTextField
            appearance="glass"
            label="Apellido"
            value={draft.contrib_apellido ?? ""}
            onChange={(ev) => onDraftChange({ contrib_apellido: ev.target.value })}
            error={!!e("contrib_apellido")}
            helperText={e("contrib_apellido")}
            fullWidth
          />
          <AppTextField
            appearance="glass"
            label="Nombre"
            value={draft.contrib_nombre ?? ""}
            onChange={(ev) => onDraftChange({ contrib_nombre: ev.target.value })}
            error={!!e("contrib_nombre")}
            helperText={e("contrib_nombre")}
            fullWidth
          />
        </Box>
      </Box>

      <BloqueIniciadorVacío />
    </>
  );

  return (
    <AppDialog
      open={open}
      onClose={(_ev, _reason) => handleClose()}
      onCloseButtonClick={handleClose}
      title={title}
      maxWidth="md"
      fullWidth
      contentDividers
      contentSx={[
        formDialogContentStackSx,
        {
          maxHeight: "min(72vh, 720px)",
          overflowY: "auto",
          gap: 2.75,
        },
      ]}
      showCloseButton
      actions={
        <Box sx={{ display: "flex", gap: 1.5, justifyContent: "flex-end", flexWrap: "wrap", width: "100%" }}>
          {!isEditing ? (
            <>
              <AppButton dsVariant="ghost" onClick={handleClose} disabled={saving}>
                Cerrar
              </AppButton>
              {canEdit && (
                <AppButton dsVariant="primary" onClick={() => setIsEditing(true)} disabled={saving}>
                  Editar
                </AppButton>
              )}
            </>
          ) : (
            <>
              <AppButton dsVariant="ghost" onClick={handleBackToDetail} disabled={saving}>
                Volver al detalle
              </AppButton>
              <AppButton dsVariant="primary" onClick={() => void onSave()} loading={saving} disabled={saving}>
                Guardar
              </AppButton>
            </>
          )}
        </Box>
      }
    >
      {!isEditing ? detalleVista : edicionVista}
    </AppDialog>
  );
}
