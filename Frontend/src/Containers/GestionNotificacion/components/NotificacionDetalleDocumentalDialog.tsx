import { useEffect, useState } from "react";
import { Alert, Box, CircularProgress, Stack, Typography } from "@mui/material";

import {
  deleteNotificacionProrrogaExpediente,
  fetchNotificacionProrrogaExpedientes,
  patchNotificacionProrrogaExpediente,
  type IActuacionesPendientesItem,
  type INotificacionProrrogaExpedienteItem,
  type INotificacionProrrogaExpedientesResponse,
} from "../../../api/actuacionesPendientesApi";
import {
  CrudDialogActions,
  CrudDialogHeader,
  CrudFormSlot,
  CrudGlassDialog,
  useNotifyModalApiError,
} from "../../../components/crudDialog";
import { useAppFeedback } from "../../../components/feedback";
import { DocumentalCrudSection } from "../../../components/documental/documentalCrudLayout";
import { crudFieldGridSx } from "../../../styles/crudDialogTokens";
import {
  DOC_MODAL_BLOCK_STACK_SPACING,
  docModalEmptyStateSx,
  documentalGlassAlertSx,
} from "../../../styles/documentalModalTokens";
import { AppButton, AppTextField, ConfirmDialog } from "../../../ui";
import type { GuardarProrrogaResult } from "../utils/prorrogaSuccessMessage";
import {
  EXPEDIENTE_ACTUALIZADO_MSG,
  EXPEDIENTE_ELIMINADO_MSG,
} from "../utils/prorrogaSuccessMessage";
import { perfTimed } from "../../../utils/perfLog";
import {
  notificacionModalSubtitulo,
  notificacionModalTitulo,
} from "../utils/notificacionModalDisplay";
import {
  DocumentalBloque,
  DocumentalFila,
  textoValor,
} from "../../ActasComprobacion/components/comprobacionOperativoBlocks";
import { formatActuacionListDomicilioLinea } from "../../../utils/formatDomicilioLineaVisible";
import { humanizarTipoActuacion } from "../../ActasComprobacion/utils/documentalLabelFormat";

type DocumentalCardShell = "glass" | "actuacion";

function contribuyenteLinea(row: IActuacionesPendientesItem): string {
  const rs = (row.razon_social ?? "").trim();
  if (rs) return rs;
  const a = (row.contrib_apellido ?? "").trim();
  const n = (row.contrib_nombre ?? "").trim();
  const t = [a, n].filter(Boolean).join(", ");
  return t || "—";
}

function domicilioLinea(row: IActuacionesPendientesItem): string {
  const t = formatActuacionListDomicilioLinea(row).trim();
  return t || "—";
}

function diasPlazoLinea(row: IActuacionesPendientesItem): string {
  if (row.dias_restantes === null || row.dias_restantes === undefined) return "—";
  if (row.dias_restantes === 0) return "0 (vencido o vence hoy)";
  return `${row.dias_restantes} días`;
}

function inspectoresLinea(row: IActuacionesPendientesItem): string {
  const t = (row.inspectores_texto ?? "").trim();
  if (t) return t;
  const parts = [row.inspector1, row.inspector2, row.inspector3]
    .map((s) => (s ?? "").trim())
    .filter(Boolean);
  return parts.length ? parts.join(" · ") : "—";
}

function filasResultadoEstado(row: IActuacionesPendientesItem): { etiqueta: string; valor: string }[] {
  const fecha = (row.comprobacion_posterior_fecha ?? "").trim();
  const insp = (row.comprobacion_posterior_inspectores_texto ?? "").trim();
  const acta = (row.comprobacion_posterior_acta_num ?? "").trim();
  return [
    { etiqueta: "Fecha de comprobación", valor: fecha || "—" },
    { etiqueta: "Inspectores", valor: insp || "—" },
    { etiqueta: "Acta de comprobación Nº", valor: acta || "—" },
  ];
}

function campoTextoUtil(s: unknown): boolean {
  return s != null && String(s).trim() !== "";
}

function visitaBaseHayContenido(row: IActuacionesPendientesItem): boolean {
  return (
    campoTextoUtil(row.orden_trabajo_numero) ||
    campoTextoUtil(row.tipo_actuacion) ||
    campoTextoUtil(row.acta_inspeccion_num) ||
    inspectoresLinea(row) !== "—"
  );
}

function motivosNotificacionLista(row: IActuacionesPendientesItem): string[] {
  return [row.notificacion_motivo_1, row.notificacion_motivo_2, row.notificacion_motivo_3]
    .map((s) => (s ?? "").trim())
    .filter(Boolean);
}

function resultadoComprobacionPosteriorHayContenido(row: IActuacionesPendientesItem): boolean {
  return (
    campoTextoUtil(row.comprobacion_posterior_fecha) ||
    campoTextoUtil(row.comprobacion_posterior_inspectores_texto) ||
    campoTextoUtil(row.comprobacion_posterior_acta_num)
  );
}


function extractApiDetail(e: unknown): string | null {
  if (e && typeof e === "object" && "response" in e) {
    return (e as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? null;
  }
  return null;
}

/**
 * Resumen de plazos (sin contadores ni expediente en actas; los ítems van abajo).
 */
function PlazosNotificacionResumenFilas({
  detalle,
  diasRestantes,
}: {
  detalle: INotificacionProrrogaExpedientesResponse;
  diasRestantes: string;
}) {
  return (
    <>
      <DocumentalFila
        etiqueta="Fecha de notificación"
        valor={textoValor(detalle.plazo_notificacion?.fecha_notificacion)}
      />
      <DocumentalFila etiqueta="Vencimiento" valor={textoValor(detalle.plazo_notificacion?.fecha_vencimiento)} />
      <DocumentalFila etiqueta="Días restantes" valor={diasRestantes} />
      <DocumentalFila
        etiqueta="Plazo legal (días hábiles)"
        valor={textoValor(detalle.plazo_notificacion?.plazo_legal_dias)}
      />
      <DocumentalFila
        etiqueta="Prórroga total (días)"
        valor={textoValor(detalle.plazo_notificacion?.prorroga_total_dias)}
      />
    </>
  );
}

/**
 * Lista de prórrogas / expedientes: resumen + ítems; edición (PATCH) y eliminación (DELETE) con refresco.
 */
function NotificacionProrrogaExpedientesCard({
  loading,
  error,
  detalle,
  actuacionId,
  onExpedienteMutacionExitosa,
  diasRestantes,
}: {
  loading: boolean;
  error: string | null;
  detalle: INotificacionProrrogaExpedientesResponse | null;
  actuacionId?: number;
  /** Tras PATCH/DELETE exitoso: toast, refresh bandejas y cierre del modal (padre). */
  onExpedienteMutacionExitosa?: (mensaje: string) => void | Promise<void>;
  diasRestantes: string;
}) {
  const feedback = useAppFeedback();
  const ed = detalle?.edicion;
  const [editingId, setEditingId] = useState<number | null>(null);
  const [exNum, setExNum] = useState("");
  const [exFecha, setExFecha] = useState("");
  const [exPlazo, setExPlazo] = useState("");
  const [savingEx, setSavingEx] = useState(false);
  const [errEx, setErrEx] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);
  const [delSaving, setDelSaving] = useState(false);

  const beginEdit = (it: INotificacionProrrogaExpedienteItem) => {
    setEditingId(it.id);
    setExNum(it.numero_expediente ?? "");
    setExFecha((it.fecha_expediente ?? "").slice(0, 10));
    setExPlazo(it.plazo_otorgado != null ? String(it.plazo_otorgado) : "0");
    setErrEx(null);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setErrEx(null);
  };

  const guardarExpediente = async () => {
    if (editingId == null || actuacionId == null) return;
    setErrEx(null);
    if (!exNum.trim() || !exFecha) {
      setErrEx("Completá número y fecha del expediente.");
      return;
    }
    const po = Number(exPlazo.trim());
    if (Number.isNaN(po) || po < 0) {
      setErrEx("El plazo otorgado debe ser un entero mayor o igual a 0.");
      return;
    }
    setSavingEx(true);
    try {
      await patchNotificacionProrrogaExpediente(actuacionId, editingId, {
        numero_expediente: exNum.trim(),
        fecha_expediente: exFecha,
        plazo_otorgado: po,
      });
      cancelEdit();
      await onExpedienteMutacionExitosa?.(EXPEDIENTE_ACTUALIZADO_MSG);
    } catch (e: unknown) {
      const detail = extractApiDetail(e);
      setErrEx(typeof detail === "string" ? detail : "No se pudo guardar el expediente.");
    } finally {
      setSavingEx(false);
    }
  };

  const puedeEditarItem = (it: INotificacionProrrogaExpedienteItem) =>
    Boolean((it.puede_editar ?? ed?.puede_editar_expediente_prorroga) && actuacionId != null);
  const puedeEliminarItem = (it: INotificacionProrrogaExpedienteItem) =>
    Boolean(
      (it.puede_eliminar ?? it.puede_editar ?? ed?.puede_eliminar_expediente_prorroga ?? ed?.puede_editar_expediente_prorroga) &&
        actuacionId != null
    );
  const bloqueoGlobal = Boolean(
    detalle?.items?.length &&
      (ed?.reinspeccion_operativamente_usada ?? ed?.notificacion_usada_como_iniciador)
  );

  useEffect(() => {
    if (errEx) feedback.error(errEx);
  }, [errEx, feedback]);

  return (
    <DocumentalBloque overline="Plazos y expedientes" layout="stack">
      {loading ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 2 }}>
          <CircularProgress size={28} />
        </Box>
      ) : error ? (
        <Typography variant="body2" sx={{ ...docModalEmptyStateSx, fontStyle: "normal" }}>
          {error}
        </Typography>
      ) : detalle ? (
        <>
          <PlazosNotificacionResumenFilas detalle={detalle} diasRestantes={diasRestantes} />

          {bloqueoGlobal ? (
            <Alert severity="warning" sx={{ mt: 1.5, ...documentalGlassAlertSx }}>
              <Typography variant="body2" fontWeight={600} sx={{ mb: 0.5 }}>
                Edición y eliminación bloqueadas
              </Typography>
              <Typography variant="body2">
                {ed?.motivos_bloqueo_expediente?.[0] ??
                  "Este expediente de prórroga ya fue utilizado en una reinspección completada y no puede modificarse desde esta vista."}
              </Typography>
            </Alert>
          ) : null}

          {!detalle.items?.length ? (
            <Typography variant="body2" sx={{ ...docModalEmptyStateSx, mt: 1.25 }}>
              Sin expedientes de prórroga registrados.
            </Typography>
          ) : (
            <Stack spacing={1.5} sx={{ mt: 1.5 }}>
              <Typography component="div" variant="subtitle2" sx={{ fontWeight: 600 }}>
                Expedientes de prórroga
              </Typography>
              {detalle.items.map((it, idx) => (
                <Box
                  key={it.id}
                  sx={{
                    pt: idx === 0 ? 0 : 1.25,
                    borderTop: idx === 0 ? "none" : "1px solid rgba(255,255,255,0.08)",
                  }}
                >
                  <Typography component="div" variant="subtitle2" sx={{ mb: 0.75, fontWeight: 600 }}>
                    Expediente {idx + 1}
                  </Typography>
                  <Box sx={crudFieldGridSx}>
                    {puedeEditarItem(it) && editingId === it.id ? (
                      <>
                        <CrudFormSlot label="Número de expediente" mode="edit">
                          <AppTextField
                            appearance="glass"
                            label="Número de expediente"
                            value={exNum}
                            onChange={(e) => setExNum(e.target.value)}
                            fullWidth
                          />
                        </CrudFormSlot>
                        <CrudFormSlot label="Fecha de expediente" mode="edit">
                          <AppTextField
                            appearance="glass"
                            label="Fecha de expediente"
                            type="date"
                            value={exFecha}
                            onChange={(e) => setExFecha(e.target.value)}
                            InputLabelProps={{ shrink: true }}
                            fullWidth
                          />
                        </CrudFormSlot>
                        <CrudFormSlot label="Plazo otorgado (días)" mode="edit">
                          <AppTextField
                            appearance="glass"
                            label="Plazo otorgado (días)"
                            type="number"
                            value={exPlazo}
                            onChange={(e) => setExPlazo(e.target.value)}
                            fullWidth
                            inputProps={{ min: 0 }}
                          />
                        </CrudFormSlot>
                      </>
                    ) : (
                      <>
                        <CrudFormSlot
                          label="Número / año"
                          mode="view"
                          value={
                            it.numero_expediente && it.anio
                              ? `${it.numero_expediente} / ${it.anio}`
                              : it.numero_expediente || it.anio || "—"
                          }
                        />
                        <CrudFormSlot label="Fecha de expediente" mode="view" value={it.fecha_expediente} />
                        <CrudFormSlot
                          label="Plazo otorgado (días)"
                          mode="view"
                          value={it.plazo_otorgado != null ? String(it.plazo_otorgado) : "—"}
                        />
                      </>
                    )}
                  </Box>

                  {puedeEditarItem(it) && editingId !== it.id ? (
                    <Box
                      sx={{
                        display: "flex",
                        gap: 1,
                        flexWrap: "wrap",
                        justifyContent: "flex-end",
                        mt: 1,
                        pt: 0.75,
                        borderTop: "1px solid rgba(255,255,255,0.06)",
                      }}
                    >
                      <AppButton dsVariant="primary" dsSize="sm" onClick={() => beginEdit(it)} disabled={savingEx || delSaving}>
                        Editar
                      </AppButton>
                      {puedeEliminarItem(it) ? (
                        <AppButton
                          dsVariant="danger"
                          dsSize="sm"
                          onClick={() => {
                            setConfirmDeleteId(it.id);
                            setErrEx(null);
                          }}
                          disabled={savingEx || delSaving}
                        >
                          Eliminar
                        </AppButton>
                      ) : null}
                    </Box>
                  ) : null}

                  {!puedeEditarItem(it) && it.motivo_bloqueo ? (
                    <Typography variant="caption" sx={{ display: "block", mt: 0.75, opacity: 0.75 }}>
                      {it.motivo_bloqueo}
                    </Typography>
                  ) : null}

                  {puedeEditarItem(it) && editingId === it.id ? (
                    <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mt: 1.25 }}>
                      <AppButton dsVariant="ghost" dsSize="sm" onClick={cancelEdit} disabled={savingEx}>
                        Cancelar
                      </AppButton>
                      <AppButton dsVariant="primary" dsSize="sm" disabled={savingEx} onClick={() => void guardarExpediente()}>
                        {savingEx ? "Guardando…" : "Guardar cambios"}
                      </AppButton>
                    </Box>
                  ) : null}
                </Box>
              ))}
            </Stack>
          )}
        </>
      ) : null}
      <ConfirmDialog
        open={confirmDeleteId != null}
        onClose={() => {
          if (!delSaving) setConfirmDeleteId(null);
        }}
        title="Eliminar expediente de prórroga"
        destructive
        loading={delSaving}
        onConfirm={async () => {
          if (confirmDeleteId == null || actuacionId == null) return;
          setDelSaving(true);
          setErrEx(null);
          try {
            await deleteNotificacionProrrogaExpediente(actuacionId, confirmDeleteId);
            if (editingId === confirmDeleteId) cancelEdit();
            setConfirmDeleteId(null);
            await onExpedienteMutacionExitosa?.(EXPEDIENTE_ELIMINADO_MSG);
          } catch (e: unknown) {
            const detail = extractApiDetail(e);
            setErrEx(typeof detail === "string" ? detail : "No se pudo eliminar el expediente.");
          } finally {
            setDelSaving(false);
          }
        }}
      >
        <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.85)" }}>
          Se marcará como eliminado este expediente de prórroga. El plazo total y el vencimiento se recalculan con las
          prórrogas que queden activas.
        </Typography>
      </ConfirmDialog>
    </DocumentalBloque>
  );
}

/** Referencia de la notificación: vista completa (historial) u operativa (solo contexto útil). */
function BloqueReferenciaNotificacion({
  row,
  perfil = "documental",
}: {
  row: IActuacionesPendientesItem;
  shell?: DocumentalCardShell;
  perfil?: "documental" | "operativa";
}) {
  if (perfil === "operativa") {
    return (
      <DocumentalBloque overline="Referencia de la notificación">
        <DocumentalFila etiqueta="Domicilio" valor={domicilioLinea(row)} />
        <DocumentalFila etiqueta="Contribuyente / razón social" valor={contribuyenteLinea(row)} />
      </DocumentalBloque>
    );
  }

  return (
    <DocumentalBloque overline="Referencia de la notificación">
      <DocumentalFila etiqueta="Domicilio" valor={domicilioLinea(row)} />
      <DocumentalFila etiqueta="Contribuyente / razón social" valor={contribuyenteLinea(row)} />
      <DocumentalFila etiqueta="Documento" valor={textoValor(row.doc_nro)} />
      <DocumentalFila etiqueta="Rubro" valor={textoValor(row.rubro_nombre)} />
    </DocumentalBloque>
  );
}

/** `documental`: ficha completa + prórrogas API (historial). `soloExpediente`: gestión de expedientes de plazo (operativa). */
export type { NotificacionDetalleModalVariant } from "../utils/notificacionModalDisplay";

export type NotificacionDetalleDocumentalDialogProps = {
  open: boolean;
  onClose: () => void;
  disablePortal?: boolean;
  row: IActuacionesPendientesItem | null;
  variant: NotificacionDetalleModalVariant;
  /** Bandeja de reinspección por notificación vencida (título contextual). */
  esReinspeccionNotificacion?: boolean;
  expNumero: string;
  onExpNumeroChange: (v: string) => void;
  expFecha: string;
  onExpFechaChange: (v: string) => void;
  prorrogaDias: string;
  onProrrogaDiasChange: (v: string) => void;
  fieldErrors: Record<string, string>;
  modalApiError: string | null;
  saving: boolean;
  /** Alta de un **nuevo** expediente (solo cuerpo del modal operativo). */
  onGuardar: () => GuardarProrrogaResult | Promise<GuardarProrrogaResult>;
  /** Tras PATCH/DELETE exitoso de expediente de prórroga. */
  onExpedienteMutacionExitosa?: (mensaje: string) => void | Promise<void>;
};

/**
 * Detalle de notificación: modo `documental` (ficha completa) o `soloExpediente` (expedientes de plazo).
 */
export function NotificacionDetalleDocumentalDialog({
  open,
  onClose,
  disablePortal,
  row,
  variant,
  esReinspeccionNotificacion = false,
  expNumero,
  onExpNumeroChange,
  expFecha,
  onExpFechaChange,
  prorrogaDias,
  onProrrogaDiasChange,
  fieldErrors,
  modalApiError,
  saving,
  onGuardar,
  onExpedienteMutacionExitosa,
}: NotificacionDetalleDocumentalDialogProps) {
  const feedback = useAppFeedback();
  const isSoloExpediente = variant === "soloExpediente";
  useNotifyModalApiError(modalApiError, open);

  const handleClose = () => {
    if (isSoloExpediente && saving) return;
    onClose();
  };

  const [prorrogaDetalle, setProrrogaDetalle] = useState<INotificacionProrrogaExpedientesResponse | null>(null);
  const [prorrogaLoading, setProrrogaLoading] = useState(false);
  const [prorrogaError, setProrrogaError] = useState<string | null>(null);
  const [prorrogaDetalleRefresh, setProrrogaDetalleRefresh] = useState(0);

  useEffect(() => {
    if (!open || !row) {
      setProrrogaDetalle(null);
      setProrrogaError(null);
      setProrrogaLoading(false);
      return;
    }
    if (row.source_type === "COMPROBACION") {
      setProrrogaDetalle(null);
      setProrrogaError(null);
      setProrrogaLoading(false);
      return;
    }

    let cancelled = false;
    setProrrogaLoading(true);
    setProrrogaError(null);
    setProrrogaDetalle(null);

    void perfTimed(
      "notificaciones.modal.expedientesProrroga",
      () => fetchNotificacionProrrogaExpedientes(row.id),
      (data) => ({ actuacionId: row.id, items: data.items?.length ?? 0 })
    )
      .then((data) => {
        if (!cancelled) {
          setProrrogaDetalle(data);
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const detail =
          err && typeof err === "object" && "response" in err
            ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
            : null;
        setProrrogaError(typeof detail === "string" ? detail : "No se pudo cargar el detalle de prórrogas.");
      })
      .finally(() => {
        if (!cancelled) setProrrogaLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [open, row?.id, row?.source_type, variant, prorrogaDetalleRefresh]);

  const ejecutarAlta = async () => {
    await onGuardar();
  };

  const headerTitulo = row != null ? notificacionModalTitulo(variant, esReinspeccionNotificacion) : "Notificación";
  const headerSubtitulo = row != null ? notificacionModalSubtitulo(row) : null;

  return (
    <CrudGlassDialog
      open={open}
      disablePortal={disablePortal}
      hideBackdrop={disablePortal}
      onClose={handleClose}
      onCloseButtonClick={handleClose}
      maxWidth="md"
      title={
        <CrudDialogHeader
          domainChip="Notificación"
          titulo={headerTitulo}
          subtitulo={headerSubtitulo}
        />
      }
      actions={
        isSoloExpediente ? (
          <CrudDialogActions
            mode="edit"
            onSave={() => void ejecutarAlta()}
            loading={saving}
            saveLabel={saving ? "Guardando…" : "Guardar expediente"}
          />
        ) : undefined
      }
    >
      {!row ? null : isSoloExpediente ? (
        <Stack spacing={DOC_MODAL_BLOCK_STACK_SPACING} component="section" aria-label="Expedientes de prórroga">
          <BloqueReferenciaNotificacion row={row} perfil="operativa" />
          {row.source_type !== "COMPROBACION" ? (
            <NotificacionProrrogaExpedientesCard
              loading={prorrogaLoading}
              error={prorrogaError}
              detalle={prorrogaDetalle}
              actuacionId={row.id}
              diasRestantes={diasPlazoLinea(row)}
              onExpedienteMutacionExitosa={onExpedienteMutacionExitosa}
            />
          ) : null}

          {row.source_type !== "COMPROBACION" ? (
            <DocumentalCrudSection title="Alta de expediente de prórroga">
              <CrudFormSlot label="Número de expediente" mode="edit" required error={Boolean(fieldErrors.expNumero)} helperText={fieldErrors.expNumero}>
                <AppTextField
                  appearance="glass"
                  label="Número de expediente"
                  value={expNumero}
                  onChange={(e) => onExpNumeroChange(e.target.value)}
                  fullWidth
                  required
                  disabled={saving}
                  error={Boolean(fieldErrors.expNumero)}
                  helperText={fieldErrors.expNumero || undefined}
                />
              </CrudFormSlot>
              <CrudFormSlot label="Fecha de expediente" mode="edit" required error={Boolean(fieldErrors.expFecha)} helperText={fieldErrors.expFecha}>
                <AppTextField
                  appearance="glass"
                  label="Fecha de expediente"
                  type="date"
                  value={expFecha}
                  onChange={(e) => onExpFechaChange(e.target.value)}
                  InputLabelProps={{ shrink: true }}
                  fullWidth
                  required
                  disabled={saving}
                  error={Boolean(fieldErrors.expFecha)}
                  helperText={fieldErrors.expFecha || undefined}
                />
              </CrudFormSlot>
              <CrudFormSlot label="Plazo otorgado (días)" mode="edit" required error={Boolean(fieldErrors.prorrogaDias)} helperText={fieldErrors.prorrogaDias}>
                <AppTextField
                  appearance="glass"
                  label="Plazo otorgado (días)"
                  type="number"
                  value={prorrogaDias}
                  onChange={(e) => onProrrogaDiasChange(e.target.value)}
                  fullWidth
                  required
                  disabled={saving}
                  error={Boolean(fieldErrors.prorrogaDias)}
                  helperText={fieldErrors.prorrogaDias || undefined}
                  inputProps={{ min: 0 }}
                />
              </CrudFormSlot>
            </DocumentalCrudSection>
          ) : null}
        </Stack>
      ) : (
        <Stack spacing={DOC_MODAL_BLOCK_STACK_SPACING} component="section" aria-label="Historial de la notificación">
          <BloqueReferenciaNotificacion row={row} perfil="documental" />

          {visitaBaseHayContenido(row) ? (
            <DocumentalBloque overline="La visita">
              <DocumentalFila etiqueta="Orden de trabajo" valor={textoValor(row.orden_trabajo_numero)} />
              <DocumentalFila etiqueta="Inspectores" valor={inspectoresLinea(row)} />
              <DocumentalFila etiqueta="Tipo de actuación" valor={humanizarTipoActuacion(row.tipo_actuacion)} />
              <DocumentalFila etiqueta="Acta de inspección Nº" valor={textoValor(row.acta_inspeccion_num)} />
            </DocumentalBloque>
          ) : null}

          {motivosNotificacionLista(row).length > 0 ? (
            <DocumentalBloque overline="Motivos de notificación">
              <CrudFormSlot
                label="Motivos"
                mode="view"
                value={motivosNotificacionLista(row).join(" · ")}
              />
            </DocumentalBloque>
          ) : null}

          {row.source_type !== "COMPROBACION" ? (
            <NotificacionProrrogaExpedientesCard
              loading={prorrogaLoading}
              error={prorrogaError}
              detalle={prorrogaDetalle}
              actuacionId={row.id}
              diasRestantes={diasPlazoLinea(row)}
              onExpedienteMutacionExitosa={onExpedienteMutacionExitosa}
            />
          ) : null}

          {resultadoComprobacionPosteriorHayContenido(row) ? (
            <DocumentalBloque overline="Resultado y seguimiento">
              {filasResultadoEstado(row).map((f) => (
                <DocumentalFila key={f.etiqueta} etiqueta={f.etiqueta} valor={f.valor} />
              ))}
            </DocumentalBloque>
          ) : null}
        </Stack>
      )}
    </CrudGlassDialog>
  );
}

/** @internal Exportado para tests de layout de plazos/expedientes. */
export { PlazosNotificacionResumenFilas, NotificacionProrrogaExpedientesCard };
