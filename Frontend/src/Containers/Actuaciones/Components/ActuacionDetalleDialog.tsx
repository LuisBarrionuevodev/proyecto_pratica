import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import type { ReactNode } from "react";
import type { SxProps, Theme } from "@mui/material/styles";
import {
  Alert,
  Autocomplete,
  Box,
  Chip,
  CircularProgress,
  Collapse,
  Divider,
  IconButton,
  Link,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { ActaCanalQuitarTipo, IActuacionListItem } from "../../../api/actuacionesListApi";
import {
  MOTIVOS_NOTIFICACION_MAX,
  mergeMotivosNotifCatalogStrings,
  motivosNotificacionFromSlots,
  orderedMotivosNotificacion,
} from "../../../utils/motivosNotificacionSlots";
import {
  hydrateMotivosComprobacion,
  mergeMotivosCompCatalogStrings,
  motivosComprobacionLecturaMultilinea,
  orderedMotivosComprobacion,
  primerMotivoComprobacionLegado,
} from "../../../utils/motivosComprobacion";
import {
  debeMostrarBloqueOrigenVerActuacion,
  filasOrigenActasVerActuacion,
} from "../../ActasComprobacion/utils/origenActasLabels";
import { mergeLegacyRubroNames } from "../../../utils/rubrosCatalogCache";
import { domicilioCalleValorEdicion, domicilioNumeroValorEdicion, domicilioRowParaEdicionCalle } from "../../../utils/domicilioCalleUi";
import { useAppFeedback } from "../../../components/feedback";
import {
  CrudDialogActions,
  CrudDialogHeader,
  CrudDialogSection,
  CrudFieldView,
  CrudFormSlot,
  CrudGlassDialog,
  useCrudDialogScrollContainer,
} from "../../../components/crudDialog";
import {
  CRUD_FIELD_INPUT_HEIGHT_PX,
  crudFieldGridSx,
  crudFieldSlotLabelSx,
  crudReadonlyFieldShellSx,
  crudReadonlyFieldValueSx,
} from "../../../styles/crudDialogTokens";
import {
  DOC_MODAL_BLOCK_STACK_SPACING,
  DOC_MODAL_TEXT,
  docModalBlockResumenSx,
  docModalChipSx,
  docModalSubheadingInCardSx,
} from "../../../styles/documentalModalTokens";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { CSS_VAR_NAMES as V } from "../../../theme/applyCssVariables";
import { resolveCrudDialogHeaderReference } from "../../../components/crudDialog/crudDialogReference";
import { mergeSx } from "../../../utils/muiSx";
import { NumeroEsquinaFreeEditor } from "./NumeroEsquinaFreeEditor";
import { AppButton, AppSelect, AppTextField } from "../../../ui";
import { COLORS } from "../styles/filtroStyles";
import { ActaNumFieldLazy } from "./ActaNumFieldLazy";
import {
  InspeccionChecklistFields,
  displayItemNombre,
  isValidActaInspeccionNum,
} from "./InspeccionChecklistFields";
import type { IItemActaInspeccionCatalogItem } from "../../../api/itemActaInspeccionCatalogApi";
import {
  cantidadPersonasSinCarnetFromRow,
  displayChecklistEstadoBienLabel,
  estadosMapFromRow,
  itemsActaInspeccionWriteFromEstados,
  normalizeChecklistItems,
  planChecklistHydration,
} from "../utils/inspeccionChecklistSubmit";
import type { ChecklistUxValue } from "../utils/inspeccionChecklistSubmit";
import {
  PersonasSinCarnetField,
  isValidActaNotificacionNum,
} from "./PersonasSinCarnetField";
import { ACTA_FIELD_LABELS } from "../utils/actaFieldLabels";
import { ActuacionDocumentacionChips } from "./ActuacionDocumentacionChips";
import {
  actuacionDocumentacionOrigenReinspeccionSegments,
  actuacionDocumentacionPropiaTramiteSegments,
} from "../utils/actuacionDocumentacionVisual";
import {
  debeMostrarCampoActaEnEdicion,
  detectBlockedActaClearAttempt,
  getActuacionEditableFields,
  resolveActuacionEditStart,
  tieneActasInspeccionNormalPersistidas,
  tieneExpedienteBloqueoEdicion,
} from "../utils/actuacionEditRules";
import { buildContraproducenciaCrudSelectOptions } from "../utils/contraproducenciaCrudOptions";
import { getContraproducenciaUxHint } from "../../CompletarTrabajos/utils/contraproducenciaUxHint";
import { filtrarContraproducenciasPorTipoIniciador } from "../../CompletarTrabajos/utils/contraproducenciasPorTipoIniciador";
import { scrollActuacionFormToFirstFieldError } from "../utils/actuacionFormScroll";
import { mergeActuacionAfterOficioCorrection } from "../utils/mergeActuacionAfterOficioCorrection";
import { corregirCierreOficio } from "../../../api/corregirCierreOficioApi";
import { detectActasClearedByUser } from "../validations/actuacionFormNormalize";
import {
  normalizeActuacionApiError,
} from "../validations/normalizeActuacionApiError";
import { MENSAJE_ERROR_GRAVE, notifyActuacionApiError } from "../utils/actuacionSaveFeedback";
import { ReinspeccionOficioForm } from "../../../shared/reinspeccionOficio/ReinspeccionOficioForm";
import {
  resolveReinspeccionOficioFormContext,
  tipoIniciadorInferidoDesdeActuacion,
} from "../../../shared/reinspeccionOficio/resolveReinspeccionOficioFormContext";
import {
  oficioCorreccionDirty,
  oficioCorreccionPayloadFromUi,
  validateReinspeccionOficioForm,
} from "../../../shared/reinspeccionOficio/reinspeccionOficioValidation";
import { tipoIniciadorDesdeSubtipoActuacionOficio } from "../../../shared/reinspeccionOficio/reinspeccionOficioSubtipo";
import type { ReinspeccionOficioValidationContextInput } from "../../../shared/reinspeccionOficio/usaInspeccionNormalReinspeccionOficio";
import { useReinspeccionOficioFormState } from "../../../shared/reinspeccionOficio/useReinspeccionOficioFormState";
import { FONT_FAMILY_UI } from "../../../theme/typography";
import {
  MSG_VERIFICAR_LEGACY_INCONSISTENTE,
  resolveVerificarEstadoFromPersisted,
} from "../../../shared/reinspeccionOficio/verificarEstadoOperativo";
import {
  boolToFaltasSubsanadasUi,
  boolToSolicitaCarnetUi,
} from "../../CompletarTrabajos/utils/actaSeguimientoUi";
import {
  applyGestionSeguimientoDraftToRow,
  gestionSeguimientoDraftFromRow,
  mergeActuacionSeguimientoFromApiRow,
  validateGestionSeguimientoFields,
} from "../utils/actuacionGestionSeguimientoPut";
import { type ContribuyenteIdentityTouched } from "../utils/contribuyenteCrudOptions";
import { InspeccionAtencionEstablecimientoFields } from "./InspeccionAtencionEstablecimientoFields";
import { InspeccionActaSegmentedRow } from "./InspeccionActaSegmentedRow";
import {
  caracterPersonaAtendioFromRow,
  contratoResiduosFromRow,
  labelCaracterPersonaAtendio,
  labelContratoResiduos,
  type InspeccionAtencionTouched,
} from "../utils/inspeccionAtencion";
import {
  OBSERVACIONES_VISITA_MAX_LENGTH,
  canEditObservacionesVisita,
  observacionesVisitaDisplayText,
  validateObservacionesVisitaFields,
} from "../utils/actuacionObservacionesVisitaPut";
import {
  formatGestionContribuyenteNombre,
  formatGestionDomicilioLinea,
  formatGestionRubroNombre,
  gestionContextoDisplayValue,
} from "../utils/actuacionGestionContexto";
import {
  ActuacionMediaGallery,
  type ActuacionMediaGalleryHandle,
} from "../../../features/media/components/ActuacionMediaGallery";
import { MediaUploadPanelErrorBoundary } from "../../../features/media/components/MediaUploadPanelErrorBoundary";
import { shouldCloseInspectorFotosModalAfterSave } from "../../../features/media/utils/actuacionManualMediaSave";
import { ConfirmDialog } from "../../../ui";
import { MEDIA_UPLOAD_ORIGIN_MIS_TRABAJOS } from "../../../features/media/mediaUploadOrigin";

const documentacionTramiteChipModalSx = {
  ...docModalChipSx,
  fontSize: "0.72rem",
  maxWidth: "100%",
  "& .MuiChip-label": {
    overflow: "hidden",
    textOverflow: "ellipsis",
    px: 0.75,
  },
} as const;

/** Líneas de «Trámite origen» en modal (F2.4): lectura documental, sin chips. */
const tramiteOrigenLineaSx = {
  color: DOC_MODAL_TEXT,
  fontSize: "0.8125rem",
  fontWeight: 400,
  lineHeight: 1.5,
  opacity: 0.94,
  m: 0,
  fontFamily: FONT_FAMILY_UI,
  wordBreak: "break-word" as const,
};

export type ActuacionEditCatalogs = {
  inspectores: string[];
  motivos: string[];
  rubros: string[];
  tipos: string[];
  contraproducencias: string[];
  motivosComprobacion: string[];
  itemsActaInspeccion: IItemActaInspeccionCatalogItem[];
};

export type ActuacionSaveOptions = {
  /** True si `corregir-cierre-oficio` ya persistió campos operativos de Oficio. */
  oficioCorrectionApplied?: boolean;
  /** Actas ya eliminadas por `corregir-cierre-oficio` en el mismo Guardar. */
  actasClearedByOficioCorrection?: ActaCanalQuitarTipo[];
  /** Estado destino del formulario Oficio para validación CRUD contextualizada. */
  oficioValidationContext?: ReinspeccionOficioValidationContextInput;
  inspeccionChecklistTouched?: { items?: boolean; carnets?: boolean };
  inspeccionAtencionTouched?: InspeccionAtencionTouched;
  contribuyenteIdentityTouched?: ContribuyenteIdentityTouched;
  inspeccionChecklistCatalog?: IItemActaInspeccionCatalogItem[];
  /** Mantiene el modal abierto tras PUT exitoso (p. ej. subida manual de fotos). */
  deferDialogClose?: boolean;
};

export type ActuacionDetalleDialogProps = {
  open: boolean;
  draft: IActuacionListItem;
  fieldErrors: Record<string, string>;
  saving: boolean;
  /** Carga del detalle autorizado (`GET /gestion`); no debe deshabilitar campos de edición. */
  detailLoading?: boolean;
  catalogs: ActuacionEditCatalogs;
  /** Catálogos de selects aún cargando (evita Autocomplete vacío aparentando listo). */
  catalogsLoading?: boolean;
  /** Error recuperable al cargar catálogos (Inspector / gestión). */
  catalogsError?: string | null;
  readOnlyColumns: string[];
  /** Opciones de calle para editor de número (p. ej. gestión domicilios); opcional en actuaciones. */
  numeroEditorLabel?: string;
  /** Si es false, no se muestra el paso a edición (p. ej. bandejas restringidas). */
  canEdit?: boolean;
  /** Inspector en Mis trabajos: modos «Editar datos y fotos» / «Gestionar fotos». */
  inspectorSelfService?: boolean;
  onClose: () => void;
  onDraftChange: (patch: Partial<IActuacionListItem>) => void;
  onSave: (
    rowOverride?: IActuacionListItem,
    options?: ActuacionSaveOptions
  ) => void | Promise<void | boolean>;
  /** Tras PUT diferido (+ fotos manuales): cierra sesión de edición sin reabrir el modal. */
  onEditSaveSessionEnd?: (outcome: "success" | "aborted") => void;
  /** Solo tests SSR; evita portal de MUI Dialog. */
  disablePortal?: boolean;
  /** Solo tests: abrir directamente en edición. */
  initialEditing?: boolean;
  /** Inspector: abre modal dedicado de fotos (Mis trabajos). */
  onRequestPhotosOnly?: () => void;
  /** Inspector Mis trabajos: consulta solo lectura sin acciones de edición/carga. */
  inspectorVerTrabajoMode?: boolean;
};

function opts(strings: string[]) {
  return strings.map((s) => ({ value: s, label: s || "—" }));
}

const sectionTitleSx = {
  color: DOC_MODAL_TEXT,
  fontFamily: FONT_FAMILY_UI,
  fontWeight: 700,
  mb: 1.5,
  display: "block" as const,
};

const blockShellSx = {
  p: 1.75,
  borderRadius: 2,
  bgcolor: "rgba(255,255,255,0.04)",
  border: "1px solid rgba(255,255,255,0.08)",
  fontFamily: FONT_FAMILY_UI,
};

/** Estilo de inputs deshabilitados en edición; referencia estable (no recrear por render). */
const roFieldSx = { "& .MuiInputBase-input": { color: GLASS_COLORS.textPrimary } };

/** Autocomplete / TextField auxiliar en modal glass (tokens semánticos). */
const modalAuxInputSx = {
  "& .MuiInputBase-input": { color: DOC_MODAL_TEXT },
  "& .MuiInputLabel-root": { color: GLASS_COLORS.textSecondary },
  "& .MuiOutlinedInput-notchedOutline": { borderColor: GLASS_COLORS.borderMedium },
  "& .MuiFormHelperText-root": { color: GLASS_COLORS.textMuted },
} as const;

const edicionGrid2ColSx = {
  display: "grid",
  gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)" },
  gap: 2,
  width: "100%",
  alignItems: "end",
} as const;

const lecturaGridSx = crudFieldGridSx;

const lecturaLabelSx = {
  color: DOC_MODAL_TEXT,
  fontSize: "0.72rem",
  fontWeight: 700,
  opacity: 0.82,
  textTransform: "uppercase" as const,
  letterSpacing: "0.04em",
  display: "block",
  mb: 0.4,
} as const;

const lecturaValueSx = {
  color: DOC_MODAL_TEXT,
  fontSize: "0.875rem",
  fontWeight: 500,
  lineHeight: 1.5,
  m: 0,
  overflowWrap: "anywhere" as const,
  whiteSpace: "pre-wrap" as const,
} as const;

const lecturaSectionTitleSx = {
  color: GLASS_COLORS.textPrimary,
  fontSize: "0.95rem",
  fontWeight: 700,
  lineHeight: 1.35,
  letterSpacing: 0,
  textTransform: "none" as const,
  mb: 1.5,
} as const;

const col = { display: "flex", flexDirection: "column" as const, gap: 1.5 };
const labelMuted = { color: GLASS_COLORS.textMuted, fontFamily: FONT_FAMILY_UI } as const;

const actuacionModalChipSx = {
  bgcolor: `var(${V.actionSelected})`,
  color: GLASS_COLORS.textPrimary,
} as const;

/** Acta de notificación / comprobación bloqueada por expediente (misma semántica que `lockedNotif` / `lockedComp`). */
const edicionActaBloqueadaShellSx = {
  mt: 0,
  p: 1.25,
  borderRadius: 1.5,
  bgcolor: "rgba(255,255,255,0.05)",
  border: "1px solid rgba(255,255,255,0.1)",
} as const;

/**
 * Modo edición: separa el título de subsección (h3 de acta) del contenido siguiente,
 * para que el label flotante del primer control no compita con el heading.
 */
const actaSubtituloMenorSx = {
  ...docModalSubheadingInCardSx,
  fontSize: "0.6875rem",
  fontWeight: 600,
  opacity: 0.9,
  mb: 1.25,
} as const;

/** Aire entre el overline/resumen del bloque documental y el primer control (p. ej. Lugar y titular, formulario). */
const edicionGapBloqueAPrimerControlSx = { mt: 2 } as const;

const dateFieldShrinkLabelProps = { shrink: true } as const;

function dash(v: unknown): string {
  if (v === null || v === undefined || v === "") return "—";
  return String(v);
}

function LecturaDato({
  label,
  value,
  fullWidth = false,
  plain = false,
}: {
  label: string;
  value: unknown;
  fullWidth?: boolean;
  /** Condiciones verificadas u otros datos no-campo: sin shell documental. */
  plain?: boolean;
}) {
  const wrapSx = fullWidth ? { gridColumn: "1 / -1", minWidth: 0, width: "100%" } : { minWidth: 0, width: "100%" };
  if (plain) {
    return (
      <Box sx={wrapSx}>
        <Typography component="span" sx={lecturaLabelSx}>
          {label}
        </Typography>
        <Typography component="p" variant="body2" sx={lecturaValueSx}>
          {dash(value)}
        </Typography>
      </Box>
    );
  }
  const texto = String(value ?? "").trim();
  const multilinea = texto.includes("\n") || texto.length > 48;
  if (!multilinea) {
    return (
      <Box sx={wrapSx}>
        <CrudFieldView label={label} value={value} />
      </Box>
    );
  }
  return (
    <Box sx={wrapSx}>
      <Typography component="label" sx={crudFieldSlotLabelSx}>
        {label}
      </Typography>
      <Box
        sx={mergeSx(crudReadonlyFieldShellSx, {
          height: "auto",
          minHeight: CRUD_FIELD_INPUT_HEIGHT_PX,
          maxHeight: "none",
          alignItems: "flex-start",
          py: 1,
        })}
      >
        <Typography variant="body2" sx={mergeSx(crudReadonlyFieldValueSx, { whiteSpace: "pre-line" })}>
          {dash(value)}
        </Typography>
      </Box>
    </Box>
  );
}

function LecturaBloque({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <DocumentalBloque overline={titulo} sectionTitleSx={lecturaSectionTitleSx}>
      {children}
    </DocumentalBloque>
  );
}

function actuacionHeaderReference(row: IActuacionListItem): string | null {
  const reference = resolveCrudDialogHeaderReference(row.orden_trabajo_numero, Number(row.id));
  if (!reference?.startsWith("OT ")) return reference;
  const year = String(row.fecha_actuacion ?? "").match(/^(\d{4})/)?.[1];
  return year ? `${reference} · ${year}` : reference;
}

function titleCaseNumeroTipo(value: string): string {
  return value
    .toLocaleLowerCase("es")
    .replaceAll("_", " ")
    .replace(/\b\p{L}/gu, (letter) => letter.toLocaleUpperCase("es"));
}

/** Línea principal del domicilio en la ficha de lectura. */
export function actuacionDetalleDomicilioLinea(row: IActuacionListItem): string {
  const calle = String(row.domicilio?.calle ?? row.calle ?? "").trim();
  const numeroTipo = String(row.numero_tipo ?? "").trim().toUpperCase();
  const complemento = String(
    numeroTipo === "ESQUINA"
      ? row.domicilio?.esquina ?? row.domicilio?.numero ?? row.numero ?? ""
      : row.domicilio?.numero ?? row.domicilio?.esquina ?? row.numero ?? ""
  ).trim();
  if (!calle) return complemento || "—";
  if (!complemento) return calle;
  return numeroTipo === "ESQUINA" ? `${calle} y ${complemento}` : `${calle} ${complemento}`;
}

/** Oculta NUMERO/NÚMERO por ser el caso convencional; presenta los casos especiales. */
export function actuacionDetalleNumeroTipoVisible(
  numeroTipo: string | null | undefined
): string | null {
  const raw = String(numeroTipo ?? "").trim();
  if (!raw) return null;
  const normalized = raw.normalize("NFD").replace(/\p{Diacritic}/gu, "").toUpperCase();
  if (normalized === "NUMERO") return null;
  if (normalized === "SIN_NUMERO") return "Sin número";
  if (normalized === "ESQUINA") return "Esquina";
  if (normalized === "REFERENCIA") return "Referencia";
  return titleCaseNumeroTipo(raw);
}

/** Texto de vinculación a establecimiento sin exponer IDs internos. */
function establecimientoVinculacionTexto(row: IActuacionListItem): string {
  if (row.establecimiento_operativo_id == null) return "—";
  if (row.establecimiento_actuaciones_en_ficha != null) {
    const n = row.establecimiento_actuaciones_en_ficha;
    return n === 1 ? "1 actuación en ficha vinculada" : `${n} actuaciones en ficha vinculada`;
  }
  return "Vinculado a ficha de establecimiento";
}

function motivosNotificacionNoVacios(draft: IActuacionListItem): string[] {
  return [draft.notificacion_motivo_1, draft.notificacion_motivo_2, draft.notificacion_motivo_3]
    .map((x) => (x != null ? String(x).trim() : ""))
    .filter(Boolean);
}

/** True si hay al menos un dato de acta para mostrar (misma lógica que `ActasVisitaLectura`). */
function actasVisitaHayContenido(draft: IActuacionListItem): boolean {
  const nIns = draft.acta_inspeccion_num;
  const nNot = draft.acta_notificacion_num;
  const nComp = draft.acta_comprobacion_num;
  const nClau = draft.acta_clausura_num;
  const nDec = draft.acta_decomiso_num;
  const kg = draft.decomiso_kilos_total;
  const motivosNoti = motivosNotificacionNoVacios(draft);
  const mComp = hydrateMotivosComprobacion(draft);
  const notificacionOrigen =
    draft.origen_reinspeccion_notificacion?.notificacion_acta_numero?.trim() ?? "";
  const comprobacionOrigen =
    draft.origen_reinspeccion_oficio?.comprobacion_acta_numero?.trim() ?? "";
  const showInspeccion = !!(nIns != null && String(nIns).trim() !== "");
  const showNotificacion =
    (nNot != null &&
      String(nNot).trim() !== "" &&
      String(nNot).trim() !== notificacionOrigen) ||
    motivosNoti.length > 0;
  const showComprobacion =
    (nComp != null &&
      String(nComp).trim() !== "" &&
      String(nComp).trim() !== comprobacionOrigen) ||
    mComp.length > 0;
  const showClausura = !!(nClau != null && String(nClau).trim() !== "");
  const showDecomiso = (nDec != null && String(nDec).trim() !== "") || kg != null;
  return showInspeccion || showNotificacion || showComprobacion || showClausura || showDecomiso;
}

/** Snapshot EpiCollect en lectura: hay algo que mostrar más allá del flag `has_epicollect_detalle`. */
function epicollectSnapshotLecturaHayContenido(draft: IActuacionListItem): boolean {
  if (!draft.has_epicollect_detalle) return false;
  const uuid = draft.ec5_uuid?.trim();
  const sectores = draft.epicollect_sectores_condiciones ?? [];
  const otrosRaw = draft.epicollect_otros_preview ?? draft.epicollect_preview ?? [];
  const otrosUtiles = otrosRaw.some((p) => String(p.value_preview ?? p.field_id ?? "").trim());
  return Boolean(uuid) || sectores.length > 0 || otrosUtiles;
}

/**
 * Lectura documental de actas por tipo: número destacado, datos secundarios subordinados.
 */
function ActasVisitaLectura({
  draft,
  catalog,
  lockedNotif,
}: {
  draft: IActuacionListItem;
  catalog: IItemActaInspeccionCatalogItem[];
  lockedNotif: boolean;
}) {
  const nIns = draft.acta_inspeccion_num;
  const nNot = draft.acta_notificacion_num;
  const nComp = draft.acta_comprobacion_num;
  const nClau = draft.acta_clausura_num;
  const nDec = draft.acta_decomiso_num;
  const kg = draft.decomiso_kilos_total;
  const motivosNoti = motivosNotificacionNoVacios(draft);
  const mComp = hydrateMotivosComprobacion(draft);
  const notificacionOrigen =
    draft.origen_reinspeccion_notificacion?.notificacion_acta_numero?.trim() ?? "";
  const comprobacionOrigen =
    draft.origen_reinspeccion_oficio?.comprobacion_acta_numero?.trim() ?? "";

  const showInspeccion = !!(nIns != null && String(nIns).trim() !== "");
  const showNotificacion =
    (nNot != null &&
      String(nNot).trim() !== "" &&
      String(nNot).trim() !== notificacionOrigen) ||
    motivosNoti.length > 0;
  const showComprobacion =
    (nComp != null &&
      String(nComp).trim() !== "" &&
      String(nComp).trim() !== comprobacionOrigen) ||
    mComp.length > 0;
  const showClausura = !!(nClau != null && String(nClau).trim() !== "");
  const showDecomiso =
    (nDec != null && String(nDec).trim() !== "") || kg != null;

  const hayAlgunaActa = showInspeccion || showNotificacion || showComprobacion || showClausura || showDecomiso;

  if (!hayAlgunaActa) {
    return null;
  }

  const numNot =
    nNot != null &&
    String(nNot).trim() !== "" &&
    String(nNot).trim() !== notificacionOrigen
      ? dash(nNot)
      : "—";
  const numComp =
    nComp != null &&
    String(nComp).trim() !== "" &&
    String(nComp).trim() !== comprobacionOrigen
      ? dash(nComp)
      : "—";
  const numDec = (nDec != null && String(nDec).trim() !== "") ? dash(nDec) : "—";

  const showPersonasSinCarnet =
    !lockedNotif &&
    isValidActaNotificacionNum(nNot != null ? String(nNot) : null) &&
    String(nNot).trim() !== notificacionOrigen;
  const seguimientoLectura = mergeActuacionSeguimientoFromApiRow(draft);
  const telefonoCarnetLectura = seguimientoLectura.telefono_contacto_solicitud_carnet?.trim() ?? "";
  const estados = estadosMapFromRow(draft, catalog);
  const readItems = normalizeChecklistItems(draft.items_acta_inspeccion);
  const readById = new Map(readItems.map((item) => [item.id, item]));
  const checklist = (
    catalog.length > 0
      ? catalog.map((item) => {
          const value = estados[item.id] ?? "NONE";
          return {
            id: item.id,
            label: displayItemNombre(item),
            value:
              value === "SI"
                ? "Sí"
                : value === "NO"
                  ? "No"
                  : value === "BIEN"
                    ? displayChecklistEstadoBienLabel(item.codigo)
                    : value === "OBSERVADO"
                      ? "Observado"
                      : "—",
          };
        })
      : readItems.map((item) => ({
          id: item.id,
          label: item.nombre?.trim() || item.codigo?.trim() || `Condición ${item.id}`,
          value:
            item.tipo_respuesta === "SI_NO"
              ? item.valor_si_no === true
                ? "Sí"
                : item.valor_si_no === false
                  ? "No"
                  : "—"
              : item.estado === "BIEN"
                ? displayChecklistEstadoBienLabel(item.codigo)
                : item.estado === "OBSERVADO"
                  ? "Observado"
                  : "—",
        }))
  ).filter((item) => item.value !== "—" || readById.has(item.id));

  const condicionesOperativas: Array<{ id: string; label: string; value: string }> = [
    {
      id: "caracter",
      label: "Carácter de quien atendió",
      value: labelCaracterPersonaAtendio(draft.caracter_persona_atendio) || "—",
    },
    {
      id: "contrato",
      label: "Contrato de retiro de residuos sólidos urbanos",
      value: labelContratoResiduos(contratoResiduosFromRow(draft)) || "—",
    },
    ...checklist.map((item) => ({
      id: `item-${item.id}`,
      label: item.label,
      value: item.value,
    })),
    {
      id: "carnet",
      label: "Solicita carnet de manipulador",
      value: siNoLectura(seguimientoLectura.solicita_carnet_manipulador),
    },
  ];
  if (telefonoCarnetLectura) {
    condicionesOperativas.push({
      id: "telefono",
      label: "Teléfono de contacto",
      value: telefonoCarnetLectura,
    });
  }

  return (
    <Box sx={{ ...col, width: "100%" }}>
      {showInspeccion ? (
        <Box>
          <LecturaDato label="N.º acta de inspección" value={nIns} />
          <Box sx={{ mt: 1.5 }}>
            <Typography component="h4" sx={lecturaLabelSx}>
              Condiciones verificadas
            </Typography>
            <Box sx={lecturaGridSx}>
              {condicionesOperativas.map((item) => (
                <LecturaDato key={item.id} label={item.label} value={item.value} plain />
              ))}
            </Box>
          </Box>
        </Box>
      ) : null}
      <Box sx={lecturaGridSx}>
        {showNotificacion ? (
          <LecturaDato label="N.º acta de notificación" value={numNot} />
        ) : null}
        {showComprobacion ? (
          <LecturaDato label="N.º acta de comprobación" value={numComp} />
        ) : null}
        {showClausura ? (
          <LecturaDato label="N.º acta de clausura" value={nClau} />
        ) : null}
        {showDecomiso ? (
          <LecturaDato label="N.º acta de decomiso" value={numDec} />
        ) : null}
      </Box>
      {motivosNoti.length > 0 ? (
        <LecturaDato
          label="Motivos de notificación"
          value={motivosNoti.join(" · ")}
          fullWidth
        />
      ) : null}
      {showPersonasSinCarnet ? (
        <LecturaDato
          label="Cantidad de personas sin carnet de sanidad"
          value={cantidadPersonasSinCarnetFromRow(draft)}
        />
      ) : null}
      {mComp.length > 0 ? (
        <LecturaDato
          label="Motivos de comprobación"
          value={motivosComprobacionLecturaMultilinea(mComp)}
          fullWidth
        />
      ) : null}
      {kg != null ? (
        <LecturaDato label="Kilos decomisados" value={`${kg} kg`} />
      ) : null}
    </Box>
  );
}

function DocumentalBloque({
  overline,
  resumen,
  sectionTitleSx,
  children,
}: {
  overline: string;
  resumen?: string;
  sectionTitleSx?: SxProps<Theme>;
  children: ReactNode;
}) {
  return (
    <CrudDialogSection title={overline} variant="plain" titleSx={sectionTitleSx}>
      {resumen ? (
        <Typography component="div" sx={{ ...docModalBlockResumenSx, mb: 1 }}>
          {resumen}
        </Typography>
      ) : null}
      {children}
    </CrudDialogSection>
  );
}

function tieneRestriccionesEdicion(row: IActuacionListItem): boolean {
  return tieneExpedienteBloqueoEdicion(row);
}

/** Texto de restricciones cuando hay bloqueo; solo se usa si `tieneRestriccionesEdicion`. */
function textoRestriccionesEdicion(row: IActuacionListItem): string {
  const parts: string[] = [];
  if (row.notificacion_editable === false) {
    parts.push("La notificación tiene expediente asociado: no puede editarse desde esta pantalla.");
  }
  if (row.comprobacion_editable === false) {
    parts.push("La comprobación tiene expediente de envío: no puede editarse desde esta pantalla.");
  }
  return parts.join(" ");
}

/** Trámite propio u origen de reinspección (sin «Cumpl. oficio»; va aparte en Resultado). */
function documentacionTramiteModalTieneContenido(d: IActuacionListItem): boolean {
  return (
    actuacionDocumentacionPropiaTramiteSegments(d).length > 0 ||
    actuacionDocumentacionOrigenReinspeccionSegments(d).length > 0
  );
}

function inspectoresLinea(row: IActuacionListItem): string {
  const parts = [row.inspector1, row.inspector2, row.inspector3].filter((x) => x?.trim());
  return parts.length ? parts.join(", ") : "—";
}

function gestionSeguimientoBloqueVisible(
  draft: IActuacionListItem,
  opts?: { omitCarnet?: boolean }
): boolean {
  const policy = draft.ui_policy;
  const showCarnet = Boolean(policy?.mostrar_solicitud_carnet_manipulador) && !opts?.omitCarnet;
  return Boolean(showCarnet || policy?.mostrar_subsanacion_notificacion);
}

function resultadoLecturaHayContenido(draft: IActuacionListItem): boolean {
  const circuito = draft.documentacion_contexto?.circuito;
  const tieneResultado = Boolean(draft.resultado_cumplimiento_oficio?.trim());
  const tieneTramitePropio =
    circuito !== "REINSPECCION_OFICIO" &&
    circuito !== "REINSPECCION_NOTIFICACION" &&
    actuacionDocumentacionPropiaTramiteSegments(draft).length > 0;
  return tieneResultado || tieneTramitePropio;
}

function antecedentesSeguimientoHayContenido(draft: IActuacionListItem): boolean {
  const hasActa = Boolean(String(draft.acta_inspeccion_num ?? "").trim());
  return Boolean(
    draft.origen_reinspeccion_oficio ||
      draft.origen_reinspeccion_notificacion ||
      gestionSeguimientoBloqueVisible(draft, { omitCarnet: hasActa })
  );
}

function ContextoEdicionFallback({ draft }: { draft: IActuacionListItem }) {
  const domicilio = formatGestionDomicilioLinea(draft);
  const contribuyente = formatGestionContribuyenteNombre(draft);
  const domicilioEditable = [draft.calle, draft.numero]
    .map((value) => String(value ?? "").trim())
    .filter(Boolean)
    .join(" ");
  const showDomicilio =
    domicilio.trim() !== "" && domicilio.trim() !== domicilioEditable.trim();
  const showContribuyente =
    !String(draft.contrib_nombre ?? "").trim() &&
    !String(draft.contrib_apellido ?? "").trim() &&
    contribuyente.trim() !== "";
  if (!showDomicilio && !showContribuyente) return null;

  return (
    <Box
      sx={{
        mb: 2,
        p: 1.25,
        borderRadius: 1.5,
        bgcolor: "rgba(255,255,255,0.04)",
        border: "1px solid rgba(255,255,255,0.08)",
      }}
    >
      <Typography component="h3" sx={actaSubtituloMenorSx}>
        Datos registrados
      </Typography>
      <Stack spacing={1}>
        {showDomicilio ? (
          <LecturaDato
            label="Domicilio"
            value={gestionContextoDisplayValue(domicilio)}
            plain
          />
        ) : null}
        {showContribuyente ? (
          <LecturaDato
            label="Contribuyente"
            value={gestionContextoDisplayValue(contribuyente)}
            plain
          />
        ) : null}
      </Stack>
    </Box>
  );
}

/** F2.4: trámite propio en chips; origen de reinspección en líneas bajo «Trámite origen». */
function DocumentacionTramiteModalLectura({ draft }: { draft: IActuacionListItem }) {
  const propia = actuacionDocumentacionPropiaTramiteSegments(draft);
  const origen = actuacionDocumentacionOrigenReinspeccionSegments(draft);
  if (!propia.length && !origen.length) {
    return null;
  }
  return (
    <Stack spacing={2} sx={{ width: "100%" }}>
      {propia.length ? (
        <Box>
          <Typography component="h3" sx={docModalSubheadingInCardSx}>
            Trámite documental
          </Typography>
          <Box sx={{ mt: 0.75 }}>
            <ActuacionDocumentacionChips labels={propia} chipSx={documentacionTramiteChipModalSx} />
          </Box>
        </Box>
      ) : null}
      {origen.length ? (
        <Box>
          <Typography component="h3" sx={docModalSubheadingInCardSx}>
            Trámite origen
          </Typography>
          <Stack spacing={0.5} sx={{ mt: 0.75 }}>
            {origen.map((line, i) => (
              <Typography key={`${line}-${i}`} component="p" variant="body2" sx={tramiteOrigenLineaSx}>
                {line}
              </Typography>
            ))}
          </Stack>
        </Box>
      ) : null}
    </Stack>
  );
}

function formatNumeroAnio(
  numero: string | number | null | undefined,
  anio: string | number | null | undefined
): string | null {
  const numeroTexto = String(numero ?? "").trim();
  if (!numeroTexto) return null;
  const anioTexto = String(anio ?? "").trim();
  return anioTexto ? `${numeroTexto}/${anioTexto}` : numeroTexto;
}

function siNoLectura(value: boolean | null | undefined): string {
  return value === true ? "Sí" : value === false ? "No" : "—";
}

/** Resultado propio de la actuación, sin repetir antecedentes de reinspección. */
function ResultadoOperativoLectura({ draft }: { draft: IActuacionListItem }) {
  const circuito = draft.documentacion_contexto?.circuito;
  const resultado = draft.resultado_cumplimiento_oficio?.trim() ?? "";
  const tramitePropio =
    circuito === "REINSPECCION_OFICIO" || circuito === "REINSPECCION_NOTIFICACION"
      ? []
      : actuacionDocumentacionPropiaTramiteSegments(draft);

  return (
    <Stack spacing={1.25}>
      {resultado ? (
        <LecturaDato label="Resultado de cumplimiento" value={resultado} />
      ) : null}
      {tramitePropio.length > 0 ? (
        <LecturaDato
          label="Trámite documental"
          value={tramitePropio.join("\n")}
          fullWidth
        />
      ) : null}
    </Stack>
  );
}

/** Antecedentes consolidados: cada dato de origen se presenta una sola vez. */
function AntecedentesSeguimientoLectura({ draft }: { draft: IActuacionListItem }) {
  const oficio = draft.origen_reinspeccion_oficio;
  const notificacion = draft.origen_reinspeccion_notificacion;
  const seguimiento = mergeActuacionSeguimientoFromApiRow(draft);
  const policy = draft.ui_policy;
  const origenNotificacion =
    formatNumeroAnio(
      notificacion?.notificacion_acta_numero,
      notificacion?.notificacion_acta_anio
    ) ??
    (draft.seguimiento?.notificacion_origen_numero?.trim() || null);
  const causa = oficio?.oficio_causa?.trim() ?? "";
  const resultado = draft.resultado_cumplimiento_oficio?.trim() ?? "";
  const causaAportaDato =
    causa !== "" && causa.toLocaleLowerCase("es") !== resultado.toLocaleLowerCase("es");

  return (
    <Stack
      spacing={2}
      divider={<Divider sx={{ borderColor: GLASS_COLORS.borderLight }} flexItem />}
    >
      {oficio ? (
        <Box>
          <Typography component="h3" sx={docModalSubheadingInCardSx}>
            Reinspección por oficio
          </Typography>
          <Box sx={{ ...lecturaGridSx, mt: 1 }}>
            {formatNumeroAnio(
              oficio.comprobacion_acta_numero,
              oficio.comprobacion_acta_anio
            ) ? (
              <LecturaDato
                label="Comprobación de origen"
                value={formatNumeroAnio(
                  oficio.comprobacion_acta_numero,
                  oficio.comprobacion_acta_anio
                )}
              />
            ) : null}
            {formatNumeroAnio(oficio.expediente_numero, oficio.expediente_anio) ? (
              <LecturaDato
                label="Expediente"
                value={formatNumeroAnio(oficio.expediente_numero, oficio.expediente_anio)}
              />
            ) : null}
            {formatNumeroAnio(oficio.oficio_numero, oficio.oficio_anio) ? (
              <LecturaDato
                label="Oficio"
                value={formatNumeroAnio(oficio.oficio_numero, oficio.oficio_anio)}
              />
            ) : null}
            {causaAportaDato ? <LecturaDato label="Causa" value={causa} fullWidth /> : null}
          </Box>
        </Box>
      ) : null}

      {notificacion || policy?.mostrar_subsanacion_notificacion ? (
        <Box>
          <Typography component="h3" sx={docModalSubheadingInCardSx}>
            Reinspección por notificación
          </Typography>
          <Box sx={{ ...lecturaGridSx, mt: 1 }}>
            {origenNotificacion ? (
              <LecturaDato label="Notificación de origen" value={origenNotificacion} />
            ) : null}
            {notificacion &&
            formatNumeroAnio(notificacion.expediente_numero, notificacion.expediente_anio) ? (
              <LecturaDato
                label="Expediente"
                value={formatNumeroAnio(
                  notificacion.expediente_numero,
                  notificacion.expediente_anio
                )}
              />
            ) : null}
            {policy?.mostrar_subsanacion_notificacion ? (
              <LecturaDato
                label="Faltas subsanadas"
                value={siNoLectura(seguimiento.faltas_notificacion_subsanadas)}
              />
            ) : null}
          </Box>
        </Box>
      ) : null}

      {policy?.mostrar_solicitud_carnet_manipulador &&
      !String(draft.acta_inspeccion_num ?? "").trim() ? (
        <Box>
          <Typography component="h3" sx={docModalSubheadingInCardSx}>
            Solicitud de carnet
          </Typography>
          <Box sx={{ ...lecturaGridSx, mt: 1 }}>
            <LecturaDato
              label="Solicita carnet de manipulador"
              value={siNoLectura(seguimiento.solicita_carnet_manipulador)}
            />
            {seguimiento.telefono_contacto_solicitud_carnet?.trim() ? (
              <LecturaDato
                label="Teléfono de contacto"
                value={seguimiento.telefono_contacto_solicitud_carnet.trim()}
              />
            ) : null}
          </Box>
        </Box>
      ) : null}
    </Stack>
  );
}

function BloqueEpicollectDetalleLectura({
  draft,
  otrosExpanded,
  onToggleOtros,
  embedded,
}: {
  draft: IActuacionListItem;
  otrosExpanded: boolean;
  onToggleOtros: () => void;
  /** Sin marco propio: va dentro de un bloque documental padre. */
  embedded?: boolean;
}) {
  if (!epicollectSnapshotLecturaHayContenido(draft)) return null;

  const sectores = draft.epicollect_sectores_condiciones ?? [];
  const otrosRaw = draft.epicollect_otros_preview ?? draft.epicollect_preview ?? [];
  const otros = otrosRaw.filter((p) => String(p.value_preview ?? p.field_id ?? "").trim());
  const uuid = draft.ec5_uuid?.trim();

  const listSx = {
    m: 0,
    pl: 2,
    pt: 0.5,
    color: DOC_MODAL_TEXT,
    fontSize: "0.8125rem",
    lineHeight: 1.45,
    fontWeight: 400,
  } as const;

  const captionSubseccionSx = {
    color: DOC_MODAL_TEXT,
    fontWeight: 700,
    textTransform: "uppercase" as const,
    letterSpacing: "0.04em",
    display: "block",
    mb: 0.75,
  };

  return (
    <Box sx={embedded ? { mb: 2 } : blockShellSx}>
      {!embedded ? (
        <Typography variant="subtitle2" sx={{ ...sectionTitleSx, mt: 0, mb: 1.25 }}>
          Formulario de campo
        </Typography>
      ) : null}

      {uuid ? (
        <Box sx={{ mb: sectores.length > 0 || otros.length > 0 ? 1.25 : 0 }}>
          <Typography variant="body2" sx={{ color: DOC_MODAL_TEXT, fontWeight: 400, lineHeight: 1.5 }}>
            <Box component="span" sx={{ opacity: 0.82 }}>
              Identificador
            </Box>
            <Box
              component="span"
              sx={{ fontFamily: "monospace", fontSize: "0.8125rem", ml: 0.75, wordBreak: "break-all" }}
            >
              {uuid}
            </Box>
          </Typography>
        </Box>
      ) : null}

      {sectores.length > 0 ? (
        <Box sx={{ mb: otros.length > 0 ? 1.25 : 0 }}>
          <Typography variant="caption" sx={captionSubseccionSx}>
            Condiciones
          </Typography>
          <Box component="ul" sx={listSx}>
            {sectores.map((s) => (
              <Box component="li" key={s.field_id} sx={{ mb: 0.6 }}>
                <Typography
                  variant="body2"
                  component="span"
                  sx={{ color: DOC_MODAL_TEXT, fontSize: "inherit", fontWeight: 600 }}
                >
                  {s.label}
                </Typography>
                {": "}
                <Typography variant="body2" component="span" sx={{ color: DOC_MODAL_TEXT, fontSize: "inherit", fontWeight: 500 }}>
                  {s.value_preview}
                </Typography>
              </Box>
            ))}
          </Box>
        </Box>
      ) : null}

      {otros.length > 0 ? (
        <>
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mb: 0.5 }}>
            <Typography variant="caption" sx={{ ...captionSubseccionSx, mb: 0, flex: "1 1 auto" }}>
              Otros datos
            </Typography>
            <IconButton
              size="small"
              onClick={onToggleOtros}
              aria-expanded={otrosExpanded}
              aria-label={otrosExpanded ? "Contraer lista" : "Expandir lista"}
              sx={{
                color: DOC_MODAL_TEXT,
                transform: otrosExpanded ? "rotate(180deg)" : "none",
                transition: "transform 0.2s ease",
              }}
            >
              <ExpandMoreIcon fontSize="small" />
            </IconButton>
          </Box>
          <Collapse in={otrosExpanded}>
            <Box component="ul" sx={{ ...listSx, pt: 0 }}>
              {otros.map((p, idx) => {
                const val = String(p.value_preview ?? "").trim();
                const line = val || String(p.field_id ?? "").trim();
                return (
                  <Box component="li" key={`${p.field_id}-${idx}`} sx={{ mb: 0.75 }}>
                    <Typography
                      variant="body2"
                      component="span"
                      sx={{ color: DOC_MODAL_TEXT, fontSize: "inherit", fontWeight: 500 }}
                    >
                      {line}
                    </Typography>
                  </Box>
                );
              })}
            </Box>
          </Collapse>
        </>
      ) : null}
    </Box>
  );
}

function BloqueEvidenciasEpicollect({ draft, embedded }: { draft: IActuacionListItem; embedded?: boolean }) {
  const total = draft.epicollect_evidencias_total ?? 0;
  const grupos = draft.epicollect_evidencias_grupos ?? [];
  if (total <= 0 || grupos.length === 0) return null;

  return (
    <Box sx={embedded ? { mb: 0 } : blockShellSx}>
      <Typography
        variant="subtitle2"
        sx={
          embedded
            ? { color: DOC_MODAL_TEXT, fontWeight: 700, mt: 0, mb: 1, display: "block" }
            : { ...sectionTitleSx, mt: 0, mb: 1 }
        }
      >
        Evidencias multimedia
      </Typography>
      <Typography variant="body2" sx={{ color: DOC_MODAL_TEXT, fontWeight: 400, mb: 1.25, lineHeight: 1.5 }}>
        Archivos vinculados desde EpiCollect (por categoría).{" "}
        <strong>{total}</strong> evidencia{total === 1 ? "" : "s"} en total. Los enlaces abren en otra pestaña.
      </Typography>
      {grupos.map((g) => {
        const links = g.items.filter((it) => it.url && String(it.url).trim() !== "");
        return (
          <Box key={g.categoria} sx={{ mb: 1.5 }}>
            <Typography variant="body2" sx={{ color: DOC_MODAL_TEXT, fontWeight: 700, mb: 0.5 }}>
              {g.label}: {g.count} {g.count === 1 ? "archivo" : "archivos"}
            </Typography>
            {links.length > 0 ? (
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, columnGap: 1.25, rowGap: 0.5 }}>
                {links.map((it, idx) => (
                  <Link
                    key={`${g.categoria}-${it.orden}-${idx}`}
                    href={it.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    underline="hover"
                    variant="body2"
                    sx={{
                      color: DOC_MODAL_TEXT,
                      fontWeight: 600,
                      fontSize: "0.8125rem",
                      textDecoration: "underline",
                      textDecorationColor: COLORS.primary,
                    }}
                  >
                    Ver {idx + 1}
                  </Link>
                ))}
              </Box>
            ) : (
              <Typography variant="caption" sx={{ color: DOC_MODAL_TEXT, fontWeight: 500, fontStyle: "italic" }}>
                Sin URL registrada
              </Typography>
            )}
          </Box>
        );
      })}
    </Box>
  );
}

function ActaSeguimientoGestionFields({
  draft,
  onDraftChange,
  fieldErrors,
  saving,
  readOnly,
  omitCarnet = false,
}: {
  draft: IActuacionListItem;
  onDraftChange?: (patch: Partial<IActuacionListItem> | IActuacionListItem) => void;
  fieldErrors: Record<string, string>;
  saving: boolean;
  readOnly: boolean;
  omitCarnet?: boolean;
}) {
  const policy = draft.ui_policy;
  const showCarnet = Boolean(policy?.mostrar_solicitud_carnet_manipulador) && !omitCarnet;
  const showSubs = Boolean(policy?.mostrar_subsanacion_notificacion);
  if (!showCarnet && !showSubs) return null;

  const puedeEditar = Boolean(policy?.puede_editar_seguimiento);
  const controlsEnabled = !readOnly && puedeEditar && !saving;

  const merged = mergeActuacionSeguimientoFromApiRow(draft);
  const solicitaUi = boolToSolicitaCarnetUi(merged.solicita_carnet_manipulador);
  const subsUi = boolToFaltasSubsanadasUi(merged.faltas_notificacion_subsanadas);
  const tel = (merged.telefono_contacto_solicitud_carnet ?? "").trim();
  const origenNum =
    (draft.seguimiento?.notificacion_origen_numero ?? "").trim() ||
    (draft.origen_reinspeccion_notificacion?.notificacion_acta_numero ?? "").trim() ||
    null;

  const patchSeguimiento = (partial: {
    solicitaCarnet?: "" | "si" | "no";
    telefonoCarnet?: string;
    faltasSubsanadas?: "" | "si" | "no";
  }) => {
    if (!onDraftChange || readOnly || !puedeEditar) return;
    const base = gestionSeguimientoDraftFromRow(draft);
    const next = { ...base, ...partial };
    if (partial.solicitaCarnet === "no") {
      next.telefonoCarnet = "";
    }
    onDraftChange(applyGestionSeguimientoDraftToRow(draft, next));
  };

  const fe = (k: string) => fieldErrors[k] ?? "";

  return (
    <Box sx={{ ...col, width: "100%", mt: 2 }}>
      {showCarnet ? (
        <Box sx={{ mb: showSubs ? 2.5 : 0 }}>
          <Typography variant="subtitle2" sx={{ color: GLASS_COLORS.textSecondary, mb: 0.5 }}>
            Solicitud de carnet de manipulador
          </Typography>
          <Typography variant="body2" sx={{ color: DOC_MODAL_TEXT, mb: 1 }}>
            ¿El personal presente solicita carnet de manipulador de alimentos?
          </Typography>
          <ToggleButtonGroup
            exclusive
            size="small"
            value={solicitaUi}
            disabled={!controlsEnabled}
            onChange={(_e, v: "" | "si" | "no" | null) => {
              if (!controlsEnabled) return;
              const next = v ?? "";
              patchSeguimiento({
                solicitaCarnet: next,
                telefonoCarnet: next === "si" ? tel : "",
              });
            }}
          >
            <ToggleButton value="si">Sí</ToggleButton>
            <ToggleButton value="no">No</ToggleButton>
          </ToggleButtonGroup>
          {fe("solicita_carnet_manipulador") ? (
            <Typography variant="caption" color="error" sx={{ mt: 0.5, display: "block" }}>
              {fe("solicita_carnet_manipulador")}
            </Typography>
          ) : null}
          {solicitaUi === "si" || (readOnly && tel) ? (
            <AppTextField
              appearance="glass"
              label="Teléfono de contacto del personal solicitante"
              value={tel}
              onChange={(e) => patchSeguimiento({ telefonoCarnet: e.target.value })}
              fullWidth
              sx={{ mt: 1.5 }}
              disabled={!controlsEnabled}
              inputProps={{ maxLength: 32, readOnly: readOnly || !controlsEnabled }}
              error={Boolean(fe("telefono_contacto_solicitud_carnet"))}
              helperText={fe("telefono_contacto_solicitud_carnet") || undefined}
            />
          ) : null}
        </Box>
      ) : null}
      {showSubs ? (
        <Box>
          <Typography variant="subtitle2" sx={{ color: GLASS_COLORS.textSecondary, mb: 0.5 }}>
            Resultado de la reinspección
          </Typography>
          {origenNum ? (
            <CrudFormSlot
              label="Notificación origen"
              mode="view"
              value={origenNum}
              sx={{ mb: 1.25 }}
            />
          ) : null}
          <InspeccionActaSegmentedRow
            label="¿Se subsanaron las faltas por las cuales se labró la notificación?"
            value={subsUi}
            allowDeselect
            disabled={!controlsEnabled}
            onChange={(next) => {
              if (!controlsEnabled) return;
              patchSeguimiento({ faltasSubsanadas: (next as "" | "si" | "no") || "" });
            }}
            options={[
              { value: "si", label: "Sí", ariaLabel: "Sí" },
              { value: "no", label: "No", ariaLabel: "No" },
            ]}
            error={fe("faltas_notificacion_subsanadas") || undefined}
          />
        </Box>
      ) : null}
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
  detailLoading = false,
  catalogs,
  catalogsLoading = false,
  catalogsError = null,
  readOnlyColumns,
  canEdit = true,
  inspectorSelfService = false,
  numeroEditorLabel = "Número o referencia",
  onClose,
  onDraftChange,
  onSave,
  onEditSaveSessionEnd,
  disablePortal,
  initialEditing = false,
  onRequestPhotosOnly,
  inspectorVerTrabajoMode = false,
}: ActuacionDetalleDialogProps) {
  const navigate = useNavigate();
  const feedback = useAppFeedback();
  const scrollContainerRef = useCrudDialogScrollContainer();
  const actaFlushRegistry = useRef<Set<() => void>>(new Set());
  const verificarInconsistentWarnedRef = useRef<number | string | null>(null);
  const mediaGalleryRef = useRef<ActuacionMediaGalleryHandle | null>(null);
  const [mediaDiscardConfirmOpen, setMediaDiscardConfirmOpen] = useState(false);
  const identidadTouchedRef = useRef<ContribuyenteIdentityTouched>({});
  const atencionTouchedRef = useRef<InspeccionAtencionTouched>({});
  const [isEditing, setIsEditing] = useState(initialEditing);
  const [photosOnlyMode, setPhotosOnlyMode] = useState(false);
  const [editBaseline, setEditBaseline] = useState<IActuacionListItem | null>(null);
  const puedeInspectorDatos = Boolean(draft.ui_policy?.puede_editar_datos_propios);
  const puedeInspectorFotos = Boolean(draft.ui_policy?.puede_gestionar_fotos_propias);
  const formEditingActive = inspectorSelfService ? isEditing && !photosOnlyMode : isEditing;
  const mediaReadOnly = inspectorVerTrabajoMode
    ? true
    : inspectorSelfService
      ? !(photosOnlyMode || (isEditing && puedeInspectorFotos))
      : !isEditing;
  const showInspectorModePicker =
    inspectorSelfService &&
    !inspectorVerTrabajoMode &&
    !formEditingActive &&
    !photosOnlyMode &&
    (puedeInspectorDatos || puedeInspectorFotos);
  const [epicollectOtrosExpanded, setEpicollectOtrosExpanded] = useState(false);
  const [inspectoresAddInput, setInspectoresAddInput] = useState("");
  const [oficioFieldErrors, setOficioFieldErrors] = useState<Record<string, string>>({});
  const [seguimientoFieldErrors, setSeguimientoFieldErrors] = useState<Record<string, string>>({});
  const oficioForm = useReinspeccionOficioFormState({ mode: "edit", initialRow: draft });
  const resetOficioFormFromRow = oficioForm.resetFromRow;

  const oficioFormCtx = useMemo(
    () => (isEditing ? resolveReinspeccionOficioFormContext({ row: draft, mode: "edit" }) : null),
    [isEditing, draft]
  );

  const editableFields = useMemo(
    () =>
      getActuacionEditableFields(draft, {
        verificarRealizoNuevaInspeccion: oficioForm.realizoNuevaInspeccion,
        oficioSubtipo: oficioFormCtx ? oficioForm.subtipo : undefined,
        verificarEstadoOperativo: oficioForm.esVerificar ? oficioForm.verificarEstadoOperativo : undefined,
        baselineRow: editBaseline ?? undefined,
      }),
    [
      draft,
      editBaseline,
      oficioForm.realizoNuevaInspeccion,
      oficioForm.subtipo,
      oficioForm.esVerificar,
      oficioForm.verificarEstadoOperativo,
      oficioFormCtx,
    ]
  );

  const dialogHeaderReference = useMemo(
    () => actuacionHeaderReference(draft),
    [draft]
  );

  const registerActaFlush = useCallback((fn: () => void) => {
    actaFlushRegistry.current.add(fn);
    return () => {
      actaFlushRegistry.current.delete(fn);
    };
  }, []);

  useEffect(() => {
    if (open) {
      setIsEditing(initialEditing);
      setPhotosOnlyMode(false);
      setEditBaseline(initialEditing ? { ...draft } : null);
      setEpicollectOtrosExpanded(false);
      setInspectoresAddInput("");
      resetOficioFormFromRow(draft);
      setOficioFieldErrors({});
      verificarInconsistentWarnedRef.current = null;
      actaFlushRegistry.current.clear();
      identidadTouchedRef.current = {};
      atencionTouchedRef.current = {};
    }
    // Solo al abrir o cambiar de actuación: no resetear si el padre actualiza `draft` al entrar en edición.
  }, [open, draft.id, initialEditing, resetOficioFormFromRow]);

  useEffect(() => {
    if (!isEditing || !editBaseline) return;
    const ctx = resolveReinspeccionOficioFormContext({ row: editBaseline, mode: "edit" });
    if (!ctx) return;
    resetOficioFormFromRow(editBaseline);
    const estadoResuelto = resolveVerificarEstadoFromPersisted(editBaseline);
    if (estadoResuelto === "INCONSISTENTE") {
      if (verificarInconsistentWarnedRef.current !== editBaseline.id) {
        verificarInconsistentWarnedRef.current = editBaseline.id;
        feedback.warning(MSG_VERIFICAR_LEGACY_INCONSISTENTE);
      }
    }
    setOficioFieldErrors({});
  }, [isEditing, editBaseline, feedback, resetOficioFormFromRow]);

  useEffect(() => {
    if (!open || !isEditing) return;
    scrollActuacionFormToFirstFieldError(scrollContainerRef?.current ?? null, fieldErrors);
  }, [open, isEditing, fieldErrors, scrollContainerRef]);

  const lockedNotif = draft.notificacion_editable === false;
  const lockedComp = draft.comprobacion_editable === false;

  const mergedCatalogs = useMemo(
    () => ({
      inspectores: catalogs.inspectores,
      motivos: catalogs.motivos,
      rubros: catalogs.rubros,
      tipos: catalogs.tipos,
      contraproducencias: catalogs.contraproducencias,
      motivosComprobacion: catalogs.motivosComprobacion,
    }),
    [
      catalogs.inspectores,
      catalogs.motivos,
      catalogs.rubros,
      catalogs.tipos,
      catalogs.contraproducencias,
      catalogs.motivosComprobacion,
    ]
  );

  const rubrosOptions = useMemo(
    () => opts(["", ...mergeLegacyRubroNames(catalogs.rubros, draft.rubro_nombre)]),
    [catalogs.rubros, draft.rubro_nombre]
  );

  const contraCrudOptions = useMemo(
    () => buildContraproducenciaCrudSelectOptions(mergedCatalogs.contraproducencias, draft.contraproducencia),
    [mergedCatalogs.contraproducencias, draft.contraproducencia]
  );

  const contraUxHint = useMemo(
    () => getContraproducenciaUxHint(draft.contraproducencia ?? ""),
    [draft.contraproducencia]
  );

  const oficioContraOpts = useMemo(() => {
    if (!oficioFormCtx || !oficioForm.subtipo.trim()) return [];
    const tipoIni =
      tipoIniciadorDesdeSubtipoActuacionOficio(oficioForm.subtipo) ??
      tipoIniciadorInferidoDesdeActuacion(draft);
    const filtradas = filtrarContraproducenciasPorTipoIniciador(
      mergedCatalogs.contraproducencias ?? [],
      tipoIni,
      oficioForm.contraproducencia,
      oficioForm.subtipo
    );
    return filtradas.map((s) => ({ value: s, label: s || "—" }));
  }, [draft, mergedCatalogs.contraproducencias, oficioForm.contraproducencia, oficioForm.subtipo, oficioFormCtx]);

  const muestraOficioResultadoEditable =
    isEditing && oficioFormCtx != null && editableFields.canEditResultadoOperativo;

  const tryCloseDialog = useCallback(() => {
    if (saving) return;
    const gallery = mediaGalleryRef.current;
    if (gallery?.isUploadInProgress()) return;
    const pending = gallery?.pendingSaveCount() ?? 0;
    if (formEditingActive && pending > 0) {
      setMediaDiscardConfirmOpen(true);
      return;
    }
    onClose();
  }, [formEditingActive, onClose, saving]);

  const handleClose = useCallback(() => {
    tryCloseDialog();
  }, [tryCloseDialog]);

  const handleDialogClose = useCallback(
    (_event: unknown, _reason: string) => {
      tryCloseDialog();
    },
    [tryCloseDialog]
  );

  const handlePrint = useCallback(() => {
    if (saving) return;
    window.print();
  }, [saving]);

  const handleStartEditing = useCallback(() => {
    const result = resolveActuacionEditStart(draft);
    if (!result.allowed) {
      feedback.warning(result.message);
      return;
    }
    const hydrated = domicilioRowParaEdicionCalle({ ...draft });
    setEditBaseline({ ...hydrated });
    identidadTouchedRef.current = {};
    setIsEditing(true);
    const patch: Partial<IActuacionListItem> = {};
    if (hydrated.calle !== draft.calle) patch.calle = hydrated.calle;
    if (hydrated.numero !== draft.numero) patch.numero = hydrated.numero;
    if (hydrated.numero_tipo !== draft.numero_tipo) patch.numero_tipo = hydrated.numero_tipo;
    if (Object.keys(patch).length > 0) {
      onDraftChange(patch);
    }
  }, [draft, feedback, onDraftChange]);

  const handleSaveClick = useCallback(async () => {
    if (inspectorSelfService && formEditingActive && !puedeInspectorDatos) {
      feedback.warning("No tenés permiso para editar los datos de esta actuación.");
      return;
    }
    if (catalogsLoading) {
      feedback.info("Esperá a que terminen de cargar los catálogos del formulario.");
      return;
    }
    if (catalogsError?.trim()) {
      feedback.warning(catalogsError.trim());
      return;
    }
    try {
      actaFlushRegistry.current.forEach((fn) => fn());
    } catch (err) {
      console.error("Error al preparar actas antes de guardar:", err);
      feedback.error(MENSAJE_ERROR_GRAVE);
      return;
    }
    const baseline = editBaseline ?? draft;
    const blockedMsg = detectBlockedActaClearAttempt(draft, baseline);
    if (blockedMsg) {
      feedback.warning(blockedMsg);
      return;
    }

    let rowForSubmit: IActuacionListItem = draft;
    let oficioCorrectionApplied = false;
    let actasClearedByOficioCorrection: ActaCanalQuitarTipo[] = [];
    const actasToClear = detectActasClearedByUser(baseline, draft).map((a) => a.tipo);

    const oficioCtx = resolveReinspeccionOficioFormContext({ row: draft, mode: "edit" });
    if (oficioCtx && editableFields.canEditResultadoOperativo) {
      const tieneActas = tieneActasInspeccionNormalPersistidas(draft);
      const validation = validateReinspeccionOficioForm({
        esRatificacion: oficioForm.esRatificacion,
        esVerificar: oficioForm.esVerificar,
        cumplimientoUi: oficioForm.cumplimientoUi,
        contraproducencia: oficioForm.contraproducencia,
        realizoNuevaInspeccion: oficioForm.realizoNuevaInspeccion,
        verificarEstadoOperativo: oficioForm.esVerificar ? oficioForm.verificarEstadoOperativo : undefined,
        tieneActasInspeccionNormal: tieneActas,
        subtipoPendiente: !oficioForm.subtipo.trim(),
      });
      if (!validation.ok) {
        setOficioFieldErrors({ [validation.field]: validation.message });
        feedback.warning(validation.message);
        return;
      }

      const dirty = oficioCorreccionDirty(
        {
          tipo_actuacion: baseline.tipo_actuacion,
          resultado_cumplimiento_oficio: baseline.resultado_cumplimiento_oficio,
          contraproducencia: baseline.contraproducencia,
          realizo_nueva_inspeccion: baseline.realizo_nueva_inspeccion,
        },
        {
          tipoActuacion: oficioForm.subtipo,
          cumplimientoUi: oficioForm.cumplimientoUi,
          contraproducencia: oficioForm.contraproducencia,
          realizoNuevaInspeccion: oficioForm.realizoNuevaInspeccion,
          verificarEstadoOperativo: oficioForm.esVerificar ? oficioForm.verificarEstadoOperativo : undefined,
        }
      );

      if (dirty) {
        try {
          const payload = {
            ...oficioCorreccionPayloadFromUi({
              tipoActuacion: oficioForm.subtipo,
              cumplimientoUi: oficioForm.cumplimientoUi,
              contraproducencia: oficioForm.contraproducencia,
              realizoNuevaInspeccion: oficioForm.realizoNuevaInspeccion,
              verificarEstadoOperativo: oficioForm.esVerificar ? oficioForm.verificarEstadoOperativo : undefined,
              esRatificacion: oficioForm.esRatificacion,
              esVerificar: oficioForm.esVerificar,
            }),
            ...(actasToClear.length > 0 ? { actas_a_quitar: actasToClear } : {}),
          };
          const updated = await corregirCierreOficio(Number(draft.id), payload);
          rowForSubmit = mergeActuacionAfterOficioCorrection({
            correctedRow: updated,
            pendingDraft: draft,
          });
          oficioCorrectionApplied = true;
          if (actasToClear.length > 0) {
            actasClearedByOficioCorrection = actasToClear;
          }
          onDraftChange(rowForSubmit);
          setEditBaseline((prev) => (prev ? { ...prev, ...rowForSubmit } : prev));
          oficioForm.resetFromRow(rowForSubmit);
          setOficioFieldErrors({});
        } catch (err) {
          const normalized = normalizeActuacionApiError(err, {
            fallbackMessage: "No se pudo corregir el cierre por oficio.",
          });
          setOficioFieldErrors(normalized.fieldErrors);
          notifyActuacionApiError(normalized, feedback);
          return;
        }
      }
    }

    const segErrors = {
      ...validateGestionSeguimientoFields(rowForSubmit, editBaseline),
      ...validateObservacionesVisitaFields(rowForSubmit),
    };
    if (Object.keys(segErrors).length > 0) {
      setSeguimientoFieldErrors(segErrors);
      if (segErrors.observaciones_ejecucion) {
        feedback.warning("Revise las observaciones de la visita antes de guardar.");
      } else {
        feedback.warning("Revise los datos de seguimiento de acta antes de guardar.");
      }
      return;
    }
    setSeguimientoFieldErrors({});

    try {
      const putOk = await onSave(rowForSubmit, {
        oficioCorrectionApplied,
        actasClearedByOficioCorrection,
        oficioValidationContext:
          oficioCtx != null
            ? {
                subtipo: oficioForm.subtipo,
                verificarEstadoOperativo: oficioForm.esVerificar ? oficioForm.verificarEstadoOperativo : "",
              }
            : undefined,
        inspeccionChecklistTouched: {
          items: checklistItemsTouchedRef.current,
          carnets: personasSinCarnetTouchedRef.current,
        },
        inspeccionAtencionTouched: { ...atencionTouchedRef.current },
        contribuyenteIdentityTouched: { ...identidadTouchedRef.current },
        inspeccionChecklistCatalog: catalogs.itemsActaInspeccion ?? [],
        deferDialogClose: true,
      });
      if (putOk === false) return;

      let sessionOutcome: "success" | "aborted" = "success";
      const gallery = mediaGalleryRef.current;
      if (gallery && gallery.pendingSaveCount() > 0) {
        const mediaOutcome = await gallery.saveQueuedPhotos();
        if (!shouldCloseInspectorFotosModalAfterSave(mediaOutcome)) {
          sessionOutcome = "aborted";
        }
      }

      if (onEditSaveSessionEnd) {
        onEditSaveSessionEnd(sessionOutcome);
        return;
      }
      if (sessionOutcome === "success") {
        onClose();
      }
    } catch (err) {
      console.error("Error al guardar actuación:", err);
      feedback.error(MENSAJE_ERROR_GRAVE);
    }
  }, [
    catalogs.itemsActaInspeccion,
    catalogsError,
    catalogsLoading,
    draft,
    editBaseline,
    editableFields.canEditResultadoOperativo,
    feedback,
    formEditingActive,
    inspectorSelfService,
    oficioForm,
    onDraftChange,
    onClose,
    onEditSaveSessionEnd,
    onSave,
    puedeInspectorDatos,
  ]);

  const applyInspectoresNombres = useCallback(
    (nombres: string[]) => {
      const dedup = [...new Set(nombres.map((x) => String(x).trim()).filter(Boolean))];
      onDraftChange({
        inspectores: dedup.length ? dedup : null,
        inspectores_texto: dedup.length ? dedup.join(", ") : null,
        inspector1: dedup[0] ?? null,
        inspector2: dedup[1] ?? null,
        inspector3: dedup[2] ?? null,
      });
    },
    [onDraftChange]
  );

  const applyMotivosNotificacion = useCallback(
    (sel: string[]) => {
      const o = orderedMotivosNotificacion(sel);
      onDraftChange({
        notificacion_motivo_1: o[0] ?? null,
        notificacion_motivo_2: o[1] ?? null,
        notificacion_motivo_3: o[2] ?? null,
      });
    },
    [onDraftChange]
  );

  const applyMotivosComprobacion = useCallback(
    (sel: string[]) => {
      const o = orderedMotivosComprobacion(sel);
      onDraftChange({
        motivos_comprobacion: o,
        comprobacion_motivo: primerMotivoComprobacionLegado(o),
      });
    },
    [onDraftChange]
  );

  const checklistItemsTouchedRef = useRef(false);
  const personasSinCarnetTouchedRef = useRef(false);
  const hydratedChecklistActIdRef = useRef<number | null>(null);
  const [checklistEstados, setChecklistEstados] = useState<Record<number, ChecklistUxValue>>(
    () => estadosMapFromRow(draft, catalogs.itemsActaInspeccion ?? [])
  );

  useEffect(() => {
    const catalog = catalogs.itemsActaInspeccion ?? [];
    const plan = planChecklistHydration({
      open,
      actId: draft.id,
      hydratedActId: hydratedChecklistActIdRef.current,
      touched: checklistItemsTouchedRef.current,
      catalogLength: catalog.length,
    });

    if (plan === "close") {
      hydratedChecklistActIdRef.current = null;
      return;
    }

    if (plan === "act_change") {
      checklistItemsTouchedRef.current = false;
      personasSinCarnetTouchedRef.current = false;
      identidadTouchedRef.current = {};
      atencionTouchedRef.current = {};
      hydratedChecklistActIdRef.current = draft.id;
      setChecklistEstados(estadosMapFromRow(draft, catalog));
      return;
    }

    if (plan === "catalog_late") {
      setChecklistEstados(estadosMapFromRow(draft, catalog));
    }
  }, [open, draft.id, draft.items_acta_inspeccion, catalogs.itemsActaInspeccion]);

  const commitActaInspeccion = useCallback(
    (value: string | null) => onDraftChange({ acta_inspeccion_num: value }),
    [onDraftChange]
  );
  const commitActaNotificacion = useCallback(
    (value: string | null) =>
      onDraftChange({
        acta_notificacion_num: value,
        ...(value == null
          ? {
              notificacion_motivo_1: null,
              notificacion_motivo_2: null,
              notificacion_motivo_3: null,
            }
          : {}),
      }),
    [onDraftChange]
  );
  const commitActaComprobacion = useCallback(
    (value: string | null) =>
      onDraftChange({
        acta_comprobacion_num: value,
        ...(value == null ? { comprobacion_motivo: null, motivos_comprobacion: [] } : {}),
      }),
    [onDraftChange]
  );
  const commitActaDecomiso = useCallback(
    (value: string | null) =>
      onDraftChange({
        acta_decomiso_num: value,
        ...(value == null ? { decomiso_kilos_total: null } : {}),
      }),
    [onDraftChange]
  );
  const commitActaClausura = useCallback(
    (value: string | null) => onDraftChange({ acta_clausura_num: value }),
    [onDraftChange]
  );

  const toggleEpicollectOtros = useCallback(() => {
    setEpicollectOtrosExpanded((v) => !v);
  }, []);

  const detalleVista = useMemo(() => {
    const tieneSnapshotEpicollectLectura = epicollectSnapshotLecturaHayContenido(draft);
    const gruposEvid = draft.epicollect_evidencias_grupos ?? [];
    const totalEvid = draft.epicollect_evidencias_total ?? 0;
    const tieneEvidenciasEpicollect = totalEvid > 0 && gruposEvid.length > 0;
    const tieneActas = actasVisitaHayContenido(draft);
    const tieneResultado = resultadoLecturaHayContenido(draft);
    const tieneAntecedentes = antecedentesSeguimientoHayContenido(draft);
    const mostrarOrigenActas = debeMostrarBloqueOrigenVerActuacion({
      actuacionId: draft.id,
      tipoActuacion: draft.tipo_actuacion,
      origenActas: draft.origen_actas,
    });
    const filasOrigenActas = mostrarOrigenActas
      ? filasOrigenActasVerActuacion(draft.origen_actas, draft.tipo_actuacion)
      : [];
    const observaciones = observacionesVisitaDisplayText(draft);
    const contribuyenteNombre =
      formatGestionContribuyenteNombre(draft) || draft.razon_social || "—";
    const domicilioLinea = actuacionDetalleDomicilioLinea(draft);
    const numeroTipoVisible = actuacionDetalleNumeroTipoVisible(draft.numero_tipo);
    const contraproducencia = String(draft.contraproducencia ?? "").trim();

    return (
    <Stack
      spacing={DOC_MODAL_BLOCK_STACK_SPACING}
      component="section"
      aria-label="Ficha de la actuación"
    >
      <LecturaBloque titulo="Visita y actuación">
        <Box sx={lecturaGridSx}>
          <LecturaDato label="Fecha" value={draft.fecha_actuacion} />
          <LecturaDato label="Tipo de actuación" value={draft.tipo_actuacion} />
          <LecturaDato
            label="Inspectores"
            value={draft.inspectores_texto?.trim() || inspectoresLinea(draft)}
          />
          {contraproducencia ? (
            <LecturaDato label="Contraproducencia" value={contraproducencia} />
          ) : null}
          {observaciones !== "—" ? (
            <LecturaDato label="Observaciones de visita" value={observaciones} fullWidth />
          ) : null}
        </Box>
      </LecturaBloque>

      <LecturaBloque titulo="Establecimiento">
        <Box sx={lecturaGridSx}>
          <LecturaDato
            label="Nombre de fantasía / razón social"
            value={draft.nombre_local}
          />
          <LecturaDato label="Rubro" value={formatGestionRubroNombre(draft)} />
        </Box>
        {draft.establecimiento_operativo_id != null && !formEditingActive ? (
          <Box
            sx={{
              mt: 1.5,
              display: "flex",
              flexDirection: { xs: "column", sm: "row" },
              alignItems: { xs: "stretch", sm: "flex-end" },
              justifyContent: "space-between",
              gap: 1.5,
            }}
          >
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <LecturaDato
                label="Vinculación a ficha de establecimiento"
                value={establecimientoVinculacionTexto(draft)}
              />
            </Box>
            <AppButton
              dsVariant="primary"
              dsSize="sm"
              onClick={() => {
                onClose();
                navigate(`/establecimientos/${draft.establecimiento_operativo_id}`);
              }}
            >
              Ver establecimiento
            </AppButton>
          </Box>
        ) : null}
      </LecturaBloque>

      <LecturaBloque titulo="Domicilio">
        <Box sx={lecturaGridSx}>
          <LecturaDato label="Dirección" value={domicilioLinea} fullWidth />
          {numeroTipoVisible ? (
            <LecturaDato label="Tipo de numeración" value={numeroTipoVisible} />
          ) : null}
        </Box>
      </LecturaBloque>

      <LecturaBloque titulo="Contribuyente">
        <Box sx={lecturaGridSx}>
          <LecturaDato label="CUIT / DNI" value={draft.doc_nro} />
          <LecturaDato label="Nombre o razón social" value={contribuyenteNombre} />
        </Box>
      </LecturaBloque>

      <LecturaBloque titulo="Actas y resultado">
        <Stack spacing={2} divider={<Divider sx={{ borderColor: GLASS_COLORS.borderLight }} />}>
          {tieneActas ? (
              <Box>
                <Typography component="h3" sx={docModalSubheadingInCardSx}>
                  Actas labradas
                </Typography>
                <Box sx={{ mt: 1 }}>
                  <ActasVisitaLectura
                    draft={draft}
                    catalog={catalogs.itemsActaInspeccion ?? []}
                    lockedNotif={draft.notificacion_editable === false}
                  />
                </Box>
              </Box>
          ) : (
            <Typography component="p" variant="body2" sx={lecturaValueSx}>
              Sin actas labradas
            </Typography>
          )}
          {tieneResultado ? (
              <Box>
                <Typography component="h3" sx={docModalSubheadingInCardSx}>
                  Resultado operativo
                </Typography>
                <Box sx={{ mt: 1 }}>
                  <ResultadoOperativoLectura draft={draft} />
                </Box>
              </Box>
          ) : null}
          {filasOrigenActas.length > 0 ? (
            <Box>
              <Typography component="h3" sx={docModalSubheadingInCardSx}>
                Actas de la comprobación de origen
              </Typography>
              <Box sx={{ mt: 1, ...lecturaGridSx }}>
                {filasOrigenActas.map((f) => (
                  <LecturaDato key={f.etiqueta} label={f.etiqueta} value={f.valor} />
                ))}
              </Box>
            </Box>
          ) : null}
        </Stack>
      </LecturaBloque>

      {tieneAntecedentes ? (
        <LecturaBloque titulo="Antecedentes y seguimiento">
          <AntecedentesSeguimientoLectura draft={draft} />
        </LecturaBloque>
      ) : null}

      {tieneSnapshotEpicollectLectura || tieneEvidenciasEpicollect ? (
        <LecturaBloque titulo="Evidencias de campo">
          {tieneSnapshotEpicollectLectura ? (
            <BloqueEpicollectDetalleLectura
              draft={draft}
              otrosExpanded={epicollectOtrosExpanded}
              onToggleOtros={toggleEpicollectOtros}
              embedded
            />
          ) : null}
          {tieneSnapshotEpicollectLectura && tieneEvidenciasEpicollect ? (
            <Divider sx={{ borderColor: GLASS_COLORS.borderLight, my: 1.5 }} />
          ) : null}
          {tieneEvidenciasEpicollect ? <BloqueEvidenciasEpicollect draft={draft} embedded /> : null}
        </LecturaBloque>
      ) : null}
    </Stack>
    );
  }, [draft, catalogs.itemsActaInspeccion, epicollectOtrosExpanded, formEditingActive, onClose, navigate, toggleEpicollectOtros]);

  const edicionVista = useMemo(() => {
    const e = (key: string) => fieldErrors[key] ?? oficioFieldErrors[key] ?? "";
    const fieldHelper = (key: string) => e(key) || "\u00a0";
    const ro = (key: string) => readOnlyColumns.includes(key);
    const canContrib = editableFields.canEditContribuyente;
    const canDom = editableFields.canEditDomicilio;
    const canRubro = editableFields.canEditRubro;
    const canNombreLocal = editableFields.canEditNombreLocal;
    const domicilioBloqueoMotivo = editableFields.domicilioEditBlockedReason;
    const canNotifEdit = editableFields.canEditNotificacion;
    const canEditActas = editableFields.canEditActas;
    const actasBaseline = editBaseline ?? draft;
    const mostrarInspeccion = debeMostrarCampoActaEnEdicion(
      "INSPECCION",
      draft,
      editableFields,
      actasBaseline
    );
    const mostrarNotificacion = debeMostrarCampoActaEnEdicion(
      "NOTIFICACION",
      draft,
      editableFields,
      actasBaseline
    );
    const mostrarComprobacion = debeMostrarCampoActaEnEdicion(
      "COMPROBACION",
      draft,
      editableFields,
      actasBaseline
    );
    const mostrarClausura = debeMostrarCampoActaEnEdicion("CLAUSURA", draft, editableFields, actasBaseline);
    const mostrarDecomiso = debeMostrarCampoActaEnEdicion("DECOMISO", draft, editableFields, actasBaseline);
    const canEditContraproducencia =
      editableFields.modoEdicion === "normal" || editableFields.modoEdicion === "reinspeccion_notificacion";
    const helperBloqueo = (key: string, locked: boolean) => {
      const msg = locked ? e(key) : e(key);
      return msg || "\u00a0";
    };
    const puedeEditarObservacionesVisita = canEditObservacionesVisita(draft);
    const obsVisitaError =
      seguimientoFieldErrors.observaciones_ejecucion ?? e("observaciones_ejecucion");

    const tieneSnapshotEpicollectLectura = epicollectSnapshotLecturaHayContenido(draft);
    const gruposEvid = draft.epicollect_evidencias_grupos ?? [];
    const totalEvid = draft.epicollect_evidencias_total ?? 0;
    const tieneEvidenciasEpicollect = totalEvid > 0 && gruposEvid.length > 0;
    const ec5Trim = draft.ec5_uuid?.trim() ?? "";
    const muestraBloqueFormulario =
      tieneSnapshotEpicollectLectura || tieneEvidenciasEpicollect || ec5Trim !== "";

    const res = draft.resultado_cumplimiento_oficio;
    const tieneResultado = res != null && String(res).trim() !== "";
    const muestraResultadoSeguimientoEdicion =
      tieneResultado || documentacionTramiteModalTieneContenido(draft) || tieneRestriccionesEdicion(draft);

    const motivosNotifSeleccionados = motivosNotificacionFromSlots(
      draft.notificacion_motivo_1,
      draft.notificacion_motivo_2,
      draft.notificacion_motivo_3
    );
    const motivosCatalogMerged = mergeMotivosNotifCatalogStrings(mergedCatalogs.motivos ?? [], motivosNotifSeleccionados);
    const motivosDisponiblesAgregar = motivosCatalogMerged.filter((m) => !motivosNotifSeleccionados.includes(m));

    const inspectoresEnOrdenLocal =
      draft.inspectores && draft.inspectores.length > 0
        ? [...new Set(draft.inspectores.map((x) => String(x ?? "").trim()).filter(Boolean))]
        : [draft.inspector1, draft.inspector2, draft.inspector3]
            .map((x) => String(x ?? "").trim())
            .filter(Boolean);
    const inspectoresCatalogMerged = [
      ...new Set([...(mergedCatalogs.inspectores ?? []), ...inspectoresEnOrdenLocal]),
    ].sort((a, b) => a.localeCompare(b, "es"));
    const inspectoresDisponiblesAgregar = inspectoresCatalogMerged.filter((n) => !inspectoresEnOrdenLocal.includes(n));

    const gridNotificacion = (
      <Box sx={{ ...col, width: "100%" }}>
        <ActaNumFieldLazy
          label={ACTA_FIELD_LABELS.notificacion}
          value={draft.acta_notificacion_num}
          onCommit={commitActaNotificacion}
          disabled={lockedNotif}
          saving={saving}
          registerFlush={registerActaFlush}
          error={!!e("acta_notificacion_num")}
          helperText={helperBloqueo("acta_notificacion_num", lockedNotif)}
        />
        <Typography variant="caption" sx={{ ...labelMuted, display: "block" }}>
          Motivos de notificación (máx. {MOTIVOS_NOTIFICACION_MAX})
        </Typography>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, alignItems: "center" }}>
          {motivosNotifSeleccionados.length === 0 ? (
            <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.45)" }}>
              —
            </Typography>
          ) : (
            motivosNotifSeleccionados.map((name) => (
              <Chip
                key={name}
                label={name}
                size="small"
                disabled={lockedNotif}
                onDelete={
                  lockedNotif
                    ? undefined
                    : () => applyMotivosNotificacion(motivosNotifSeleccionados.filter((x) => x !== name))
                }
                sx={actuacionModalChipSx}
              />
            ))
          )}
        </Box>
        <Autocomplete
            size="small"
            options={motivosDisponiblesAgregar}
            value={null}
            disabled={lockedNotif || !canNotifEdit || motivosNotifSeleccionados.length >= MOTIVOS_NOTIFICACION_MAX}
            onChange={(_, value) => {
              if (!value || lockedNotif) return;
              if (motivosNotifSeleccionados.includes(value)) return;
              if (motivosNotifSeleccionados.length >= MOTIVOS_NOTIFICACION_MAX) return;
              applyMotivosNotificacion(orderedMotivosNotificacion([...motivosNotifSeleccionados, value]));
            }}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Agregar motivo"
                placeholder="Catálogo"
                sx={modalAuxInputSx}
                error={!!e("notificacion_motivo_1")}
                helperText={helperBloqueo("notificacion_motivo_1", lockedNotif)}
              />
            )}
          />
        {!lockedNotif ? (
          <PersonasSinCarnetField
            appearance="glass"
            value={cantidadPersonasSinCarnetFromRow(draft)}
            onChange={(v) => {
              personasSinCarnetTouchedRef.current = true;
              const n = parseInt(v, 10);
              onDraftChange({
                cantidad_personas_sin_carnet_sanidad: Number.isNaN(n) || n < 0 ? 0 : n,
              });
            }}
            disabled={!isValidActaNotificacionNum(draft.acta_notificacion_num) || saving}
            error={e("cantidad_personas_sin_carnet_sanidad")}
          />
        ) : null}
      </Box>
    );

    const motivosCompSeleccionados = hydrateMotivosComprobacion(draft);
    const motivosCompCatalogMerged = mergeMotivosCompCatalogStrings(
      catalogs.motivosComprobacion ?? [],
      motivosCompSeleccionados
    );
    const motivosCompDisponiblesAgregar = motivosCompCatalogMerged.filter(
      (m) => !motivosCompSeleccionados.includes(m)
    );

    const gridComprobacion = (
      <Box sx={{ ...col, width: "100%" }}>
        <ActaNumFieldLazy
          label={ACTA_FIELD_LABELS.comprobacion}
          value={draft.acta_comprobacion_num}
          onCommit={commitActaComprobacion}
          disabled={lockedComp}
          saving={saving}
          registerFlush={registerActaFlush}
          error={!!e("acta_comprobacion_num")}
          helperText={helperBloqueo("acta_comprobacion_num", lockedComp)}
        />
        <Typography variant="caption" sx={{ ...labelMuted, display: "block" }}>
          Motivos de comprobación
        </Typography>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, alignItems: "center" }}>
          {motivosCompSeleccionados.length === 0 ? (
            <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.45)" }}>
              —
            </Typography>
          ) : (
            motivosCompSeleccionados.map((name) => (
              <Chip
                key={name}
                label={name}
                size="small"
                disabled={lockedComp}
                onDelete={
                  lockedComp
                    ? undefined
                    : () =>
                        applyMotivosComprobacion(motivosCompSeleccionados.filter((x) => x !== name))
                }
                sx={actuacionModalChipSx}
              />
            ))
          )}
        </Box>
        <Autocomplete
          size="small"
          options={motivosCompDisponiblesAgregar}
          value={null}
          disabled={lockedComp || motivosCompDisponiblesAgregar.length === 0}
          onChange={(_, value) => {
            if (!value || lockedComp) return;
            if (motivosCompSeleccionados.includes(value)) return;
            applyMotivosComprobacion([...motivosCompSeleccionados, value]);
          }}
          renderInput={(params) => (
            <TextField
              {...params}
              label="Agregar motivo"
              placeholder="Catálogo"
              sx={modalAuxInputSx}
              error={!!(e("comprobacion_motivo") || e("motivos_comprobacion"))}
              helperText={helperBloqueo("comprobacion_motivo", lockedComp) || helperBloqueo("motivos_comprobacion", lockedComp)}
            />
          )}
        />
      </Box>
    );

    return (
      <Stack spacing={DOC_MODAL_BLOCK_STACK_SPACING} component="section" aria-label="Edición de la actuación">
        <DocumentalBloque overline="Datos del establecimiento">
          <ContextoEdicionFallback draft={draft} />
          <Typography component="h3" sx={actaSubtituloMenorSx}>
            Establecimiento
          </Typography>
          <Box sx={edicionGrid2ColSx}>
            <AppTextField
              appearance="glass"
              label="Nombre de fantasía"
              value={draft.nombre_local ?? ""}
              onChange={(ev) => onDraftChange({ nombre_local: ev.target.value || null })}
              disabled={!canNombreLocal}
              error={!!e("nombre_local")}
              helperText={fieldHelper("nombre_local")}
              sx={!canNombreLocal ? roFieldSx : undefined}
              fullWidth
            />
            <AppSelect
              appearance="glass"
              label="Rubro"
              value={draft.rubro_nombre ?? ""}
              onChange={(ev) => onDraftChange({ rubro_nombre: ev.target.value as string })}
              options={rubrosOptions}
              disabled={ro("rubro_nombre") || !canRubro}
              error={!!e("rubro_nombre")}
              helperText={fieldHelper("rubro_nombre")}
              fullWidth
            />
          </Box>
          <Typography component="h3" sx={{ ...actaSubtituloMenorSx, mt: 2 }}>
            Domicilio
          </Typography>
          {!canDom && domicilioBloqueoMotivo ? (
            <Typography variant="body2" sx={{ color: GLASS_COLORS.textSecondary, mb: 1 }}>
              {domicilioBloqueoMotivo}
            </Typography>
          ) : null}
          <Box sx={{ ...edicionGrid2ColSx, ...edicionGapBloqueAPrimerControlSx }}>
            <AppTextField
              appearance="glass"
              label="Calle"
              value={domicilioCalleValorEdicion(draft)}
              onChange={(ev) => onDraftChange({ calle: ev.target.value })}
              disabled={!canDom || ro("calle")}
              error={!!e("calle")}
              helperText={fieldHelper("calle")}
              sx={!canDom ? roFieldSx : undefined}
              fullWidth
            />
            <NumeroEsquinaFreeEditor
              value={domicilioNumeroValorEdicion(draft) || null}
              onChange={(newValue) => onDraftChange({ numero: newValue })}
              onModeChange={(editorMode) => onDraftChange({ numero_tipo: editorMode })}
              label={numeroEditorLabel}
              error={!!e("numero")}
              helperText={fieldHelper("numero")}
              disabled={!canDom || ro("numero")}
              initialMode={draft.numero_tipo === "ESQUINA" ? "ESQUINA" : "NUMERO"}
            />
          </Box>
          <Typography component="h3" sx={{ ...actaSubtituloMenorSx, mt: 2 }}>
            Contribuyente
          </Typography>
          <Box sx={{ ...edicionGrid2ColSx, mt: 2 }}>
            <AppTextField
              appearance="glass"
              label="N.º de documento"
              value={draft.doc_nro ?? ""}
              onChange={(ev) => {
                identidadTouchedRef.current = { ...identidadTouchedRef.current, doc_nro: true };
                onDraftChange({ doc_nro: ev.target.value });
              }}
              disabled={!canContrib}
              error={!!e("doc_nro")}
              helperText={fieldHelper("doc_nro")}
              sx={!canContrib ? roFieldSx : undefined}
              fullWidth
            />
            <AppTextField
              appearance="glass"
              label="Apellido"
              value={draft.contrib_apellido ?? ""}
              onChange={(ev) => {
                identidadTouchedRef.current = {
                  ...identidadTouchedRef.current,
                  contrib_apellido: true,
                };
                onDraftChange({ contrib_apellido: ev.target.value });
              }}
              disabled={!canContrib}
              error={!!e("contrib_apellido")}
              helperText={fieldHelper("contrib_apellido")}
              sx={!canContrib ? roFieldSx : undefined}
              fullWidth
            />
            <AppTextField
              appearance="glass"
              label="Nombre"
              value={draft.contrib_nombre ?? ""}
              onChange={(ev) => {
                identidadTouchedRef.current = {
                  ...identidadTouchedRef.current,
                  contrib_nombre: true,
                };
                onDraftChange({ contrib_nombre: ev.target.value });
              }}
              disabled={!canContrib}
              error={!!e("contrib_nombre")}
              helperText={fieldHelper("contrib_nombre")}
              sx={!canContrib ? roFieldSx : undefined}
              fullWidth
            />
            <AppTextField
              appearance="glass"
              label="Razón social"
              value={draft.razon_social ?? ""}
              onChange={(ev) => {
                identidadTouchedRef.current = {
                  ...identidadTouchedRef.current,
                  razon_social: true,
                };
                onDraftChange({ razon_social: ev.target.value || null });
              }}
              disabled={!canContrib}
              error={!!e("razon_social")}
              helperText={fieldHelper("razon_social")}
              sx={{ gridColumn: { xs: "1 / -1", sm: "1 / -1" }, ...(!canContrib ? roFieldSx : {}) }}
              fullWidth
            />
          </Box>
        </DocumentalBloque>

        <DocumentalBloque overline="Visita y actuación">
          <Box sx={edicionGapBloqueAPrimerControlSx}>
            <Box sx={edicionGrid2ColSx}>
              <AppTextField
                appearance="glass"
                label="OT"
                value={draft.orden_trabajo_numero ?? ""}
                disabled
                error={!!e("orden_trabajo_numero")}
                helperText={fieldHelper("orden_trabajo_numero")}
                sx={roFieldSx}
                fullWidth
              />
              <AppTextField
                appearance="glass"
                label="Fecha de la visita"
                type="date"
                value={draft.fecha_actuacion ?? ""}
                disabled
                error={!!e("fecha_actuacion")}
                helperText={fieldHelper("fecha_actuacion")}
                sx={roFieldSx}
                InputLabelProps={dateFieldShrinkLabelProps}
                fullWidth
              />
              <AppTextField
                appearance="glass"
                label="Tipo de actuación"
                value={draft.tipo_actuacion ?? ""}
                disabled
                error={!!e("tipo_actuacion")}
                helperText={fieldHelper("tipo_actuacion")}
                sx={roFieldSx}
                fullWidth
              />
              {!muestraOficioResultadoEditable ? (
              <AppSelect
                appearance="glass"
                label="Contraproducencia"
                value={draft.contraproducencia ?? ""}
                onChange={(ev) => {
                  const v = String(ev.target.value ?? "").trim();
                  onDraftChange({ contraproducencia: v || null });
                }}
                options={contraCrudOptions}
                disabled={saving || !canEditContraproducencia}
                error={!!e("contraproducencia")}
                helperText={
                  fieldHelper("contraproducencia") ||
                  (contraUxHint && !e("contraproducencia") ? contraUxHint : undefined)
                }
                fullWidth
              />
              ) : null}
            </Box>
            <Box sx={{ mt: 2, width: "100%" }}>
              <Typography variant="caption" sx={{ ...labelMuted, display: "block" }}>
                Inspectores
              </Typography>
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, alignItems: "center" }}>
                {inspectoresEnOrdenLocal.length === 0 ? (
                  <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.45)" }}>
                    —
                  </Typography>
                ) : (
                  inspectoresEnOrdenLocal.map((name) => (
                    <Chip
                      key={name}
                      label={name}
                      size="small"
                      onDelete={
                        saving
                          ? undefined
                          : () => applyInspectoresNombres(inspectoresEnOrdenLocal.filter((x) => x !== name))
                      }
                      sx={actuacionModalChipSx}
                    />
                  ))
                )}
              </Box>
              <Autocomplete
                size="small"
                options={inspectoresDisponiblesAgregar}
                value={null}
                inputValue={inspectoresAddInput}
                onInputChange={(_, newInput, reason) => {
                  if (reason === "input") setInspectoresAddInput(newInput);
                  else if (reason === "clear" || reason === "reset") setInspectoresAddInput("");
                }}
                disabled={saving || inspectoresDisponiblesAgregar.length === 0}
                onChange={(_, value) => {
                  if (!value || saving) return;
                  if (inspectoresEnOrdenLocal.includes(value)) return;
                  applyInspectoresNombres([...inspectoresEnOrdenLocal, value]);
                  setInspectoresAddInput("");
                }}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Agregar inspector"
                    placeholder="Catálogo"
                    sx={modalAuxInputSx}
                    error={!!e("inspectores")}
                    helperText={fieldHelper("inspectores")}
                  />
                )}
              />
            </Box>
          </Box>
        </DocumentalBloque>

        <DocumentalBloque overline="Observaciones de la visita">
          {puedeEditarObservacionesVisita ? (
            <AppTextField
              appearance="glass"
              label="Observaciones"
              value={draft.observaciones_ejecucion ?? ""}
              onChange={(ev) =>
                onDraftChange({ observaciones_ejecucion: ev.target.value || null })
              }
              disabled={saving}
              error={!!obsVisitaError}
              helperText={obsVisitaError || "\u00a0"}
              multiline
              minRows={3}
              maxRows={8}
              inputProps={{ maxLength: OBSERVACIONES_VISITA_MAX_LENGTH }}
              sx={{ width: "100%" }}
              fullWidth
            />
          ) : (
            <CrudFormSlot
              label="Observaciones"
              mode="view"
              value={observacionesVisitaDisplayText(draft)}
              sx={{ width: "100%" }}
            />
          )}
        </DocumentalBloque>

        {canEditActas ? (
        <DocumentalBloque overline="Actas labradas">
          <Box sx={{ ...col, width: "100%" }}>
            {mostrarInspeccion ? (
            <>
            <ActaNumFieldLazy
              label={ACTA_FIELD_LABELS.inspeccion}
              value={draft.acta_inspeccion_num}
              onCommit={commitActaInspeccion}
              saving={saving}
              registerFlush={registerActaFlush}
              error={!!e("acta_inspeccion_num")}
              helperText={fieldHelper("acta_inspeccion_num")}
            />
            <InspeccionAtencionEstablecimientoFields
              hideHeading
              caracter={caracterPersonaAtendioFromRow(draft)}
              contrato={contratoResiduosFromRow(draft)}
              onCaracterChange={(value) => {
                atencionTouchedRef.current = { ...atencionTouchedRef.current, caracter: true };
                onDraftChange({ caracter_persona_atendio: value });
              }}
              onContratoChange={(value) => {
                atencionTouchedRef.current = { ...atencionTouchedRef.current, contrato: true };
                onDraftChange({ posee_contrato_retiro_residuos_solidos_urbanos: value });
              }}
              showCarnet={Boolean(draft.ui_policy?.mostrar_solicitud_carnet_manipulador)}
              carnet={boolToSolicitaCarnetUi(
                mergeActuacionSeguimientoFromApiRow(draft).solicita_carnet_manipulador
              )}
              onCarnetChange={(next) => {
                if (!draft.ui_policy?.puede_editar_seguimiento) return;
                const base = gestionSeguimientoDraftFromRow(draft);
                const tel =
                  (mergeActuacionSeguimientoFromApiRow(draft).telefono_contacto_solicitud_carnet ?? "").trim();
                onDraftChange(
                  applyGestionSeguimientoDraftToRow(draft, {
                    ...base,
                    solicitaCarnet: next,
                    telefonoCarnet: next === "si" ? tel : "",
                  })
                );
              }}
              telefonoCarnet={
                (mergeActuacionSeguimientoFromApiRow(draft).telefono_contacto_solicitud_carnet ?? "").trim()
              }
              onTelefonoCarnetChange={(value) => {
                if (!draft.ui_policy?.puede_editar_seguimiento) return;
                const base = gestionSeguimientoDraftFromRow(draft);
                onDraftChange(
                  applyGestionSeguimientoDraftToRow(draft, {
                    ...base,
                    telefonoCarnet: value,
                  })
                );
              }}
              carnetDisabled={!draft.ui_policy?.puede_editar_seguimiento}
              disabled={!isValidActaInspeccionNum(draft.acta_inspeccion_num) || saving}
              errors={{
                caracter: e("caracter_persona_atendio"),
                contrato: e("posee_contrato_retiro_residuos_solidos_urbanos"),
                carnet: e("solicita_carnet_manipulador"),
                telefonoCarnet: e("telefono_contacto_solicitud_carnet"),
              }}
            />
            <InspeccionChecklistFields
              catalog={catalogs.itemsActaInspeccion ?? []}
              estados={checklistEstados}
              onEstadosChange={(estados) => {
                checklistItemsTouchedRef.current = true;
                setChecklistEstados(estados);
                onDraftChange({
                  items_acta_inspeccion: itemsActaInspeccionWriteFromEstados(
                    estados,
                    catalogs.itemsActaInspeccion ?? []
                  ),
                });
              }}
              disabled={!isValidActaInspeccionNum(draft.acta_inspeccion_num) || saving}
              errors={{
                items: e("items_acta_inspeccion"),
              }}
            />
            </>
            ) : null}

            {mostrarNotificacion ? (
              lockedNotif ? (
                <Box sx={edicionActaBloqueadaShellSx}>
                  <Typography
                    variant="caption"
                    component="p"
                    sx={{
                      color: DOC_MODAL_TEXT,
                      opacity: 0.96,
                      lineHeight: 1.45,
                      mb: 1.25,
                      maxWidth: 520,
                    }}
                  >
                    Expediente asociado: bloqueado en canal actas. Los motivos y el número no se modifican aquí.
                  </Typography>
                  {gridNotificacion}
                </Box>
              ) : (
                gridNotificacion
              )
            ) : null}

            {mostrarComprobacion ? (
            lockedComp ? (
              <Box sx={edicionActaBloqueadaShellSx}>
                <Typography
                  variant="caption"
                  component="p"
                  sx={{
                    color: DOC_MODAL_TEXT,
                    opacity: 0.96,
                    lineHeight: 1.45,
                    mb: 1.25,
                    maxWidth: 520,
                  }}
                >
                  Expediente de envío: bloqueado en canal actas. El motivo y el número no se modifican aquí.
                </Typography>
                {gridComprobacion}
              </Box>
            ) : (
              gridComprobacion
            )
            ) : null}

            {mostrarClausura || mostrarDecomiso ? (
            <Box sx={edicionGrid2ColSx}>
              {mostrarClausura ? (
              <ActaNumFieldLazy
                label={ACTA_FIELD_LABELS.clausura}
                value={draft.acta_clausura_num}
                onCommit={commitActaClausura}
                saving={saving}
                registerFlush={registerActaFlush}
                error={!!e("acta_clausura_num")}
                helperText={fieldHelper("acta_clausura_num")}
              />
              ) : null}
              {mostrarDecomiso ? (
              <ActaNumFieldLazy
                label={ACTA_FIELD_LABELS.decomiso}
                value={draft.acta_decomiso_num}
                onCommit={commitActaDecomiso}
                saving={saving}
                registerFlush={registerActaFlush}
                error={!!e("acta_decomiso_num")}
                helperText={fieldHelper("acta_decomiso_num")}
              />
              ) : null}
            </Box>
            ) : null}
            {mostrarDecomiso ? (
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
              helperText={fieldHelper("decomiso_kilos_total")}
              fullWidth
            />
            ) : null}
          </Box>
        </DocumentalBloque>
        ) : null}

        {gestionSeguimientoBloqueVisible(draft, { omitCarnet: mostrarInspeccion }) ? (
          <DocumentalBloque overline="Seguimiento">
            <ActaSeguimientoGestionFields
              draft={draft}
              onDraftChange={onDraftChange}
              fieldErrors={{ ...fieldErrors, ...seguimientoFieldErrors }}
              saving={saving}
              readOnly={false}
              omitCarnet={mostrarInspeccion}
            />
          </DocumentalBloque>
        ) : null}

        {muestraOficioResultadoEditable && oficioFormCtx ? (
          <DocumentalBloque overline="Resultado operativo">
            <Box sx={edicionGapBloqueAPrimerControlSx}>
              <ReinspeccionOficioForm
                form={oficioForm}
                contraOptions={oficioContraOpts}
                fieldErrors={{ ...fieldErrors, ...oficioFieldErrors }}
                disabled={saving}
              />
            </Box>
            {documentacionTramiteModalTieneContenido(draft) ? (
              <Box sx={{ mt: 2 }}>
                <DocumentacionTramiteModalLectura draft={draft} />
              </Box>
            ) : null}
          </DocumentalBloque>
        ) : muestraResultadoSeguimientoEdicion ? (
          <DocumentalBloque overline="Resultado operativo">
            {tieneResultado ? (
              <Box sx={edicionGapBloqueAPrimerControlSx}>
                <CrudFormSlot label="Resultado cumplimiento oficio" mode="view" value={dash(res)} />
              </Box>
            ) : null}
            {documentacionTramiteModalTieneContenido(draft) ? (
              <Box sx={{ mt: tieneResultado ? 2 : 0 }}>
                <DocumentacionTramiteModalLectura draft={draft} />
              </Box>
            ) : null}
            {tieneRestriccionesEdicion(draft) ? (
              <Box
                sx={{
                  mt: tieneResultado || documentacionTramiteModalTieneContenido(draft) ? 2 : 0,
                  p: 1.25,
                  borderRadius: 1.5,
                  bgcolor: "rgba(255,255,255,0.04)",
                  border: "1px solid rgba(255,255,255,0.08)",
                }}
              >
                <Typography component="h3" sx={actaSubtituloMenorSx}>
                  Edición en canal actas
                </Typography>
                <Typography variant="body2" sx={{ color: DOC_MODAL_TEXT, fontSize: "0.8125rem", mt: 1, lineHeight: 1.55 }}>
                  {textoRestriccionesEdicion(draft)}
                </Typography>
              </Box>
            ) : null}
          </DocumentalBloque>
        ) : null}

        {muestraBloqueFormulario ? (
          <DocumentalBloque overline="Evidencias">
            {ec5Trim !== "" ? (
              <AppTextField
                appearance="glass"
                label="Identificador EpiCollect"
                value={draft.ec5_uuid ?? ""}
                disabled
                sx={{
                  ...roFieldSx,
                  ...edicionGapBloqueAPrimerControlSx,
                  mb: tieneSnapshotEpicollectLectura || tieneEvidenciasEpicollect ? 2 : 0,
                }}
                fullWidth
              />
            ) : null}
            {tieneSnapshotEpicollectLectura ? (
              <Box sx={ec5Trim !== "" ? undefined : edicionGapBloqueAPrimerControlSx}>
                <BloqueEpicollectDetalleLectura
                  draft={draft}
                  otrosExpanded={epicollectOtrosExpanded}
                  onToggleOtros={toggleEpicollectOtros}
                  embedded
                />
              </Box>
            ) : null}
            {tieneSnapshotEpicollectLectura && tieneEvidenciasEpicollect ? (
              <Divider sx={{ borderColor: GLASS_COLORS.borderLight, my: 1.5 }} />
            ) : null}
            {tieneEvidenciasEpicollect ? (
              <Box
                sx={
                  ec5Trim !== "" || tieneSnapshotEpicollectLectura
                    ? undefined
                    : edicionGapBloqueAPrimerControlSx
                }
              >
                <BloqueEvidenciasEpicollect draft={draft} embedded />
              </Box>
            ) : null}
          </DocumentalBloque>
        ) : null}
      </Stack>
    );
  }, [
    draft,
    fieldErrors,
    oficioFieldErrors,
    oficioFormCtx,
    oficioForm,
    oficioContraOpts,
    muestraOficioResultadoEditable,
    readOnlyColumns,
    editableFields,
    editBaseline,
    registerActaFlush,
    numeroEditorLabel,
    lockedNotif,
    lockedComp,
    mergedCatalogs,
    rubrosOptions,
    catalogs.motivosComprobacion,
    contraCrudOptions,
    contraUxHint,
    epicollectOtrosExpanded,
    toggleEpicollectOtros,
    onDraftChange,
    commitActaInspeccion,
    commitActaNotificacion,
    commitActaComprobacion,
    commitActaClausura,
    commitActaDecomiso,
    applyMotivosNotificacion,
    applyMotivosComprobacion,
    applyInspectoresNombres,
    saving,
    seguimientoFieldErrors,
  ]);

  return (
    <CrudGlassDialog
      open={open}
      disablePortal={disablePortal}
      hideBackdrop={disablePortal}
      onClose={handleDialogClose}
      onCloseButtonClick={handleClose}
      maxWidth="md"
      mobileFullScreen
      title={
        <CrudDialogHeader
          titulo={
            inspectorVerTrabajoMode
              ? "Ver trabajo"
              : isEditing
                ? "Editar actuación"
                : "Ver actuación"
          }
          reference={dialogHeaderReference}
          referenceProminent
        />
      }
      actions={
        <CrudDialogActions
          mode={formEditingActive ? "edit" : "view"}
          onEdit={!inspectorSelfService && canEdit ? handleStartEditing : undefined}
          onSave={formEditingActive ? handleSaveClick : undefined}
          loading={saving || detailLoading}
          saveDisabled={formEditingActive && (catalogsLoading || Boolean(catalogsError?.trim()))}
          canEdit={!inspectorSelfService && canEdit && !detailLoading && !catalogsLoading}
          saveLabel="Guardar cambios"
          extraActions={
            <>
              {showInspectorModePicker && puedeInspectorDatos ? (
                <AppButton dsVariant="primary" dsSize="sm" onClick={() => handleStartEditing()} disabled={saving}>
                  Editar datos
                </AppButton>
              ) : null}
              {showInspectorModePicker && puedeInspectorFotos ? (
                <AppButton
                  dsVariant="secondary"
                  dsSize="sm"
                  onClick={() => {
                    if (onRequestPhotosOnly) {
                      onRequestPhotosOnly();
                    } else {
                      setPhotosOnlyMode(true);
                    }
                  }}
                  disabled={saving}
                >
                  Cargar más fotos
                </AppButton>
              ) : null}
              {inspectorSelfService && (photosOnlyMode || formEditingActive) ? (
                <AppButton
                  dsVariant="ghost"
                  dsSize="sm"
                  onClick={() => {
                    setPhotosOnlyMode(false);
                    setIsEditing(false);
                    setEditBaseline(null);
                  }}
                  disabled={saving}
                >
                  Volver
                </AppButton>
              ) : null}
              {!inspectorSelfService ? (
                <AppButton dsVariant="ghost" dsSize="sm" onClick={handlePrint} disabled={saving}>
                  Imprimir
                </AppButton>
              ) : null}
            </>
          }
        />
      }
    >
      <Box
        sx={{
          position: "relative",
          pb: formEditingActive ? 0 : { xs: 4, sm: 3 },
        }}
      >
        <Box sx={{ display: formEditingActive ? "none" : "block" }} aria-hidden={formEditingActive}>
          {detalleVista}
        </Box>
        <Box sx={{ display: formEditingActive ? "block" : "none" }} aria-hidden={!formEditingActive}>
          {catalogsLoading ? (
            <Alert severity="info" sx={{ mb: 2 }}>
              Cargando catálogos del formulario…
            </Alert>
          ) : null}
          {catalogsError?.trim() ? (
            <Alert severity="warning" sx={{ mb: 2 }}>
              {catalogsError.trim()}
            </Alert>
          ) : null}
          {edicionVista}
        </Box>
        <DocumentalBloque
          overline="Fotos y documentación"
          sectionTitleSx={!formEditingActive ? lecturaSectionTitleSx : undefined}
        >
          <MediaUploadPanelErrorBoundary
            resetKey={`${draft.id}-${draft.ruta_item_id ?? 0}`}
            rutaItemId={draft.ruta_item_id ?? null}
            onClosePanel={() => undefined}
          >
            <ActuacionMediaGallery
              ref={mediaGalleryRef}
              rutaItemId={draft.ruta_item_id}
              readOnly={mediaReadOnly}
              hideTitle
              manualSave={formEditingActive && !inspectorVerTrabajoMode}
              uploadOrigin={MEDIA_UPLOAD_ORIGIN_MIS_TRABAJOS}
            />
          </MediaUploadPanelErrorBoundary>
        </DocumentalBloque>
        {detailLoading ? (
          <Box
            sx={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              bgcolor: "rgba(0,0,0,0.35)",
              borderRadius: 1,
              zIndex: 2,
            }}
          >
            <CircularProgress size={32} sx={{ color: COLORS.primary }} />
          </Box>
        ) : null}
      </Box>
      <ConfirmDialog
        open={mediaDiscardConfirmOpen}
        onClose={() => setMediaDiscardConfirmOpen(false)}
        onConfirm={() => {
          mediaGalleryRef.current?.discardLocalQueue();
          setMediaDiscardConfirmOpen(false);
          onClose();
        }}
        title="¿Salir sin guardar las fotos seleccionadas?"
        confirmLabel="Salir sin guardar"
        cancelLabel="Seguir editando"
      >
        Las fotos elegidas todavía no se subieron.
      </ConfirmDialog>
    </CrudGlassDialog>
  );
}
