import { useCallback, useEffect, useMemo, useRef, useState, type MouseEvent, type ReactNode } from "react";
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
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";

import type { ICompletarTrabajoInspectorGrupo, ICompletarTrabajoPendienteRow } from "../../../api/completarTrabajoApi";
import { getCompletarTrabajoDetalle } from "../../../api/completarTrabajoApi";
import { formatActuacionListDomicilioLinea } from "../../../utils/formatDomicilioLineaVisible";
import {
  CrudDialogActions,
  CrudDialogHeader,
  CrudDialogSection,
  CrudGlassDialog,
  useCrudDialogScrollContainer,
} from "../../../components/crudDialog";
import {
  DOC_MODAL_BLOCK_STACK_SPACING,
  DOC_MODAL_TEXT,
  documentalGlassWarningAlertSx,
} from "../../../styles/documentalModalTokens";
import { AppSelect, AppTextField } from "../../../ui";
import { useAppFeedback } from "../../../components/feedback";
import { ActaNumFieldLazy } from "../../Actuaciones/Components/ActaNumFieldLazy";
import { NumeroEsquinaFreeEditor } from "../../Actuaciones/Components/NumeroEsquinaFreeEditor";
import {
  MENSAJE_VALIDACION_LOCAL,
  notifyActuacionFormValidationResult,
} from "../../Actuaciones/utils/actuacionSaveFeedback";
import { scrollActuacionFormToFirstFieldError } from "../../Actuaciones/utils/actuacionFormScroll";
import { commitActaNumInputValue } from "../../Actuaciones/validations/actuacionFormNormalize";
import { submitCompletarTrabajoCierreFromRow } from "../completion/submitCompletarTrabajoCierre";
import { emitGestionNotificacionReinspeccionRefresh } from "../../GestionNotificacion/gestionNotificacionReinspeccionRefresh";
import type { CompletarTrabajoCatalogs } from "../hooks/completarTrabajoCatalogsCache";
import {
  completarTrabajoHeaderSubtitulo,
  completarTrabajoHeaderTitulo,
  completarTrabajoShowDomicilioEnDetalle,
} from "../utils/completarTrabajoModalDisplay";
import { prefillOperativoReinspeccionNotificacion } from "../utils/completarTrabajoReinspeccionNotificacionPrefill";
import { operativoHydrationFromRow } from "../utils/completarTrabajoVerificarInformarPrefill";
import { domicilioRowParaHidratacionCompletarTrabajo } from "../../../utils/domicilioCalleUi";
import { showContribuyenteDomicilioEditableEnCompletarTrabajo } from "../utils/completarTrabajoReinspeccionNotificacionUi";
import {
  OFICIO_CUMPLE_OPTS,
  TIPO_ACTUACION_REINSPECCION_OFICIO,
  tipoActuacionInicialReinspeccionOficio,
  tipoActuacionReinspeccionOficioOpts,
} from "../utils/completarTrabajoReinspeccionOficioUi";
import { esNoPermiteInspeccionContraproducencia } from "../utils/completarTrabajoContraproducencia";
import {
  actuacionCompletarTrabajoValidationContext,
  validateActuacionFormForSubmit,
} from "../../Actuaciones/validations/actuacionFormValidation";
import { filtrarContraproducenciasPorTipoIniciador } from "../utils/contraproducenciasPorTipoIniciador";
import {
  esFlujoCierreOficio,
  esFlujoCumplimientoRatificacion,
  esFlujoVerificarInformar,
  esRatificacionOficio,
  esReinspeccionOficioGenerico,
  esTipoActuacionVerificarInformar,
  esVerificarInformarOficio,
  REALIZO_NUEVA_INSPECCION_OPTS,
  TIPO_ACTUACION_VERIFICAR_INFORMAR,
  tipoActuacionEfectivoOficio,
  tipoActuacionFijoDesdeIniciadorOficio,
} from "../utils/completarTrabajoTipoIniciadorUi";
import { getContraproducenciaUxHint } from "../utils/contraproducenciaUxHint";
import {
  applyCompletarTrabajoFieldErrorsFromApi,
  formatCompletarTrabajoApiError,
} from "../utils/completarTrabajoErrors";
import {
  MOTIVOS_NOTIFICACION_MAX,
  mergeMotivosNotifCatalogStrings,
  motivosNotificacionFromSlots,
  slotsToMotivosApi,
} from "../../../utils/motivosNotificacionSlots";

const modalAuxInputSx = {
  "& .MuiInputBase-input": { color: DOC_MODAL_TEXT },
  "& .MuiInputLabel-root": { color: "rgba(255,255,255,0.92)" },
  "& .MuiOutlinedInput-notchedOutline": { borderColor: "rgba(255,255,255,0.38)" },
  "& .MuiFormHelperText-root": { color: "rgba(255,255,255,0.88)" },
} as const;

const edicionGrid2ColSx = {
  display: "grid",
  gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)" },
  gap: 2,
  width: "100%",
  alignItems: "end",
} as const;

function CompletarBloque({ title, children }: { title: string; children: ReactNode }) {
  return (
    <CrudDialogSection title={title} variant="plain">
      {children}
    </CrudDialogSection>
  );
}

function actaNumForPayload(value: string): string {
  return commitActaNumInputValue(value) ?? "";
}

function buildCompletarTrabajoValidationForm(
  resolvedRow: ICompletarTrabajoPendienteRow,
  params: {
    contraproducencia: string;
    calle: string;
    numero: string;
    rubroNombre: string;
    docNro: string;
    contribApellido: string;
    contribNombre: string;
    razonSocial: string;
    titularModo: TitularModoCompletarTrabajo;
    nombreLocal: string;
    actaInspeccion: string;
    actaNotificacion: string;
    notifMotivosSeleccion: string[];
    actaComprobacion: string;
    comprobacionMotivo: string;
    actaClausura: string;
    actaDecomiso: string;
    decomisoKilos: string;
    inspectoresList: string[];
  }
) {
  const notifSlotsPre = slotsToMotivosApi(params.notifMotivosSeleccion);
  const titular =
    params.titularModo === "persona"
      ? {
          contrib_apellido: params.contribApellido,
          contrib_nombre: params.contribNombre,
          razon_social: null as string | null,
        }
      : {
          contrib_apellido: null as string | null,
          contrib_nombre: null as string | null,
          razon_social: params.razonSocial,
        };

  return {
    contraproducencia: params.contraproducencia,
    calle: params.calle,
    numero: params.numero,
    rubro_nombre: params.rubroNombre,
    doc_nro: params.docNro,
    ...titular,
    nombre_local: params.nombreLocal,
    fecha_actuacion: resolvedRow.fecha_actuacion,
    tipo_actuacion: resolvedRow.tipo_actuacion,
    acta_inspeccion_num: params.actaInspeccion,
    acta_comprobacion_num: params.actaComprobacion,
    comprobacion_motivo: params.comprobacionMotivo,
    acta_notificacion_num: params.actaNotificacion,
    notificacion_motivo_1: notifSlotsPre.m1,
    notificacion_motivo_2: notifSlotsPre.m2,
    notificacion_motivo_3: notifSlotsPre.m3,
    acta_clausura_num: params.actaClausura,
    acta_decomiso_num: params.actaDecomiso,
    decomiso_kilos_total:
      params.decomisoKilos === "" ? null : Number(params.decomisoKilos),
    inspector1: params.inspectoresList[0] ?? null,
    inspector2: params.inspectoresList[1] ?? null,
    inspector3: params.inspectoresList[2] ?? null,
    inspectores: params.inspectoresList,
  };
}

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

function domicilioCamposDesdeRow(row: ICompletarTrabajoPendienteRow): {
  calle: string;
  numero: string;
  numeroTipo: "NUMERO" | "ESQUINA";
} {
  const h = domicilioRowParaHidratacionCompletarTrabajo(row);
  return {
    calle: h.calle ?? "",
    numero: h.numero ?? "",
    numeroTipo: h.numero_tipo === "ESQUINA" ? "ESQUINA" : "NUMERO",
  };
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

/** Titular del domicilio: persona física (apellido + nombre) o razón social (PJ). */
type TitularModoCompletarTrabajo = "persona" | "razon_social";

const TIPO_ACTUACION_REINSPECCION_OFICIO_OPTS = tipoActuacionReinspeccionOficioOpts();

function titularModoInicialDesdeRow(r: ICompletarTrabajoPendienteRow): TitularModoCompletarTrabajo {
  const rs = (r.razon_social ?? "").trim();
  return rs ? "razon_social" : "persona";
}

type OperativoFieldSetters = {
  setCalle: (v: string) => void;
  setNumero: (v: string) => void;
  setNumeroTipo: (v: "NUMERO" | "ESQUINA") => void;
  setRubroNombre: (v: string) => void;
  setDocNro: (v: string) => void;
  setContribApellido: (v: string) => void;
  setContribNombre: (v: string) => void;
  setRazonSocial: (v: string) => void;
  setTitularModo: (v: TitularModoCompletarTrabajo) => void;
  setNombreLocal: (v: string) => void;
  setActaInspeccion: (v: string) => void;
  setActaNotificacion: (v: string) => void;
  setNotifMotivosSeleccion: (v: string[]) => void;
  setActaComprobacion: (v: string) => void;
  setComprobacionMotivo: (v: string) => void;
  setActaClausura: (v: string) => void;
  setActaDecomiso: (v: string) => void;
  setDecomisoKilos: (v: string) => void;
};

function hydrateOperativoFieldsFromRow(row: ICompletarTrabajoPendienteRow, set: OperativoFieldSetters): void {
  const h = operativoHydrationFromRow(row);
  set.setCalle(h.calle);
  set.setNumero(h.numero);
  set.setNumeroTipo(h.numeroTipo);
  set.setRubroNombre(h.rubroNombre);
  set.setDocNro(h.docNro);
  set.setContribApellido(h.contribApellido);
  set.setContribNombre(h.contribNombre);
  set.setRazonSocial(h.razonSocial);
  set.setTitularModo(titularModoInicialDesdeRow(row));
  set.setNombreLocal(h.nombreLocal);
  set.setActaInspeccion(h.actaInspeccion);
  set.setActaNotificacion(h.actaNotificacion);
  set.setNotifMotivosSeleccion(h.notifMotivosSeleccion);
  set.setActaComprobacion(h.actaComprobacion);
  set.setComprobacionMotivo(h.comprobacionMotivo);
  set.setActaClausura(h.actaClausura);
  set.setActaDecomiso(h.actaDecomiso);
  set.setDecomisoKilos(h.decomisoKilos);
}

function clearOperativoFields(set: OperativoFieldSetters): void {
  set.setCalle("");
  set.setNumero("");
  set.setNumeroTipo("NUMERO");
  set.setRubroNombre("");
  set.setDocNro("");
  set.setContribApellido("");
  set.setContribNombre("");
  set.setRazonSocial("");
  set.setTitularModo("persona");
  set.setNombreLocal("");
  set.setActaInspeccion("");
  set.setActaNotificacion("");
  set.setNotifMotivosSeleccion([]);
  set.setActaComprobacion("");
  set.setComprobacionMotivo("");
  set.setActaClausura("");
  set.setActaDecomiso("");
  set.setDecomisoKilos("");
}

export type CompletarTrabajoModalProps = {
  open: boolean;
  /** Fila del listado al abrir; el modal refresca con GET detalle antes de editar. */
  row: ICompletarTrabajoPendienteRow | null;
  catalogs: CompletarTrabajoCatalogs | null;
  catalogsReady: boolean;
  onClose: () => void;
  onSuccess: (rutaItemId: number) => void;
  /** SSR/tests: evita portal MUI para renderizar título y acciones en el markup. */
  disablePortal?: boolean;
};

/**
 * Cierre Completar trabajo: cabecera fija.
 * Al abrir, carga `GET /actuaciones/completar-trabajo/detalle/:ruta_item_id` para fila fresca,
 * inspectores del grupo y referencia de tipo; si falla, usa la fila del listado.
 * - `REINSPECCION_OFICIO` / ratificaciones promovidas: tipo (si aplica) + dio cumplimiento + observaciones.
 * - Resto: editables en orden cerrado, actas solo sin contraproducencia.
 */
export function CompletarTrabajoModal({
  open,
  row,
  catalogs,
  catalogsReady,
  onClose,
  onSuccess,
  disablePortal,
}: CompletarTrabajoModalProps) {
  const feedback = useAppFeedback();
  const scrollContainerRef = useCrudDialogScrollContainer();
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
  const [numeroTipo, setNumeroTipo] = useState<"NUMERO" | "ESQUINA">("NUMERO");
  const [rubroNombre, setRubroNombre] = useState("");
  const [docNro, setDocNro] = useState("");
  const [contribApellido, setContribApellido] = useState("");
  const [contribNombre, setContribNombre] = useState("");
  const [razonSocial, setRazonSocial] = useState("");
  const [titularModo, setTitularModo] = useState<TitularModoCompletarTrabajo>("persona");
  const [nombreLocal, setNombreLocal] = useState("");
  const [actaInspeccion, setActaInspeccion] = useState("");
  const [actaNotificacion, setActaNotificacion] = useState("");
  const [notifMotivosSeleccion, setNotifMotivosSeleccion] = useState<string[]>([]);
  const [actaComprobacion, setActaComprobacion] = useState("");
  const [comprobacionMotivo, setComprobacionMotivo] = useState("");
  const [actaClausura, setActaClausura] = useState("");
  const [actaDecomiso, setActaDecomiso] = useState("");
  const [decomisoKilos, setDecomisoKilos] = useState("");
  const [tipoActuacionOficio, setTipoActuacionOficio] = useState("");
  const [resultadoCumplimientoOficio, setResultadoCumplimientoOficio] = useState("");
  const [realizoNuevaInspeccion, setRealizoNuevaInspeccion] = useState("");
  const [observacionesEjecucion, setObservacionesEjecucion] = useState("");
  const [saving, setSaving] = useState(false);
  /** Claves alineadas al payload / errores 422 del backend (pydantic field names). */
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  /** Fila efectiva tras GET detalle (o fallback a `row` si el GET falla). */
  const [resolvedRow, setResolvedRow] = useState<ICompletarTrabajoPendienteRow | null>(null);
  const [detalleLoading, setDetalleLoading] = useState(false);
  const [detalleError, setDetalleError] = useState<string | null>(null);
  const [inspectoresGrupo, setInspectoresGrupo] = useState<ICompletarTrabajoInspectorGrupo[]>([]);
  const [tipoActuacionEsperadoRef, setTipoActuacionEsperadoRef] = useState<string | null>(null);

  const [inspectoresList, setInspectoresList] = useState<string[]>([]);
  /** Búsqueda en Autocompletes de agregar ítem; se limpia tras cada selección. */
  const [inspectoresAddInput, setInspectoresAddInput] = useState("");
  const [notifMotivosAddInput, setNotifMotivosAddInput] = useState("");
  const baselineInspectoresRef = useRef<string[]>([]);

  useEffect(() => {
    if (!open || Object.keys(fieldErrors).length === 0) return;
    scrollActuacionFormToFirstFieldError(scrollContainerRef?.current ?? null, fieldErrors);
  }, [open, fieldErrors, scrollContainerRef]);

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

    setFieldErrors({});
    const operativoSetters: OperativoFieldSetters = {
      setCalle,
      setNumero,
      setNumeroTipo,
      setRubroNombre,
      setDocNro,
      setContribApellido,
      setContribNombre,
      setRazonSocial,
      setTitularModo,
      setNombreLocal,
      setActaInspeccion,
      setActaNotificacion,
      setNotifMotivosSeleccion,
      setActaComprobacion,
      setComprobacionMotivo,
      setActaClausura,
      setActaDecomiso,
      setDecomisoKilos,
    };
    if (esFlujoCierreOficio(resolvedRow.tipo_iniciador)) {
      const fijo = tipoActuacionFijoDesdeIniciadorOficio(resolvedRow.tipo_iniciador);
      const fromRow = tipoActuacionInicialReinspeccionOficio(resolvedRow.tipo_actuacion);
      const fromEsperado = tipoActuacionInicialReinspeccionOficio(
        resolvedRow.tipo_actuacion_esperado ?? tipoActuacionEsperadoRef
      );
      const tipoIni = fijo || fromRow || fromEsperado;
      setTipoActuacionOficio(tipoIni);
      setResultadoCumplimientoOficio(resolvedRow.resultado_cumplimiento_oficio ?? "");
      setRealizoNuevaInspeccion("");
      setContraproducencia(resolvedRow.contraproducencia ?? "");
      setObservacionesEjecucion(resolvedRow.observaciones_ejecucion ?? "");
      setInspectoresAddInput("");
      setNotifMotivosAddInput("");
      if (esFlujoVerificarInformar(resolvedRow.tipo_iniciador, tipoIni)) {
        hydrateOperativoFieldsFromRow(resolvedRow, operativoSetters);
      } else {
        clearOperativoFields(operativoSetters);
      }
      return;
    }
    if (esVerificarInformarOficio(resolvedRow.tipo_iniciador)) {
      setTipoActuacionOficio(TIPO_ACTUACION_VERIFICAR_INFORMAR);
      setResultadoCumplimientoOficio("");
      setRealizoNuevaInspeccion("");
      setContraproducencia(resolvedRow.contraproducencia ?? "");
      setObservacionesEjecucion(resolvedRow.observaciones_ejecucion ?? "");
      hydrateOperativoFieldsFromRow(resolvedRow, operativoSetters);
      setInspectoresAddInput("");
      setNotifMotivosAddInput("");
      return;
    }
    if (resolvedRow.tipo_iniciador === "REINSPECCION_NOTIFICACION") {
      setResultadoCumplimientoOficio("");
      setContraproducencia(resolvedRow.contraproducencia ?? "");
      setObservacionesEjecucion(resolvedRow.observaciones_ejecucion ?? "");
      const pre = prefillOperativoReinspeccionNotificacion(resolvedRow);
      const dom = domicilioCamposDesdeRow(resolvedRow);
      setCalle(dom.calle);
      setNumero(dom.numero);
      setNumeroTipo(dom.numeroTipo);
      setRubroNombre(pre.rubroNombre);
      setDocNro(pre.docNro);
      setContribApellido(pre.contribApellido);
      setContribNombre(pre.contribNombre);
      setRazonSocial(pre.razonSocial);
      setTitularModo(titularModoInicialDesdeRow(resolvedRow));
      setNombreLocal(pre.nombreLocal);
      setActaInspeccion(pre.actaInspeccion);
      setActaNotificacion(pre.actaNotificacion);
      setNotifMotivosSeleccion(pre.notifMotivosSeleccion);
      setActaComprobacion(pre.actaComprobacion);
      setComprobacionMotivo(pre.comprobacionMotivo);
      setActaClausura(pre.actaClausura);
      setActaDecomiso(pre.actaDecomiso);
      setDecomisoKilos(pre.decomisoKilos);
      setInspectoresAddInput("");
      setNotifMotivosAddInput("");
      return;
    }
    setResultadoCumplimientoOficio("");
    setObservacionesEjecucion(resolvedRow.observaciones_ejecucion ?? "");
    setContraproducencia(resolvedRow.contraproducencia ?? "");
    hydrateOperativoFieldsFromRow(resolvedRow, operativoSetters);
    setInspectoresAddInput("");
    setNotifMotivosAddInput("");
  }, [open, resolvedRow, inspectoresGrupo, tipoActuacionEsperadoRef]);

  useEffect(() => {
    if (open) return;
    const operativoSetters: OperativoFieldSetters = {
      setCalle,
      setNumero,
      setNumeroTipo,
      setRubroNombre,
      setDocNro,
      setContribApellido,
      setContribNombre,
      setRazonSocial,
      setTitularModo,
      setNombreLocal,
      setActaInspeccion,
      setActaNotificacion,
      setNotifMotivosSeleccion,
      setActaComprobacion,
      setComprobacionMotivo,
      setActaClausura,
      setActaDecomiso,
      setDecomisoKilos,
    };
    setContraproducencia("");
    clearOperativoFields(operativoSetters);
    setTipoActuacionOficio("");
    setResultadoCumplimientoOficio("");
    setRealizoNuevaInspeccion("");
    setObservacionesEjecucion("");
    setFieldErrors({});
    setInspectoresList([]);
    setInspectoresAddInput("");
    setNotifMotivosAddInput("");
    baselineInspectoresRef.current = [];
  }, [open]);

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
  const displayRow = resolvedRow ?? row;
  const tipoActuacionOficioEfectivo = useMemo(
    () => tipoActuacionEfectivoOficio(displayRow?.tipo_iniciador, tipoActuacionOficio),
    [displayRow?.tipo_iniciador, tipoActuacionOficio]
  );
  const esFlujoVerificarInformarUi = esFlujoVerificarInformar(
    displayRow?.tipo_iniciador,
    tipoActuacionOficioEfectivo
  );
  const esFlujoCumplimientoRatificacionUi = esFlujoCumplimientoRatificacion(
    displayRow?.tipo_iniciador,
    tipoActuacionOficioEfectivo
  );
  const esReinspeccionOficioGenericoUi = esReinspeccionOficioGenerico(displayRow?.tipo_iniciador);
  const esReinspeccionNotificacion = displayRow?.tipo_iniciador === "REINSPECCION_NOTIFICACION";
  const verificarMuestraInspeccionNormal =
    esFlujoVerificarInformarUi && realizoNuevaInspeccion === "si";
  const verificarSinInspeccionNormal =
    esFlujoVerificarInformarUi && realizoNuevaInspeccion === "no";
  const muestraFlujoInspeccionNormal =
    !esFlujoCumplimientoRatificacionUi &&
    (!esFlujoVerificarInformarUi || verificarMuestraInspeccionNormal);
  const showContribDomicilioEditable = showContribuyenteDomicilioEditableEnCompletarTrabajo(
    displayRow?.tipo_iniciador,
    {
      tipoActuacionOficio: tipoActuacionOficioEfectivo,
      realizoNuevaInspeccion,
    }
  );
  const omitContribDomEnValidacion =
    esReinspeccionNotificacion ||
    esFlujoCumplimientoRatificacionUi ||
    (esFlujoVerificarInformarUi && realizoNuevaInspeccion !== "si");
  const oficioNoCumple = esFlujoCumplimientoRatificacionUi && resultadoCumplimientoOficio === "NO_CUMPLE";
  const tipoIniciadorLabel = completarTrabajoHeaderTitulo(displayRow?.tipo_iniciador);
  const headerSubtitulo = completarTrabajoHeaderSubtitulo(displayRow?.fecha_actuacion);
  const showDomicilioEnDetalle = completarTrabajoShowDomicilioEnDetalle(displayRow?.tipo_iniciador);
  const detalleLabelSx = { color: "rgba(255,255,255,0.95)", fontWeight: 700 } as const;
  const detalleValueSx = { color: "rgba(255,255,255,0.85)", fontWeight: 500 } as const;

  useEffect(() => {
    if (!open || !resolvedRow) return;
    if (!esReinspeccionOficioGenerico(resolvedRow.tipo_iniciador)) return;
    if (!esFlujoVerificarInformar(resolvedRow.tipo_iniciador, tipoActuacionOficioEfectivo)) return;
    const operativoSetters: OperativoFieldSetters = {
      setCalle,
      setNumero,
      setNumeroTipo,
      setRubroNombre,
      setDocNro,
      setContribApellido,
      setContribNombre,
      setRazonSocial,
      setTitularModo,
      setNombreLocal,
      setActaInspeccion,
      setActaNotificacion,
      setNotifMotivosSeleccion,
      setActaComprobacion,
      setComprobacionMotivo,
      setActaClausura,
      setActaDecomiso,
      setDecomisoKilos,
    };
    if (realizoNuevaInspeccion === "si") {
      hydrateOperativoFieldsFromRow(resolvedRow, operativoSetters);
      return;
    }
    if (realizoNuevaInspeccion === "no") {
      clearOperativoFields(operativoSetters);
    }
  }, [
    open,
    resolvedRow,
    resolvedRow?.ruta_item_id,
    tipoActuacionOficioEfectivo,
    realizoNuevaInspeccion,
  ]);

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

  const contraCatalogFiltrado = useMemo(
    () =>
      filtrarContraproducenciasPorTipoIniciador(
        cat.contraproducencias ?? [],
        resolvedRow?.tipo_iniciador,
        resolvedRow?.contraproducencia,
        esFlujoCumplimientoRatificacionUi ? tipoActuacionOficioEfectivo ?? undefined : undefined
      ),
    [
      cat.contraproducencias,
      resolvedRow?.tipo_iniciador,
      resolvedRow?.contraproducencia,
      esFlujoCumplimientoRatificacionUi,
      tipoActuacionOficioEfectivo,
    ]
  );
  const contraOpts = useMemo(
    () => {
      const sinRealizadaLabel = oficioNoCumple
        ? "— Elegí contraproducencia —"
        : "Sin contraproducencia (visita realizada)";
      return [
        { value: "", label: sinRealizadaLabel },
        ...mergeCatalogOpts(contraCatalogFiltrado, resolvedRow?.contraproducencia).filter((o) => o.value !== ""),
      ];
    },
    [contraCatalogFiltrado, resolvedRow?.contraproducencia, oficioNoCumple]
  );
  const motivosNotifCatalogSorted = useMemo(
    () => mergeMotivosNotifCatalogStrings(cat.motivos ?? [], notifMotivosSeleccion),
    [cat.motivos, notifMotivosSeleccion]
  );
  const motivosDisponiblesParaAgregar = useMemo(
    () => motivosNotifCatalogSorted.filter((m) => !notifMotivosSeleccion.includes(m)),
    [motivosNotifCatalogSorted, notifMotivosSeleccion]
  );
  const motivoCompOpts = useMemo(
    () => mergeCatalogOpts(cat.motivosComprobacion, undefined),
    [cat.motivosComprobacion]
  );

  const handleClose = useCallback(() => {
    if (saving) return;
    onClose();
  }, [saving, onClose]);

  const handleDialogClose = useCallback(
    (_event: unknown, _reason: string) => {
      if (saving) return;
      onClose();
    },
    [saving, onClose]
  );

  const handleSubmit = async () => {
    if (!resolvedRow || detalleLoading) return;
    setFieldErrors({});

    if (esFlujoCumplimientoRatificacion(resolvedRow.tipo_iniciador, tipoActuacionOficioEfectivo)) {
      const preSubmitErrors: Record<string, string> = {};
      const tipoCierre =
        tipoActuacionFijoDesdeIniciadorOficio(resolvedRow.tipo_iniciador) || tipoActuacionOficio.trim();
      if (
        !tipoCierre ||
        !(TIPO_ACTUACION_REINSPECCION_OFICIO as readonly string[]).includes(tipoCierre)
      ) {
        preSubmitErrors.tipo_actuacion = "Elegí el tipo de actuación.";
      }
      if (!resultadoCumplimientoOficio || !["CUMPLE", "NO_CUMPLE"].includes(resultadoCumplimientoOficio)) {
        preSubmitErrors.resultado_cumplimiento_oficio = "Seleccioná si dio cumplimiento o no.";
      }
      const contraTrim = contraproducencia.trim();
      if (resultadoCumplimientoOficio === "NO_CUMPLE" && contraTrim) {
        if (
          !filtrarContraproducenciasPorTipoIniciador(
            cat.contraproducencias ?? [],
            resolvedRow.tipo_iniciador,
            contraTrim,
            tipoCierre
          ).some((x) => x.trim() === contraTrim)
        ) {
          preSubmitErrors.contraproducencia = "La contraproducencia no aplica al tipo de actuación elegido.";
        }
      }
      if (Object.keys(preSubmitErrors).length > 0) {
        setFieldErrors(preSubmitErrors);
        feedback.warning(MENSAJE_VALIDACION_LOCAL);
        return;
      }
      setSaving(true);
      try {
        const usaContraReencolado = resultadoCumplimientoOficio === "NO_CUMPLE" && contraTrim;
        const values: Record<string, unknown> = {
          contraproducencia: usaContraReencolado ? contraTrim : "",
          tipo_actuacion: tipoCierre,
          ...(usaContraReencolado
            ? {}
            : { resultado_cumplimiento_oficio: resultadoCumplimientoOficio }),
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
        if (resolvedRow.tipo_iniciador === "REINSPECCION_NOTIFICACION") {
          emitGestionNotificacionReinspeccionRefresh();
        }
        feedback.success("Trabajo completado correctamente.");
        onSuccess(resolvedRow.ruta_item_id);
        onClose();
      } catch (e) {
        const { fieldErrors: nextFe, generalMessage } = applyCompletarTrabajoFieldErrorsFromApi(e);
        setFieldErrors(nextFe);
        feedback.error(generalMessage);
      } finally {
        setSaving(false);
      }
      return;
    }

    if (esFlujoVerificarInformar(resolvedRow.tipo_iniciador, tipoActuacionOficioEfectivo)) {
      const preSubmitErrors: Record<string, string> = {};
      const tipoCierre =
        tipoActuacionFijoDesdeIniciadorOficio(resolvedRow.tipo_iniciador) ||
        tipoActuacionOficio.trim() ||
        TIPO_ACTUACION_VERIFICAR_INFORMAR;
      if (!realizoNuevaInspeccion || !["si", "no"].includes(realizoNuevaInspeccion)) {
        preSubmitErrors.realizo_nueva_inspeccion = "Indicá si realizó nueva inspección.";
      }
      if (Object.keys(preSubmitErrors).length > 0) {
        setFieldErrors(preSubmitErrors);
        feedback.warning(MENSAJE_VALIDACION_LOCAL);
        return;
      }

      if (realizoNuevaInspeccion === "no") {
        setSaving(true);
        try {
          const values: Record<string, unknown> = {
            tipo_actuacion: tipoCierre,
            realizo_nueva_inspeccion: "no",
            contraproducencia,
            observaciones_ejecucion: observacionesEjecucion.trim(),
            ...ACTA_KEYS_EMPTY,
          };
          const base = baselineInspectoresRef.current;
          const inspectoresDirty = !sameInspectoresListOrder(inspectoresList, base);
          await submitCompletarTrabajoCierreFromRow(resolvedRow, values, {
            includeTipoActuacion: true,
            omitPrecargadoPr2: false,
            incluirInspeccionNormal: false,
            ...(inspectoresDirty
              ? { inspectoresExplicitos: dedupeInspectoresPreserveOrder(inspectoresList) }
              : {}),
          });
          feedback.success("Trabajo completado correctamente.");
          onSuccess(resolvedRow.ruta_item_id);
          onClose();
        } catch (e) {
          const { fieldErrors: nextFe, generalMessage } = applyCompletarTrabajoFieldErrorsFromApi(e);
          setFieldErrors(nextFe);
          feedback.error(generalMessage);
        } finally {
          setSaving(false);
        }
        return;
      }

      // Sí → validación y cierre con inspección normal (continúa abajo).
    }

    const preValidation = validateActuacionFormForSubmit(
      buildCompletarTrabajoValidationForm(resolvedRow, {
        contraproducencia,
        calle,
        numero,
        rubroNombre,
        docNro,
        contribApellido,
        contribNombre,
        razonSocial,
        titularModo,
        nombreLocal,
        actaInspeccion,
        actaNotificacion,
        notifMotivosSeleccion,
        actaComprobacion,
        comprobacionMotivo,
        actaClausura,
        actaDecomiso,
        decomisoKilos,
        inspectoresList,
      }),
      actuacionCompletarTrabajoValidationContext(
        visitaRealizada,
        esReinspeccionNotificacion,
        omitContribDomEnValidacion
      )
    );
    if (!preValidation.canSubmit) {
      setFieldErrors(preValidation.fieldErrors);
      notifyActuacionFormValidationResult(preValidation, feedback);
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
        observaciones_ejecucion: observacionesEjecucion.trim(),
        ...ACTA_KEYS_EMPTY,
      };
      if (esFlujoVerificarInformarUi) {
        values.tipo_actuacion =
          tipoActuacionFijoDesdeIniciadorOficio(resolvedRow.tipo_iniciador) ||
          tipoActuacionOficioEfectivo ||
          TIPO_ACTUACION_VERIFICAR_INFORMAR;
        values.realizo_nueva_inspeccion = "si";
      }
      if (showContribDomicilioEditable) {
        Object.assign(values, {
          rubro_nombre: rubroNombre,
          calle,
          numero,
          numero_tipo: numeroTipo,
          doc_nro: docNro,
          ...titularPayload,
          nombre_local: nombreLocal,
        });
      }

      const notifSlots = slotsToMotivosApi(notifMotivosSeleccion);
      if (visitaRealizada) {
        Object.assign(values, {
          acta_inspeccion_num: actaNumForPayload(actaInspeccion),
          acta_comprobacion_num: actaNumForPayload(actaComprobacion),
          comprobacion_motivo: comprobacionMotivo,
          acta_clausura_num: actaNumForPayload(actaClausura),
          acta_decomiso_num: actaNumForPayload(actaDecomiso),
          decomiso_kilos_total: decomisoKilos,
        });
        if (!esReinspeccionNotificacion) {
          Object.assign(values, {
            acta_notificacion_num: actaNumForPayload(actaNotificacion),
            notificacion_motivo_1: notifSlots.m1,
            notificacion_motivo_2: notifSlots.m2,
            notificacion_motivo_3: notifSlots.m3,
          });
        }
      } else if (esNoPermiteInspeccion) {
        Object.assign(values, {
          acta_comprobacion_num: actaNumForPayload(actaComprobacion),
          comprobacion_motivo: comprobacionMotivo,
          acta_clausura_num: actaNumForPayload(actaClausura),
        });
      }

      const base = baselineInspectoresRef.current;
      const inspectoresDirty = !sameInspectoresListOrder(inspectoresList, base);
      await submitCompletarTrabajoCierreFromRow(resolvedRow, values, {
        omitPrecargadoPr2: !esFlujoVerificarInformarUi,
        includeTipoActuacion: esFlujoVerificarInformarUi,
        ...(inspectoresDirty
          ? { inspectoresExplicitos: dedupeInspectoresPreserveOrder(inspectoresList) }
          : {}),
      });
      if (resolvedRow.tipo_iniciador === "REINSPECCION_NOTIFICACION") {
        emitGestionNotificacionReinspeccionRefresh();
      }
      feedback.success("Trabajo completado correctamente.");
      onSuccess(resolvedRow.ruta_item_id);
      onClose();
    } catch (e) {
      const { fieldErrors: nextFe, generalMessage } = applyCompletarTrabajoFieldErrorsFromApi(e);
      setFieldErrors(nextFe);
      feedback.error(generalMessage);
    } finally {
      setSaving(false);
    }
  };

  const col = { display: "flex", flexDirection: "column" as const, gap: 1.5 };
  const labelMuted = { color: "rgba(255,255,255,0.5)", fontFamily: '"Tactic Sans", sans-serif' } as const;

  return (
    <CrudGlassDialog
      open={open && row != null}
      onClose={handleDialogClose}
      onCloseButtonClick={handleClose}
      maxWidth="md"
      disablePortal={disablePortal}
      hideBackdrop={disablePortal}
      title={
        <CrudDialogHeader
          domainChip="Completar trabajo"
          titulo={tipoIniciadorLabel}
          subtitulo={headerSubtitulo}
        />
      }
      actions={
        <CrudDialogActions
          mode="edit"
          onSave={() => void handleSubmit()}
          loading={saving}
          saveLabel="Guardar cierre"
        />
      }
    >
      <Stack spacing={DOC_MODAL_BLOCK_STACK_SPACING} ref={scrollContainerRef}>
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

      {displayRow && (
        <CompletarBloque title="Contexto del trabajo">
        <Box
          sx={{
            ...col,
            p: 1.5,
            borderRadius: 2,
            bgcolor: "rgba(255,255,255,0.06)",
            fontFamily: '"Tactic Sans", sans-serif',
          }}
        >
          <Typography variant="subtitle2" sx={{ ...detalleLabelSx, mb: 0.25 }}>
            Detalle
          </Typography>
          <Typography variant="body2" sx={detalleValueSx}>
            <Box component="span" sx={detalleLabelSx}>
              Grupo:{" "}
            </Box>
            {displayRow.grupo_nombre?.trim() || "—"}
          </Typography>
          <Typography variant="body2" sx={detalleValueSx}>
            <Box component="span" sx={detalleLabelSx}>
              Orden de trabajo:{" "}
            </Box>
            {displayRow.orden_trabajo_numero ?? "—"}
          </Typography>
          {showDomicilioEnDetalle ? (
            <Typography variant="body2" sx={detalleValueSx}>
              <Box component="span" sx={detalleLabelSx}>
                Domicilio actual:{" "}
              </Box>
              {domicilioResumen(displayRow)}
            </Typography>
          ) : null}
        </Box>
        </CompletarBloque>
      )}

      {displayRow && !detalleLoading && (
        <CompletarBloque title="Datos generales">
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
            inputValue={inspectoresAddInput}
            onInputChange={(_, newInput, reason) => {
              if (reason === "input") setInspectoresAddInput(newInput);
              else if (reason === "clear" || reason === "reset") setInspectoresAddInput("");
            }}
            onChange={(_, value) => {
              if (value && !inspectoresList.includes(value)) {
                setInspectoresList((prev) => [...prev, value]);
                clearFe("inspectores");
                setInspectoresAddInput("");
              }
            }}
            disabled={!catalogsReady || inspectoresDisponiblesParaAgregar.length === 0}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Agregar inspector"
                placeholder={catalogsReady ? "Catálogo" : "…"}
                sx={modalAuxInputSx}
                error={Boolean(fe("inspectores"))}
                helperText={fe("inspectores") || undefined}
              />
            )}
          />
        </Box>
        </CompletarBloque>
      )}

      {displayRow && esReinspeccionOficioGenericoUi && (
        <CompletarBloque title="Cierre por oficio">
        <Box sx={col}>
          <AppSelect
            appearance="glass"
            label="Tipo de actuación"
            value={tipoActuacionOficio}
            onChange={(e) => {
              const next = e.target.value as string;
              setTipoActuacionOficio(next);
              setResultadoCumplimientoOficio("");
              setRealizoNuevaInspeccion("");
              if (contraproducencia.trim()) {
                const validas = filtrarContraproducenciasPorTipoIniciador(
                  cat.contraproducencias ?? [],
                  resolvedRow.tipo_iniciador,
                  contraproducencia,
                  next
                );
                if (!validas.some((x) => x.trim() === contraproducencia.trim())) {
                  setContraproducencia("");
                }
              }
              clearFe("tipo_actuacion");
              clearFe("resultado_cumplimiento_oficio");
              clearFe("realizo_nueva_inspeccion");
            }}
            fullWidth
            options={TIPO_ACTUACION_REINSPECCION_OFICIO_OPTS}
            error={Boolean(fe("tipo_actuacion"))}
            helperText={fe("tipo_actuacion") || "Obligatorio."}
          />
        </Box>
        </CompletarBloque>
      )}

      {displayRow && esFlujoCumplimientoRatificacionUi && (
        <CompletarBloque title={esRatificacionOficio(displayRow.tipo_iniciador) ? "Cierre de ratificación" : "Cierre por oficio"}>
        <Box sx={col}>
          <AppSelect
            appearance="glass"
            label="¿Dio cumplimiento?"
            value={resultadoCumplimientoOficio}
            onChange={(e) => {
              const next = e.target.value as string;
              setResultadoCumplimientoOficio(next);
              if (next !== "NO_CUMPLE") {
                setContraproducencia("");
                clearFe("contraproducencia");
              }
              clearFe("resultado_cumplimiento_oficio");
            }}
            fullWidth
            options={OFICIO_CUMPLE_OPTS}
            error={Boolean(fe("resultado_cumplimiento_oficio"))}
            helperText={
              fe("resultado_cumplimiento_oficio") || "Indicá si el establecimiento dio cumplimiento al oficio."
            }
          />
          {oficioNoCumple && (
            <>
              <AppSelect
                appearance="glass"
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
                helperText={
                  fe("contraproducencia") ||
                  "Opcional: elegí el motivo operativo. Si no elegís ninguna, el caso vuelve a pendientes por no cumplimiento."
                }
              />
              {contraHint === "reingreso_prioridad_alta" && (
                <Alert severity="info" sx={{ borderRadius: 2 }}>
                  <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
                    Reingreso a pendientes
                  </Typography>
                  <Typography variant="body2">
                    El trabajo vuelve a <strong>pendientes</strong> con prioridad alta para una nueva visita.
                  </Typography>
                </Alert>
              )}
            </>
          )}
          <AppTextField
            appearance="glass"
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
        </CompletarBloque>
      )}

      {displayRow && esFlujoVerificarInformarUi && (
        <CompletarBloque title="Verificar e informar">
        <Box sx={col}>
          <AppSelect
            appearance="glass"
            label="¿Realizó nueva inspección?"
            value={realizoNuevaInspeccion}
            onChange={(e) => {
              const next = e.target.value as string;
              setRealizoNuevaInspeccion(next);
              if (next !== "si") {
                setActaInspeccion("");
                setActaNotificacion("");
                setNotifMotivosSeleccion([]);
                setActaComprobacion("");
                setComprobacionMotivo("");
                setActaClausura("");
                setActaDecomiso("");
                setDecomisoKilos("");
              }
              clearFe("realizo_nueva_inspeccion");
            }}
            fullWidth
            options={REALIZO_NUEVA_INSPECCION_OPTS}
            error={Boolean(fe("realizo_nueva_inspeccion"))}
            helperText={
              fe("realizo_nueva_inspeccion") ||
              "Si realizó inspección, elegí Sí para cargar actas. Si no, elegí No para cerrar sin actas normales."
            }
          />
        </Box>
        </CompletarBloque>
      )}

      {displayRow && (muestraFlujoInspeccionNormal || verificarSinInspeccionNormal) && (
        <>
      <CompletarBloque title="Contraproducencia">
      <Box sx={col}>
        <AppSelect
          appearance="glass"
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
        {contraHint === "correctiva_rubro_direccion" && (
          <Alert severity="info" sx={{ borderRadius: 2 }}>
            <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
              Corrección de datos y reingreso
            </Typography>
            <Typography variant="body2" sx={{ mb: 0.5 }}>
              El trabajo vuelve a <strong>pendientes</strong> con prioridad alta. Ajustá abajo el rubro y/o la
              dirección según corresponda y guardá: los cambios quedan en la actuación y en el iniciador para la
              próxima visita.
            </Typography>
            <Typography variant="caption" sx={{ display: "block", opacity: 0.9 }}>
              No se cargan actas del día en este cierre. Si cambió mucho la dirección, el mapa puede mostrar el punto
              en revisión hasta que termine la normalización / geocodificación automática.
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

        {visitaRealizada && showContribDomicilioEditable && (
          <Alert severity="info" sx={{ borderRadius: 2 }}>
            <Typography variant="body2">
              Con visita realizada, revisá calle, rubro y titular: datos correctos ayudan a vincular la actuación con la{" "}
              <strong>ficha operativa</strong> al guardar.
            </Typography>
          </Alert>
        )}

        {muestraFlujoInspeccionNormal && showContribDomicilioEditable && (
        <>
        <CompletarBloque title="Domicilio y establecimiento">
        <Box sx={{ ...col, width: "100%" }}>
        <Box sx={edicionGrid2ColSx}>
          <AppTextField
            appearance="glass"
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
          <NumeroEsquinaFreeEditor
            value={numero || null}
            onChange={(v) => {
              setNumero(v ?? "");
              clearFe("numero");
            }}
            onModeChange={setNumeroTipo}
            compact
            error={Boolean(fe("numero"))}
            helperText={fe("numero") || undefined}
            initialMode={numeroTipo}
          />
        </Box>

        <AppSelect
          appearance="glass"
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
        </Box>
        </CompletarBloque>

        <CompletarBloque title="Contribuyente / titular">
        <Box sx={{ ...col, width: "100%" }}>
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
          <Box sx={edicionGrid2ColSx}>
            <AppTextField
              appearance="glass"
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
              appearance="glass"
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
          </Box>
        ) : (
          <AppTextField
            appearance="glass"
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
          appearance="glass"
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
          appearance="glass"
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
        </CompletarBloque>
        </>
        )}
      </Box>
      </CompletarBloque>

      {muestraFlujoInspeccionNormal && (visitaRealizada || esNoPermiteInspeccion) && (
        <CompletarBloque title="Actas labradas">
        <Box sx={{ ...col, width: "100%" }}>
          {esNoPermiteInspeccion && !visitaRealizada && (
            <Typography variant="subtitle2" sx={{ color: "rgba(255,255,255,0.85)", letterSpacing: 0.2 }}>
              Actas para este cierre
            </Typography>
          )}
          {visitaRealizada && (
            <>
              <Box sx={edicionGrid2ColSx}>
                <ActaNumFieldLazy
                  appearance="glass"
                  label="N° acta de inspección"
                  value={actaInspeccion || null}
                  onCommit={(v) => {
                    setActaInspeccion(v ?? "");
                    clearFe("acta_inspeccion_num");
                  }}
                  error={Boolean(fe("acta_inspeccion_num"))}
                  helperText={fe("acta_inspeccion_num") || undefined}
                />
                {esReinspeccionNotificacion ? (
                  <Box
                    sx={{
                      p: 1.5,
                      borderRadius: 2,
                      bgcolor: "rgba(255,255,255,0.06)",
                      fontFamily: '"Tactic Sans", sans-serif',
                    }}
                  >
                    <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.5)", textTransform: "uppercase" }}>
                      Notificación origen (solo lectura)
                    </Typography>
                    <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.85)", mt: 0.5 }}>
                      {(resolvedRow?.acta_notificacion_num ?? "").trim()
                        ? `Notif. ${(resolvedRow?.acta_notificacion_num ?? "").trim()}`
                        : "—"}
                    </Typography>
                  </Box>
                ) : (
                  <ActaNumFieldLazy
                    appearance="glass"
                    label="N° acta de notificación"
                    value={actaNotificacion || null}
                    onCommit={(v) => {
                      setActaNotificacion(v ?? "");
                      clearFe("acta_notificacion_num");
                    }}
                    error={Boolean(fe("acta_notificacion_num"))}
                    helperText={fe("acta_notificacion_num") || undefined}
                  />
                )}
              </Box>
              {!esReinspeccionNotificacion ? (
                <>
                  <Typography variant="caption" sx={labelMuted}>
                    Motivos de notificación (máx. {MOTIVOS_NOTIFICACION_MAX})
                  </Typography>
                  <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, alignItems: "center" }}>
                    {notifMotivosSeleccion.length === 0 ? (
                      <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.45)" }}>
                        —
                      </Typography>
                    ) : (
                      notifMotivosSeleccion.map((name, idx) => (
                        <Chip
                          key={`${idx}-${name}`}
                          label={name}
                          size="small"
                          onDelete={() => {
                            setNotifMotivosSeleccion((prev) => prev.filter((_, i) => i !== idx));
                            clearFe("notificacion_motivo_1");
                            clearFe("notificacion_motivo_2");
                            clearFe("notificacion_motivo_3");
                          }}
                          sx={{ bgcolor: "rgba(255,255,255,0.12)", color: "rgba(255,255,255,0.92)" }}
                        />
                      ))
                    )}
                  </Box>
                  <Autocomplete
                    size="small"
                    options={motivosDisponiblesParaAgregar}
                    value={null}
                    inputValue={notifMotivosAddInput}
                    onInputChange={(_, newInput, reason) => {
                      if (reason === "input") setNotifMotivosAddInput(newInput);
                      else if (reason === "clear" || reason === "reset") setNotifMotivosAddInput("");
                    }}
                    onChange={(_, value) => {
                      if (
                        value &&
                        !notifMotivosSeleccion.includes(value) &&
                        notifMotivosSeleccion.length < MOTIVOS_NOTIFICACION_MAX
                      ) {
                        setNotifMotivosSeleccion((prev) => [...prev, value]);
                        clearFe("notificacion_motivo_1");
                        clearFe("notificacion_motivo_2");
                        clearFe("notificacion_motivo_3");
                        setNotifMotivosAddInput("");
                      }
                    }}
                    disabled={
                      !catalogsReady ||
                      motivosDisponiblesParaAgregar.length === 0 ||
                      notifMotivosSeleccion.length >= MOTIVOS_NOTIFICACION_MAX
                    }
                    renderInput={(params) => (
                      <TextField
                        {...params}
                        label="Agregar motivo"
                        placeholder={catalogsReady ? "Catálogo" : "…"}
                        sx={modalAuxInputSx}
                        error={Boolean(
                          fe("notificacion_motivo_1") || fe("notificacion_motivo_2") || fe("notificacion_motivo_3")
                        )}
                        helperText={
                          fe("notificacion_motivo_1") ||
                          fe("notificacion_motivo_2") ||
                          fe("notificacion_motivo_3") ||
                          undefined
                        }
                      />
                    )}
                  />
                </>
              ) : null}
            </>
          )}
          <Box sx={edicionGrid2ColSx}>
            <ActaNumFieldLazy
              appearance="glass"
              label={
                esNoPermiteInspeccion && !visitaRealizada
                  ? "N° acta de comprobación (obligatorio)"
                  : "N° acta de comprobación"
              }
              value={actaComprobacion || null}
              onCommit={(v) => {
                setActaComprobacion(v ?? "");
                clearFe("acta_comprobacion_num");
              }}
              error={Boolean(fe("acta_comprobacion_num"))}
              helperText={
                fe("acta_comprobacion_num") ||
                (esNoPermiteInspeccion && !visitaRealizada ? "Obligatorio para esta contraproducencia." : undefined)
              }
            />
            <AppSelect
              appearance="glass"
              label="Motivo de comprobación"
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
          </Box>
          <Box sx={edicionGrid2ColSx}>
            <ActaNumFieldLazy
              appearance="glass"
              label="N° acta de clausura (opcional)"
              value={actaClausura || null}
              onCommit={(v) => {
                setActaClausura(v ?? "");
                clearFe("acta_clausura_num");
              }}
              error={Boolean(fe("acta_clausura_num"))}
              helperText={fe("acta_clausura_num") || undefined}
            />
            {visitaRealizada ? (
              <ActaNumFieldLazy
                appearance="glass"
                label="N° acta de decomiso"
                value={actaDecomiso || null}
                onCommit={(v) => {
                  setActaDecomiso(v ?? "");
                  clearFe("acta_decomiso_num");
                }}
                error={Boolean(fe("acta_decomiso_num"))}
                helperText={fe("acta_decomiso_num") || undefined}
              />
            ) : (
              <Box />
            )}
          </Box>
          {visitaRealizada ? (
            <AppTextField
              appearance="glass"
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
          ) : null}
        </Box>
        </CompletarBloque>
      )}
      <CompletarBloque title="Observaciones">
        <Box sx={{ ...col, width: "100%" }}>
          <AppTextField
            appearance="glass"
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
      </CompletarBloque>
        </>
      )}
      </Stack>
    </CrudGlassDialog>
  );
}
