import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import type { ReactNode } from "react";
import type { SxProps, Theme } from "@mui/material/styles";
import {
  Autocomplete,
  Box,
  Chip,
  Collapse,
  Divider,
  IconButton,
  Link,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import {
  MOTIVOS_NOTIFICACION_MAX,
  mergeMotivosNotifCatalogStrings,
  motivosNotificacionFromSlots,
  orderedMotivosNotificacion,
} from "../../../utils/motivosNotificacionSlots";
import { getDropdownOptions } from "../../CargarActuaciones/config/dropdownOptions";
import { mergeLegacyRubroNames } from "../../../utils/rubrosCatalogCache";
import { domicilioCalleCargadaEditable, domicilioNumeroEditable } from "../../../utils/domicilioCalleUi";
import { useAppFeedback } from "../../../components/feedback";
import {
  CrudDialogActions,
  CrudDialogHeader,
  CrudDialogSection,
  CrudFormSlot,
  CrudGlassDialog,
  useCrudDialogScrollContainer,
} from "../../../components/crudDialog";
import {
  DOC_MODAL_BLOCK_STACK_SPACING,
  DOC_MODAL_TEXT,
  docModalBlockResumenSx,
  docModalChipSx,
  docModalIntroParagraphSx,
  docModalSubheadingInCardSx,
} from "../../../styles/documentalModalTokens";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { NumeroEsquinaFreeEditor } from "./NumeroEsquinaFreeEditor";
import { AppButton, AppSelect, AppTextField } from "../../../ui";
import { COLORS } from "../styles/filtroStyles";
import { ActaNumFieldLazy } from "./ActaNumFieldLazy";
import { ActuacionDocumentacionChips } from "./ActuacionDocumentacionChips";
import {
  actuacionDocumentacionOrigenReinspeccionSegments,
  actuacionDocumentacionPropiaTramiteSegments,
} from "../utils/actuacionDocumentacionVisual";
import {
  detectBlockedActaClearAttempt,
  getActuacionEditableFields,
  resolveActuacionEditStart,
  tieneExpedienteBloqueoEdicion,
} from "../utils/actuacionEditRules";
import { buildContraproducenciaCrudSelectOptions } from "../utils/contraproducenciaCrudOptions";
import { getContraproducenciaUxHint } from "../../CompletarTrabajos/utils/contraproducenciaUxHint";
import { scrollActuacionFormToFirstFieldError } from "../utils/actuacionFormScroll";

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
  fontFamily: '"Tactic Sans", sans-serif',
  wordBreak: "break-word" as const,
};

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
  /** Opciones de calle para editor de número (p. ej. gestión domicilios); opcional en actuaciones. */
  numeroEditorLabel?: string;
  /** Si es false, no se muestra el paso a edición (p. ej. bandejas restringidas). */
  canEdit?: boolean;
  onClose: () => void;
  onDraftChange: (patch: Partial<IActuacionListItem>) => void;
  onSave: () => void | Promise<void>;
  /** Solo tests SSR; evita portal de MUI Dialog. */
  disablePortal?: boolean;
  /** Solo tests: abrir directamente en edición. */
  initialEditing?: boolean;
};

function opts(strings: string[]) {
  return strings.map((s) => ({ value: s, label: s || "—" }));
}

const sectionTitleSx = {
  color: DOC_MODAL_TEXT,
  fontFamily: '"Tactic Sans", sans-serif',
  fontWeight: 700,
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

/** Estilo de inputs deshabilitados en edición; referencia estable (no recrear por render). */
const roFieldSx = { "& .MuiInputBase-input": { color: "rgba(255,255,255,0.94)" } };

/** Autocomplete / TextField auxiliar: alto contraste sobre fondo oscuro del modal. */
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

/** Título principal de la sección «Actas labradas» (mayor jerarquía que cada acta). */
const actasLabradasSectionTitleSx = {
  fontSize: "0.875rem",
  fontWeight: 700,
  letterSpacing: "0.06em",
  mb: 1.75,
} as const;

/** Aire entre el overline/resumen del bloque documental y el primer control (p. ej. Lugar y titular, formulario). */
const edicionGapBloqueAPrimerControlSx = { mt: 2 } as const;

const dateFieldShrinkLabelProps = { shrink: true } as const;

function dash(v: unknown): string {
  if (v === null || v === undefined || v === "") return "—";
  return String(v);
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

const actaGrupoWrapperSx = {
  pb: 1.75,
  borderBottom: "1px solid rgba(255,255,255,0.07)",
  "&:last-of-type": { borderBottom: "none", pb: 0 },
};

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
  const mComp = draft.comprobacion_motivo != null ? String(draft.comprobacion_motivo).trim() : "";
  const showInspeccion = !!(nIns != null && String(nIns).trim() !== "");
  const showNotificacion =
    (nNot != null && String(nNot).trim() !== "") || motivosNoti.length > 0;
  const showComprobacion = (nComp != null && String(nComp).trim() !== "") || mComp !== "";
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
function ActasVisitaLectura({ draft }: { draft: IActuacionListItem }) {
  const nIns = draft.acta_inspeccion_num;
  const nNot = draft.acta_notificacion_num;
  const nComp = draft.acta_comprobacion_num;
  const nClau = draft.acta_clausura_num;
  const nDec = draft.acta_decomiso_num;
  const kg = draft.decomiso_kilos_total;
  const motivosNoti = motivosNotificacionNoVacios(draft);
  const mComp = draft.comprobacion_motivo != null ? String(draft.comprobacion_motivo).trim() : "";

  const showInspeccion = !!(nIns != null && String(nIns).trim() !== "");
  const showNotificacion =
    (nNot != null && String(nNot).trim() !== "") || motivosNoti.length > 0;
  const showComprobacion = (nComp != null && String(nComp).trim() !== "") || mComp !== "";
  const showClausura = !!(nClau != null && String(nClau).trim() !== "");
  const showDecomiso =
    (nDec != null && String(nDec).trim() !== "") || kg != null;

  const hayAlgunaActa = showInspeccion || showNotificacion || showComprobacion || showClausura || showDecomiso;

  if (!hayAlgunaActa) {
    return null;
  }

  const numNot = (nNot != null && String(nNot).trim() !== "") ? dash(nNot) : "—";
  const numComp = (nComp != null && String(nComp).trim() !== "") ? dash(nComp) : "—";
  const numDec = (nDec != null && String(nDec).trim() !== "") ? dash(nDec) : "—";

  return (
    <Box component="div" sx={{ display: "flex", flexDirection: "column", gap: 0 }}>
      {showInspeccion ? (
        <Box sx={actaGrupoWrapperSx}>
          <Typography component="h3" sx={actaSubtituloMenorSx}>
            Acta de inspección
          </Typography>
          <CrudFormSlot label="Número de acta" mode="view" value={dash(nIns)} />
        </Box>
      ) : null}

      {showNotificacion ? (
        <Box sx={actaGrupoWrapperSx}>
          <Typography component="h3" sx={actaSubtituloMenorSx}>
            Acta de notificación
          </Typography>
          <CrudFormSlot label="Número de acta" mode="view" value={numNot} />
          {motivosNoti.length > 0 ? (
            <CrudFormSlot
              label="Motivos de notificación"
              mode="view"
              value={motivosNoti.join(" · ")}
              sx={{ mt: 2 }}
            />
          ) : null}
        </Box>
      ) : null}

      {showComprobacion ? (
        <Box sx={actaGrupoWrapperSx}>
          <Typography component="h3" sx={actaSubtituloMenorSx}>
            Acta de comprobación
          </Typography>
          <CrudFormSlot label="Número de acta" mode="view" value={numComp} />
          {mComp ? (
            <CrudFormSlot label="Motivo de comprobación" mode="view" value={mComp} sx={{ mt: 2 }} />
          ) : null}
        </Box>
      ) : null}

      {showClausura ? (
        <Box sx={actaGrupoWrapperSx}>
          <Typography component="h3" sx={actaSubtituloMenorSx}>
            Acta de clausura
          </Typography>
          <CrudFormSlot label="Número de acta" mode="view" value={dash(nClau)} />
        </Box>
      ) : null}

      {showDecomiso ? (
        <Box sx={actaGrupoWrapperSx}>
          <Typography component="h3" sx={actaSubtituloMenorSx}>
            Acta de decomiso
          </Typography>
          <CrudFormSlot label="Número de acta" mode="view" value={numDec} />
          {kg != null ? (
            <CrudFormSlot label="Kilos decomisados" mode="view" value={`${kg} kg`} sx={{ mt: 2 }} />
          ) : null}
        </Box>
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

function resultadoSeguimientoHayContenido(draft: IActuacionListItem): boolean {
  const res = draft.resultado_cumplimiento_oficio;
  const tieneResultado = res != null && String(res).trim() !== "";
  return tieneResultado || documentacionTramiteModalTieneContenido(draft) || tieneRestriccionesEdicion(draft);
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

/**
 * Card "Resultado y seguimiento": solo subsecciones con dato útil; sin texto vacío ni pedagógico.
 */
function ResultadoSeguimientoLectura({ draft }: { draft: IActuacionListItem }) {
  const res = draft.resultado_cumplimiento_oficio;
  const tieneResultado = res != null && String(res).trim() !== "";
  const showDoc = documentacionTramiteModalTieneContenido(draft);
  const showEdicion = tieneRestriccionesEdicion(draft);

  if (!tieneResultado && !showDoc && !showEdicion) {
    return null;
  }

  const bloques: ReactNode[] = [];
  if (tieneResultado) {
    bloques.push(
      <CrudFormSlot
        key="res"
        label="Resultado cumplimiento oficio"
        mode="view"
        value={dash(res)}
      />
    );
  }
  if (showDoc) {
    bloques.push(
      <Box key="doc">
        <DocumentacionTramiteModalLectura draft={draft} />
      </Box>
    );
  }
  if (showEdicion) {
    bloques.push(
      <Box
        key="ed"
        sx={{
          p: 1.25,
          borderRadius: 1.5,
          bgcolor: "rgba(255,255,255,0.04)",
          border: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        <Typography
          component="h3"
          sx={{
            ...docModalSubheadingInCardSx,
            fontSize: "0.6875rem",
            opacity: 0.9,
          }}
        >
          Edición en canal actas
        </Typography>
        <Typography
          variant="body2"
          sx={{
            color: DOC_MODAL_TEXT,
            fontSize: "0.8125rem",
            fontWeight: 400,
            lineHeight: 1.55,
            mt: 1,
            opacity: 0.88,
          }}
        >
          {textoRestriccionesEdicion(draft)}
        </Typography>
      </Box>
    );
  }

  return (
    <Stack
      divider={<Divider sx={{ borderColor: GLASS_COLORS.borderLight, opacity: 0.9 }} flexItem />}
      spacing={2.25}
      sx={{ width: "100%" }}
    >
      {bloques}
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
  numeroEditorLabel = "Número o referencia",
  onClose,
  onDraftChange,
  onSave,
  disablePortal,
  initialEditing = false,
}: ActuacionDetalleDialogProps) {
  const navigate = useNavigate();
  const feedback = useAppFeedback();
  const scrollContainerRef = useCrudDialogScrollContainer();
  const actaFlushRegistry = useRef<Set<() => void>>(new Set());
  const [isEditing, setIsEditing] = useState(initialEditing);
  const [editBaseline, setEditBaseline] = useState<IActuacionListItem | null>(null);
  const [epicollectOtrosExpanded, setEpicollectOtrosExpanded] = useState(false);
  const [inspectoresAddInput, setInspectoresAddInput] = useState("");

  const editableFields = useMemo(() => getActuacionEditableFields(draft), [draft]);

  const registerActaFlush = useCallback((fn: () => void) => {
    actaFlushRegistry.current.add(fn);
    return () => {
      actaFlushRegistry.current.delete(fn);
    };
  }, []);

  useEffect(() => {
    if (open) {
      setIsEditing(initialEditing);
      setEditBaseline(initialEditing ? { ...draft } : null);
      setEpicollectOtrosExpanded(false);
      setInspectoresAddInput("");
      actaFlushRegistry.current.clear();
    }
  }, [open, draft.id, initialEditing]);

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

  const motivoComprobacionOptions = useMemo(
    () => opts(getDropdownOptions("Motivo comprobación", mergedCatalogs)),
    [mergedCatalogs]
  );

  const contraCrudOptions = useMemo(
    () => buildContraproducenciaCrudSelectOptions(mergedCatalogs.contraproducencias, draft.contraproducencia),
    [mergedCatalogs.contraproducencias, draft.contraproducencia]
  );

  const contraUxHint = useMemo(
    () => getContraproducenciaUxHint(draft.contraproducencia ?? ""),
    [draft.contraproducencia]
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

  const handleBackToDetail = useCallback(() => {
    if (saving) return;
    setIsEditing(false);
  }, [saving]);

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
    setEditBaseline({ ...draft });
    setIsEditing(true);
  }, [draft, feedback]);

  const handleSaveClick = useCallback(() => {
    actaFlushRegistry.current.forEach((fn) => fn());
    const baseline = editBaseline ?? draft;
    const blockedMsg = detectBlockedActaClearAttempt(draft, baseline);
    if (blockedMsg) {
      feedback.warning(blockedMsg);
      return;
    }
    void onSave();
  }, [draft, editBaseline, feedback, onSave]);

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
        ...(value == null ? { comprobacion_motivo: null } : {}),
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

    return (
    <Stack spacing={DOC_MODAL_BLOCK_STACK_SPACING} component="section" aria-label="Ficha de la actuación">
      <DocumentalBloque overline="Domicilio y establecimiento">
        <Box sx={{ ...edicionGrid2ColSx, ...edicionGapBloqueAPrimerControlSx }}>
          <CrudFormSlot label="Calle" mode="view" value={dash(draft.calle)} />
          <CrudFormSlot label="Número o referencia" mode="view" value={dash(draft.numero)} />
          <CrudFormSlot
            label="Tipo de numeración"
            mode="view"
            value={dash(draft.numero_tipo)}
            sx={{ gridColumn: { xs: "1 / -1", sm: "1 / -1" } }}
          />
        </Box>
        <CrudFormSlot label="Nombre de fantasía" mode="view" value={dash(draft.nombre_local)} sx={{ mt: 2 }} />
        <Box sx={{ ...edicionGrid2ColSx, mt: 2 }}>
          <CrudFormSlot label="Rubro" mode="view" value={dash(draft.rubro_nombre)} />
          <CrudFormSlot label="N.º de documento" mode="view" value={dash(draft.doc_nro)} />
          <CrudFormSlot label="Apellido" mode="view" value={dash(draft.contrib_apellido)} />
          <CrudFormSlot label="Nombre" mode="view" value={dash(draft.contrib_nombre)} />
          <CrudFormSlot
            label="Razón social"
            mode="view"
            value={dash(draft.razon_social)}
            sx={{ gridColumn: { xs: "1 / -1", sm: "1 / -1" } }}
          />
        </Box>
        <CrudFormSlot
          label="Vinculación a ficha de establecimiento"
          mode="view"
          value={establecimientoVinculacionTexto(draft)}
          sx={{ mt: 2 }}
        />
        {draft.establecimiento_operativo_id != null ? (
          <Box sx={{ mt: 1.5 }}>
            <AppButton
              dsVariant="secondary"
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
      </DocumentalBloque>

      <DocumentalBloque overline="Datos de la actuación">
        <Box sx={edicionGrid2ColSx}>
          <CrudFormSlot label="OT" mode="view" value={dash(draft.orden_trabajo_numero)} />
          <CrudFormSlot label="Fecha de la visita" mode="view" value={dash(draft.fecha_actuacion)} />
          <CrudFormSlot label="Tipo de actuación" mode="view" value={dash(draft.tipo_actuacion)} />
          <CrudFormSlot label="Contraproducencia" mode="view" value={dash(draft.contraproducencia)} />
        </Box>
        <CrudFormSlot
          label="Inspectores a cargo"
          mode="view"
          value={draft.inspectores_texto?.trim() || inspectoresLinea(draft)}
          sx={{ mt: 2, width: "100%" }}
        />
      </DocumentalBloque>

      {actasVisitaHayContenido(draft) ? (
        <DocumentalBloque overline="Actas labradas" sectionTitleSx={actasLabradasSectionTitleSx}>
          <ActasVisitaLectura draft={draft} />
        </DocumentalBloque>
      ) : null}

      {resultadoSeguimientoHayContenido(draft) ? (
        <DocumentalBloque overline="Resultado operativo">
          <ResultadoSeguimientoLectura draft={draft} />
        </DocumentalBloque>
      ) : null}

      {tieneSnapshotEpicollectLectura || tieneEvidenciasEpicollect ? (
        <DocumentalBloque overline="Formulario de campo y evidencias">
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
        </DocumentalBloque>
      ) : null}
    </Stack>
    );
  }, [draft, epicollectOtrosExpanded, onClose, navigate, toggleEpicollectOtros]);

  const edicionVista = useMemo(() => {
    const e = (key: string) => fieldErrors[key] ?? "";
    const fieldHelper = (key: string) => e(key) || "\u00a0";
    const ro = (key: string) => readOnlyColumns.includes(key);
    const canContrib = editableFields.canEditContribuyente;
    const canDom = editableFields.canEditDomicilio;
    const canNotifEdit = editableFields.canEditNotificacion;
    const helperBloqueo = (key: string, locked: boolean) => {
      const msg = locked ? e(key) : e(key);
      return msg || "\u00a0";
    };

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
      <Box sx={{ display: "flex", flexDirection: "column", gap: 2, width: "100%" }}>
        <ActaNumFieldLazy
          value={draft.acta_notificacion_num}
          onCommit={commitActaNotificacion}
          disabled={lockedNotif}
          saving={saving}
          registerFlush={registerActaFlush}
          error={!!e("acta_notificacion_num")}
          helperText={helperBloqueo("acta_notificacion_num", lockedNotif)}
        />
        <Box sx={{ width: "100%" }}>
          <Typography variant="body2" sx={{ color: DOC_MODAL_TEXT, fontWeight: 600, mb: 0.75 }}>
            Motivos de notificación (máx. {MOTIVOS_NOTIFICACION_MAX})
          </Typography>
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, mb: 1.25, minHeight: 36 }}>
            {motivosNotifSeleccionados.length === 0 ? (
              <Typography variant="body2" sx={{ color: DOC_MODAL_TEXT, opacity: 0.9 }}>
                Ninguno — agregá desde el catálogo.
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
                  sx={{ color: DOC_MODAL_TEXT, borderColor: "rgba(255,255,255,0.35)" }}
                  variant="outlined"
                />
              ))
            )}
          </Box>
          <Autocomplete
            size="small"
            options={motivosDisponiblesAgregar}
            value={null}
            disabled={lockedNotif || motivosNotifSeleccionados.length >= MOTIVOS_NOTIFICACION_MAX}
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
        </Box>
      </Box>
    );

    const gridComprobacion = (
      <Box sx={{ display: "flex", flexDirection: "column", gap: 2, width: "100%" }}>
        <ActaNumFieldLazy
          value={draft.acta_comprobacion_num}
          onCommit={commitActaComprobacion}
          disabled={lockedComp}
          saving={saving}
          registerFlush={registerActaFlush}
          error={!!e("acta_comprobacion_num")}
          helperText={helperBloqueo("acta_comprobacion_num", lockedComp)}
        />
        <AppSelect
          appearance="glass"
          label="Motivo de comprobación"
          value={draft.comprobacion_motivo ?? ""}
          onChange={(ev) => onDraftChange({ comprobacion_motivo: ev.target.value as string })}
          options={motivoComprobacionOptions}
          disabled={lockedComp}
          error={!!e("comprobacion_motivo")}
          helperText={helperBloqueo("comprobacion_motivo", lockedComp)}
          fullWidth
        />
      </Box>
    );

    return (
      <Stack spacing={DOC_MODAL_BLOCK_STACK_SPACING} component="section" aria-label="Edición de la actuación">
        <DocumentalBloque overline="Domicilio y establecimiento">
          <Box sx={{ ...edicionGrid2ColSx, ...edicionGapBloqueAPrimerControlSx }}>
            <AppTextField
              appearance="glass"
              label="Calle"
              value={domicilioCalleCargadaEditable(draft)}
              onChange={(ev) => onDraftChange({ calle: ev.target.value.trim() ? ev.target.value.trim() : null })}
              disabled={ro("calle") || !canDom}
              error={!!e("calle")}
              helperText={fieldHelper("calle")}
              sx={!canDom ? roFieldSx : undefined}
              fullWidth
            />
            <NumeroEsquinaFreeEditor
              value={
                draft.numero_tipo === "ESQUINA"
                  ? domicilioNumeroEditable(draft) || null
                  : draft.numero ?? null
              }
              onChange={(newValue) => onDraftChange({ numero: newValue })}
              onModeChange={(editorMode) => onDraftChange({ numero_tipo: editorMode })}
              label={numeroEditorLabel}
              error={!!e("numero")}
              helperText={fieldHelper("numero")}
              disabled={ro("numero") || !canDom}
              initialMode={draft.numero_tipo === "ESQUINA" ? "ESQUINA" : "NUMERO"}
            />
          </Box>
          <AppTextField
            appearance="glass"
            label="Nombre de fantasía"
            value={draft.nombre_local ?? ""}
            onChange={(ev) => onDraftChange({ nombre_local: ev.target.value || null })}
            disabled={!canContrib}
            error={!!e("nombre_local")}
            helperText={fieldHelper("nombre_local")}
            sx={{ mt: 2, ...(!canContrib ? roFieldSx : {}) }}
            fullWidth
          />
          <Box sx={{ ...edicionGrid2ColSx, mt: 2 }}>
            <AppSelect
              appearance="glass"
              label="Rubro"
              value={draft.rubro_nombre ?? ""}
              onChange={(ev) => onDraftChange({ rubro_nombre: ev.target.value as string })}
              options={rubrosOptions}
              disabled={ro("rubro_nombre") || !canDom}
              error={!!e("rubro_nombre")}
              helperText={fieldHelper("rubro_nombre")}
              fullWidth
            />
            <AppTextField
              appearance="glass"
              label="N.º de documento"
              value={draft.doc_nro ?? ""}
              onChange={(ev) => onDraftChange({ doc_nro: ev.target.value })}
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
              onChange={(ev) => onDraftChange({ contrib_apellido: ev.target.value })}
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
              onChange={(ev) => onDraftChange({ contrib_nombre: ev.target.value })}
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
              onChange={(ev) => onDraftChange({ razon_social: ev.target.value || null })}
              disabled={!canContrib}
              error={!!e("razon_social")}
              helperText={fieldHelper("razon_social")}
              sx={{ gridColumn: { xs: "1 / -1", sm: "1 / -1" }, ...(!canContrib ? roFieldSx : {}) }}
              fullWidth
            />
          </Box>
        </DocumentalBloque>

        <DocumentalBloque overline="Datos de la actuación">
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
              <AppSelect
                appearance="glass"
                label="Contraproducencia"
                value={draft.contraproducencia ?? ""}
                onChange={(ev) => {
                  const v = String(ev.target.value ?? "").trim();
                  onDraftChange({ contraproducencia: v || null });
                }}
                options={contraCrudOptions}
                disabled={saving}
                error={!!e("contraproducencia")}
                helperText={
                  fieldHelper("contraproducencia") ||
                  (contraUxHint && !e("contraproducencia") ? contraUxHint : undefined)
                }
                fullWidth
              />
            </Box>
            <Box sx={{ mt: 2, width: "100%" }}>
              <Typography variant="body2" sx={{ color: DOC_MODAL_TEXT, fontWeight: 600, mb: 0.5 }}>
                Inspectores a cargo
              </Typography>
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, mb: 1.25, minHeight: 36 }}>
                {inspectoresEnOrdenLocal.length === 0 ? (
                  <Typography variant="body2" sx={{ color: DOC_MODAL_TEXT, opacity: 0.92 }}>
                    Ninguno — agregá desde el catálogo.
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
                      sx={{ color: DOC_MODAL_TEXT, borderColor: "rgba(255,255,255,0.35)" }}
                      variant="outlined"
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

        <DocumentalBloque overline="Actas labradas" sectionTitleSx={actasLabradasSectionTitleSx}>
          <Box sx={actaGrupoWrapperSx}>
            <Typography component="h3" sx={actaSubtituloMenorSx}>
              Acta de inspección
            </Typography>
            <ActaNumFieldLazy
              value={draft.acta_inspeccion_num}
              onCommit={commitActaInspeccion}
              saving={saving}
              registerFlush={registerActaFlush}
              error={!!e("acta_inspeccion_num")}
              helperText={fieldHelper("acta_inspeccion_num")}
            />
          </Box>

          {canNotifEdit ? (
          <Box sx={actaGrupoWrapperSx}>
            <Typography component="h3" sx={actaSubtituloMenorSx}>
              Acta de notificación
            </Typography>
            {lockedNotif ? (
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
            )}
          </Box>
          ) : null}

          <Box sx={actaGrupoWrapperSx}>
            <Typography component="h3" sx={actaSubtituloMenorSx}>
              Acta de comprobación
            </Typography>
            {lockedComp ? (
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
            )}
          </Box>

          <Box sx={actaGrupoWrapperSx}>
            <Typography component="h3" sx={actaSubtituloMenorSx}>
              Acta de clausura
            </Typography>
            <ActaNumFieldLazy
              value={draft.acta_clausura_num}
              onCommit={commitActaClausura}
              saving={saving}
              registerFlush={registerActaFlush}
              error={!!e("acta_clausura_num")}
              helperText={fieldHelper("acta_clausura_num")}
            />
          </Box>

          <Box sx={actaGrupoWrapperSx}>
            <Typography component="h3" sx={actaSubtituloMenorSx}>
              Acta de decomiso
            </Typography>
            <ActaNumFieldLazy
              value={draft.acta_decomiso_num}
              onCommit={commitActaDecomiso}
              saving={saving}
              registerFlush={registerActaFlush}
              error={!!e("acta_decomiso_num")}
              helperText={fieldHelper("acta_decomiso_num")}
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
              helperText={fieldHelper("decomiso_kilos_total")}
              fullWidth
              sx={{ mt: 1.5 }}
            />
          </Box>
        </DocumentalBloque>

        {muestraResultadoSeguimientoEdicion ? (
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
          <DocumentalBloque overline="Formulario de campo y evidencias">
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
    readOnlyColumns,
    editableFields,
    registerActaFlush,
    numeroEditorLabel,
    lockedNotif,
    lockedComp,
    mergedCatalogs,
    rubrosOptions,
    motivoComprobacionOptions,
    epicollectOtrosExpanded,
    toggleEpicollectOtros,
    onDraftChange,
    commitActaInspeccion,
    commitActaNotificacion,
    commitActaComprobacion,
    commitActaClausura,
    commitActaDecomiso,
    applyMotivosNotificacion,
    applyInspectoresNombres,
    saving,
  ]);

  return (
    <CrudGlassDialog
      open={open}
      disablePortal={disablePortal}
      hideBackdrop={disablePortal}
      onClose={handleDialogClose}
      onCloseButtonClick={handleClose}
      maxWidth="md"
      title={
        <CrudDialogHeader
          domainChip="Actuaciones"
          mode={isEditing ? "edit" : "view"}
          titulo={isEditing ? "Editar actuación" : "Ver actuación"}
          subtitulo="Detalle operativo"
        />
      }
      actions={
        <CrudDialogActions
          mode={isEditing ? "edit" : "view"}
          onEdit={canEdit ? handleStartEditing : undefined}
          onSave={handleSaveClick}
          loading={saving}
          canEdit={canEdit}
          saveLabel="Guardar cambios"
          extraActions={
            <AppButton dsVariant="ghost" dsSize="sm" onClick={handlePrint} disabled={saving}>
              Imprimir
            </AppButton>
          }
        />
      }
    >
      {!isEditing ? detalleVista : edicionVista}
    </CrudGlassDialog>
  );
}
