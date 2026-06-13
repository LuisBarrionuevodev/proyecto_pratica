import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import type { ReactNode } from "react";
import {
  Alert,
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
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { ActaCanalQuitarTipo, IActuacionListItem } from "../../../api/actuacionesListApi";
import { formatActuacionListDomicilioLinea } from "../../../utils/formatDomicilioLineaVisible";
import {
  MOTIVOS_NOTIFICACION_MAX,
  mergeMotivosNotifCatalogStrings,
  motivosNotificacionFromSlots,
  orderedMotivosNotificacion,
} from "../../../utils/motivosNotificacionSlots";
import { getDropdownOptions } from "../../CargarActuaciones/config/dropdownOptions";
import { mergeLegacyRubroNames } from "../../../utils/rubrosCatalogCache";
import { applyActuacionErrorsFromApi } from "../utils/submitActuacionRow";
import { formDialogContentStackSx } from "../../../styles/formDialogStyles";
import {
  DOC_MODAL_BLOCK_STACK_SPACING,
  DOC_MODAL_TEXT,
  docModalBlockOverlineSx,
  docModalBlockResumenSx,
  docModalChipSx,
  docModalFilaEtiquetaSx,
  docModalFilaValorSx,
  docModalFooterButtonsSx,
  docModalFooterHintSx,
  docModalFooterRowSx,
  docModalActuacionScrollCardShellSx,
  docModalHeaderStackSx,
  docModalIntroParagraphSx,
  docModalReferenceSx,
  docModalSubheadingInCardSx,
  docModalSubtitleSx,
  docModalTitleSx,
} from "../../../styles/documentalModalTokens";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { AppButton, AppDialog, AppSelect, AppTextField, ConfirmDialog } from "../../../ui";
import { COLORS } from "../styles/filtroStyles";
import { ActuacionDocumentacionChips } from "./ActuacionDocumentacionChips";
import {
  actuacionDocumentacionOrigenReinspeccionSegments,
  actuacionDocumentacionPropiaTramiteSegments,
} from "../utils/actuacionDocumentacionVisual";

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

const QUITAR_ACTA_TITLE: Record<ActaCanalQuitarTipo, string> = {
  INSPECCION: "Quitar acta de inspección",
  NOTIFICACION: "Quitar acta de notificación",
  COMPROBACION: "Quitar acta de comprobación",
  CLAUSURA: "Quitar acta de clausura",
  DECOMISO: "Quitar acta de decomiso",
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
  /** Resumen breve cuando hay errores por campo; error global si no hay mapeo inline. */
  formGlobalError?: string | null;
  saving: boolean;
  catalogs: ActuacionEditCatalogs;
  readOnlyColumns: string[];
  /** Opciones de calle para editor de número (p. ej. gestión domicilios); opcional en actuaciones. */
  numeroCallesOptions?: string[];
  numeroEditorLabel?: string;
  numeroAllowFreeSolo?: boolean;
  /** Si es false, no se muestra el paso a edición (p. ej. bandejas restringidas). */
  canEdit?: boolean;
  /** Si se informa, el modal muestra «Eliminar» por acta y llama aquí tras confirmar (POST quitar-acta). */
  onQuitarActa?: (tipo: ActaCanalQuitarTipo) => Promise<void>;
  onClose: () => void;
  onDraftChange: (patch: Partial<IActuacionListItem>) => void;
  onSave: () => void | Promise<void>;
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

/** Marco discreto para datos de visita de solo contexto en edición. */
const edicionContextoVisitaSx = {
  p: 1.5,
  borderRadius: 1.5,
  bgcolor: "rgba(255,255,255,0.03)",
  border: "1px solid rgba(255,255,255,0.06)",
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
const edicionActaSubtituloSx = { ...docModalSubheadingInCardSx, mb: 1.5 } as const;

/** Aire entre el overline/resumen del bloque documental y el primer control (p. ej. Lugar y titular, formulario). */
const edicionGapBloqueAPrimerControlSx = { mt: 2 } as const;

const dateFieldShrinkLabelProps = { shrink: true } as const;

function dash(v: unknown): string {
  if (v === null || v === undefined || v === "") return "—";
  return String(v);
}

function domicilioTexto(row: IActuacionListItem): string {
  const line = formatActuacionListDomicilioLinea(row).trim();
  return line || "—";
}

function titularLinea(row: IActuacionListItem): string {
  const rs = (row.razon_social ?? "").trim();
  if (rs) return rs;
  const a = (row.contrib_apellido ?? "").trim();
  const n = (row.contrib_nombre ?? "").trim();
  const t = [a, n].filter(Boolean).join(", ");
  return t || "—";
}

function actaInspeccionTieneNumero(d: IActuacionListItem): boolean {
  const n = d.acta_inspeccion_num;
  return n != null && String(n).trim() !== "";
}

function actaNotificacionTieneContenido(d: IActuacionListItem): boolean {
  const n = d.acta_notificacion_num;
  const num = n != null && String(n).trim() !== "";
  return num || motivosNotificacionNoVacios(d).length > 0;
}

function actaComprobacionTieneContenido(d: IActuacionListItem): boolean {
  const n = d.acta_comprobacion_num;
  const num = n != null && String(n).trim() !== "";
  const m = d.comprobacion_motivo != null && String(d.comprobacion_motivo).trim() !== "";
  return num || m;
}

function actaClausuraTieneNumero(d: IActuacionListItem): boolean {
  const n = d.acta_clausura_num;
  return n != null && String(n).trim() !== "";
}

function actaDecomisoTieneContenido(d: IActuacionListItem): boolean {
  const n = d.acta_decomiso_num;
  const num = n != null && String(n).trim() !== "";
  const k = d.decomiso_kilos_total != null && Number(d.decomiso_kilos_total) > 0;
  return num || k;
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

/** Número de acta como lectura principal en la card "Actas de la visita". */
const actaNumeroPrincipalSx = {
  color: DOC_MODAL_TEXT,
  fontWeight: 700,
  fontSize: "1.0625rem",
  lineHeight: 1.35,
  letterSpacing: "0.02em",
  fontFamily: '"Tactic Sans", sans-serif',
  mt: 0.75,
  wordBreak: "break-word" as const,
};

/** Motivos, kilos y complementos bajo el número de acta. */
const actaDetalleSecundarioSx = {
  color: DOC_MODAL_TEXT,
  fontSize: "0.8125rem",
  fontWeight: 400,
  lineHeight: 1.5,
  opacity: 0.92,
  mt: 1,
};

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
          <Typography component="h3" sx={docModalSubheadingInCardSx}>
            Acta de inspección
          </Typography>
          <Typography component="p" sx={actaNumeroPrincipalSx}>
            {dash(nIns)}
          </Typography>
        </Box>
      ) : null}

      {showNotificacion ? (
        <Box sx={actaGrupoWrapperSx}>
          <Typography component="h3" sx={docModalSubheadingInCardSx}>
            Acta de notificación
          </Typography>
          <Typography component="p" sx={actaNumeroPrincipalSx}>
            {numNot}
          </Typography>
          {motivosNoti.length > 0 ? (
            <Box sx={{ mt: 1.25, pl: 0.25 }}>
              <Typography
                variant="caption"
                component="p"
                sx={{
                  color: DOC_MODAL_TEXT,
                  opacity: 0.65,
                  fontWeight: 600,
                  letterSpacing: "0.06em",
                  textTransform: "uppercase",
                  fontSize: "0.6875rem",
                  mb: 0.75,
                }}
              >
                Motivos
              </Typography>
              <Stack spacing={0.5} component="div">
                {motivosNoti.map((m, i) => (
                  <Typography key={i} sx={{ ...actaDetalleSecundarioSx, pl: 1, borderLeft: "2px solid rgba(255,255,255,0.12)" }}>
                    {m}
                  </Typography>
                ))}
              </Stack>
            </Box>
          ) : null}
        </Box>
      ) : null}

      {showComprobacion ? (
        <Box sx={actaGrupoWrapperSx}>
          <Typography component="h3" sx={docModalSubheadingInCardSx}>
            Acta de comprobación
          </Typography>
          <Typography component="p" sx={actaNumeroPrincipalSx}>
            {numComp}
          </Typography>
          {mComp ? (
            <Typography component="p" sx={actaDetalleSecundarioSx}>
              <Box component="span" sx={{ opacity: 0.75, fontWeight: 600 }}>
                Motivo:{" "}
              </Box>
              {mComp}
            </Typography>
          ) : null}
        </Box>
      ) : null}

      {showClausura ? (
        <Box sx={actaGrupoWrapperSx}>
          <Typography component="h3" sx={docModalSubheadingInCardSx}>
            Acta de clausura
          </Typography>
          <Typography component="p" sx={actaNumeroPrincipalSx}>
            {dash(nClau)}
          </Typography>
        </Box>
      ) : null}

      {showDecomiso ? (
        <Box sx={actaGrupoWrapperSx}>
          <Typography component="h3" sx={docModalSubheadingInCardSx}>
            Acta de decomiso
          </Typography>
          <Typography component="p" sx={actaNumeroPrincipalSx}>
            {numDec}
          </Typography>
          {kg != null ? (
            <Typography component="p" sx={{ ...actaDetalleSecundarioSx, mt: 1 }}>
              <Box component="span" sx={{ opacity: 0.75, fontWeight: 600 }}>
                Kilos decomisados:{" "}
              </Box>
              {kg} kg
            </Typography>
          ) : null}
        </Box>
      ) : null}
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
    <Box sx={docModalActuacionScrollCardShellSx(COLORS.primary)}>
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

function tieneRestriccionesEdicion(row: IActuacionListItem): boolean {
  return row.notificacion_editable === false || row.comprobacion_editable === false;
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
      <Box key="res">
        <Typography component="p" sx={{ ...actaNumeroPrincipalSx, m: 0 }}>
          {dash(res)}
        </Typography>
      </Box>
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
  formGlobalError = null,
  saving,
  catalogs,
  readOnlyColumns,
  canEdit = true,
  onQuitarActa,
  onClose,
  onDraftChange,
  onSave,
}: ActuacionDetalleDialogProps) {
  const navigate = useNavigate();
  const [isEditing, setIsEditing] = useState(false);
  const [epicollectOtrosExpanded, setEpicollectOtrosExpanded] = useState(false);
  const [quitarConfirmTipo, setQuitarConfirmTipo] = useState<ActaCanalQuitarTipo | null>(null);
  const [quitarBusy, setQuitarBusy] = useState(false);
  const [quitarActaError, setQuitarActaError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setIsEditing(false);
      setEpicollectOtrosExpanded(false);
    }
  }, [open, draft.id]);

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

  const handleStartEditing = useCallback(() => setIsEditing(true), []);

  const handleSaveClick = useCallback(() => {
    void onSave();
  }, [onSave]);

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

  const handleAskQuitarActa = useCallback((tipo: ActaCanalQuitarTipo) => {
    setQuitarConfirmTipo(tipo);
  }, []);

  const handleDismissQuitar = useCallback(() => {
    if (!quitarBusy) setQuitarConfirmTipo(null);
  }, [quitarBusy]);

  const handleConfirmQuitarActa = useCallback(async () => {
    if (!quitarConfirmTipo || !onQuitarActa) return;
    setQuitarBusy(true);
    setQuitarActaError(null);
    try {
      await onQuitarActa(quitarConfirmTipo);
      setQuitarConfirmTipo(null);
    } catch (err: unknown) {
      const { globalMessage } = applyActuacionErrorsFromApi(err);
      setQuitarActaError(globalMessage ?? "No se pudo quitar el acta.");
    } finally {
      setQuitarBusy(false);
    }
  }, [quitarConfirmTipo, onQuitarActa]);

  const toggleEpicollectOtros = useCallback(() => {
    setEpicollectOtrosExpanded((v) => !v);
  }, []);

  const documentalTitleRead = useMemo(
    () => (
      <Box sx={{ ...docModalHeaderStackSx, width: "100%" }}>
        <Chip label="Actuaciones" size="small" sx={docModalChipSx} variant="outlined" />
        <Typography component="span" variant="h6" sx={docModalTitleSx}>
          {`OT ${dash(draft.orden_trabajo_numero)}`}
        </Typography>
        <Typography variant="body2" sx={docModalSubtitleSx}>
          {dash(draft.tipo_actuacion)}
        </Typography>
        <Typography variant="caption" component="div" sx={{ ...docModalReferenceSx, maxWidth: "100%" }}>
          Actuación #{draft.id}
        </Typography>
      </Box>
    ),
    [draft.id, draft.orden_trabajo_numero, draft.tipo_actuacion]
  );

  /** Misma identidad que lectura, con marca discreta de modo edición. */
  const documentalTitleEdit = useMemo(
    () => (
      <Box sx={{ ...docModalHeaderStackSx, width: "100%" }}>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, alignItems: "center" }}>
          <Chip label="Actuaciones" size="small" sx={docModalChipSx} variant="outlined" />
          <Chip
            label="Edición"
            size="small"
            sx={{
              ...docModalChipSx,
              borderColor: "rgba(255,255,255,0.38)",
              bgcolor: "rgba(255,255,255,0.08)",
            }}
            variant="outlined"
          />
        </Box>
        <Typography component="span" variant="h6" sx={docModalTitleSx}>
          {`OT ${dash(draft.orden_trabajo_numero)}`}
        </Typography>
        <Typography variant="body2" sx={docModalSubtitleSx}>
          {dash(draft.tipo_actuacion)}
        </Typography>
        <Typography variant="caption" component="div" sx={{ ...docModalReferenceSx, maxWidth: "100%" }}>
          Actuación #{draft.id}
        </Typography>
      </Box>
    ),
    [draft.id, draft.orden_trabajo_numero, draft.tipo_actuacion]
  );

  const detalleVista = useMemo(() => {
    const tieneSnapshotEpicollectLectura = epicollectSnapshotLecturaHayContenido(draft);
    const gruposEvid = draft.epicollect_evidencias_grupos ?? [];
    const totalEvid = draft.epicollect_evidencias_total ?? 0;
    const tieneEvidenciasEpicollect = totalEvid > 0 && gruposEvid.length > 0;

    return (
    <Stack spacing={DOC_MODAL_BLOCK_STACK_SPACING} component="section" aria-label="Ficha de la actuación">
      <DocumentalBloque overline="Lugar y titular">
        <DocumentalFila etiqueta="Domicilio (calle y número)" valor={domicilioTexto(draft)} />
        <DocumentalFila etiqueta="Nombre de fantasía" valor={dash(draft.nombre_local)} />
        <DocumentalFila etiqueta="Titular o razón social" valor={titularLinea(draft)} />
        <DocumentalFila etiqueta="N.º de documento" valor={dash(draft.doc_nro)} />
        <DocumentalFila etiqueta="Rubro" valor={dash(draft.rubro_nombre)} />
        <DocumentalFila
          etiqueta="Vinculación a ficha de establecimiento"
          valor={
            draft.establecimiento_operativo_id != null
              ? `Ficha n.º ${draft.establecimiento_operativo_id}${
                  draft.establecimiento_actuaciones_en_ficha != null
                    ? ` · ${draft.establecimiento_actuaciones_en_ficha} actuación${
                        draft.establecimiento_actuaciones_en_ficha === 1 ? "" : "es"
                      } en esa ficha`
                    : ""
                }`
              : "—"
          }
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

      <DocumentalBloque overline="La visita">
        <DocumentalFila etiqueta="Fecha de la visita" valor={dash(draft.fecha_actuacion)} />
        <DocumentalFila etiqueta="Inspectores a cargo" valor={draft.inspectores_texto?.trim() || inspectoresLinea(draft)} />
        <DocumentalFila etiqueta="Contraproducencia" valor={dash(draft.contraproducencia)} />
      </DocumentalBloque>

      {actasVisitaHayContenido(draft) ? (
        <DocumentalBloque overline="Actas de la visita">
          <ActasVisitaLectura draft={draft} />
        </DocumentalBloque>
      ) : null}

      {resultadoSeguimientoHayContenido(draft) ? (
        <DocumentalBloque overline="Resultado y seguimiento">
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
    const ro = (key: string) => readOnlyColumns.includes(key);
    const helperBloqueo = (key: string, locked: boolean) => (locked ? e(key) || undefined : e(key));

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
        <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "flex-start", gap: 1 }}>
          <Box sx={{ flex: "1 1 220px", minWidth: 0 }}>
            <AppTextField
              appearance="glass"
              label="Número de acta"
              value={draft.acta_notificacion_num ?? ""}
              onChange={(ev) => onDraftChange({ acta_notificacion_num: ev.target.value })}
              disabled={lockedNotif}
              error={!!e("acta_notificacion_num")}
              helperText={helperBloqueo("acta_notificacion_num", lockedNotif)}
              fullWidth
            />
          </Box>
          {onQuitarActa && actaNotificacionTieneContenido(draft) && !lockedNotif ? (
            <AppButton
              dsVariant="danger"
              dsSize="sm"
              sx={{ flexShrink: 0, mt: 0.5 }}
              onClick={() => handleAskQuitarActa("NOTIFICACION")}
              disabled={saving}
            >
              Eliminar
            </AppButton>
          ) : null}
        </Box>
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
                helperText={helperBloqueo("notificacion_motivo_1", lockedNotif) || undefined}
              />
            )}
          />
        </Box>
      </Box>
    );

    const gridComprobacion = (
      <Box sx={{ display: "flex", flexDirection: "column", gap: 2, width: "100%" }}>
        <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "flex-start", gap: 1 }}>
          <Box sx={{ flex: "1 1 220px", minWidth: 0 }}>
            <AppTextField
              appearance="glass"
              label="Número de acta"
              value={draft.acta_comprobacion_num ?? ""}
              onChange={(ev) => onDraftChange({ acta_comprobacion_num: ev.target.value })}
              disabled={lockedComp}
              error={!!e("acta_comprobacion_num")}
              helperText={helperBloqueo("acta_comprobacion_num", lockedComp)}
              fullWidth
            />
          </Box>
          {onQuitarActa && actaComprobacionTieneContenido(draft) && !lockedComp ? (
            <AppButton
              dsVariant="danger"
              dsSize="sm"
              sx={{ flexShrink: 0, mt: 0.5 }}
              onClick={() => handleAskQuitarActa("COMPROBACION")}
              disabled={saving}
            >
              Eliminar
            </AppButton>
          ) : null}
        </Box>
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
        {formGlobalError ? (
          <Alert severity="error" sx={{ borderRadius: 2 }}>
            {formGlobalError}
          </Alert>
        ) : null}
        <DocumentalBloque overline="Lugar y titular">
          <Box sx={{ ...edicionGrid2ColSx, ...edicionGapBloqueAPrimerControlSx }}>
            <AppTextField
              appearance="glass"
              label="Calle"
              value={draft.calle ?? ""}
              onChange={(ev) => onDraftChange({ calle: ev.target.value.trim() ? ev.target.value.trim() : null })}
              disabled={ro("calle")}
              error={!!e("calle")}
              helperText={e("calle")}
              fullWidth
            />
            <AppTextField
              appearance="glass"
              label="Número o referencia"
              value={draft.numero ?? ""}
              onChange={(ev) => onDraftChange({ numero: ev.target.value.trim() ? ev.target.value.trim() : null })}
              disabled={ro("numero")}
              error={!!e("numero")}
              helperText={e("numero")}
              fullWidth
            />
            <AppSelect
              appearance="glass"
              label="Tipo de numeración"
              value={(draft.numero_tipo ?? "").trim().toUpperCase() || ""}
              onChange={(ev) => {
                const v = String(ev.target.value ?? "").trim().toUpperCase();
                onDraftChange({ numero_tipo: v ? v : null });
              }}
              options={opts(["", "NUMERO", "ESQUINA", "OTRO"])}
              disabled={ro("numero_tipo")}
              error={!!e("numero_tipo")}
              helperText={e("numero_tipo")}
              fullWidth
              sx={{ gridColumn: { xs: "1 / -1", sm: "1 / -1" } }}
            />
          </Box>
          <AppTextField
            appearance="glass"
            label="Nombre de fantasía"
            value={draft.nombre_local ?? ""}
            onChange={(ev) => onDraftChange({ nombre_local: ev.target.value || null })}
            error={!!e("nombre_local")}
            helperText={e("nombre_local")}
            sx={{ mt: 2 }}
            fullWidth
          />
          <Box sx={{ ...edicionGrid2ColSx, mt: 2 }}>
            <AppSelect
              appearance="glass"
              label="Rubro"
              value={draft.rubro_nombre ?? ""}
              onChange={(ev) => onDraftChange({ rubro_nombre: ev.target.value as string })}
              options={rubrosOptions}
              disabled={ro("rubro_nombre")}
              error={!!e("rubro_nombre")}
              helperText={e("rubro_nombre")}
              fullWidth
            />
            <AppTextField
              appearance="glass"
              label="N.º de documento"
              value={draft.doc_nro ?? ""}
              onChange={(ev) => onDraftChange({ doc_nro: ev.target.value })}
              error={!!e("doc_nro")}
              helperText={e("doc_nro")}
              fullWidth
            />
            <AppTextField
              appearance="glass"
              label="Apellido"
              value={draft.contrib_apellido ?? ""}
              onChange={(ev) => onDraftChange({ contrib_apellido: ev.target.value })}
              error={!!e("contrib_apellido")}
              helperText={e("contrib_apellido")}
              fullWidth
            />
            <AppTextField
              appearance="glass"
              label="Nombre"
              value={draft.contrib_nombre ?? ""}
              onChange={(ev) => onDraftChange({ contrib_nombre: ev.target.value })}
              error={!!e("contrib_nombre")}
              helperText={e("contrib_nombre")}
              fullWidth
            />
            <AppTextField
              appearance="glass"
              label="Razón social"
              value={draft.razon_social ?? ""}
              onChange={(ev) => onDraftChange({ razon_social: ev.target.value || null })}
              error={!!e("razon_social")}
              helperText={e("razon_social")}
              sx={{ gridColumn: { xs: "1 / -1", sm: "1 / -1" } }}
              fullWidth
            />
          </Box>
          <DocumentalFila etiqueta="Titular o razón social" valor={titularLinea(draft)} />
          <DocumentalFila
            etiqueta="Vinculación a ficha de establecimiento"
            valor={
              draft.establecimiento_operativo_id != null
                ? `Ficha n.º ${draft.establecimiento_operativo_id}${
                    draft.establecimiento_actuaciones_en_ficha != null
                      ? ` · ${draft.establecimiento_actuaciones_en_ficha} actuación${
                          draft.establecimiento_actuaciones_en_ficha === 1 ? "" : "es"
                        } en esa ficha`
                      : ""
                  }`
                : "—"
            }
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

        <DocumentalBloque overline="La visita">
          <Box sx={{ ...edicionContextoVisitaSx, ...edicionGapBloqueAPrimerControlSx }}>
            <Box sx={edicionGrid2ColSx}>
              <AppTextField
                appearance="glass"
                label="OT"
                value={draft.orden_trabajo_numero ?? ""}
                disabled
                sx={roFieldSx}
                fullWidth
              />
              <AppTextField
                appearance="glass"
                label="Fecha de la visita"
                type="date"
                value={draft.fecha_actuacion ?? ""}
                disabled
                sx={roFieldSx}
                InputLabelProps={dateFieldShrinkLabelProps}
                fullWidth
              />
              <AppTextField
                appearance="glass"
                label="Tipo de actuación"
                value={draft.tipo_actuacion ?? ""}
                disabled
                sx={roFieldSx}
                fullWidth
              />
              <AppTextField
                appearance="glass"
                label="Contraproducencia"
                value={draft.contraproducencia ?? ""}
                disabled
                sx={roFieldSx}
                fullWidth
              />
            </Box>
            <Box sx={{ mt: 2, width: "100%" }}>
              <Typography variant="body2" sx={{ color: DOC_MODAL_TEXT, fontWeight: 600, mb: 0.5 }}>
                Inspectores a cargo
              </Typography>
              <Typography variant="caption" component="div" sx={{ color: DOC_MODAL_TEXT, mb: 1.25, lineHeight: 1.45 }}>
                Elegí del catálogo; quitá con la cruz. Sin duplicados (orden de carga se conserva).
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
                disabled={saving || inspectoresDisponiblesAgregar.length === 0}
                onChange={(_, value) => {
                  if (!value || saving) return;
                  if (inspectoresEnOrdenLocal.includes(value)) return;
                  applyInspectoresNombres([...inspectoresEnOrdenLocal, value]);
                }}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Agregar inspector"
                    placeholder="Catálogo"
                    sx={modalAuxInputSx}
                    error={!!e("inspectores")}
                    helperText={e("inspectores") || undefined}
                  />
                )}
              />
            </Box>
          </Box>
        </DocumentalBloque>

        <DocumentalBloque overline="Actas de la visita">
          <Box sx={actaGrupoWrapperSx}>
            <Typography component="h3" sx={edicionActaSubtituloSx}>
              Acta de inspección
            </Typography>
            <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "flex-start", gap: 1 }}>
              <Box sx={{ flex: "1 1 220px", minWidth: 0 }}>
                <AppTextField
                  appearance="glass"
                  label="Número de acta"
                  value={draft.acta_inspeccion_num ?? ""}
                  onChange={(ev) => onDraftChange({ acta_inspeccion_num: ev.target.value })}
                  error={!!e("acta_inspeccion_num")}
                  helperText={e("acta_inspeccion_num")}
                  fullWidth
                />
              </Box>
              {onQuitarActa && actaInspeccionTieneNumero(draft) ? (
                <AppButton
                  dsVariant="danger"
                  dsSize="sm"
                  sx={{ flexShrink: 0, mt: 0.5 }}
                  onClick={() => handleAskQuitarActa("INSPECCION")}
                  disabled={saving}
                >
                  Eliminar
                </AppButton>
              ) : null}
            </Box>
          </Box>

          <Box sx={actaGrupoWrapperSx}>
            <Typography component="h3" sx={edicionActaSubtituloSx}>
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

          <Box sx={actaGrupoWrapperSx}>
            <Typography component="h3" sx={edicionActaSubtituloSx}>
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
            <Typography component="h3" sx={edicionActaSubtituloSx}>
              Acta de clausura
            </Typography>
            <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "flex-start", gap: 1 }}>
              <Box sx={{ flex: "1 1 220px", minWidth: 0 }}>
                <AppTextField
                  appearance="glass"
                  label="Número de acta"
                  value={draft.acta_clausura_num ?? ""}
                  onChange={(ev) => onDraftChange({ acta_clausura_num: ev.target.value })}
                  error={!!e("acta_clausura_num")}
                  helperText={e("acta_clausura_num")}
                  fullWidth
                />
              </Box>
              {onQuitarActa && actaClausuraTieneNumero(draft) ? (
                <AppButton
                  dsVariant="danger"
                  dsSize="sm"
                  sx={{ flexShrink: 0, mt: 0.5 }}
                  onClick={() => handleAskQuitarActa("CLAUSURA")}
                  disabled={saving}
                >
                  Eliminar
                </AppButton>
              ) : null}
            </Box>
          </Box>

          <Box sx={actaGrupoWrapperSx}>
            <Typography component="h3" sx={edicionActaSubtituloSx}>
              Acta de decomiso
            </Typography>
            <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "flex-start", gap: 1, width: "100%" }}>
              <Box sx={{ flex: "1 1 220px", minWidth: 0 }}>
                <AppTextField
                  appearance="glass"
                  label="Número de acta"
                  value={draft.acta_decomiso_num ?? ""}
                  onChange={(ev) => onDraftChange({ acta_decomiso_num: ev.target.value })}
                  error={!!e("acta_decomiso_num")}
                  helperText={e("acta_decomiso_num")}
                  fullWidth
                />
              </Box>
              {onQuitarActa && actaDecomisoTieneContenido(draft) ? (
                <AppButton
                  dsVariant="danger"
                  dsSize="sm"
                  sx={{ flexShrink: 0, mt: 0.5 }}
                  onClick={() => handleAskQuitarActa("DECOMISO")}
                  disabled={saving}
                >
                  Eliminar
                </AppButton>
              ) : null}
            </Box>
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
              helperText={e("decomiso_kilos_total")}
              fullWidth
              sx={{ mt: 1.5 }}
            />
          </Box>
        </DocumentalBloque>

        {muestraResultadoSeguimientoEdicion ? (
          <DocumentalBloque overline="Resultado y seguimiento">
            {tieneResultado ? (
              <Box sx={edicionGapBloqueAPrimerControlSx}>
                <Typography component="p" sx={{ ...actaNumeroPrincipalSx, m: 0 }}>
                  {dash(res)}
                </Typography>
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
                <Typography component="h3" sx={{ ...edicionActaSubtituloSx, fontSize: "0.6875rem", opacity: 0.9 }}>
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
    formGlobalError,
    readOnlyColumns,
    lockedNotif,
    lockedComp,
    mergedCatalogs,
    rubrosOptions,
    motivoComprobacionOptions,
    epicollectOtrosExpanded,
    toggleEpicollectOtros,
    onDraftChange,
    navigate,
    onClose,
    onQuitarActa,
    handleAskQuitarActa,
    applyMotivosNotificacion,
    applyInspectoresNombres,
    saving,
  ]);

  const dialogContentExtraSx = useMemo(
    () => ({
      maxHeight: "min(72vh, 720px)",
      overflowY: "auto" as const,
      gap: 0,
      pt: isEditing ? undefined : 2,
      pb: isEditing ? undefined : 2,
    }),
    [isEditing]
  );

  const dialogContentSx = useMemo(
    () => [formDialogContentStackSx, dialogContentExtraSx],
    [dialogContentExtraSx]
  );

  const dialogActions = useMemo(
    () => (
      <Box sx={docModalFooterRowSx}>
        <Typography variant="caption" component="div" sx={{ ...docModalFooterHintSx, flex: "1 1 200px" }}>
          {isEditing
            ? "Guardar aplica en canal actas."
            : "Impresión: usa el menú del navegador si el diálogo no aparece en la vista previa."}
        </Typography>
        <Box sx={docModalFooterButtonsSx}>
          {!isEditing ? (
            <>
              <AppButton dsVariant="ghost" dsSize="sm" onClick={handleClose} disabled={saving}>
                Cerrar
              </AppButton>
              {canEdit ? (
                <AppButton dsVariant="secondary" dsSize="sm" onClick={handleStartEditing} disabled={saving}>
                  Editar
                </AppButton>
              ) : null}
              <AppButton dsVariant="primary" dsSize="sm" onClick={handlePrint} disabled={saving}>
                Imprimir
              </AppButton>
            </>
          ) : (
            <>
              <AppButton dsVariant="ghost" dsSize="sm" onClick={handleBackToDetail} disabled={saving}>
                Volver al detalle
              </AppButton>
              <AppButton dsVariant="secondary" dsSize="sm" onClick={handlePrint} disabled={saving}>
                Imprimir
              </AppButton>
              <AppButton dsVariant="primary" dsSize="sm" onClick={handleSaveClick} loading={saving} disabled={saving}>
                Guardar
              </AppButton>
            </>
          )}
        </Box>
      </Box>
    ),
    [isEditing, saving, canEdit, handleClose, handleBackToDetail, handlePrint, handleStartEditing, handleSaveClick]
  );

  return (
    <>
      <AppDialog
        open={open}
        onClose={handleDialogClose}
        onCloseButtonClick={handleClose}
        title={isEditing ? documentalTitleEdit : documentalTitleRead}
        appearance="glass"
        maxWidth="md"
        fullWidth
        contentDividers
        contentSx={dialogContentSx}
        showCloseButton
        actions={dialogActions}
      >
        {!isEditing ? detalleVista : edicionVista}
      </AppDialog>
      <ConfirmDialog
        open={quitarConfirmTipo != null}
        onClose={handleDismissQuitar}
        onConfirm={() => void handleConfirmQuitarActa()}
        title={quitarConfirmTipo ? QUITAR_ACTA_TITLE[quitarConfirmTipo] : ""}
        destructive
        loading={quitarBusy}
        confirmLabel="Eliminar"
      >
        <Stack spacing={1.5}>
          <Typography variant="body2" sx={{ color: "text.primary", lineHeight: 1.5 }}>
            Se quitará el acta de esta actuación. Si tenés otros cambios sin guardar, guardalos antes o perderán
            consistencia con el servidor.
          </Typography>
          {quitarActaError ? (
            <Alert severity="error" sx={{ borderRadius: 1 }}>
              {quitarActaError}
            </Alert>
          ) : null}
        </Stack>
      </ConfirmDialog>
    </>
  );
}
