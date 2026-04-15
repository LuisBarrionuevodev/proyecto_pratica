import type { ReactNode } from "react";
import { Alert, Box, Chip, Divider, Typography } from "@mui/material";

import type { IActuacionesPendientesItem } from "../../../api/actuacionesPendientesApi";
import { formDialogContentStackSx } from "../../../styles/formDialogStyles";
import { GLASS_COLORS, glassCard } from "../../../styles/GlassStyles";
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
      <Typography
        component="span"
        variant="body2"
        sx={{ color: GLASS_COLORS.textSecondary, minWidth: { sm: 160 }, flex: { xs: "1 1 100%", sm: "0 1 38%" } }}
      >
        {etiqueta}
      </Typography>
      <Typography
        component="span"
        variant="body2"
        sx={{
          color: GLASS_COLORS.textPrimary,
          fontWeight: 500,
          textAlign: { xs: "left", sm: "right" },
          flex: { xs: "1 1 100%", sm: "1 1 50%" },
          wordBreak: "break-word",
        }}
      >
        {valor}
      </Typography>
    </Box>
  );
}

function DocumentalBloque({
  overline,
  resumen,
  children,
}: {
  overline: string;
  resumen?: string;
  children: ReactNode;
}) {
  return (
    <Box
      sx={{
        ...glassCard,
        p: 2,
        mb: 2,
        borderLeft: `3px solid ${COLORS.primary}`,
        borderRadius: "12px",
      }}
    >
      <Typography variant="overline" sx={{ color: COLORS.primary, letterSpacing: 1.1, fontWeight: 700 }}>
        {overline}
      </Typography>
      {resumen ? (
        <Typography variant="caption" sx={{ display: "block", color: GLASS_COLORS.textSecondary, mb: 1.25, mt: 0.25 }}>
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

/**
 * Estado / resultado inferible desde la fila de bandeja (sin endpoint de detalle).
 * Textos conservadores cuando falta dato.
 */
function filasResultadoEstado(row: IActuacionesPendientesItem): { etiqueta: string; valor: string }[] {
  const comprobNum = (row.acta_comprobacion_num ?? "").trim();
  const comprobMot = (row.comprobacion_motivo ?? "").trim();
  const comprobacion: string =
    comprobNum || comprobMot
      ? [comprobNum ? `Acta ${comprobNum}` : null, comprobMot || null].filter(Boolean).join(" · ") || "—"
      : "No consta comprobación vinculada en esta fila.";

  let expedientePlazo: string;
  if (row.notificacion_editable === false) {
    expedientePlazo =
      "La grilla marca la notificación como no editable (suele indicar expediente de plazo u otro vínculo administrativo).";
  } else if ((row.plazos_otorgados ?? 0) > 0) {
    expedientePlazo = `Constan ${row.plazos_otorgados} plazo(s) / prórroga(s) otorgado(s) en el consolidado.`;
  } else {
    expedientePlazo = "Sin prórrogas registradas en el consolidado de esta fila.";
  }

  const dr = row.dias_restantes;
  let plazoOp: string;
  if (dr === null || dr === undefined) {
    plazoOp = "—";
  } else if (dr <= 0) {
    plazoOp = "Vencido o vence hoy (según días restantes del consolidado).";
  } else {
    plazoOp = `Pendiente de vencimiento — restan ${dr} día(s).`;
  }

  const canal = row.source_type ? String(row.source_type) : null;

  const base: { etiqueta: string; valor: string }[] = [
    { etiqueta: "Comprobación posterior", valor: comprobacion },
    { etiqueta: "Expediente de plazo (inferido)", valor: expedientePlazo },
    { etiqueta: "Situación del plazo", valor: plazoOp },
  ];
  if (canal) base.push({ etiqueta: "Canal de la bandeja", valor: canal });
  return base;
}

function tituloPrincipal(row: IActuacionesPendientesItem): string {
  const n = (row.acta_notificacion_num ?? "").trim();
  if (n) return `Acta de notificación Nº ${n}`;
  return `Notificación — actuación #${row.id}`;
}

function subtituloCabecera(row: IActuacionesPendientesItem): string {
  const fecha = (row.fecha_actuacion ?? "").trim() || "—";
  const dom = domicilioLinea(row);
  const tit = contribuyenteLinea(row);
  return `${fecha} · ${dom} · ${tit}`;
}

function expedienteActasLinea(row: IActuacionesPendientesItem): string {
  if (!row.expediente_numero) return "—";
  return row.expediente_anio != null ? `${row.expediente_numero} / ${row.expediente_anio}` : String(row.expediente_numero);
}

export type NotificacionDetalleDocumentalDialogProps = {
  open: boolean;
  onClose: () => void;
  row: IActuacionesPendientesItem | null;
  /** En historial u otras vistas solo lectura: oculta el bloque de alta de expediente. */
  allowRegistrarExpediente: boolean;
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
 * Ficha documental de una fila de notificación (bandeja de expediente de plazo), con opción de registrar expediente.
 * Datos desde `IActuacionesPendientesItem` del listado actual (sin endpoint de detalle adicional).
 */
export function NotificacionDetalleDocumentalDialog({
  open,
  onClose,
  row,
  allowRegistrarExpediente,
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
  const handleClose = () => {
    if (saving) return;
    onClose();
  };

  const distritoNom = row ? distritoNombreSiHay(row) : null;

  const titleNode =
    row != null ? (
      <Box sx={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 0.75, py: 0.25, minWidth: 0 }}>
        <Chip
          label="Notificación"
          size="small"
          sx={{
            height: 24,
            fontWeight: 600,
            borderColor: GLASS_COLORS.borderMedium,
            color: GLASS_COLORS.textSecondary,
            backgroundColor: "rgba(255,255,255,0.06)",
          }}
          variant="outlined"
        />
        <Typography
          component="span"
          variant="h6"
          sx={{
            fontWeight: 700,
            lineHeight: 1.25,
            color: GLASS_COLORS.textPrimary,
            wordBreak: "break-word",
          }}
        >
          {tituloPrincipal(row)}
        </Typography>
        <Typography
          variant="body2"
          sx={{
            color: GLASS_COLORS.textSecondary,
            fontWeight: 500,
            lineHeight: 1.4,
            wordBreak: "break-word",
          }}
        >
          {subtituloCabecera(row)}
        </Typography>
        <Typography variant="caption" sx={{ color: GLASS_COLORS.textMuted }}>
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
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1.5, justifyContent: "flex-end", width: "100%" }}>
            <AppButton dsVariant="ghost" dsSize="sm" onClick={handleClose} disabled={saving}>
              Cancelar
            </AppButton>
            <AppButton dsVariant="primary" dsSize="sm" onClick={() => void onGuardar()} disabled={saving}>
              {saving ? "Guardando…" : "Guardar expediente"}
            </AppButton>
          </Box>
        ) : (
          <Box
            sx={{
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 1.5,
              width: "100%",
            }}
          >
            <Typography variant="caption" sx={{ color: GLASS_COLORS.textSecondary, flex: "1 1 220px", minWidth: 0 }}>
              Vista solo consulta. Los datos reflejan el estado al cargar la bandeja o el historial.
            </Typography>
            <AppButton dsVariant="primary" dsSize="sm" onClick={handleClose}>
              Cerrar
            </AppButton>
          </Box>
        )
      }
    >
      {!row ? null : (
        <>
          <Typography variant="body2" sx={{ color: GLASS_COLORS.textSecondary, mb: 1.5 }}>
            Ficha de consulta con los datos de la bandeja. El bloque final resume estado inferible desde la fila; un
            PR posterior puede enriquecer con expedientes de prórroga y distrito nominal.
          </Typography>

          <DocumentalBloque
            overline="Domicilio y titular"
            resumen="Ubicación, titular o razón social, documento y rubro según consta en la actuación."
          >
            <DocumentalFila etiqueta="Calle y número" valor={domicilioLinea(row)} />
            <DocumentalFila etiqueta="Contribuyente / razón social" valor={contribuyenteLinea(row)} />
            <DocumentalFila etiqueta="Documento" valor={textoValor(row.doc_nro)} />
            <DocumentalFila etiqueta="Rubro" valor={textoValor(row.rubro_nombre)} />
            {distritoNom ? <DocumentalFila etiqueta="Distrito" valor={distritoNom} /> : null}
          </DocumentalBloque>

          <DocumentalBloque
            overline="Inspección base"
            resumen="Datos de la visita que originó el acta en esta fila (fecha y equipo de la actuación; no implica otra actuación previa si el DTO no la trae)."
          >
            <DocumentalFila
              etiqueta="Fecha de la actuación (visita registrada)"
              valor={textoValor(row.fecha_actuacion)}
            />
            <DocumentalFila etiqueta="Acta de inspección (si consta)" valor={textoValor(row.acta_inspeccion_num)} />
            <DocumentalFila etiqueta="Inspectores" valor={inspectoresLinea(row)} />
            <DocumentalFila etiqueta="Orden de trabajo" valor={textoValor(row.orden_trabajo_numero)} />
            <DocumentalFila etiqueta="Tipo de actuación" valor={textoValor(row.tipo_actuacion)} />
          </DocumentalBloque>

          <DocumentalBloque overline="Motivos / infracciones" resumen="Hasta tres motivos vinculados a la notificación.">
            <DocumentalFila etiqueta="Motivo 1" valor={textoValor(row.notificacion_motivo_1)} />
            <DocumentalFila etiqueta="Motivo 2" valor={textoValor(row.notificacion_motivo_2)} />
            <DocumentalFila etiqueta="Motivo 3" valor={textoValor(row.notificacion_motivo_3)} />
          </DocumentalBloque>

          <DocumentalBloque
            overline="Plazo"
            resumen="Vencimiento operativo y cantidad de prórrogas registradas; expediente de actas solo si viene en el DTO."
          >
            <DocumentalFila etiqueta="Días restantes (vencimiento)" valor={diasPlazoLinea(row)} />
            <DocumentalFila etiqueta="Plazos otorgados (cantidad)" valor={textoValor(row.plazos_otorgados)} />
            <DocumentalFila etiqueta="Expediente asociado (DTO actas, si consta)" valor={expedienteActasLinea(row)} />
          </DocumentalBloque>

          <DocumentalBloque
            overline="Resultado / estado actual"
            resumen="Síntesis conservadora a partir de la fila (comprobación, plazos, editabilidad); no reemplaza un detalle por expediente."
          >
            {filasResultadoEstado(row).map((f) => (
              <DocumentalFila key={f.etiqueta} etiqueta={f.etiqueta} valor={f.valor} />
            ))}
          </DocumentalBloque>

          {allowRegistrarExpediente ? (
            <>
              <Divider sx={{ borderColor: GLASS_COLORS.borderLight, my: 1 }} />
              <Typography variant="subtitle2" sx={{ color: GLASS_COLORS.textPrimary, mb: 1 }}>
                Registrar expediente de plazo
              </Typography>
              {modalApiError ? (
                <Alert severity="error" sx={{ mb: 1 }}>
                  {modalApiError}
                </Alert>
              ) : null}
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
                label="Prórroga (días)"
                type="number"
                value={prorrogaDias}
                onChange={(e) => onProrrogaDiasChange(e.target.value)}
                fullWidth
                required
                error={Boolean(fieldErrors.prorrogaDias)}
                helperText={fieldErrors.prorrogaDias ?? "Días que se suman al plazo consolidado de la notificación."}
              />
            </>
          ) : null}
        </>
      )}
    </AppDialog>
  );
}
