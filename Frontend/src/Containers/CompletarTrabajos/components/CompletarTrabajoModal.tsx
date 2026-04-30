import { useCallback, useEffect, useMemo, useRef, useState, type MouseEvent } from "react";
import {
  Alert,
  Autocomplete,
  Box,
  Chip,
  CircularProgress,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";

import type { ICompletarTrabajoInspectorGrupo, ICompletarTrabajoPendienteRow } from "../../../api/completarTrabajoApi";
import { getCompletarTrabajoDetalle } from "../../../api/completarTrabajoApi";
import { formatActuacionListDomicilioLinea } from "../../../utils/formatDomicilioLineaVisible";
import { AppButton, AppDialog, AppSelect, AppTextField } from "../../../ui";
import { submitCompletarTrabajoCierreFromRow } from "../completion/submitCompletarTrabajoCierre";
import type { CompletarTrabajoCatalogs } from "../hooks/completarTrabajoCatalogsCache";
import { esNoPermiteInspeccionContraproducencia } from "../utils/completarTrabajoContraproducencia";
import { getContraproducenciaUxHint } from "../utils/contraproducenciaUxHint";
import {
  applyCompletarTrabajoFieldErrorsFromApi,
  COMPLETAR_TRABAJO_FIELD_ERROR_SUMMARY,
  formatCompletarTrabajoApiError,
} from "../utils/completarTrabajoErrors";

const ACTA_KEYS_EMPTY = {
  acta_inspeccion_num: "",
  acta_notificacion_num: "",
  notificacion_motivo_1: "",
  notificacion_motivo_2: "",
  notificacion_motivo_3: "",
  acta_comprobacion_num: "",
  comprobacion_motivo: "",
  acta_clausura_num: "",
  acta_decomiso_num: "",
  decomiso_kilos_total: "",
} as const;

function mergeCatalogOpts(catalog: string[], current: string | null | undefined): { value: string; label: string }[] {
  const set = new Set<string>(catalog);
  const c = (current ?? "").trim();
  if (c) set.add(c);
  return [{ value: "", label: "—" }, ...[...set].sort().map((v) => ({ value: v, label: v }))];
}

function domicilioResumen(r: ICompletarTrabajoPendienteRow): string {
  const fromApi = r.domicilio_texto?.trim();
  if (fromApi) return fromApi;
  const line = formatActuacionListDomicilioLinea(r).trim();
  return line || "—";
}

function dedupeInspectoresPreserveOrder(names: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const n of names) {
    const t = n.trim();
    if (!t || seen.has(t)) continue;
    seen.add(t);
    out.push(t);
  }
  return out;
}

/**
 * Lista inicial: grupo de ruta (orden estable); si no hay, `inspectores[]` o slots 1–3 de la fila.
 */
function initialInspectoresList(
  row: ICompletarTrabajoPendienteRow,
  grupo: ICompletarTrabajoInspectorGrupo[]
): string[] {
  if (grupo.length > 0) {
    return dedupeInspectoresPreserveOrder(grupo.map((g) => (g.nombre ?? "").trim()).filter(Boolean));
  }
  if (Array.isArray(row.inspectores) && row.inspectores.length > 0) {
    return dedupeInspectoresPreserveOrder(row.inspectores.map((x) => String(x)));
  }
  return dedupeInspectoresPreserveOrder([
    (row.inspector1 ?? "").trim(),
    (row.inspector2 ?? "").trim(),
    (row.inspector3 ?? "").trim(),
  ].filter(Boolean));
}

function sameInspectoresListOrder(a: string[], b: string[]): boolean {
  const na = a.map((x) => x.trim()).filter(Boolean);
  const nb = b.map((x) => x.trim()).filter(Boolean);
  if (na.length !== nb.length) return false;
  return na.every((v, i) => v === nb[i]);
}

function dashIfEmpty(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

const CUMPLE_OPTS: { value: string; label: string }[] = [
  { value: "", label: "—" },
  { value: "CUMPLE", label: "CUMPLE" },
  { value: "NO_CUMPLE", label: "NO_CUMPLE" },
];

/** Catálogo `Actuaciones.tipo` permitido al cerrar `REINSPECCION_OFICIO` (alineado al backend). */
const TIPO_ACTUACION_REINSPECCION_OFICIO = [
  "RATIFICACION DE CLAUSURA",
  "RATIFICACION DE DECOMISO",
  "VERIFICAR E INFORMAR",
] as const;

const TIPO_ACTUACION_REINSPECCION_OFICIO_OPTS: { value: string; label: string }[] = [
  { value: "", label: "—" },
  ...TIPO_ACTUACION_REINSPECCION_OFICIO.map((v) => ({ value: v, label: v })),
];

function tipoActuacionInicialReinspeccionOficio(tipo: string | null | undefined): string {
  const t = (tipo ?? "").trim();
  return (TIPO_ACTUACION_REINSPECCION_OFICIO as readonly string[]).includes(t) ? t : "";
}

/** Titular del domicilio: persona física (apellido + nombre) o razón social (PJ). */
type TitularModoCompletarTrabajo = "persona" | "razon_social";

function titularModoInicialDesdeRow(r: ICompletarTrabajoPendienteRow): TitularModoCompletarTrabajo {
  const rs = (r.razon_social ?? "").trim();
  return rs ? "razon_social" : "persona";
}

export type CompletarTrabajoModalProps = {
  open: boolean;
  /** Fila del listado al abrir; el modal refresca con GET detalle antes de editar. */
  row: ICompletarTrabajoPendienteRow | null;
  catalogs: CompletarTrabajoCatalogs | null;
  catalogsReady: boolean;
  onClose: () => void;
  onSuccess: (rutaItemId: number) => void;
};

/**
 * Cierre Completar trabajo: cabecera fija.
 * Al abrir, carga `GET /actuaciones/completar-trabajo/detalle/:ruta_item_id` para fila fresca,
 * inspectores del grupo y referencia de tipo; si falla, usa la fila del listado.
 * - `REINSPECCION_OFICIO`: tipo de actuación + dio cumplimiento + observaciones opcionales.
 * - Resto: editables en orden cerrado, actas solo sin contraproducencia.
 */
export function CompletarTrabajoModal({
  open,
  row,
  catalogs,
  catalogsReady,
  onClose,
  onSuccess,
}: CompletarTrabajoModalProps) {
  const cat = catalogs ?? {
    motivos: [],
    motivosComprobacion: [],
    contraproducencias: [],
    inspectores: [],
    rubros: [],
  };
  const [contraproducencia, setContraproducencia] = useState("");
  const [calle, setCalle] = useState("");
  const [numero, setNumero] = useState("");
  const [rubroNombre, setRubroNombre] = useState("");
  const [docNro, setDocNro] = useState("");
  const [contribApellido, setContribApellido] = useState("");
  const [contribNombre, setContribNombre] = useState("");
  const [razonSocial, setRazonSocial] = useState("");
  const [titularModo, setTitularModo] = useState<TitularModoCompletarTrabajo>("persona");
  const [nombreLocal, setNombreLocal] = useState("");
  const [actaInspeccion, setActaInspeccion] = useState("");
  const [actaNotificacion, setActaNotificacion] = useState("");
  const [notifM1, setNotifM1] = useState("");
  const [notifM2, setNotifM2] = useState("");
  const [notifM3, setNotifM3] = useState("");
  const [actaComprobacion, setActaComprobacion] = useState("");
  const [comprobacionMotivo, setComprobacionMotivo] = useState("");
  const [actaClausura, setActaClausura] = useState("");
  const [actaDecomiso, setActaDecomiso] = useState("");
  const [decomisoKilos, setDecomisoKilos] = useState("");
  const [tipoActuacionOficio, setTipoActuacionOficio] = useState("");
  const [resultadoCumplimientoOficio, setResultadoCumplimientoOficio] = useState("");
  const [observacionesEjecucion, setObservacionesEjecucion] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  /** Claves alineadas al payload / errores 422 del backend (pydantic field names). */
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  /** Fila efectiva tras GET detalle (o fallback a `row` si el GET falla). */
  const [resolvedRow, setResolvedRow] = useState<ICompletarTrabajoPendienteRow | null>(null);
  const [detalleLoading, setDetalleLoading] = useState(false);
  const [detalleError, setDetalleError] = useState<string | null>(null);
  const [inspectoresGrupo, setInspectoresGrupo] = useState<ICompletarTrabajoInspectorGrupo[]>([]);
  const [tipoActuacionEsperadoRef, setTipoActuacionEsperadoRef] = useState<string | null>(null);

  const [inspectoresList, setInspectoresList] = useState<string[]>([]);
  const baselineInspectoresRef = useRef<string[]>([]);

  useEffect(() => {
    if (!open || !row) {
      setResolvedRow(null);
      setDetalleLoading(false);
      setDetalleError(null);
      setInspectoresGrupo([]);
      setTipoActuacionEsperadoRef(null);
      return;
    }
    let cancelled = false;
    setResolvedRow(null);
    setDetalleLoading(true);
    setDetalleError(null);
    setInspectoresGrupo([]);
    setTipoActuacionEsperadoRef(null);

    getCompletarTrabajoDetalle(row.ruta_item_id)
      .then((d) => {
        if (cancelled) return;
        setResolvedRow(d.row);
        setInspectoresGrupo(d.inspectores_grupo ?? []);
        setTipoActuacionEsperadoRef(d.tipo_actuacion_esperado ?? d.row.tipo_actuacion_esperado ?? null);
        setDetalleLoading(false);
      })
      .catch((e) => {
        if (cancelled) return;
        setResolvedRow(row);
        setInspectoresGrupo([]);
        setTipoActuacionEsperadoRef(row.tipo_actuacion_esperado ?? null);
        setDetalleError(formatCompletarTrabajoApiError(e));
        setDetalleLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [open, row]);

  useEffect(() => {
    if (!open || !resolvedRow) return;
    const initial = initialInspectoresList(resolvedRow, inspectoresGrupo);
    setInspectoresList(initial);
    baselineInspectoresRef.current = initial;

    setError(null);
    setFieldErrors({});
    if (resolvedRow.tipo_iniciador === "REINSPECCION_OFICIO") {
      setTipoActuacionOficio(tipoActuacionInicialReinspeccionOficio(resolvedRow.tipo_actuacion));
      setResultadoCumplimientoOficio(resolvedRow.resultado_cumplimiento_oficio ?? "");
      setObservacionesEjecucion(resolvedRow.observaciones_ejecucion ?? "");
      return;
    }
    setResultadoCumplimientoOficio("");
    setObservacionesEjecucion(resolvedRow.observaciones_ejecucion ?? "");
    setContraproducencia(resolvedRow.contraproducencia ?? "");
    setCalle(resolvedRow.calle ?? "");
    setNumero(resolvedRow.numero ?? "");
    setRubroNombre(resolvedRow.rubro_nombre ?? "");
    setDocNro(resolvedRow.doc_nro ?? "");
    setContribApellido(resolvedRow.contrib_apellido ?? "");
    setContribNombre(resolvedRow.contrib_nombre ?? "");
    setRazonSocial(resolvedRow.razon_social ?? "");
    setTitularModo(titularModoInicialDesdeRow(resolvedRow));
    setNombreLocal(resolvedRow.nombre_local ?? "");
    setActaInspeccion(resolvedRow.acta_inspeccion_num ?? "");
    setActaNotificacion(resolvedRow.acta_notificacion_num ?? "");
    setNotifM1(resolvedRow.notificacion_motivo_1 ?? "");
    setNotifM2(resolvedRow.notificacion_motivo_2 ?? "");
    setNotifM3(resolvedRow.notificacion_motivo_3 ?? "");
    setActaComprobacion(resolvedRow.acta_comprobacion_num ?? "");
    setComprobacionMotivo(resolvedRow.comprobacion_motivo ?? "");
    setActaClausura(resolvedRow.acta_clausura_num ?? "");
    setActaDecomiso(resolvedRow.acta_decomiso_num ?? "");
    const k = resolvedRow.decomiso_kilos_total;
    setDecomisoKilos(k == null ? "" : String(k));
  }, [open, resolvedRow, inspectoresGrupo]);

  const fe = useCallback((apiField: string) => fieldErrors[apiField], [fieldErrors]);
  const clearFe = useCallback((apiField: string) => {
    setFieldErrors((prev) => {
      if (!(apiField in prev)) return prev;
      const next = { ...prev };
      delete next[apiField];
      return next;
    });
  }, []);

  const contraHint = useMemo(() => getContraproducenciaUxHint(contraproducencia), [contraproducencia]);
  const visitaRealizada = !contraproducencia.trim();
  const esNoPermiteInspeccion = esNoPermiteInspeccionContraproducencia(contraproducencia);
  const esReinspeccionOficio = resolvedRow?.tipo_iniciador === "REINSPECCION_OFICIO";

  /** Inspectores del catálogo que aún no están en la lista (agregar). */
  const inspectoresDisponiblesParaAgregar = useMemo(() => {
    const catalog = cat.inspectores ?? [];
    const ya = new Set(inspectoresList.map((x) => x.trim()).filter(Boolean));
    return [...catalog].filter((n) => !ya.has(n)).sort((a, b) => a.localeCompare(b, "es", { sensitivity: "base" }));
  }, [cat.inspectores, inspectoresList]);

  /** Rubro actual siempre en opciones aunque el catálogo aún no incluya ese string (merge con DB). */
  const rubroSelectOptions = useMemo(
    () => mergeCatalogOpts(cat.rubros ?? [], rubroNombre),
    [cat.rubros, rubroNombre]
  );

  const handleTitularModoChange = useCallback(
    (_: MouseEvent<HTMLElement>, next: TitularModoCompletarTrabajo | null) => {
      if (next == null || next === titularModo) return;
      if (next === "razon_social") {
        setContribApellido("");
        setContribNombre("");
      } else {
        setRazonSocial("");
      }
      setTitularModo(next);
      ["contrib_apellido", "contrib_nombre", "razon_social"].forEach((k) => clearFe(k));
    },
    [titularModo, clearFe]
  );

  const contraOpts = useMemo(
    () => [
      { value: "", label: "Sin contraproducencia (visita realizada)" },
      ...mergeCatalogOpts(cat.contraproducencias, resolvedRow?.contraproducencia).filter((o) => o.value !== ""),
    ],
    [cat.contraproducencias, resolvedRow?.contraproducencia]
  );
  const motivoNotifOpts = useMemo(() => mergeCatalogOpts(cat.motivos, undefined), [cat.motivos]);
  const motivoCompOpts = useMemo(
    () => mergeCatalogOpts(cat.motivosComprobacion, undefined),
    [cat.motivosComprobacion]
  );

  const handleClose = useCallback(() => {
    if (saving) return;
    onClose();
  }, [saving, onClose]);

  const handleSubmit = async () => {
    if (!resolvedRow) return;
    setFieldErrors({});
    setError(null);

    if (resolvedRow.tipo_iniciador === "REINSPECCION_OFICIO") {
      const preSubmitErrors: Record<string, string> = {};
      if (
        !tipoActuacionOficio.trim() ||
        !(TIPO_ACTUACION_REINSPECCION_OFICIO as readonly string[]).includes(tipoActuacionOficio)
      ) {
        preSubmitErrors.tipo_actuacion = "Elegí el tipo de actuación.";
      }
      if (!resultadoCumplimientoOficio || !["CUMPLE", "NO_CUMPLE"].includes(resultadoCumplimientoOficio)) {
        preSubmitErrors.resultado_cumplimiento_oficio = "Seleccioná si dio cumplimiento o no.";
      }
      if (Object.keys(preSubmitErrors).length > 0) {
        setFieldErrors(preSubmitErrors);
        setError(COMPLETAR_TRABAJO_FIELD_ERROR_SUMMARY);
        return;
      }
      setSaving(true);
      try {
        const values: Record<string, unknown> = {
          contraproducencia: "",
          tipo_actuacion: tipoActuacionOficio,
          resultado_cumplimiento_oficio: resultadoCumplimientoOficio,
          observaciones_ejecucion: observacionesEjecucion.trim(),
          ...ACTA_KEYS_EMPTY,
        };
        const base = baselineInspectoresRef.current;
        const inspectoresDirty = !sameInspectoresListOrder(inspectoresList, base);
        await submitCompletarTrabajoCierreFromRow(resolvedRow, values, {
          includeTipoActuacion: true,
          omitPrecargadoPr2: false,
          ...(inspectoresDirty
            ? { inspectoresExplicitos: dedupeInspectoresPreserveOrder(inspectoresList) }
            : {}),
        });
        onSuccess(resolvedRow.ruta_item_id);
        onClose();
      } catch (e) {
        const { fieldErrors: nextFe, generalMessage } = applyCompletarTrabajoFieldErrorsFromApi(e);
        setFieldErrors(nextFe);
        setError(generalMessage);
      } finally {
        setSaving(false);
      }
      return;
    }

    const preSubmitErrors: Record<string, string> = {};
    if (visitaRealizada && actaComprobacion.trim() && !comprobacionMotivo.trim()) {
      preSubmitErrors.comprobacion_motivo =
        "Si cargás acta de comprobación, elegí un motivo de comprobación.";
    }
    if (esNoPermiteInspeccion) {
      if (!actaComprobacion.trim()) {
        preSubmitErrors.acta_comprobacion_num = "Con esta contraproducencia el acta de comprobación es obligatoria.";
      }
      if (!comprobacionMotivo.trim()) {
        preSubmitErrors.comprobacion_motivo = "Con esta contraproducencia el motivo de comprobación es obligatorio.";
      }
    }
    if (
      visitaRealizada &&
      actaNotificacion.trim() &&
      ![notifM1, notifM2, notifM3].some((x) => x.trim())
    ) {
      preSubmitErrors.notificacion_motivo_1 = "La notificación requiere al menos un motivo.";
    }
    if (Object.keys(preSubmitErrors).length > 0) {
      setFieldErrors(preSubmitErrors);
      setError(COMPLETAR_TRABAJO_FIELD_ERROR_SUMMARY);
      return;
    }
    setSaving(true);
    try {
      const titularPayload: Record<string, unknown> =
        titularModo === "persona"
          ? {
              contrib_apellido: contribApellido,
              contrib_nombre: contribNombre,
              razon_social: null,
            }
          : {
              contrib_apellido: null,
              contrib_nombre: null,
              razon_social: razonSocial,
            };

      const values: Record<string, unknown> = {
        contraproducencia,
        rubro_nombre: rubroNombre,
        calle,
        numero,
        doc_nro: docNro,
        ...titularPayload,
        nombre_local: nombreLocal,
        observaciones_ejecucion: observacionesEjecucion.trim(),
        ...ACTA_KEYS_EMPTY,
      };

      if (visitaRealizada) {
        Object.assign(values, {
          acta_inspeccion_num: actaInspeccion,
          acta_notificacion_num: actaNotificacion,
          notificacion_motivo_1: notifM1,
          notificacion_motivo_2: notifM2,
          notificacion_motivo_3: notifM3,
          acta_comprobacion_num: actaComprobacion,
          comprobacion_motivo: comprobacionMotivo,
          acta_clausura_num: actaClausura,
          acta_decomiso_num: actaDecomiso,
          decomiso_kilos_total: decomisoKilos,
        });
      } else if (esNoPermiteInspeccion) {
        Object.assign(values, {
          acta_comprobacion_num: actaComprobacion,
          comprobacion_motivo: comprobacionMotivo,
          acta_clausura_num: actaClausura,
        });
      }

      const base = baselineInspectoresRef.current;
      const inspectoresDirty = !sameInspectoresListOrder(inspectoresList, base);
      await submitCompletarTrabajoCierreFromRow(resolvedRow, values, {
        omitPrecargadoPr2: true,
        ...(inspectoresDirty
          ? { inspectoresExplicitos: dedupeInspectoresPreserveOrder(inspectoresList) }
          : {}),
      });
      onSuccess(resolvedRow.ruta_item_id);
      onClose();
    } catch (e) {
      const { fieldErrors: nextFe, generalMessage } = applyCompletarTrabajoFieldErrorsFromApi(e);
      setFieldErrors(nextFe);
      setError(generalMessage);
    } finally {
      setSaving(false);
    }
  };

  const col = { display: "flex", flexDirection: "column" as const, gap: 1.5 };
  const labelMuted = { color: "rgba(255,255,255,0.5)", fontFamily: '"Tactic Sans", sans-serif' } as const;

  return (
    <AppDialog
      open={open && row != null}
      onClose={handleClose}
      onCloseButtonClick={handleClose}
      title="Completar trabajo"
      maxWidth="sm"
      fullWidth
      showCloseButton
      contentSx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}
      actions={
        <>
          <AppButton dsVariant="ghost" onClick={handleClose} disabled={saving}>
            Cancelar
          </AppButton>
          <AppButton
            dsVariant="primary"
            onClick={() => void handleSubmit()}
            disabled={saving || !resolvedRow || detalleLoading}
            loading={saving}
          >
            Guardar cierre
          </AppButton>
        </>
      }
    >
      {row && detalleLoading && !resolvedRow && (
        <Box sx={{ display: "flex", flexDirection: "column", alignItems: "stretch", gap: 2 }}>
          <LinearProgress sx={{ borderRadius: 1 }} />
          <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 1.5, py: 2 }}>
            <CircularProgress size={32} sx={{ color: "rgba(255,255,255,0.7)" }} />
            <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.55)", textAlign: "center" }}>
              Cargando detalle del trabajo…
            </Typography>
          </Box>
        </Box>
      )}

      {detalleError && resolvedRow && (
        <Alert severity="warning" sx={{ borderRadius: 2 }}>
          <Typography variant="body2" sx={{ mb: 0.5 }}>
            No se pudo cargar el detalle actualizado del servidor.
          </Typography>
          <Typography variant="body2" sx={{ whiteSpace: "pre-line", opacity: 0.95 }}>
            {detalleError}
          </Typography>
          <Typography variant="caption" sx={{ display: "block", mt: 1, opacity: 0.9 }}>
            Se muestran los datos del listado. Podés intentar cerrar y volver a abrir, o continuar si coinciden con lo
            que ves en terreno.
          </Typography>
        </Alert>
      )}

      {resolvedRow && (
        <Box
          sx={{
            ...col,
            p: 1.5,
            borderRadius: 2,
            bgcolor: "rgba(255,255,255,0.06)",
            fontFamily: '"Tactic Sans", sans-serif',
          }}
        >
          <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.5)", textTransform: "uppercase" }}>
            Solo lectura
          </Typography>
          <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.75)" }}>
            Fecha: {dashIfEmpty(resolvedRow.fecha_actuacion)}
          </Typography>
          <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.75)" }}>
            Tipo de iniciador: {dashIfEmpty(resolvedRow.tipo_iniciador)}
          </Typography>
          {resolvedRow.grupo_nombre?.trim() ? (
            <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.75)" }}>
              Grupo: {resolvedRow.grupo_nombre}
            </Typography>
          ) : null}
          <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.85)" }}>
            OT {resolvedRow.orden_trabajo_numero ?? "—"}
          </Typography>
          {tipoActuacionEsperadoRef?.trim() ? (
            <Box>
              <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.45)", display: "block" }}>
                Tipo de actuación esperado (referencia catálogo)
              </Typography>
              <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.8)" }}>
                {tipoActuacionEsperadoRef}
              </Typography>
            </Box>
          ) : null}
          <Box>
            <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.45)", display: "block" }}>
              Domicilio actual
            </Typography>
            <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.75)" }}>
              {domicilioResumen(resolvedRow)}
            </Typography>
          </Box>
        </Box>
      )}

      {resolvedRow && !detalleLoading && (
        <Box sx={{ ...col, width: "100%" }}>
          <Typography variant="caption" sx={{ ...labelMuted, display: "block" }}>
            Inspectores
          </Typography>
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, alignItems: "center" }}>
            {inspectoresList.length === 0 ? (
              <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.45)" }}>
                —
              </Typography>
            ) : (
              inspectoresList.map((name, idx) => (
                <Chip
                  key={`${idx}-${name}`}
                  label={name}
                  size="small"
                  onDelete={() => {
                    setInspectoresList((prev) => prev.filter((_, i) => i !== idx));
                    clearFe("inspectores");
                  }}
                  sx={{ bgcolor: "rgba(255,255,255,0.12)", color: "rgba(255,255,255,0.92)" }}
                />
              ))
            )}
          </Box>
          <Autocomplete
            size="small"
            options={inspectoresDisponiblesParaAgregar}
            value={null}
            onChange={(_, value) => {
              if (value && !inspectoresList.includes(value)) {
                setInspectoresList((prev) => [...prev, value]);
                clearFe("inspectores");
              }
            }}
            disabled={!catalogsReady || inspectoresDisponiblesParaAgregar.length === 0}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Agregar"
                placeholder={catalogsReady ? "Catálogo" : "…"}
                error={Boolean(fe("inspectores"))}
                helperText={fe("inspectores") || undefined}
              />
            )}
          />
        </Box>
      )}

      {resolvedRow && error && (
        <Alert severity="error" sx={{ borderRadius: 2, whiteSpace: "pre-line" }}>
          {error}
        </Alert>
      )}

      {resolvedRow && esReinspeccionOficio && (
        <Box sx={col}>
          <AppSelect
            label="Tipo de actuación"
            value={tipoActuacionOficio}
            onChange={(e) => {
              setTipoActuacionOficio(e.target.value as string);
              clearFe("tipo_actuacion");
            }}
            fullWidth
            options={TIPO_ACTUACION_REINSPECCION_OFICIO_OPTS}
            error={Boolean(fe("tipo_actuacion"))}
            helperText={fe("tipo_actuacion") || "Obligatorio."}
          />
          <AppSelect
            label="Dio cumplimiento"
            value={resultadoCumplimientoOficio}
            onChange={(e) => {
              setResultadoCumplimientoOficio(e.target.value as string);
              clearFe("resultado_cumplimiento_oficio");
            }}
            fullWidth
            options={CUMPLE_OPTS}
            error={Boolean(fe("resultado_cumplimiento_oficio"))}
            helperText={
              fe("resultado_cumplimiento_oficio") || "Seleccioná si dio cumplimiento o no."
            }
          />
          <AppTextField
            appearance="dense"
            label="Observaciones de ejecución (opcional)"
            value={observacionesEjecucion}
            onChange={(e) => {
              setObservacionesEjecucion(e.target.value);
              clearFe("observaciones_ejecucion");
            }}
            fullWidth
            multiline
            minRows={2}
            inputProps={{ maxLength: 4000 }}
            error={Boolean(fe("observaciones_ejecucion"))}
            helperText={fe("observaciones_ejecucion") || undefined}
          />
        </Box>
      )}

      {resolvedRow && !esReinspeccionOficio && (
        <>
      <Box sx={col}>
        <AppSelect
          label="Contraproducencia"
          value={contraproducencia}
          onChange={(e) => {
            setContraproducencia(e.target.value as string);
            clearFe("contraproducencia");
          }}
          fullWidth
          disabled={!catalogsReady}
          options={contraOpts}
          error={Boolean(fe("contraproducencia"))}
          helperText={fe("contraproducencia") || undefined}
        />
        {contraHint === "cierra_sin_reingreso" && (
          <Alert severity="warning" sx={{ borderRadius: 2 }}>
            <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
              Cierre del caso en esta cola
            </Typography>
            <Typography variant="body2" sx={{ mb: 0.5 }}>
              Este motivo <strong>cierra el iniciador</strong>: no vuelve a pendientes ni se reagenda desde Completar
              trabajo.
            </Typography>
            <Typography variant="caption" sx={{ display: "block", opacity: 0.92 }}>
              No se registran actas del día en este cierre.
            </Typography>
          </Alert>
        )}
        {contraHint === "reingreso_prioridad_alta" && (
          <Alert severity="info" sx={{ borderRadius: 2 }}>
            <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
              Reingreso a pendientes
            </Typography>
            <Typography variant="body2" sx={{ mb: 0.5 }}>
              En este cierre <strong>no se cargan actas</strong> del día: solo la contraproducencia y, si los ajustás,
              domicilio y titular.
            </Typography>
            <Typography variant="body2">
              El trabajo vuelve a <strong>pendientes</strong> con prioridad alta para una nueva visita.
            </Typography>
          </Alert>
        )}
        {contraHint === "no_permite_inspeccion" && (
          <Alert severity="warning" sx={{ borderRadius: 2 }}>
            <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
              Cierre por negativa a la inspección
            </Typography>
            <List dense disablePadding sx={{ listStyleType: "disc", pl: 2.25, "& .MuiListItem-root": { display: "list-item", py: 0 } }}>
              <ListItem disableGutters>
                <ListItemText primary="Acta de comprobación: obligatoria" />
              </ListItem>
              <ListItem disableGutters>
                <ListItemText primary="Motivo de comprobación: obligatorio" />
              </ListItem>
              <ListItem disableGutters>
                <ListItemText primary="Acta de clausura: opcional" />
              </ListItem>
            </List>
            <Typography variant="caption" sx={{ display: "block", opacity: 0.9, mt: 0.5 }}>
              El trabajo vuelve a pendientes con prioridad alta.
            </Typography>
          </Alert>
        )}

        {visitaRealizada && (
          <Alert severity="info" sx={{ borderRadius: 2 }}>
            <Typography variant="body2">
              Con visita realizada, revisá calle, rubro y titular: datos correctos ayudan a vincular la actuación con la{" "}
              <strong>ficha operativa</strong> al guardar.
            </Typography>
          </Alert>
        )}

        <Typography variant="caption" sx={labelMuted}>
          Domicilio
        </Typography>
        <AppTextField
          appearance="dense"
          label="Calle"
          value={calle}
          onChange={(e) => {
            setCalle(e.target.value);
            clearFe("calle");
          }}
          fullWidth
          error={Boolean(fe("calle"))}
          helperText={fe("calle") || undefined}
        />
        <AppTextField
          appearance="dense"
          label="Número"
          value={numero}
          onChange={(e) => {
            setNumero(e.target.value);
            clearFe("numero");
          }}
          fullWidth
          error={Boolean(fe("numero"))}
          helperText={fe("numero") || undefined}
        />

        <AppSelect
          appearance="dense"
          label="Rubro"
          value={rubroNombre}
          onChange={(e) => {
            setRubroNombre(e.target.value as string);
            clearFe("rubro_nombre");
          }}
          fullWidth
          disabled={!catalogsReady}
          options={rubroSelectOptions}
          error={Boolean(fe("rubro_nombre"))}
          helperText={fe("rubro_nombre") || undefined}
        />

        <Typography variant="caption" sx={labelMuted}>
          Titular
        </Typography>
        <ToggleButtonGroup
          exclusive
          value={titularModo}
          onChange={handleTitularModoChange}
          size="small"
          fullWidth
          sx={{
            "& .MuiToggleButton-root": {
              flex: 1,
              textTransform: "none",
              fontFamily: '"Tactic Sans", sans-serif',
              fontSize: "0.8125rem",
              color: "rgba(255,255,255,0.75)",
              borderColor: "rgba(255,255,255,0.2)",
            },
            "& .Mui-selected": {
              bgcolor: "rgba(255,255,255,0.12) !important",
              color: "rgba(255,255,255,0.95) !important",
            },
          }}
        >
          <ToggleButton value="persona">Contribuyente</ToggleButton>
          <ToggleButton value="razon_social">Razón social</ToggleButton>
        </ToggleButtonGroup>

        {titularModo === "persona" ? (
          <>
            <AppTextField
              appearance="dense"
              label="Apellido"
              value={contribApellido}
              onChange={(e) => {
                setContribApellido(e.target.value);
                clearFe("contrib_apellido");
              }}
              fullWidth
              error={Boolean(fe("contrib_apellido"))}
              helperText={fe("contrib_apellido") || undefined}
            />
            <AppTextField
              appearance="dense"
              label="Nombre"
              value={contribNombre}
              onChange={(e) => {
                setContribNombre(e.target.value);
                clearFe("contrib_nombre");
              }}
              fullWidth
              error={Boolean(fe("contrib_nombre"))}
              helperText={fe("contrib_nombre") || undefined}
            />
          </>
        ) : (
          <AppTextField
            appearance="dense"
            label="Razón social"
            value={razonSocial}
            onChange={(e) => {
              setRazonSocial(e.target.value);
              clearFe("razon_social");
            }}
            fullWidth
            error={Boolean(fe("razon_social"))}
            helperText={fe("razon_social") || undefined}
          />
        )}

        <AppTextField
          appearance="dense"
          label="CUIT / DNI"
          value={docNro}
          onChange={(e) => {
            setDocNro(e.target.value);
            clearFe("doc_nro");
          }}
          fullWidth
          error={Boolean(fe("doc_nro"))}
          helperText={fe("doc_nro") || undefined}
        />
        <AppTextField
          appearance="dense"
          label="Nombre del local"
          value={nombreLocal}
          onChange={(e) => {
            setNombreLocal(e.target.value);
            clearFe("nombre_local");
          }}
          fullWidth
          inputProps={{ maxLength: 255 }}
          error={Boolean(fe("nombre_local"))}
          helperText={fe("nombre_local") || undefined}
        />
      </Box>

      {(visitaRealizada || esNoPermiteInspeccion) && (
        <Box sx={{ ...col, pt: 0.5 }}>
          {esNoPermiteInspeccion && !visitaRealizada && (
            <Typography variant="subtitle2" sx={{ color: "rgba(255,255,255,0.85)", letterSpacing: 0.2 }}>
              Actas para este cierre
            </Typography>
          )}
          {visitaRealizada && (
            <>
              <AppTextField
                appearance="dense"
                label="N° acta de inspección"
                value={actaInspeccion}
                onChange={(e) => {
                  setActaInspeccion(e.target.value);
                  clearFe("acta_inspeccion_num");
                }}
                fullWidth
                error={Boolean(fe("acta_inspeccion_num"))}
                helperText={fe("acta_inspeccion_num") || undefined}
              />
              <AppTextField
                appearance="dense"
                label="N° acta de notificación"
                value={actaNotificacion}
                onChange={(e) => {
                  setActaNotificacion(e.target.value);
                  clearFe("acta_notificacion_num");
                }}
                fullWidth
                error={Boolean(fe("acta_notificacion_num"))}
                helperText={fe("acta_notificacion_num") || undefined}
              />
              <AppSelect
                label="Motivo notificación 1"
                value={notifM1}
                onChange={(e) => {
                  setNotifM1(e.target.value);
                  clearFe("notificacion_motivo_1");
                }}
                fullWidth
                disabled={!catalogsReady}
                options={motivoNotifOpts}
                error={Boolean(fe("notificacion_motivo_1"))}
                helperText={fe("notificacion_motivo_1") || undefined}
              />
              <AppSelect
                label="Motivo notificación 2"
                value={notifM2}
                onChange={(e) => {
                  setNotifM2(e.target.value);
                  clearFe("notificacion_motivo_2");
                }}
                fullWidth
                disabled={!catalogsReady}
                options={motivoNotifOpts}
                error={Boolean(fe("notificacion_motivo_2"))}
                helperText={fe("notificacion_motivo_2") || undefined}
              />
              <AppSelect
                label="Motivo notificación 3"
                value={notifM3}
                onChange={(e) => {
                  setNotifM3(e.target.value);
                  clearFe("notificacion_motivo_3");
                }}
                fullWidth
                disabled={!catalogsReady}
                options={motivoNotifOpts}
                error={Boolean(fe("notificacion_motivo_3"))}
                helperText={fe("notificacion_motivo_3") || undefined}
              />
            </>
          )}
          <AppTextField
            appearance="dense"
            label={
              esNoPermiteInspeccion && !visitaRealizada
                ? "N° acta de comprobación (obligatorio)"
                : "N° acta de comprobación"
            }
            value={actaComprobacion}
            onChange={(e) => {
              setActaComprobacion(e.target.value);
              clearFe("acta_comprobacion_num");
            }}
            fullWidth
            required={esNoPermiteInspeccion && !visitaRealizada}
            error={Boolean(fe("acta_comprobacion_num"))}
            helperText={
              fe("acta_comprobacion_num") ||
              (esNoPermiteInspeccion && !visitaRealizada ? "Obligatorio para esta contraproducencia." : undefined)
            }
          />
          <AppSelect
            label={
              esNoPermiteInspeccion && !visitaRealizada
                ? "Motivo de comprobación (obligatorio)"
                : "Motivo de comprobación"
            }
            value={comprobacionMotivo}
            onChange={(e) => {
              setComprobacionMotivo(e.target.value);
              clearFe("comprobacion_motivo");
            }}
            fullWidth
            disabled={!catalogsReady}
            options={motivoCompOpts}
            required={esNoPermiteInspeccion && !visitaRealizada}
            error={Boolean(fe("comprobacion_motivo"))}
            helperText={
              fe("comprobacion_motivo") ||
              (esNoPermiteInspeccion && !visitaRealizada ? "Obligatorio para esta contraproducencia." : undefined)
            }
          />
          <AppTextField
            appearance="dense"
            label="N° acta de clausura (opcional)"
            value={actaClausura}
            onChange={(e) => {
              setActaClausura(e.target.value);
              clearFe("acta_clausura_num");
            }}
            fullWidth
            error={Boolean(fe("acta_clausura_num"))}
            helperText={fe("acta_clausura_num") || undefined}
          />
          {visitaRealizada && (
            <>
              <AppTextField
                appearance="dense"
                label="N° acta de decomiso"
                value={actaDecomiso}
                onChange={(e) => {
                  setActaDecomiso(e.target.value);
                  clearFe("acta_decomiso_num");
                }}
                fullWidth
                error={Boolean(fe("acta_decomiso_num"))}
                helperText={fe("acta_decomiso_num") || undefined}
              />
              <AppTextField
                appearance="dense"
                label="Kilos decomisados"
                value={decomisoKilos}
                onChange={(e) => {
                  setDecomisoKilos(e.target.value);
                  clearFe("decomiso_kilos_total");
                }}
                fullWidth
                error={Boolean(fe("decomiso_kilos_total"))}
                helperText={fe("decomiso_kilos_total") || undefined}
              />
            </>
          )}
        </Box>
      )}
          <AppTextField
            appearance="dense"
            label="Observaciones de ejecución (opcional)"
            value={observacionesEjecucion}
            onChange={(e) => {
              setObservacionesEjecucion(e.target.value);
              clearFe("observaciones_ejecucion");
            }}
            fullWidth
            multiline
            minRows={2}
            inputProps={{ maxLength: 4000 }}
            error={Boolean(fe("observaciones_ejecucion"))}
            helperText={fe("observaciones_ejecucion") || undefined}
          />
        </>
      )}
    </AppDialog>
  );
}
