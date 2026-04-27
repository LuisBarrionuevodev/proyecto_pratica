import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { Alert, Box, Chip, CircularProgress, Stack, Typography } from "@mui/material";

import {
  fetchNotificacionProrrogaExpedientes,
  patchNotificacionProrrogaExpediente,
  type IActuacionesPendientesItem,
  type INotificacionProrrogaExpedienteItem,
  type INotificacionProrrogaExpedientesResponse,
} from "../../../api/actuacionesPendientesApi";
import { formDialogContentStackSx } from "../../../styles/formDialogStyles";
import {
  DOC_MODAL_BLOCK_STACK_SPACING,
  docModalActuacionScrollCardShellSx,
  docModalBlockOverlineSx,
  docModalBlockResumenSx,
  docModalChipSx,
  docModalFilaEtiquetaSx,
  docModalFilaValorSx,
  docModalFooterButtonsSx,
  docModalFooterRowSx,
  docModalGlassCardShellSx,
  docModalHeaderStackSx,
  docModalEmptyStateSx,
  docModalSubheadingInCardSx,
  docModalSubtitleSx,
  docModalTitleSx,
} from "../../../styles/documentalModalTokens";
import { AppButton, AppDialog, AppTextField } from "../../../ui";
import { COLORS } from "../../Actuaciones/styles/filtroStyles";

function textoValor(val: unknown): string {
  if (val === null || val === undefined || val === "") return "—";
  return String(val);
}

function DocumentalFila({ etiqueta, valor }: { etiqueta: string; valor: string }) {
  return (
    <Box
      sx={{
        display: "flex",
        flexWrap: "wrap",
        gap: { xs: 0.25, sm: 1 },
        justifyContent: "space-between",
        alignItems: "baseline",
        py: 0.65,
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        "&:last-of-type": { borderBottom: "none", pb: 0 },
      }}
    >
      <Typography component="span" variant="body2" sx={docModalFilaEtiquetaSx}>
        {etiqueta}
      </Typography>
      <Typography component="span" variant="body2" sx={docModalFilaValorSx}>
        {valor}
      </Typography>
    </Box>
  );
}

type DocumentalCardShell = "glass" | "actuacion";

function DocumentalBloque({
  overline,
  resumen,
  children,
  shell = "glass",
}: {
  overline: string;
  resumen?: string;
  children: ReactNode;
  shell?: DocumentalCardShell;
}) {
  const shellSx =
    shell === "actuacion" ? docModalActuacionScrollCardShellSx(COLORS.primary) : docModalGlassCardShellSx(COLORS.primary);
  return (
    <Box sx={shellSx}>
      <Typography component="div" sx={docModalBlockOverlineSx}>
        {overline}
      </Typography>
      {resumen ? (
        <Typography component="div" sx={docModalBlockResumenSx}>
          {resumen}
        </Typography>
      ) : null}
      {children}
    </Box>
  );
}

function contribuyenteLinea(row: IActuacionesPendientesItem): string {
  const rs = (row.razon_social ?? "").trim();
  if (rs) return rs;
  const a = (row.contrib_apellido ?? "").trim();
  const n = (row.contrib_nombre ?? "").trim();
  const t = [a, n].filter(Boolean).join(", ");
  return t || "—";
}

function domicilioLinea(row: IActuacionesPendientesItem): string {
  const c = (row.calle ?? "").trim();
  const n = (row.numero ?? "").trim();
  const t = [c, n].filter(Boolean).join(" ");
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

function distritoNombreSiHay(row: IActuacionesPendientesItem): string | null {
  const n = (row as { distrito_nombre?: string | null }).distrito_nombre;
  const s = (n ?? "").trim();
  return s || null;
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
    campoTextoUtil(row.acta_inspeccion_num) ||
    campoTextoUtil(row.orden_trabajo_numero) ||
    campoTextoUtil(row.tipo_actuacion) ||
    inspectoresLinea(row) !== "—"
  );
}

function motivosNotificacionHayContenido(row: IActuacionesPendientesItem): boolean {
  return [row.notificacion_motivo_1, row.notificacion_motivo_2, row.notificacion_motivo_3].some(campoTextoUtil);
}

function resultadoComprobacionPosteriorHayContenido(row: IActuacionesPendientesItem): boolean {
  return (
    campoTextoUtil(row.comprobacion_posterior_fecha) ||
    campoTextoUtil(row.comprobacion_posterior_inspectores_texto) ||
    campoTextoUtil(row.comprobacion_posterior_acta_num)
  );
}

function actaNotificacionCabecera(row: IActuacionesPendientesItem): string {
  const n = (row.acta_notificacion_num ?? "").trim();
  return n ? `Acta de notificación Nº ${n}` : "Acta de notificación";
}

function fechaActuacionLinea(row: IActuacionesPendientesItem): string {
  return (row.fecha_actuacion ?? "").trim() || "—";
}

function actaNotificacionNumValor(row: IActuacionesPendientesItem): string {
  return (row.acta_notificacion_num ?? "").trim() || "—";
}

function expedienteActasLinea(row: IActuacionesPendientesItem): string {
  const num = String(row.expediente_numero ?? "").trim();
  const an = row.expediente_anio != null && String(row.expediente_anio).trim() !== "" ? String(row.expediente_anio) : "";
  if (!num && !an) return "—";
  return an ? `${num} / ${an}` : `${num} / —`;
}

function extractApiDetail(e: unknown): string | null {
  if (e && typeof e === "object" && "response" in e) {
    return (e as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? null;
  }
  return null;
}

/**
 * Lista de prórrogas / expedientes: resumen + ítems; edición inline con PATCH y refresco del GET.
 */
function NotificacionProrrogaExpedientesCard({
  loading,
  error,
  detalle,
  modo,
  actuacionId,
  onAfterPatch,
  onListaRefresh,
  resumenCompacto = false,
  shell = "glass",
}: {
  loading: boolean;
  error: string | null;
  detalle: INotificacionProrrogaExpedientesResponse | null;
  modo: "operativa" | "documental";
  actuacionId?: number;
  onAfterPatch?: () => void;
  /** Tras PATCH OK: refrescar bandeja (días restantes, etc.). */
  onListaRefresh?: () => void | Promise<void>;
  /** Oculta filas de resumen pensadas para auditoría / menos ruido en operativa. */
  resumenCompacto?: boolean;
  shell?: DocumentalCardShell;
}) {
  const operativa = modo === "operativa";
  const ed = detalle?.edicion;
  const [editingId, setEditingId] = useState<number | null>(null);
  const [exNum, setExNum] = useState("");
  const [exFecha, setExFecha] = useState("");
  const [exPlazo, setExPlazo] = useState("");
  const [savingEx, setSavingEx] = useState(false);
  const [errEx, setErrEx] = useState<string | null>(null);

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
      onAfterPatch?.();
      void onListaRefresh?.();
    } catch (e: unknown) {
      const detail = extractApiDetail(e);
      setErrEx(typeof detail === "string" ? detail : "No se pudo guardar el expediente.");
    } finally {
      setSavingEx(false);
    }
  };

  const puedeEditarItems = Boolean(ed?.puede_editar_expediente_prorroga && actuacionId != null);
  const bloqueoGlobal = Boolean(detalle?.items?.length && ed?.notificacion_usada_como_iniciador);

  return (
    <DocumentalBloque overline="Prórrogas y expedientes" shell={shell}>
      {loading ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 2 }}>
          <CircularProgress size={28} sx={{ color: COLORS.primary }} />
        </Box>
      ) : error ? (
        <Typography variant="body2" sx={{ ...docModalEmptyStateSx, fontStyle: "normal" }}>
          {error}
        </Typography>
      ) : detalle ? (
        <>
          {!resumenCompacto ? (
            <>
              <DocumentalFila
                etiqueta="Plazo legal (días hábiles)"
                valor={textoValor(detalle.plazo_notificacion?.plazo_legal_dias)}
              />
              <DocumentalFila
                etiqueta="Prórroga total (días)"
                valor={textoValor(detalle.plazo_notificacion?.prorroga_total_dias)}
              />
            </>
          ) : null}
          <DocumentalFila
            etiqueta="Fecha de notificación"
            valor={textoValor(detalle.plazo_notificacion?.fecha_notificacion)}
          />
          <DocumentalFila etiqueta="Vencimiento" valor={textoValor(detalle.plazo_notificacion?.fecha_vencimiento)} />
          <DocumentalFila etiqueta="Expedientes de prórroga" valor={String(detalle.plazos_otorgados ?? 0)} />

          {bloqueoGlobal ? (
            <Alert severity="warning" sx={{ mt: 1.5 }}>
              <Typography variant="body2" fontWeight={600} sx={{ mb: 0.5 }}>
                Edición bloqueada
              </Typography>
              <Typography variant="body2">
                {ed?.motivos_bloqueo_expediente?.[0] ??
                  "Esta notificación ya fue usada como iniciador; no se pueden modificar los expedientes de prórroga."}
              </Typography>
            </Alert>
          ) : null}

          {!detalle.items?.length ? (
            <Typography variant="body2" sx={{ ...docModalEmptyStateSx, mt: 0.75 }}>
              Sin expedientes de prórroga registrados.
            </Typography>
          ) : (
            <Stack spacing={1.5} sx={{ mt: 1.5 }}>
              {detalle.items.map((it, idx) => (
                <Box
                  key={it.id}
                  sx={{
                    pt: idx === 0 ? 0 : 1.25,
                    borderTop: idx === 0 ? "none" : "1px solid rgba(255,255,255,0.08)",
                  }}
                >
                  <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 1, mb: 0.75 }}>
                    <Typography component="div" sx={{ ...docModalSubheadingInCardSx, flex: "1 1 160px", mb: 0 }}>
                      Expediente {idx + 1}
                    </Typography>
                    {puedeEditarItems && editingId !== it.id ? (
                      <AppButton dsVariant="primary" dsSize="sm" onClick={() => beginEdit(it)} disabled={savingEx}>
                        Editar
                      </AppButton>
                    ) : null}
                  </Box>
                  <DocumentalFila
                    etiqueta="Número / año"
                    valor={
                      it.numero_expediente && it.anio
                        ? `${it.numero_expediente} / ${it.anio}`
                        : textoValor(it.numero_expediente || it.anio)
                    }
                  />
                  <DocumentalFila etiqueta="Fecha de expediente" valor={textoValor(it.fecha_expediente)} />
                  {operativa ? null : (
                    <>
                      <DocumentalFila etiqueta="Tipo" valor={textoValor(it.tipo_expediente)} />
                      <DocumentalFila etiqueta="Registrado" valor={textoValor(it.created_at)} />
                    </>
                  )}
                  <DocumentalFila
                    etiqueta="Plazo otorgado (días)"
                    valor={it.plazo_otorgado != null ? String(it.plazo_otorgado) : "—"}
                  />

                  {puedeEditarItems && editingId === it.id ? (
                    <Stack spacing={1.25} sx={{ mt: 1.25, pt: 1.25, borderTop: "1px solid rgba(255,255,255,0.08)" }}>
                      {errEx ? (
                        <Alert severity="error" onClose={() => setErrEx(null)}>
                          {errEx}
                        </Alert>
                      ) : null}
                      <AppTextField
                        appearance="glass"
                        label="Número de expediente"
                        value={exNum}
                        onChange={(e) => setExNum(e.target.value)}
                        fullWidth
                      />
                      <AppTextField
                        appearance="glass"
                        label="Fecha de expediente"
                        type="date"
                        value={exFecha}
                        onChange={(e) => setExFecha(e.target.value)}
                        InputLabelProps={{ shrink: true }}
                        fullWidth
                      />
                      <AppTextField
                        appearance="glass"
                        label="Plazo otorgado (días)"
                        type="number"
                        value={exPlazo}
                        onChange={(e) => setExPlazo(e.target.value)}
                        fullWidth
                        inputProps={{ min: 0 }}
                      />
                      <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
                        <AppButton dsVariant="ghost" dsSize="sm" onClick={cancelEdit} disabled={savingEx}>
                          Cancelar
                        </AppButton>
                        <AppButton dsVariant="primary" dsSize="sm" disabled={savingEx} onClick={() => void guardarExpediente()}>
                          {savingEx ? "Guardando…" : "Guardar cambios"}
                        </AppButton>
                      </Box>
                    </Stack>
                  ) : null}
                </Box>
              ))}
            </Stack>
          )}
        </>
      ) : null}
    </DocumentalBloque>
  );
}

/** Referencia de la notificación: vista completa (historial) u operativa (solo contexto útil). */
function BloqueReferenciaNotificacion({
  row,
  shell = "glass",
  perfil = "documental",
}: {
  row: IActuacionesPendientesItem;
  shell?: DocumentalCardShell;
  perfil?: "documental" | "operativa";
}) {
  if (perfil === "operativa") {
    return (
      <DocumentalBloque overline="Datos de la notificación" shell={shell}>
        <DocumentalFila etiqueta="Domicilio" valor={domicilioLinea(row)} />
        <DocumentalFila etiqueta="Contribuyente / razón social" valor={contribuyenteLinea(row)} />
        <DocumentalFila etiqueta="Acta de notificación Nº" valor={actaNotificacionNumValor(row)} />
        <DocumentalFila etiqueta="Fecha de actuación" valor={fechaActuacionLinea(row)} />
      </DocumentalBloque>
    );
  }

  const distritoNom = distritoNombreSiHay(row);
  return (
    <DocumentalBloque overline="Referencia de la notificación" shell={shell}>
      <DocumentalFila etiqueta="Domicilio" valor={domicilioLinea(row)} />
      <DocumentalFila etiqueta="Contribuyente / razón social" valor={contribuyenteLinea(row)} />
      <DocumentalFila etiqueta="Documento" valor={textoValor(row.doc_nro)} />
      <DocumentalFila etiqueta="Rubro" valor={textoValor(row.rubro_nombre)} />
      {distritoNom ? <DocumentalFila etiqueta="Distrito" valor={distritoNom} /> : null}
      <DocumentalFila etiqueta="Acta de notificación Nº" valor={actaNotificacionNumValor(row)} />
      <DocumentalFila etiqueta="Fecha de actuación" valor={fechaActuacionLinea(row)} />
      <DocumentalFila etiqueta="Días restantes" valor={diasPlazoLinea(row)} />
      <DocumentalFila etiqueta="Plazos otorgados" valor={textoValor(row.plazos_otorgados)} />
      <DocumentalFila etiqueta="Expediente en actas" valor={expedienteActasLinea(row)} />
    </DocumentalBloque>
  );
}

/** `documental`: ficha completa + prórrogas API (historial). `soloExpediente`: gestión de expedientes de plazo (operativa). */
export type NotificacionDetalleModalVariant = "documental" | "soloExpediente";

export type NotificacionDetalleDocumentalDialogProps = {
  open: boolean;
  onClose: () => void;
  row: IActuacionesPendientesItem | null;
  variant: NotificacionDetalleModalVariant;
  expNumero: string;
  onExpNumeroChange: (v: string) => void;
  expFecha: string;
  onExpFechaChange: (v: string) => void;
  prorrogaDias: string;
  onProrrogaDiasChange: (v: string) => void;
  fieldErrors: Record<string, string>;
  modalApiError: string | null;
  saving: boolean;
  /** Alta de un **nuevo** expediente (solo cuerpo del modal operativo). Devuelve `true` si se creó correctamente. */
  onGuardar: () => boolean | Promise<boolean>;
  /** Tras editar prórroga vía PATCH o tras alta: actualizar filas de la bandeja. */
  onOperativaListaRefresh?: () => void | Promise<void>;
};

/**
 * Detalle de notificación: modo `documental` (ficha completa) o `soloExpediente` (expedientes de plazo).
 */
export function NotificacionDetalleDocumentalDialog({
  open,
  onClose,
  row,
  variant,
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
  onOperativaListaRefresh,
}: NotificacionDetalleDocumentalDialogProps) {
  const isSoloExpediente = variant === "soloExpediente";
  const [altaFormVisible, setAltaFormVisible] = useState(false);
  const [altaInlineMsg, setAltaInlineMsg] = useState<string | null>(null);

  const handleClose = () => {
    if (isSoloExpediente && saving) return;
    onClose();
  };

  const [prorrogaDetalle, setProrrogaDetalle] = useState<INotificacionProrrogaExpedientesResponse | null>(null);
  const [prorrogaLoading, setProrrogaLoading] = useState(false);
  const [prorrogaError, setProrrogaError] = useState<string | null>(null);
  const [prorrogaDetalleRefresh, setProrrogaDetalleRefresh] = useState(0);

  useEffect(() => {
    if (open && isSoloExpediente) {
      setAltaFormVisible(false);
      setAltaInlineMsg(null);
    }
  }, [open, isSoloExpediente, row?.id]);

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

    void fetchNotificacionProrrogaExpedientes(row.id)
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

  const refrescarDetalleYBandeja = () => {
    setProrrogaDetalleRefresh((k) => k + 1);
    void onOperativaListaRefresh?.();
  };

  const ejecutarAlta = async () => {
    setAltaInlineMsg(null);
    const ok = await onGuardar();
    if (ok) {
      setAltaFormVisible(false);
      refrescarDetalleYBandeja();
      setAltaInlineMsg("Expediente registrado correctamente.");
    }
  };

  const titleNode =
    row != null ? (
      <Box sx={{ ...docModalHeaderStackSx, width: "100%" }}>
        <Chip label="Notificación" size="small" sx={docModalChipSx} variant="outlined" />
        <Typography component="span" variant="h6" sx={docModalTitleSx}>
          {isSoloExpediente ? "Expedientes de prórroga" : "Historial de notificación"}
        </Typography>
        <Typography variant="body2" sx={docModalSubtitleSx}>
          {actaNotificacionCabecera(row)}
        </Typography>
      </Box>
    ) : (
      "Detalle"
    );

  return (
    <AppDialog
      open={open}
      onClose={handleClose}
      onCloseButtonClick={handleClose}
      title={titleNode}
      fullWidth
      maxWidth="md"
      appearance="glass"
      contentDividers
      contentSx={{ ...formDialogContentStackSx, pt: 2, pb: 2 }}
      showCloseButton
      actions={
        <Box sx={docModalFooterRowSx}>
          <Box sx={{ flex: "1 1 120px", minWidth: 0 }} />
          <Box sx={docModalFooterButtonsSx}>
            <AppButton dsVariant="primary" dsSize="sm" onClick={handleClose} disabled={isSoloExpediente && saving}>
              Cerrar
            </AppButton>
          </Box>
        </Box>
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
              modo="operativa"
              actuacionId={row.id}
              resumenCompacto
              onAfterPatch={() => setProrrogaDetalleRefresh((k) => k + 1)}
              onListaRefresh={onOperativaListaRefresh}
            />
          ) : null}

          {row.source_type !== "COMPROBACION" ? (
            <Stack spacing={1.5}>
              {altaInlineMsg ? (
                <Alert severity="success" onClose={() => setAltaInlineMsg(null)}>
                  {altaInlineMsg}
                </Alert>
              ) : null}
              {!altaFormVisible ? (
                <AppButton
                  dsVariant="primary"
                  dsSize="sm"
                  onClick={() => {
                    setAltaInlineMsg(null);
                    setAltaFormVisible(true);
                  }}
                  disabled={saving}
                >
                  Añadir expediente de prórroga
                </AppButton>
              ) : (
                <DocumentalBloque overline="Nuevo expediente de prórroga">
                  <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.7)", mb: 1.5 }}>
                    Completá los datos y guardá para registrar una nueva prórroga. Podés cancelar para volver al listado.
                  </Typography>
                  {modalApiError ? (
                    <Alert severity="error" sx={{ mb: 1.5 }}>
                      {modalApiError}
                    </Alert>
                  ) : null}
                  <Stack spacing={2} sx={{ width: "100%" }}>
                    <AppTextField
                      appearance="glass"
                      label="Número de expediente"
                      value={expNumero}
                      onChange={(e) => onExpNumeroChange(e.target.value)}
                      fullWidth
                      required
                      error={Boolean(fieldErrors.expNumero)}
                      helperText={fieldErrors.expNumero || undefined}
                    />
                    <AppTextField
                      appearance="glass"
                      label="Fecha de expediente"
                      type="date"
                      value={expFecha}
                      onChange={(e) => onExpFechaChange(e.target.value)}
                      InputLabelProps={{ shrink: true }}
                      fullWidth
                      required
                      error={Boolean(fieldErrors.expFecha)}
                      helperText={fieldErrors.expFecha || undefined}
                    />
                    <AppTextField
                      appearance="glass"
                      label="Días de prórroga otorgados"
                      type="number"
                      value={prorrogaDias}
                      onChange={(e) => onProrrogaDiasChange(e.target.value)}
                      fullWidth
                      required
                      error={Boolean(fieldErrors.prorrogaDias)}
                      helperText={fieldErrors.prorrogaDias || undefined}
                    />
                  </Stack>
                  <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mt: 2 }}>
                    <AppButton
                      dsVariant="ghost"
                      dsSize="sm"
                      onClick={() => {
                        setAltaFormVisible(false);
                        setAltaInlineMsg(null);
                      }}
                      disabled={saving}
                    >
                      Cancelar
                    </AppButton>
                    <AppButton dsVariant="primary" dsSize="sm" disabled={saving} onClick={() => void ejecutarAlta()}>
                      {saving ? "Guardando…" : "Guardar nuevo expediente"}
                    </AppButton>
                  </Box>
                </DocumentalBloque>
              )}
            </Stack>
          ) : null}
        </Stack>
      ) : (
        <Stack spacing={DOC_MODAL_BLOCK_STACK_SPACING} component="section" aria-label="Historial de la notificación">
          <BloqueReferenciaNotificacion row={row} shell="actuacion" perfil="documental" />

          {visitaBaseHayContenido(row) ? (
            <DocumentalBloque overline="La visita" shell="actuacion">
              <DocumentalFila etiqueta="Acta de inspección Nº" valor={textoValor(row.acta_inspeccion_num)} />
              <DocumentalFila etiqueta="Inspectores" valor={inspectoresLinea(row)} />
              <DocumentalFila etiqueta="Orden de trabajo" valor={textoValor(row.orden_trabajo_numero)} />
              <DocumentalFila etiqueta="Tipo de actuación" valor={textoValor(row.tipo_actuacion)} />
            </DocumentalBloque>
          ) : null}

          {motivosNotificacionHayContenido(row) ? (
            <DocumentalBloque overline="Motivos" shell="actuacion">
              <DocumentalFila etiqueta="Motivo 1" valor={textoValor(row.notificacion_motivo_1)} />
              <DocumentalFila etiqueta="Motivo 2" valor={textoValor(row.notificacion_motivo_2)} />
              <DocumentalFila etiqueta="Motivo 3" valor={textoValor(row.notificacion_motivo_3)} />
            </DocumentalBloque>
          ) : null}

          {row.source_type !== "COMPROBACION" ? (
            <NotificacionProrrogaExpedientesCard
              loading={prorrogaLoading}
              error={prorrogaError}
              detalle={prorrogaDetalle}
              modo="documental"
              shell="actuacion"
              actuacionId={row.id}
              resumenCompacto={false}
              onAfterPatch={() => setProrrogaDetalleRefresh((k) => k + 1)}
              onListaRefresh={onOperativaListaRefresh}
            />
          ) : null}

          {modalApiError ? (
            <Alert severity="error" sx={{ mb: 0 }}>
              {modalApiError}
            </Alert>
          ) : null}

          {resultadoComprobacionPosteriorHayContenido(row) ? (
            <DocumentalBloque overline="Resultado y seguimiento" shell="actuacion">
              {filasResultadoEstado(row).map((f) => (
                <DocumentalFila key={f.etiqueta} etiqueta={f.etiqueta} valor={f.valor} />
              ))}
            </DocumentalBloque>
          ) : null}
        </Stack>
      )}
    </AppDialog>
  );
}
