import { useEffect, useMemo, useState } from "react";
import { Alert, Box, Chip, CircularProgress, Stack, Typography } from "@mui/material";

import {
  type IComprobacionDocumentalEdicion,
  type IComprobacionDocumentalExpedienteItem,
  type IComprobacionDocumentalOficioItem,
  type IComprobacionDocumentalResponse,
  type IJuzgadoCatalogItem,
  patchComprobacionExpedienteEnvio,
  patchComprobacionOficioBloque,
} from "../../../api/actuacionesPendientesApi";
import { formDialogContentStackSx } from "../../../styles/formDialogStyles";
import {
  docModalChipSx,
  docModalFooterButtonsSx,
  docModalFooterRowSx,
  docModalHeaderStackSx,
  docModalReferenceSx,
  docModalSubtitleSx,
  docModalTitleSx,
} from "../../../styles/documentalModalTokens";
import { AppButton, AppDialog, AppSelect, AppTextField } from "../../../ui";
import {
  BloqueInspeccionBaseFromOficioRow,
  BloqueReferenciaComprobacionOficio,
  DOC_MODAL_BLOCK_STACK_SPACING,
  DocumentalBloque,
  DocumentalFila,
  textoValor,
  type ComprobacionOficioReferenciaRow,
} from "./comprobacionOperativoBlocks";

/** Fila oficio + campos opcionales de inspección si el backend los envía. */
export type OficioOperativoRow = ComprobacionOficioReferenciaRow & {
  acta_inspeccion_num?: string | null;
  inspectores_texto?: string | null;
  inspector1?: string | null;
  inspector2?: string | null;
  inspector3?: string | null;
  tipo_actuacion?: string | null;
};

function actaCabecera(row: OficioOperativoRow): string {
  const n = (row.acta_comprobacion_num ?? "").trim();
  return n ? `Acta de comprobación Nº ${n}` : "Acta de comprobación";
}

function campoUtilMerge(v: unknown): boolean {
  return v != null && String(v).trim() !== "";
}

/**
 * Fuente canónica operativa: ``GET .../comprobacion/documental`` (referencia + acta) con fallback a la fila de bandeja.
 */
function mergeOficioRowConDocumental(
  row: OficioOperativoRow,
  doc: IComprobacionDocumentalResponse | null
): OficioOperativoRow {
  if (!doc) return row;
  const out: Record<string, unknown> = { ...row };
  const snap = doc.referencia_actuacion;
  if (snap && typeof snap === "object") {
    for (const [k, v] of Object.entries(snap)) {
      if (campoUtilMerge(v)) out[k] = v;
    }
  }
  if (campoUtilMerge(doc.acta_comprobacion?.motivo)) {
    out.comprobacion_motivo = doc.acta_comprobacion!.motivo;
  }
  if (campoUtilMerge(doc.acta_comprobacion?.numero)) {
    out.acta_comprobacion_num = doc.acta_comprobacion!.numero;
  }
  return out as unknown as OficioOperativoRow;
}

function filasOficioDocumental(ofi: IComprobacionDocumentalOficioItem) {
  const juz = (ofi.juzgado_nombre ?? "").trim();
  return (
    <>
      <DocumentalFila etiqueta="Número de oficio" valor={textoValor(ofi.numero_oficio)} />
      <DocumentalFila etiqueta="Año" valor={textoValor(ofi.anio)} />
      <DocumentalFila etiqueta="Fecha de oficio" valor={textoValor(ofi.fecha_oficio)} />
      <DocumentalFila etiqueta="Causa" valor={textoValor(ofi.causa)} />
      <DocumentalFila etiqueta="Juzgado" valor={juz || "—"} />
    </>
  );
}

function filasExpedienteRespuestaDocumental(ex: IComprobacionDocumentalExpedienteItem) {
  const num = (ex.numero_expediente ?? "").toString().trim();
  const an = (ex.anio ?? "").toString().trim();
  const identidad = num || an ? `${num || "—"}/${an || "—"}` : "—";
  return (
    <>
      <DocumentalFila etiqueta="Expediente (n.º / año)" valor={identidad} />
      <DocumentalFila etiqueta="Fecha" valor={textoValor(ex.fecha_expediente)} />
      <DocumentalFila etiqueta="Tipo" valor={textoValor(ex.tipo_expediente)} />
    </>
  );
}

function OperativoOficioYRespuestaEditable({
  open,
  actuacionId,
  documental,
  juzgados,
  onDocumentalUpdated,
}: {
  open: boolean;
  actuacionId: number;
  documental: IComprobacionDocumentalResponse;
  juzgados: IJuzgadoCatalogItem[];
  onDocumentalUpdated: () => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [numOfi, setNumOfi] = useState("");
  const [fecOfi, setFecOfi] = useState("");
  const [juzId, setJuzId] = useState<number | "">("");
  const [causa, setCausa] = useState("");
  const [numEx, setNumEx] = useState("");
  const [fecEx, setFecEx] = useState("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const ofi = documental.oficio!;
  const exR = documental.expediente_respuesta!;
  const edicion = documental.edicion;
  const puede = edicion?.puede_editar_bloque_oficio === true;
  const motivos = edicion?.motivos_bloqueo_oficio ?? [];

  useEffect(() => {
    setNumOfi((ofi.numero_oficio ?? "").trim());
    setFecOfi(ofi.fecha_oficio ? ofi.fecha_oficio.slice(0, 10) : "");
    setJuzId(ofi.juzgado_id != null ? ofi.juzgado_id : "");
    setCausa((ofi.causa ?? "").trim());
    setNumEx((exR.numero_expediente ?? "").trim());
    setFecEx(exR.fecha_expediente ? exR.fecha_expediente.slice(0, 10) : "");
  }, [ofi.id, exR.id, ofi.numero_oficio, ofi.fecha_oficio, ofi.juzgado_id, ofi.causa, exR.numero_expediente, exR.fecha_expediente]);

  useEffect(() => {
    if (!open) {
      setEditing(false);
      setErr(null);
    }
  }, [open]);

  return (
    <DocumentalBloque overline="Oficio y expediente de respuesta">
      <Stack spacing={1.25}>
        <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.7)", lineHeight: 1.45 }}>
          Datos registrados. La edición queda acá (no en Recorrido). Los cambios se guardan con «Guardar cambios».
        </Typography>
        <Typography component="div" variant="subtitle2" sx={{ color: "rgba(255,255,255,0.9)", pt: 0.5 }}>
          Oficio
        </Typography>
        {filasOficioDocumental(ofi)}
        <Typography component="div" variant="subtitle2" sx={{ color: "rgba(255,255,255,0.9)", pt: 1 }}>
          Expediente de respuesta
        </Typography>
        {filasExpedienteRespuestaDocumental(exR)}
        <Stack spacing={1.5} sx={{ pt: 1.5, borderTop: "1px solid rgba(255,255,255,0.08)" }}>
          {!puede && (edicion?.comprobacion_usada_como_iniciador || motivos.length > 0) ? (
            <Alert severity="warning">{motivos[0] ?? "No se puede editar el oficio ni el expediente de respuesta."}</Alert>
          ) : null}
          {!editing ? (
            puede ? (
              <AppButton dsVariant="primary" dsSize="sm" onClick={() => setEditing(true)}>
                Editar oficio y expediente de respuesta
              </AppButton>
            ) : null
          ) : (
            <>
              {err ? (
                <Alert severity="error" onClose={() => setErr(null)}>
                  {err}
                </Alert>
              ) : null}
              <AppTextField appearance="glass" label="Número de oficio" value={numOfi} onChange={(e) => setNumOfi(e.target.value)} fullWidth />
              <AppTextField
                appearance="glass"
                label="Fecha de oficio"
                type="date"
                value={fecOfi}
                onChange={(e) => setFecOfi(e.target.value)}
                InputLabelProps={{ shrink: true }}
                fullWidth
              />
              <AppSelect
                appearance="glass"
                label="Juzgado"
                value={juzId === "" ? "" : String(juzId)}
                onChange={(e) => setJuzId(e.target.value === "" ? "" : Number(e.target.value))}
                fullWidth
                variant="outlined"
                options={[{ value: "", label: "Seleccionar…" }, ...juzgados.map((j) => ({ value: String(j.id), label: j.nombre }))]}
              />
              <AppTextField appearance="glass" label="Causa" value={causa} onChange={(e) => setCausa(e.target.value)} fullWidth />
              <AppTextField
                appearance="glass"
                label="Número de expediente de respuesta"
                value={numEx}
                onChange={(e) => setNumEx(e.target.value)}
                fullWidth
              />
              <AppTextField
                appearance="glass"
                label="Fecha del expediente de respuesta"
                type="date"
                value={fecEx}
                onChange={(e) => setFecEx(e.target.value)}
                InputLabelProps={{ shrink: true }}
                fullWidth
              />
              <Stack direction="row" spacing={1} flexWrap="wrap">
                <AppButton
                  dsVariant="primary"
                  dsSize="sm"
                  disabled={saving || !numOfi.trim() || !fecOfi || juzId === "" || !numEx.trim() || !fecEx}
                  onClick={() => {
                    void (async () => {
                      setSaving(true);
                      setErr(null);
                      try {
                        await patchComprobacionOficioBloque(actuacionId, ofi.id, {
                          numero_oficio: numOfi.trim(),
                          fecha_oficio: fecOfi,
                          juzgado_id: Number(juzId),
                          causa: causa.trim() || null,
                          numero_expediente_respuesta: numEx.trim(),
                          fecha_expediente_respuesta: fecEx,
                        });
                        setEditing(false);
                        await onDocumentalUpdated();
                      } catch (e: unknown) {
                        const detail =
                          e && typeof e === "object" && "response" in e
                            ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
                            : null;
                        setErr(detail || "No se pudo guardar");
                      } finally {
                        setSaving(false);
                      }
                    })();
                  }}
                >
                  {saving ? "Guardando…" : "Guardar cambios"}
                </AppButton>
                <AppButton
                  dsVariant="ghost"
                  dsSize="sm"
                  disabled={saving}
                  onClick={() => {
                    setEditing(false);
                    setNumOfi((ofi.numero_oficio ?? "").trim());
                    setFecOfi(ofi.fecha_oficio ? ofi.fecha_oficio.slice(0, 10) : "");
                    setJuzId(ofi.juzgado_id != null ? ofi.juzgado_id : "");
                    setCausa((ofi.causa ?? "").trim());
                    setNumEx((exR.numero_expediente ?? "").trim());
                    setFecEx(exR.fecha_expediente ? exR.fecha_expediente.slice(0, 10) : "");
                    setErr(null);
                  }}
                >
                  Cancelar
                </AppButton>
              </Stack>
            </>
          )}
        </Stack>
      </Stack>
    </DocumentalBloque>
  );
}

function BloqueExpedienteEnvioEditable({
  actuacionId,
  expediente,
  edicion,
  documentalLoading,
  onDocumentalUpdated,
  pendienteRow,
  documentalError,
}: {
  actuacionId: number;
  expediente: IComprobacionDocumentalExpedienteItem | null;
  edicion: IComprobacionDocumentalEdicion | null;
  documentalLoading: boolean;
  onDocumentalUpdated: () => Promise<void>;
  pendienteRow: OficioOperativoRow | null;
  documentalError: string | null;
}) {
  const [editing, setEditing] = useState(false);
  const [num, setNum] = useState("");
  const [fec, setFec] = useState("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const expedienteDesdeLista: IComprobacionDocumentalExpedienteItem | null =
    expediente == null &&
    pendienteRow != null &&
    (pendienteRow.expediente_original_numero ?? "").trim() !== "" &&
    pendienteRow.expediente_original_id != null
      ? {
          id: pendienteRow.expediente_original_id,
          numero_expediente: (pendienteRow.expediente_original_numero ?? "").trim(),
          anio: String(pendienteRow.expediente_original_anio ?? ""),
          fecha_expediente: pendienteRow.expediente_original_fecha ?? null,
          tipo_expediente: "ENVIO_ACTA",
          oficio_id: null,
        }
      : null;

  const displayExp = expediente ?? expedienteDesdeLista;
  const puedeEditarApi = expediente != null && edicion?.puede_editar_expediente_envio === true;
  const soloLecturaLista = expediente == null && expedienteDesdeLista != null;

  useEffect(() => {
    if (!displayExp) return;
    setNum((displayExp.numero_expediente ?? "").trim());
    setFec(displayExp.fecha_expediente ? displayExp.fecha_expediente.slice(0, 10) : "");
  }, [displayExp?.id, displayExp?.numero_expediente, displayExp?.fecha_expediente]);

  useEffect(() => {
    if (!documentalLoading) setErr(null);
  }, [documentalLoading]);

  if (documentalLoading) {
    return (
      <DocumentalBloque overline="Expediente de envío">
        <Box sx={{ display: "flex", justifyContent: "center", py: 2 }}>
          <CircularProgress size={28} />
        </Box>
      </DocumentalBloque>
    );
  }

  if (!displayExp) return null;

  const motivos = edicion?.motivos_bloqueo_expediente_envio ?? [];
  const bloqueadoPorIniciador =
    expediente != null && !puedeEditarApi && (edicion?.comprobacion_usada_como_iniciador === true || motivos.length > 0);

  return (
    <DocumentalBloque overline="Expediente de envío">
      <Stack spacing={2}>
        {soloLecturaLista ? (
          <Alert severity="warning">
            {documentalError ??
              "No se pudieron cargar permisos de edición desde el servidor. Ves el expediente según el listado; cerrá y volvé a abrir o verificá la sesión."}
          </Alert>
        ) : null}
        {bloqueadoPorIniciador ? (
          <Alert severity="warning">
            {motivos[0] ?? "No se puede editar el expediente de envío en este estado."}
          </Alert>
        ) : null}
        {!editing ? (
          <>
            <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.85)" }}>
              <strong>Expediente (n.º / año):</strong>{" "}
              {(displayExp.numero_expediente ?? "").toString().trim() || "—"}/
              {(displayExp.anio ?? "").toString().trim() || "—"}
            </Typography>
            <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.85)" }}>
              <strong>Fecha:</strong> {displayExp.fecha_expediente ?? "—"}
            </Typography>
            {puedeEditarApi ? (
              <AppButton dsVariant="primary" dsSize="sm" onClick={() => setEditing(true)}>
                Editar
              </AppButton>
            ) : null}
          </>
        ) : (
          <>
            {err ? (
              <Alert severity="error" onClose={() => setErr(null)}>
                {err}
              </Alert>
            ) : null}
            <AppTextField
              appearance="glass"
              label="Número de expediente"
              value={num}
              onChange={(e) => setNum(e.target.value)}
              fullWidth
              required
            />
            <AppTextField
              appearance="glass"
              label="Fecha de expediente"
              type="date"
              value={fec}
              onChange={(e) => setFec(e.target.value)}
              InputLabelProps={{ shrink: true }}
              fullWidth
              required
            />
            <Stack direction="row" spacing={1} flexWrap="wrap">
              <AppButton
                dsVariant="primary"
                dsSize="sm"
                disabled={saving || !num.trim() || !fec || expediente == null}
                onClick={() => {
                  void (async () => {
                    if (expediente == null) return;
                    setSaving(true);
                    setErr(null);
                    try {
                      await patchComprobacionExpedienteEnvio(actuacionId, expediente.id, {
                        numero_expediente: num.trim(),
                        fecha_expediente: fec,
                      });
                      setEditing(false);
                      await onDocumentalUpdated();
                    } catch (e: unknown) {
                      const detail =
                        e && typeof e === "object" && "response" in e
                          ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
                          : null;
                      setErr(detail || "No se pudo guardar el expediente");
                    } finally {
                      setSaving(false);
                    }
                  })();
                }}
              >
                {saving ? "Guardando…" : "Guardar cambios"}
              </AppButton>
              <AppButton
                dsVariant="ghost"
                dsSize="sm"
                disabled={saving}
                onClick={() => {
                  setEditing(false);
                  setNum((displayExp.numero_expediente ?? "").trim());
                  setFec(displayExp.fecha_expediente ? displayExp.fecha_expediente.slice(0, 10) : "");
                  setErr(null);
                }}
              >
                Cancelar
              </AppButton>
            </Stack>
          </>
        )}
      </Stack>
    </DocumentalBloque>
  );
}

export type ComprobacionOficioOperativoDialogProps = {
  open: boolean;
  onClose: () => void;
  row: OficioOperativoRow | null;
  juzgados: IJuzgadoCatalogItem[];
  documental: IComprobacionDocumentalResponse | null;
  documentalLoading: boolean;
  documentalError: string | null;
  onDocumentalUpdated: () => Promise<void>;
  numeroOficio: string;
  onNumeroOficioChange: (v: string) => void;
  fechaOficio: string;
  onFechaOficioChange: (v: string) => void;
  juzgadoId: number | "";
  onJuzgadoIdChange: (v: number | "") => void;
  causa: string;
  onCausaChange: (v: string) => void;
  expNumero: string;
  onExpNumeroChange: (v: string) => void;
  expFecha: string;
  onExpFechaChange: (v: string) => void;
  modalApiError: string | null;
  saving: boolean;
  onGuardar: () => void | Promise<void>;
};

/**
 * Alta de oficio y expediente de respuesta: Referencia, visita y carga en card de acción.
 */
export function ComprobacionOficioOperativoDialog({
  open,
  onClose,
  row,
  juzgados,
  numeroOficio,
  onNumeroOficioChange,
  fechaOficio,
  onFechaOficioChange,
  juzgadoId,
  onJuzgadoIdChange,
  causa,
  onCausaChange,
  expNumero,
  onExpNumeroChange,
  expFecha,
  onExpFechaChange,
  modalApiError,
  saving,
  onGuardar,
  documental,
  documentalLoading,
  documentalError,
  onDocumentalUpdated,
}: ComprobacionOficioOperativoDialogProps) {
  const handleClose = () => {
    if (saving) return;
    onClose();
  };

  const displayRow = useMemo(
    () => (row == null ? null : mergeOficioRowConDocumental(row, documental)),
    [row, documental]
  );

  const tieneOficioCompleto =
    !documentalLoading && documental?.oficio != null && documental?.expediente_respuesta != null;

  const titleNode =
    displayRow != null ? (
      <Box sx={{ ...docModalHeaderStackSx, width: "100%" }}>
        <Chip label="Comprobación" size="small" sx={docModalChipSx} variant="outlined" />
        <Typography component="span" variant="h6" sx={docModalTitleSx}>
          {tieneOficioCompleto ? "Gestionar oficio y expediente de respuesta" : "Registrar oficio y expediente de respuesta"}
        </Typography>
        <Typography variant="body2" sx={docModalSubtitleSx}>
          {actaCabecera(displayRow)}
        </Typography>
        <Typography variant="caption" component="div" sx={{ ...docModalReferenceSx, maxWidth: "100%" }}>
          Actuación #{displayRow.id}
        </Typography>
      </Box>
    ) : (
      "Oficio"
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
            <AppButton dsVariant="primary" dsSize="sm" onClick={handleClose} disabled={saving}>
              Cerrar
            </AppButton>
          </Box>
        </Box>
      }
    >
      {!displayRow ? null : (
        <Stack spacing={DOC_MODAL_BLOCK_STACK_SPACING}>
          {documentalError ? (
            <Alert severity="warning">
              {documentalError} (referencia y visita siguen según el listado; reintentá si hace falta.)
            </Alert>
          ) : null}
          <BloqueReferenciaComprobacionOficio row={displayRow} />
          <BloqueInspeccionBaseFromOficioRow row={displayRow} />
          <BloqueExpedienteEnvioEditable
            actuacionId={displayRow.id}
            expediente={documental?.expediente_envio ?? null}
            edicion={documental?.edicion ?? null}
            documentalLoading={documentalLoading}
            onDocumentalUpdated={onDocumentalUpdated}
            pendienteRow={displayRow}
            documentalError={documentalError}
          />
          {documentalLoading ? (
            <DocumentalBloque overline="Oficio y expediente de respuesta">
              <Box sx={{ display: "flex", justifyContent: "center", py: 2 }}>
                <CircularProgress size={28} />
              </Box>
            </DocumentalBloque>
          ) : tieneOficioCompleto && documental ? (
            <OperativoOficioYRespuestaEditable
              open={open}
              actuacionId={displayRow.id}
              documental={documental}
              juzgados={juzgados}
              onDocumentalUpdated={onDocumentalUpdated}
            />
          ) : (
            <DocumentalBloque overline="Alta de oficio y expediente de respuesta">
              <Stack spacing={2}>
                <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.65)", lineHeight: 1.4 }}>
                  Carga manual: podés ingresar o corregir el número de oficio y el resto de los datos antes de guardar.
                </Typography>
                {modalApiError ? (
                  <Alert severity="error" sx={{ mb: 0 }}>
                    {modalApiError}
                  </Alert>
                ) : null}
                <AppTextField
                  appearance="glass"
                  label="Número de oficio"
                  value={numeroOficio}
                  onChange={(e) => onNumeroOficioChange(e.target.value)}
                  fullWidth
                  required
                />
                <AppTextField
                  appearance="glass"
                  label="Fecha de oficio"
                  type="date"
                  value={fechaOficio}
                  onChange={(e) => onFechaOficioChange(e.target.value)}
                  InputLabelProps={{ shrink: true }}
                  fullWidth
                  required
                />
                <AppSelect
                  appearance="glass"
                  label="Juzgado"
                  value={juzgadoId === "" ? "" : String(juzgadoId)}
                  onChange={(e) => onJuzgadoIdChange(e.target.value === "" ? "" : Number(e.target.value))}
                  fullWidth
                  required
                  variant="outlined"
                  options={[{ value: "", label: "Seleccionar…" }, ...juzgados.map((j) => ({ value: String(j.id), label: j.nombre }))]}
                />
                <AppTextField appearance="glass" label="Causa" value={causa} onChange={(e) => onCausaChange(e.target.value)} fullWidth />
                <AppTextField
                  appearance="glass"
                  label="Número de expediente de respuesta"
                  value={expNumero}
                  onChange={(e) => onExpNumeroChange(e.target.value)}
                  fullWidth
                  required
                />
                <AppTextField
                  appearance="glass"
                  label="Fecha del expediente de respuesta"
                  type="date"
                  value={expFecha}
                  onChange={(e) => onExpFechaChange(e.target.value)}
                  InputLabelProps={{ shrink: true }}
                  fullWidth
                  required
                />
                <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", pt: 0.5 }}>
                  <AppButton dsVariant="primary" dsSize="sm" onClick={() => void onGuardar()} disabled={saving}>
                    {saving ? "Guardando…" : "Guardar"}
                  </AppButton>
                </Box>
              </Stack>
            </DocumentalBloque>
          )}
        </Stack>
      )}
    </AppDialog>
  );
}
