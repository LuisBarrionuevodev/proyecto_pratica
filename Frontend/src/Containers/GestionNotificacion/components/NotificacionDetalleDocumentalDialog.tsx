import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { Alert, Box, Chip, CircularProgress, Stack, Typography } from "@mui/material";

import {
  fetchNotificacionProrrogaExpedientes,
  type IActuacionesPendientesItem,
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
  docModalReferenceSx,
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
  /** `actuacion`: mismo shell liviano que Actuaciones (scroll/compositing). Solo variante documental. */
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

/** Solo si el backend envía nombre (p. ej. futuro); no mostrar solo id. */
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

/** Línea de cabecera: acta de notificación (gestión notificación siempre con número en bandeja). */
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
  if (!row.expediente_numero) return "—";
  return row.expediente_anio != null ? `${row.expediente_numero} / ${row.expediente_anio}` : String(row.expediente_numero);
}

/**
 * GET `/actuaciones/:id/notificacion/expedientes-prorroga` — documental (historial) vs operativa (soloExpediente).
 */
function NotificacionProrrogaExpedientesCard({
  loading,
  error,
  detalle,
  modo,
  shell = "glass",
}: {
  loading: boolean;
  error: string | null;
  detalle: INotificacionProrrogaExpedientesResponse | null;
  modo: "operativa" | "documental";
  shell?: DocumentalCardShell;
}) {
  const operativa = modo === "operativa";
  return (
    <DocumentalBloque overline="Plazo y expedientes de prórroga" shell={shell}>
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
          <DocumentalFila
            etiqueta="Plazo base (hábiles)"
            valor={textoValor(detalle.consolidado?.plazo_dias)}
          />
          <DocumentalFila etiqueta="Prórroga acumulada (días)" valor={textoValor(detalle.consolidado?.prorroga_dias)} />
          <DocumentalFila etiqueta="Fecha de notificación" valor={textoValor(detalle.consolidado?.fecha_notificacion)} />
          <DocumentalFila etiqueta="Vencimiento" valor={textoValor(detalle.consolidado?.fecha_vencimiento)} />
          <DocumentalFila etiqueta="Expedientes de prórroga" valor={String(detalle.plazos_otorgados ?? 0)} />
          {!detalle.items?.length ? (
            <Typography variant="body2" sx={{ ...docModalEmptyStateSx, mt: 0.75 }}>
              Sin registros de prórroga.
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
                  <Typography component="div" sx={{ ...docModalSubheadingInCardSx, mb: 0.75 }}>
                    Expediente {idx + 1}
                  </Typography>
                  <DocumentalFila etiqueta="Número" valor={textoValor(it.numero_expediente)} />
                  <DocumentalFila etiqueta="Año" valor={textoValor(it.anio)} />
                  <DocumentalFila etiqueta="Fecha de expediente" valor={textoValor(it.fecha_expediente)} />
                  {operativa ? null : (
                    <>
                      <DocumentalFila etiqueta="Tipo" valor={textoValor(it.tipo_expediente)} />
                      <DocumentalFila etiqueta="Registrado" valor={textoValor(it.created_at)} />
                    </>
                  )}
                  <DocumentalFila
                    etiqueta="Días (esta alta)"
                    valor={it.prorroga_dias_solicitada != null ? String(it.prorroga_dias_solicitada) : "—"}
                  />
                </Box>
              ))}
            </Stack>
          )}
        </>
      ) : null}
    </DocumentalBloque>
  );
}

/**
 * Contexto de fila. Misma jerarquía operativa / documental (PR N1–N2); `shell="actuacion"` en historial.
 */
function BloqueReferenciaNotificacion({
  row,
  shell = "glass",
}: {
  row: IActuacionesPendientesItem;
  shell?: DocumentalCardShell;
}) {
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

/** `documental`: ficha completa + prórrogas API (historial). `soloExpediente`: alta mínima expediente/plazo (operativa). */
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
  onGuardar: () => void | Promise<void>;
};

/**
 * Detalle de notificación: modo `documental` (ficha completa) o `soloExpediente` (alta de expediente de plazo).
 * En ambos casos se consulta GET `/actuaciones/:id/notificacion/expedientes-prorroga` con `row.id` = actuación.
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
}: NotificacionDetalleDocumentalDialogProps) {
  const allowRegistrarExpediente = variant === "soloExpediente";
  const handleClose = () => {
    if (saving) return;
    onClose();
  };

  const [prorrogaDetalle, setProrrogaDetalle] = useState<INotificacionProrrogaExpedientesResponse | null>(null);
  const [prorrogaLoading, setProrrogaLoading] = useState(false);
  const [prorrogaError, setProrrogaError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !row) {
      setProrrogaDetalle(null);
      setProrrogaError(null);
      setProrrogaLoading(false);
      return;
    }
    /** Prórrogas solo aplican a actuaciones de rama notificación (no comprobación “posterior” en misma UI). */
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
        if (!cancelled) setProrrogaDetalle(data);
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
  }, [open, row?.id, row?.source_type, variant]);

  const titleNode =
    row != null ? (
      <Box sx={{ ...docModalHeaderStackSx, width: "100%" }}>
        <Chip label="Notificación" size="small" sx={docModalChipSx} variant="outlined" />
        <Typography component="span" variant="h6" sx={docModalTitleSx}>
          {variant === "soloExpediente" ? "Registrar expediente de plazo" : "Historial de notificación"}
        </Typography>
        <Typography variant="body2" sx={docModalSubtitleSx}>
          {actaNotificacionCabecera(row)}
        </Typography>
        <Typography variant="caption" component="div" sx={{ ...docModalReferenceSx, maxWidth: "100%" }}>
          Actuación #{row.id}
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
        allowRegistrarExpediente ? (
          <Box sx={docModalFooterRowSx}>
            <Box sx={{ flex: "1 1 120px", minWidth: 0 }} />
            <Box sx={docModalFooterButtonsSx}>
              <AppButton dsVariant="ghost" dsSize="sm" onClick={handleClose} disabled={saving}>
                Cancelar
              </AppButton>
              <AppButton dsVariant="primary" dsSize="sm" onClick={() => void onGuardar()} disabled={saving}>
                {saving ? "Guardando…" : "Guardar expediente"}
              </AppButton>
            </Box>
          </Box>
        ) : (
          <Box sx={docModalFooterRowSx}>
            <Box sx={{ flex: "1 1 120px", minWidth: 0 }} />
            <Box sx={docModalFooterButtonsSx}>
              <AppButton dsVariant="primary" dsSize="sm" onClick={handleClose}>
                Cerrar
              </AppButton>
            </Box>
          </Box>
        )
      }
    >
      {!row ? null : variant === "soloExpediente" ? (
        <Stack spacing={DOC_MODAL_BLOCK_STACK_SPACING} component="section" aria-label="Alta de expediente de plazo">
          <BloqueReferenciaNotificacion row={row} />
          {row.source_type !== "COMPROBACION" ? (
            <NotificacionProrrogaExpedientesCard
              loading={prorrogaLoading}
              error={prorrogaError}
              detalle={prorrogaDetalle}
              modo="operativa"
            />
          ) : null}
          {modalApiError ? (
            <Alert severity="error" sx={{ mb: 0 }}>
              {modalApiError}
            </Alert>
          ) : null}
          <DocumentalBloque overline="Alta de expediente de plazo">
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
                label="Días de prórroga"
                type="number"
                value={prorrogaDias}
                onChange={(e) => onProrrogaDiasChange(e.target.value)}
                fullWidth
                required
                error={Boolean(fieldErrors.prorrogaDias)}
                helperText={fieldErrors.prorrogaDias || undefined}
              />
            </Stack>
          </DocumentalBloque>
        </Stack>
      ) : (
        <Stack spacing={DOC_MODAL_BLOCK_STACK_SPACING} component="section" aria-label="Historial de la notificación">
          <BloqueReferenciaNotificacion row={row} shell="actuacion" />

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
            />
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
