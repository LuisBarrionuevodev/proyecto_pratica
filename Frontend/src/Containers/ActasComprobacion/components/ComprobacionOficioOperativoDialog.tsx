import type { ChangeEvent } from "react";
import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Alert, Box, CircularProgress, Stack, Typography } from "@mui/material";
import type { SelectChangeEvent } from "@mui/material/Select";

import {
  deleteComprobacionExpedienteEnvio,
  deleteComprobacionOficioBloque,
  type IComprobacionDocumentalEdicion,
  type IComprobacionDocumentalExpedienteItem,
  type IComprobacionDocumentalOficioItem,
  type IComprobacionDocumentalResponse,
  type IJuzgadoCatalogItem,
  patchComprobacionExpedienteEnvio,
  patchComprobacionOficioBloque,
} from "../../../api/actuacionesPendientesApi";
import { DocumentalModalFooter, DocumentalModalTitleStack } from "../../../components/documental/DocumentalModalChrome";
import { formDialogContentStackSx } from "../../../styles/formDialogStyles";
import { documentalGlassAlertSx } from "../../../styles/documentalModalTokens";
import { applyOficioAltaErrorsFromApi } from "../../../utils/oficioFormErrors";
import { AppButton, AppDialog, AppSelect, AppTextField, ConfirmDialog } from "../../../ui";
import { ComprobacionOficiosTribunalSection } from "./ComprobacionOficiosTribunalSection";
import {
  BloqueInspeccionBaseFromOficioRow,
  BloqueReferenciaComprobacionOficio,
  DOC_MODAL_BLOCK_STACK_SPACING,
  DocumentalBloque,
  DocumentalFila,
  parNumAnio,
  textoValor,
  type ComprobacionOficioReferenciaRow,
} from "./comprobacionOperativoBlocks";
import type { OficioComprobacionItem } from "../../../api/actuacionesPendientesApi";

/** Payload enviado al guardar el alta (misma forma que `createOficioDesdeActuacion`). */
export type ComprobacionOficioAltaPayload = {
  numero_oficio: string;
  fecha_oficio: string;
  juzgado_id: number;
  causa: string | null;
  numero_expediente_oficio: string;
  fecha_expediente_oficio: string;
};
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
      <DocumentalFila etiqueta="N.º y año" valor={parNumAnio(ofi.numero_oficio ?? null, ofi.anio ?? null)} />
      <DocumentalFila etiqueta="Fecha de oficio" valor={textoValor(ofi.fecha_oficio)} />
      <DocumentalFila etiqueta="Causa" valor={textoValor(ofi.causa)} />
      <DocumentalFila etiqueta="Juzgado" valor={juz || "—"} />
    </>
  );
}

function filasExpedienteRespuestaDocumental(ex: IComprobacionDocumentalExpedienteItem) {
  return (
    <>
      <DocumentalFila etiqueta="N.º y año" valor={parNumAnio(ex.numero_expediente ?? null, ex.anio ?? null)} />
      <DocumentalFila etiqueta="Fecha" valor={textoValor(ex.fecha_expediente)} />
    </>
  );
}

/** Mismo bloque editable que en «Pendientes de oficio» (oficio, causa, expediente de respuesta). Reutilizable en otros modales documentales. */
export const OperativoOficioYRespuestaEditable = memo(function OperativoOficioYRespuestaEditable({
  open,
  actuacionId,
  documental,
  juzgados,
  onDocumentalUpdated,
  oficioEditable,
  bloqueadoMotivo,
}: {
  open: boolean;
  actuacionId: number;
  documental: IComprobacionDocumentalResponse;
  juzgados: IJuzgadoCatalogItem[];
  onDocumentalUpdated: () => Promise<void>;
  /** Si viene del listado por oficio (PR4b), prevalece sobre permisos legacy del documental. */
  oficioEditable?: boolean | null;
  bloqueadoMotivo?: string | null;
}) {
  const [editing, setEditing] = useState(false);
  const [numOfi, setNumOfi] = useState("");
  const [fecOperativa, setFecOperativa] = useState("");
  const [juzId, setJuzId] = useState<number | "">("");
  const [causa, setCausa] = useState("");
  const [numEx, setNumEx] = useState("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const fe = useCallback((key: string) => fieldErrors[key] ?? "", [fieldErrors]);

  const ofi = documental.oficio!;
  const exR = documental.expediente_respuesta!;
  const edicion = documental.edicion;
  const motivos = edicion?.motivos_bloqueo_oficio ?? [];
  const puede =
    oficioEditable !== undefined && oficioEditable !== null
      ? oficioEditable
      : edicion?.puede_editar_bloque_oficio === true;
  const puedeEliminarBloque =
    oficioEditable !== undefined && oficioEditable !== null
      ? oficioEditable
      : edicion?.puede_eliminar_bloque_oficio === true;
  const motivoBloqueo =
    (bloqueadoMotivo ?? "").trim() ||
    motivos[0] ||
    (edicion?.comprobacion_usada_como_iniciador
      ? "No se puede editar el oficio ni el expediente de respuesta."
      : null);
  const [confirmDelBloqueOpen, setConfirmDelBloqueOpen] = useState(false);
  const [delBloqueSaving, setDelBloqueSaving] = useState(false);

  const juzgadoSelectOptions = useMemo(
    () => [{ value: "", label: "Seleccionar…" }, ...juzgados.map((j) => ({ value: String(j.id), label: j.nombre }))],
    [juzgados]
  );

  const filasExReadonly = useMemo(() => filasExpedienteRespuestaDocumental(exR), [exR]);
  const filasOfiReadonly = useMemo(() => filasOficioDocumental(ofi), [ofi]);

  const handleNumExChange = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    setNumEx(e.target.value);
  }, []);
  const handleFecOperativaChange = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    setFecOperativa(e.target.value);
  }, []);
  const handleNumOfiChange = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    setNumOfi(e.target.value);
  }, []);
  const handleCausaChange = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    setCausa(e.target.value);
  }, []);
  const handleJuzChange = useCallback((e: SelectChangeEvent<string>) => {
    const v = e.target.value;
    setJuzId(v === "" ? "" : Number(v));
  }, []);

  useEffect(() => {
    setNumOfi((ofi.numero_oficio ?? "").trim());
    const fo = ofi.fecha_oficio ? ofi.fecha_oficio.slice(0, 10) : "";
    const fe = exR.fecha_expediente ? exR.fecha_expediente.slice(0, 10) : "";
    setFecOperativa(fo || fe || "");
    setJuzId(ofi.juzgado_id != null ? ofi.juzgado_id : "");
    setCausa((ofi.causa ?? "").trim());
    setNumEx((exR.numero_expediente ?? "").trim());
  }, [ofi.id, exR.id, ofi.numero_oficio, ofi.fecha_oficio, ofi.juzgado_id, ofi.causa, exR.numero_expediente, exR.fecha_expediente]);

  useEffect(() => {
    if (!open) {
      setEditing(false);
      setErr(null);
      setFieldErrors({});
    }
  }, [open]);

  return (
    <DocumentalBloque overline="Oficio y expediente de respuesta">
      <Stack spacing={1.25}>
        {err ? (
          <Alert severity="error" sx={documentalGlassAlertSx} onClose={() => setErr(null)}>
            <Typography variant="body2" fontWeight={600} sx={{ mb: 0.5 }}>
              Error
            </Typography>
            <Typography variant="body2">{err}</Typography>
          </Alert>
        ) : null}
        <Typography component="div" variant="subtitle2" sx={{ color: "rgba(255,255,255,0.9)", pt: 0.5 }}>
          Expediente de respuesta
        </Typography>
        {filasExReadonly}
        <Typography component="div" variant="subtitle2" sx={{ color: "rgba(255,255,255,0.9)", pt: 1 }}>
          Oficio
        </Typography>
        {filasOfiReadonly}
        <Stack spacing={1.5} sx={{ pt: 1.5, borderTop: "1px solid rgba(255,255,255,0.08)" }}>
          {!puede && motivoBloqueo ? (
            <Alert severity="warning" sx={documentalGlassAlertSx}>
              <Typography variant="body2" fontWeight={600} sx={{ mb: 0.5 }}>
                No editable
              </Typography>
              <Typography variant="body2">{motivoBloqueo}</Typography>
            </Alert>
          ) : null}
          {!editing ? (
            puede ? (
              <Stack direction="row" spacing={1} flexWrap="wrap" alignItems="center">
                <AppButton dsVariant="primary" dsSize="sm" onClick={() => setEditing(true)}>
                  Editar
                </AppButton>
                {puedeEliminarBloque ? (
                  <AppButton dsVariant="danger" dsSize="sm" onClick={() => setConfirmDelBloqueOpen(true)}>
                    Eliminar
                  </AppButton>
                ) : null}
              </Stack>
            ) : null
          ) : (
            <>
              <AppTextField
                appearance="glass"
                label="Número de expediente de respuesta"
                value={numEx}
                onChange={handleNumExChange}
                fullWidth
                error={Boolean(fe("numero_expediente_oficio"))}
                helperText={fe("numero_expediente_oficio") || undefined}
              />
              <AppTextField
                appearance="glass"
                label="Fecha"
                type="date"
                value={fecOperativa}
                onChange={handleFecOperativaChange}
                InputLabelProps={{ shrink: true }}
                fullWidth
                error={Boolean(fe("fecha_oficio"))}
                helperText={fe("fecha_oficio") || undefined}
              />
              <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.55)", mt: -0.5, display: "block" }}>
                Una sola fecha para oficio y expediente de respuesta (mismo dato operativo).
              </Typography>
              <AppTextField
                appearance="glass"
                label="Número de oficio"
                value={numOfi}
                onChange={handleNumOfiChange}
                fullWidth
                error={Boolean(fe("numero_oficio"))}
                helperText={fe("numero_oficio") || undefined}
              />
              <AppTextField
                appearance="glass"
                label="Causa"
                value={causa}
                onChange={handleCausaChange}
                fullWidth
                error={Boolean(fe("causa"))}
                helperText={fe("causa") || undefined}
              />
              <AppSelect
                appearance="glass"
                label="Juzgado"
                value={juzId === "" ? "" : String(juzId)}
                onChange={handleJuzChange}
                fullWidth
                variant="outlined"
                error={Boolean(fe("juzgado_id"))}
                helperText={fe("juzgado_id") || undefined}
                options={juzgadoSelectOptions}
              />
              <Stack direction="row" spacing={1} flexWrap="wrap">
                <AppButton
                  dsVariant="primary"
                  dsSize="sm"
                  disabled={saving || !numOfi.trim() || !fecOperativa || juzId === "" || !numEx.trim()}
                  onClick={() => {
                    void (async () => {
                      setSaving(true);
                      setErr(null);
                      setFieldErrors({});
                      try {
                        await patchComprobacionOficioBloque(actuacionId, ofi.id, {
                          numero_oficio: numOfi.trim(),
                          fecha_oficio: fecOperativa,
                          juzgado_id: Number(juzId),
                          causa: causa.trim() || null,
                          numero_expediente_respuesta: numEx.trim(),
                          fecha_expediente_respuesta: fecOperativa,
                        });
                        setEditing(false);
                        await onDocumentalUpdated();
                      } catch (e: unknown) {
                        const parsed = applyOficioAltaErrorsFromApi(e);
                        setFieldErrors(parsed.fieldErrors);
                        setErr(parsed.globalMessage);
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
                    const fo = ofi.fecha_oficio ? ofi.fecha_oficio.slice(0, 10) : "";
                    const fe = exR.fecha_expediente ? exR.fecha_expediente.slice(0, 10) : "";
                    setFecOperativa(fo || fe || "");
                    setJuzId(ofi.juzgado_id != null ? ofi.juzgado_id : "");
                    setCausa((ofi.causa ?? "").trim());
                    setNumEx((exR.numero_expediente ?? "").trim());
                    setErr(null);
                  }}
                >
                  Cancelar
                </AppButton>
              </Stack>
            </>
          )}
        </Stack>
        <ConfirmDialog
          open={confirmDelBloqueOpen}
          onClose={() => {
            if (!delBloqueSaving) setConfirmDelBloqueOpen(false);
          }}
          title="Eliminar oficio y expediente de respuesta"
          destructive
          loading={delBloqueSaving}
          onConfirm={async () => {
            setDelBloqueSaving(true);
            setErr(null);
            try {
              await deleteComprobacionOficioBloque(actuacionId, ofi.id);
              setConfirmDelBloqueOpen(false);
              await onDocumentalUpdated();
            } catch (e: unknown) {
              const detail =
                e && typeof e === "object" && "response" in e
                  ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
                  : null;
              setErr(detail || "No se pudo eliminar");
            } finally {
              setDelBloqueSaving(false);
            }
          }}
        >
          <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.85)" }}>
            Se marcarán como eliminados el oficio y el expediente de respuesta. La actuación y el acta de comprobación no se
            borran; podés volver a cargar el oficio desde la bandeja si corresponde.
          </Typography>
        </ConfirmDialog>
      </Stack>
    </DocumentalBloque>
  );
});

/** Estado local del alta: evita re-render del modal completo (referencia, visita, expediente envío) en cada tecla. */
export const ComprobacionOficioAltaFields = memo(function ComprobacionOficioAltaFields({
  open,
  defaultFechaAlta,
  juzgados,
  modalApiError,
  fieldErrors = {},
  saving,
  onGuardarAlta,
}: {
  open: boolean;
  defaultFechaAlta: string;
  juzgados: IJuzgadoCatalogItem[];
  modalApiError: string | null;
  fieldErrors?: Record<string, string>;
  saving: boolean;
  onGuardarAlta: (payload: ComprobacionOficioAltaPayload) => void | Promise<void>;
}) {
  const [altaNumEx, setAltaNumEx] = useState("");
  const [altaFecha, setAltaFecha] = useState("");
  const [altaNumOfi, setAltaNumOfi] = useState("");
  const [altaCausa, setAltaCausa] = useState("");
  const [altaJuzId, setAltaJuzId] = useState<number | "">("");

  const prevOpenRef = useRef(false);
  useEffect(() => {
    if (open && !prevOpenRef.current) {
      setAltaNumEx("");
      setAltaFecha(defaultFechaAlta);
      setAltaNumOfi("");
      setAltaCausa("");
      setAltaJuzId("");
    }
    prevOpenRef.current = open;
  }, [open, defaultFechaAlta]);

  const juzgadoOptionsAlta = useMemo(
    () => [{ value: "", label: "Seleccionar…" }, ...juzgados.map((j) => ({ value: String(j.id), label: j.nombre }))],
    [juzgados]
  );

  const handleGuardarAltaClick = useCallback(() => {
    if (altaJuzId === "") return;
    void onGuardarAlta({
      numero_oficio: altaNumOfi.trim(),
      fecha_oficio: altaFecha,
      juzgado_id: Number(altaJuzId),
      causa: altaCausa.trim() || null,
      numero_expediente_oficio: altaNumEx.trim(),
      fecha_expediente_oficio: altaFecha,
    });
  }, [altaJuzId, altaNumOfi, altaFecha, altaCausa, altaNumEx, onGuardarAlta]);

  const fe = useCallback((key: string) => fieldErrors[key] ?? "", [fieldErrors]);

  const handleAltaNumExChange = useCallback((e: ChangeEvent<HTMLInputElement>) => setAltaNumEx(e.target.value), []);
  const handleAltaFechaChange = useCallback((e: ChangeEvent<HTMLInputElement>) => setAltaFecha(e.target.value), []);
  const handleAltaNumOfiChange = useCallback((e: ChangeEvent<HTMLInputElement>) => setAltaNumOfi(e.target.value), []);
  const handleAltaCausaChange = useCallback((e: ChangeEvent<HTMLInputElement>) => setAltaCausa(e.target.value), []);
  const handleAltaJuzChange = useCallback((e: SelectChangeEvent<string>) => {
    const v = e.target.value;
    setAltaJuzId(v === "" ? "" : Number(v));
  }, []);

  return (
    <DocumentalBloque overline="Alta de oficio y expediente de respuesta">
      <Stack spacing={2}>
        <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.65)", lineHeight: 1.4 }}>
          Primero el expediente de respuesta y la fecha compartida; luego el oficio, la causa y el juzgado.
        </Typography>
        {modalApiError ? (
          <Alert severity="error" sx={{ mb: 0, ...documentalGlassAlertSx }}>
            <Typography variant="body2">{modalApiError}</Typography>
          </Alert>
        ) : null}
        <AppTextField
          appearance="glass"
          label="Número de expediente de respuesta"
          value={altaNumEx}
          onChange={handleAltaNumExChange}
          fullWidth
          required
          error={Boolean(fe("numero_expediente_oficio"))}
          helperText={fe("numero_expediente_oficio") || undefined}
        />
        <AppTextField
          appearance="glass"
          label="Fecha"
          type="date"
          value={altaFecha}
          onChange={handleAltaFechaChange}
          InputLabelProps={{ shrink: true }}
          fullWidth
          required
          error={Boolean(fe("fecha_oficio"))}
          helperText={fe("fecha_oficio") || undefined}
        />
        <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.55)", mt: -0.5, display: "block" }}>
          Una sola fecha para oficio y expediente de respuesta (mismo dato operativo).
        </Typography>
        <AppTextField
          appearance="glass"
          label="Número de oficio"
          value={altaNumOfi}
          onChange={handleAltaNumOfiChange}
          fullWidth
          required
          error={Boolean(fe("numero_oficio"))}
          helperText={fe("numero_oficio") || undefined}
        />
        <AppTextField
          appearance="glass"
          label="Causa"
          value={altaCausa}
          onChange={handleAltaCausaChange}
          fullWidth
          error={Boolean(fe("causa"))}
          helperText={fe("causa") || undefined}
        />
        <AppSelect
          appearance="glass"
          label="Juzgado"
          value={altaJuzId === "" ? "" : String(altaJuzId)}
          onChange={handleAltaJuzChange}
          fullWidth
          required
          variant="outlined"
          error={Boolean(fe("juzgado_id"))}
          helperText={fe("juzgado_id") || undefined}
          options={juzgadoOptionsAlta}
        />
        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", pt: 0.5 }}>
          <AppButton
            dsVariant="primary"
            dsSize="sm"
            loading={saving}
            onClick={handleGuardarAltaClick}
            disabled={saving || !altaNumOfi.trim() || !altaFecha || altaJuzId === "" || !altaNumEx.trim()}
            sx={{ fontWeight: 700 }}
          >
            {saving ? "Guardando…" : "Guardar"}
          </AppButton>
        </Box>
      </Stack>
    </DocumentalBloque>
  );
});

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
  const [confirmDelEnvioOpen, setConfirmDelEnvioOpen] = useState(false);
  const [delEnvioSaving, setDelEnvioSaving] = useState(false);

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
  const puedeEliminarEnvioApi = expediente != null && edicion?.puede_eliminar_expediente_envio === true;
  const motivosEliminarEnvio = edicion?.motivos_bloqueo_eliminar_expediente_envio ?? [];
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
        {err ? (
          <Alert severity="error" sx={documentalGlassAlertSx} onClose={() => setErr(null)}>
            <Typography variant="body2" fontWeight={600} sx={{ mb: 0.5 }}>
              Error
            </Typography>
            <Typography variant="body2">{err}</Typography>
          </Alert>
        ) : null}
        {soloLecturaLista ? (
          <Alert severity="warning" sx={documentalGlassAlertSx}>
            <Typography variant="body2" fontWeight={600} sx={{ mb: 0.5 }}>
              Edición no disponible en el servidor
            </Typography>
            <Typography variant="body2">
              {documentalError ??
                "No se pudieron cargar los permisos de edición. Ves el expediente según el listado; cerrá y volvé a abrir o verificá la sesión."}
            </Typography>
          </Alert>
        ) : null}
        {bloqueadoPorIniciador ? (
          <Alert severity="warning" sx={documentalGlassAlertSx}>
            <Typography variant="body2" fontWeight={600} sx={{ mb: 0.5 }}>
              Edición bloqueada
            </Typography>
            <Typography variant="body2">
              {motivos[0] ?? "No se puede editar el expediente de envío en este estado."}
            </Typography>
          </Alert>
        ) : null}
        {!editing ? (
          <>
            <DocumentalFila
              etiqueta="N.º y año"
              valor={parNumAnio(displayExp.numero_expediente ?? null, displayExp.anio ?? null)}
            />
            <DocumentalFila etiqueta="Fecha" valor={textoValor(displayExp.fecha_expediente)} />
            {puedeEditarApi || puedeEliminarEnvioApi ? (
              <Stack direction="row" spacing={1} flexWrap="wrap" alignItems="center">
                {puedeEditarApi ? (
                  <AppButton dsVariant="primary" dsSize="sm" onClick={() => setEditing(true)}>
                    Editar
                  </AppButton>
                ) : null}
                {puedeEliminarEnvioApi ? (
                  <AppButton dsVariant="danger" dsSize="sm" onClick={() => setConfirmDelEnvioOpen(true)}>
                    Eliminar
                  </AppButton>
                ) : null}
              </Stack>
            ) : null}
            {!puedeEliminarEnvioApi && expediente != null && motivosEliminarEnvio.length > 0 ? (
              <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.55)", display: "block", pt: 0.5 }}>
                {motivosEliminarEnvio[0]}
              </Typography>
            ) : null}
          </>
        ) : (
          <>
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
        <ConfirmDialog
          open={confirmDelEnvioOpen}
          onClose={() => {
            if (!delEnvioSaving) setConfirmDelEnvioOpen(false);
          }}
          title="Eliminar expediente de envío"
          destructive
          loading={delEnvioSaving}
          onConfirm={async () => {
            if (expediente == null) return;
            setDelEnvioSaving(true);
            setErr(null);
            try {
              await deleteComprobacionExpedienteEnvio(actuacionId, expediente.id);
              setConfirmDelEnvioOpen(false);
              setEditing(false);
              await onDocumentalUpdated();
            } catch (e: unknown) {
              const detail =
                e && typeof e === "object" && "response" in e
                  ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
                  : null;
              setErr(detail || "No se pudo eliminar el expediente");
            } finally {
              setDelEnvioSaving(false);
            }
          }}
        >
          <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.85)" }}>
            Se marcará como eliminado solo el expediente de envío del acta. No se borra la actuación ni el acta de
            comprobación. Si necesitás otro número, podés cargarlo de nuevo desde la bandeja de expedientes.
          </Typography>
        </ConfirmDialog>
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
  oficios: OficioComprobacionItem[];
  oficiosLoading: boolean;
  oficiosError: string | null;
  onDocumentalUpdated: () => Promise<void>;
  /** Fecha por defecto del alta (p. ej. fin de mes en curso); no re-renderiza la página al tipear. */
  defaultFechaAlta: string;
  modalApiError: string | null;
  modalFieldErrors?: Record<string, string>;
  saving: boolean;
  onGuardarAlta: (payload: ComprobacionOficioAltaPayload) => void | Promise<void>;
};

/**
 * Alta de oficio y expediente de respuesta: Referencia, visita y carga en card de acción.
 */
export function ComprobacionOficioOperativoDialog({
  open,
  onClose,
  row,
  juzgados,
  defaultFechaAlta,
  modalApiError,
  modalFieldErrors = {},
  saving,
  onGuardarAlta,
  documental,
  documentalLoading,
  documentalError,
  oficios,
  oficiosLoading,
  oficiosError,
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

  const tieneOficios =
    oficios.length > 0 || (documental?.oficio != null && documental?.expediente_respuesta != null);

  const titleNode =
    displayRow != null ? (
      <DocumentalModalTitleStack
        dominioChip="Comprobación"
        titulo={actaCabecera(displayRow)}
        subtitulo={tieneOficios ? "Oficios y respuestas del tribunal" : "Registrar oficio y expediente de respuesta"}
        actuacionId={undefined}
      />
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
      actions={undefined}
    >
      {!displayRow ? null : (
        <Stack spacing={DOC_MODAL_BLOCK_STACK_SPACING}>
          {documentalError ? (
            <Alert severity="warning" sx={documentalGlassAlertSx}>
              <Typography variant="body2" fontWeight={600} sx={{ mb: 0.5 }}>
                Carga documental incompleta
              </Typography>
              <Typography variant="body2">
                {documentalError} La referencia y la visita siguen según el listado; reintentá si hace falta.
              </Typography>
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
          <ComprobacionOficiosTribunalSection
            open={open}
            actuacionId={displayRow.id}
            documental={documental}
            documentalLoading={documentalLoading}
            oficios={oficios}
            oficiosLoading={oficiosLoading}
            oficiosError={oficiosError}
            juzgados={juzgados}
            defaultFechaAlta={defaultFechaAlta}
            modalApiError={modalApiError}
            modalFieldErrors={modalFieldErrors}
            saving={saving}
            onGuardarAlta={onGuardarAlta}
            onDocumentalUpdated={onDocumentalUpdated}
          />
        </Stack>
      )}
    </AppDialog>
  );
}
