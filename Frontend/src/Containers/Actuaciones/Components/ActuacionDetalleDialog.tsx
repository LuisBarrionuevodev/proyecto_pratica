import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import type { ReactNode } from "react";
import { Alert, Box, Chip, Collapse, Divider, IconButton, Link, Stack, Typography } from "@mui/material";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import { getDropdownOptions } from "../../CargarActuaciones/config/dropdownOptions";
import { formDialogContentStackSx } from "../../../styles/formDialogStyles";
import {
  DOC_MODAL_BLOCK_STACK_SPACING,
  DOC_MODAL_TEXT,
  docModalBlockOverlineSx,
  docModalBlockResumenSx,
  docModalChipSx,
  docModalEmptyStateSx,
  docModalFilaEtiquetaSx,
  docModalFilaValorSx,
  docModalFooterButtonsSx,
  docModalFooterHintSx,
  docModalFooterRowSx,
  docModalGlassCardShellSx,
  docModalHeaderStackSx,
  docModalIntroParagraphSx,
  docModalReferenceSx,
  docModalSubheadingInCardSx,
  docModalSubtitleSx,
  docModalTitleSx,
} from "../../../styles/documentalModalTokens";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { AppButton, AppDialog, AppSelect, AppTextField } from "../../../ui";
import { COLORS } from "../styles/filtroStyles";

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
  /** Reservados para una futura edición de domicilio; no usados en el modo edición actual. */
  numeroCallesOptions?: string[];
  numeroEditorLabel?: string;
  numeroAllowFreeSolo?: boolean;
  /** Si es false, no se muestra el paso a edición (p. ej. bandejas restringidas). */
  canEdit?: boolean;
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

function dash(v: unknown): string {
  if (v === null || v === undefined || v === "") return "—";
  return String(v);
}

function domicilioTexto(row: IActuacionListItem): string {
  const calle =
    row.calle_estado === "OK" && row.calle_normalizada ? row.calle_normalizada : row.calle ?? "";
  let numero = "";
  if (row.numero_tipo === "ESQUINA" && (row.numero_esquina || row.esquina_normalizada)) {
    numero = row.numero_esquina || row.esquina_normalizada || "";
  } else {
    numero = row.numero ?? "";
  }
  const line = [calle, numero].filter(Boolean).join(" ").trim();
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
    <Box sx={docModalGlassCardShellSx(COLORS.primary)}>
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

function inspectoresLinea(row: IActuacionListItem): string {
  const parts = [row.inspector1, row.inspector2, row.inspector3].filter((x) => x?.trim());
  return parts.length ? parts.join(", ") : "—";
}

function tieneReferenciaAdmin(row: IActuacionListItem): boolean {
  return !!(
    row.expediente_numero ||
    row.expediente_anio != null ||
    row.oficio_numero ||
    row.oficio_anio != null ||
    (row.oficio_causa != null && String(row.oficio_causa).trim() !== "")
  );
}

/** True si hay líneas concretas de expediente, oficio o causa para mostrar. */
function expedienteOficioTieneContenido(draft: IActuacionListItem): boolean {
  if (!tieneReferenciaAdmin(draft)) return false;
  const exp =
    (draft.expediente_numero != null && String(draft.expediente_numero).trim() !== "") ||
    draft.expediente_anio != null;
  const ofi =
    (draft.oficio_numero != null && String(draft.oficio_numero).trim() !== "") ||
    draft.oficio_anio != null;
  const causa = draft.oficio_causa != null && String(draft.oficio_causa).trim() !== "";
  return exp || ofi || causa;
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

function resultadoSeguimientoHayContenido(draft: IActuacionListItem): boolean {
  const res = draft.resultado_cumplimiento_oficio;
  const tieneResultado = res != null && String(res).trim() !== "";
  return tieneResultado || expedienteOficioTieneContenido(draft) || tieneRestriccionesEdicion(draft);
}

/** Referencias de expediente, oficio y causa; una línea por dato disponible. */
function ExpedienteOficioLectura({ draft }: { draft: IActuacionListItem }) {
  if (!expedienteOficioTieneContenido(draft)) {
    return null;
  }

  const lineas: ReactNode[] = [];
  if (
    (draft.expediente_numero != null && String(draft.expediente_numero).trim() !== "") ||
    draft.expediente_anio != null
  ) {
    lineas.push(
      <Typography key="exp" sx={{ color: DOC_MODAL_TEXT, fontSize: "0.875rem", lineHeight: 1.5 }}>
        <Box component="span" sx={{ fontWeight: 700 }}>
          Expediente:{" "}
        </Box>
        {dash(draft.expediente_numero)} / {dash(draft.expediente_anio)}
      </Typography>
    );
  }
  if (
    (draft.oficio_numero != null && String(draft.oficio_numero).trim() !== "") ||
    draft.oficio_anio != null
  ) {
    lineas.push(
      <Typography key="ofi" sx={{ color: DOC_MODAL_TEXT, fontSize: "0.875rem", lineHeight: 1.5 }}>
        <Box component="span" sx={{ fontWeight: 700 }}>
          Oficio:{" "}
        </Box>
        {dash(draft.oficio_numero)} / {dash(draft.oficio_anio)}
      </Typography>
    );
  }
  if (draft.oficio_causa != null && String(draft.oficio_causa).trim() !== "") {
    lineas.push(
      <Typography key="causa" sx={{ color: DOC_MODAL_TEXT, fontSize: "0.875rem", lineHeight: 1.5 }}>
        <Box component="span" sx={{ fontWeight: 700 }}>
          Causa:{" "}
        </Box>
        {dash(draft.oficio_causa)}
      </Typography>
    );
  }

  return (
    <Stack component="div" spacing={1}>
      {lineas}
    </Stack>
  );
}

/**
 * Card "Resultado y seguimiento": solo subsecciones con dato útil; sin texto vacío ni pedagógico.
 */
function ResultadoSeguimientoLectura({ draft }: { draft: IActuacionListItem }) {
  const res = draft.resultado_cumplimiento_oficio;
  const tieneResultado = res != null && String(res).trim() !== "";
  const showExp = expedienteOficioTieneContenido(draft);
  const showEdicion = tieneRestriccionesEdicion(draft);

  if (!tieneResultado && !showExp && !showEdicion) {
    return null;
  }

  const bloques: ReactNode[] = [];
  if (tieneResultado) {
    bloques.push(
      <Box key="res">
        <Typography component="h3" sx={docModalSubheadingInCardSx}>
          Resultado
        </Typography>
        <Typography component="p" sx={{ ...actaNumeroPrincipalSx, mt: 0.75 }}>
          {dash(res)}
        </Typography>
      </Box>
    );
  }
  if (showExp) {
    bloques.push(
      <Box key="exp">
        <Typography component="h3" sx={docModalSubheadingInCardSx}>
          Expediente y oficio
        </Typography>
        <Box sx={{ mt: 0.75 }}>
          <ExpedienteOficioLectura draft={draft} />
        </Box>
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
  if (!draft.has_epicollect_detalle) return null;

  const n = draft.epicollect_non_media_field_count ?? 0;
  const sectores = draft.epicollect_sectores_condiciones ?? [];
  const otros = draft.epicollect_otros_preview ?? draft.epicollect_preview ?? [];
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

  return (
    <Box sx={embedded ? { mb: 2 } : blockShellSx}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap", mb: 1 }}>
        <Typography
          variant="subtitle2"
          sx={{
            ...(embedded
              ? { color: DOC_MODAL_TEXT, fontWeight: 700, mt: 0, mb: 0, flex: "1 1 auto" }
              : { ...sectionTitleSx, mt: 0, mb: 0, flex: "1 1 auto" }),
          }}
        >
          Datos importados de EpiCollect
        </Typography>
        <Chip
          label="Formulario"
          size="small"
          sx={{
            borderColor: "rgba(129, 199, 132, 0.55)",
            color: "rgba(200, 230, 201, 0.95)",
            bgcolor: "rgba(76, 175, 80, 0.12)",
          }}
          variant="outlined"
        />
      </Box>
      <Typography variant="body2" sx={{ color: DOC_MODAL_TEXT, fontWeight: 400, mb: 0.75, lineHeight: 1.5 }}>
        Hay un snapshot local de <strong>{n}</strong> respuesta{n === 1 ? "" : "s"} del formulario (sin fotos). Solo
        lectura; no se edita desde aquí.
      </Typography>
      {uuid ? (
        <Typography
          variant="caption"
          sx={{
            color: DOC_MODAL_TEXT,
            fontWeight: 400,
            display: "block",
            mb: 1,
            fontFamily: "monospace",
            fontSize: "0.75rem",
          }}
        >
          ec5_uuid: {uuid}
        </Typography>
      ) : null}

      {sectores.length > 0 ? (
        <Box sx={{ mb: otros.length > 0 ? 1.25 : 0 }}>
          <Typography
            variant="caption"
            sx={{
              color: DOC_MODAL_TEXT,
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.04em",
              display: "block",
              mb: 0.75,
            }}
          >
            Sectores / condiciones
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
            <Typography
              variant="caption"
              sx={{
                color: DOC_MODAL_TEXT,
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.04em",
                flex: "1 1 auto",
              }}
            >
              Otros campos del formulario
            </Typography>
            <IconButton
              size="small"
              onClick={onToggleOtros}
              aria-expanded={otrosExpanded}
              aria-label={otrosExpanded ? "Ocultar otros campos" : "Mostrar otros campos"}
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
              {otros.map((p) => (
                <Box component="li" key={p.field_id} sx={{ mb: 0.75 }}>
                  <Typography variant="body2" component="span" sx={{ color: DOC_MODAL_TEXT, fontSize: "inherit", fontWeight: 600 }}>
                    {p.field_id}
                  </Typography>
                  {": "}
                  <Typography variant="body2" component="span" sx={{ color: DOC_MODAL_TEXT, fontSize: "inherit", fontWeight: 500 }}>
                    {p.value_preview}
                  </Typography>
                </Box>
              ))}
            </Box>
          </Collapse>
        </>
      ) : sectores.length === 0 ? (
        <Typography variant="caption" sx={{ ...docModalEmptyStateSx, display: "block", pt: 0.5, fontSize: "0.8125rem" }}>
          No hay datos de formulario en el snapshot (o payload vacío).
        </Typography>
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

function BloqueIniciadorVacío() {
  return (
    <Box sx={blockShellSx}>
      <Typography variant="subtitle2" sx={{ ...sectionTitleSx, mt: 0 }}>
        3. Iniciador de la ruta
      </Typography>
      <Typography variant="body2" sx={{ color: DOC_MODAL_TEXT, fontWeight: 400, lineHeight: 1.5 }}>
        Los datos del iniciador de ruta no están disponibles desde este listado. Cuando el API los
        incluya, se mostrarán aquí sin mezclarlos con la actuación ni el local.
      </Typography>
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
  onClose,
  onDraftChange,
  onSave,
}: ActuacionDetalleDialogProps) {
  const navigate = useNavigate();
  const [isEditing, setIsEditing] = useState(false);
  const [epicollectOtrosExpanded, setEpicollectOtrosExpanded] = useState(false);

  useEffect(() => {
    if (open) {
      setIsEditing(false);
      setEpicollectOtrosExpanded(false);
    }
  }, [open, draft.id]);

  const e = (key: string) => fieldErrors[key] ?? "";
  const ro = (key: string) => readOnlyColumns.includes(key);
  const lockedNotif = draft.notificacion_editable === false;
  const lockedComp = draft.comprobacion_editable === false;

  const mergedCatalogs = {
    inspectores: catalogs.inspectores,
    motivos: catalogs.motivos,
    rubros: catalogs.rubros,
    tipos: catalogs.tipos,
    contraproducencias: catalogs.contraproducencias,
    motivosComprobacion: catalogs.motivosComprobacion,
  };

  const handleClose = () => {
    if (saving) return;
    onClose();
  };

  const handleBackToDetail = () => {
    if (saving) return;
    setIsEditing(false);
  };

  const handlePrint = () => {
    if (saving) return;
    window.print();
  };

  const documentalTitleRead = (
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
  );

  const tieneSnapEpicollect = Boolean(draft.has_epicollect_detalle);
  const gruposEvid = draft.epicollect_evidencias_grupos ?? [];
  const totalEvid = draft.epicollect_evidencias_total ?? 0;
  const tieneEvidenciasEpicollect = totalEvid > 0 && gruposEvid.length > 0;

  const detalleVista = (
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

      {tieneSnapEpicollect || tieneEvidenciasEpicollect ? (
        <DocumentalBloque overline="Formulario de campo y evidencias">
          {tieneSnapEpicollect ? (
            <BloqueEpicollectDetalleLectura
              draft={draft}
              otrosExpanded={epicollectOtrosExpanded}
              onToggleOtros={() => setEpicollectOtrosExpanded((v) => !v)}
              embedded
            />
          ) : null}
          {tieneSnapEpicollect && tieneEvidenciasEpicollect ? (
            <Divider sx={{ borderColor: GLASS_COLORS.borderLight, my: 1.5 }} />
          ) : null}
          {tieneEvidenciasEpicollect ? <BloqueEvidenciasEpicollect draft={draft} embedded /> : null}
        </DocumentalBloque>
      ) : null}
    </Stack>
  );

  const roFieldSx = { "& .MuiInputBase-input": { color: "rgba(255,255,255,0.72)" } };

  const edicionVista = (
    <>
      {(lockedNotif || lockedComp) && (
        <Alert severity="info" variant="outlined" sx={{ mb: 1 }}>
          {lockedNotif && "Algunos campos de notificación están bloqueados (expediente). "}
          {lockedComp && "Algunos campos de comprobación están bloqueados (expediente). "}
        </Alert>
      )}

      <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.55)", fontFamily: '"Tactic Sans", sans-serif' }}>
        ID actuación: {draft.id}
      </Typography>

      <Box sx={blockShellSx}>
        <Typography variant="subtitle2" sx={{ ...sectionTitleSx, mt: 0 }}>
          1. Datos de la actuación actual
        </Typography>
        <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.45)", display: "block", mb: 1 }}>
          Solo lectura: OT, fecha, tipo, contraproducencia e inspectores no se editan desde este canal.
        </Typography>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)" },
            gap: 2,
            width: "100%",
          }}
        >
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
            label="Fecha"
            type="date"
            value={draft.fecha_actuacion ?? ""}
            disabled
            sx={roFieldSx}
            InputLabelProps={{ shrink: true }}
            fullWidth
          />
          <AppTextField appearance="glass" label="Tipo" value={draft.tipo_actuacion ?? ""} disabled sx={roFieldSx} fullWidth />
          <AppTextField
            appearance="glass"
            label="Contraproducencia"
            value={draft.contraproducencia ?? ""}
            disabled
            sx={roFieldSx}
            fullWidth
          />
          {draft.resultado_cumplimiento_oficio != null &&
            String(draft.resultado_cumplimiento_oficio).trim() !== "" && (
              <AppTextField
                appearance="glass"
                label="Resultado (oficio / reinspección)"
                value={draft.resultado_cumplimiento_oficio ?? ""}
                disabled
                sx={{ ...roFieldSx, gridColumn: { xs: "1 / -1", sm: "1 / -1" } }}
                fullWidth
              />
            )}
          <AppTextField
            appearance="glass"
            label="Inspectores"
            value={draft.inspectores_texto?.trim() || inspectoresLinea(draft)}
            disabled
            sx={{ ...roFieldSx, gridColumn: { xs: "1 / -1", sm: "1 / -1" } }}
            fullWidth
          />
          <AppTextField
            appearance="glass"
            label="EpiCollect (ID) — solo lectura"
            value={draft.ec5_uuid ?? ""}
            disabled
            sx={{ ...roFieldSx, gridColumn: { xs: "1 / -1", sm: "1 / -1" } }}
            fullWidth
            helperText="No editable desde este canal."
          />
        </Box>

        <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.5)", display: "block", mt: 2, mb: 1 }}>
          Actas del día (editables)
        </Typography>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)" },
            gap: 2,
            width: "100%",
          }}
        >
          <AppTextField
            appearance="glass"
            label="Acta inspección"
            value={draft.acta_inspeccion_num ?? ""}
            onChange={(ev) => onDraftChange({ acta_inspeccion_num: ev.target.value })}
            error={!!e("acta_inspeccion_num")}
            helperText={e("acta_inspeccion_num")}
            fullWidth
          />
        </Box>

        <Typography variant="subtitle2" sx={{ ...sectionTitleSx, mt: 2, mb: 1.5 }}>
          Notificación
        </Typography>
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)" }, gap: 2, width: "100%" }}>
          <AppTextField
            appearance="glass"
            label="Acta notificación"
            value={draft.acta_notificacion_num ?? ""}
            onChange={(ev) => onDraftChange({ acta_notificacion_num: ev.target.value })}
            disabled={lockedNotif}
            error={!!e("acta_notificacion_num")}
            helperText={lockedNotif ? "Notificación con expediente: no editable aquí." : e("acta_notificacion_num")}
            fullWidth
          />
          <AppSelect
            appearance="glass"
            label="Motivo notif. 1"
            value={draft.notificacion_motivo_1 ?? ""}
            onChange={(ev) => onDraftChange({ notificacion_motivo_1: ev.target.value as string })}
            options={opts(["", ...catalogs.motivos])}
            disabled={lockedNotif}
            error={!!e("notificacion_motivo_1")}
            helperText={lockedNotif ? "Notificación con expediente: no editable aquí." : e("notificacion_motivo_1")}
            fullWidth
          />
          <AppSelect
            appearance="glass"
            label="Motivo notif. 2"
            value={draft.notificacion_motivo_2 ?? ""}
            onChange={(ev) => onDraftChange({ notificacion_motivo_2: ev.target.value as string })}
            options={opts(["", ...catalogs.motivos])}
            disabled={lockedNotif}
            error={!!e("notificacion_motivo_2")}
            helperText={lockedNotif ? "Notificación con expediente: no editable aquí." : e("notificacion_motivo_2")}
            fullWidth
          />
          <AppSelect
            appearance="glass"
            label="Motivo notif. 3"
            value={draft.notificacion_motivo_3 ?? ""}
            onChange={(ev) => onDraftChange({ notificacion_motivo_3: ev.target.value as string })}
            options={opts(["", ...catalogs.motivos])}
            disabled={lockedNotif}
            error={!!e("notificacion_motivo_3")}
            helperText={lockedNotif ? "Notificación con expediente: no editable aquí." : e("notificacion_motivo_3")}
            fullWidth
          />
        </Box>

        <Typography variant="subtitle2" sx={{ ...sectionTitleSx, mt: 2, mb: 1.5 }}>
          Comprobación
        </Typography>
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)" }, gap: 2, width: "100%" }}>
          <AppTextField
            appearance="glass"
            label="Acta comprobación"
            value={draft.acta_comprobacion_num ?? ""}
            onChange={(ev) => onDraftChange({ acta_comprobacion_num: ev.target.value })}
            disabled={lockedComp}
            error={!!e("acta_comprobacion_num")}
            helperText={lockedComp ? "Comprobación con expediente: no editable aquí." : e("acta_comprobacion_num")}
            fullWidth
          />
          <AppSelect
            appearance="glass"
            label="Motivo comprobación"
            value={draft.comprobacion_motivo ?? ""}
            onChange={(ev) => onDraftChange({ comprobacion_motivo: ev.target.value as string })}
            options={opts(getDropdownOptions("Motivo comprobación", mergedCatalogs))}
            disabled={lockedComp}
            error={!!e("comprobacion_motivo")}
            helperText={lockedComp ? "Comprobación con expediente: no editable aquí." : e("comprobacion_motivo")}
            fullWidth
          />
        </Box>

        <Typography variant="subtitle2" sx={{ ...sectionTitleSx, mt: 2, mb: 1.5 }}>
          Clausura / decomiso
        </Typography>
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)" }, gap: 2, width: "100%" }}>
          <AppTextField
            appearance="glass"
            label="Acta clausura"
            value={draft.acta_clausura_num ?? ""}
            onChange={(ev) => onDraftChange({ acta_clausura_num: ev.target.value })}
            error={!!e("acta_clausura_num")}
            helperText={e("acta_clausura_num")}
            fullWidth
          />
          <AppTextField
            appearance="glass"
            label="Acta decomiso"
            value={draft.acta_decomiso_num ?? ""}
            onChange={(ev) => onDraftChange({ acta_decomiso_num: ev.target.value })}
            error={!!e("acta_decomiso_num")}
            helperText={e("acta_decomiso_num")}
            fullWidth
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
            helperText={e("decomiso_kilos_total")}
            fullWidth
          />
        </Box>

        {tieneReferenciaAdmin(draft) && (
          <Box sx={{ mt: 2, pt: 1.5, borderTop: "1px solid rgba(255,255,255,0.08)" }}>
            <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.45)", display: "block", mb: 0.75 }}>
              Referencia administrativa (solo lectura; no se envía por este canal de guardado)
            </Typography>
            <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.62)" }}>
              Expediente: {dash(draft.expediente_numero)} / {dash(draft.expediente_anio)} · Oficio:{" "}
              {dash(draft.oficio_numero)} / {dash(draft.oficio_anio)}
              {draft.oficio_causa != null && String(draft.oficio_causa).trim() !== ""
                ? ` · Causa: ${dash(draft.oficio_causa)}`
                : ""}
            </Typography>
          </Box>
        )}
      </Box>

      <Box sx={blockShellSx}>
        <Typography variant="subtitle2" sx={{ ...sectionTitleSx, mt: 0 }}>
          2. Datos del local
        </Typography>
        <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.45)", display: "block", mb: 1 }}>
          Domicilio en solo lectura. Podés corregir nombre del local, rubro y contribuyente.
        </Typography>
        <AppTextField
          appearance="glass"
          label="Domicilio"
          value={domicilioTexto(draft)}
          disabled
          sx={roFieldSx}
          fullWidth
        />
        <AppTextField
          appearance="glass"
          label="Nombre del local"
          value={draft.nombre_local ?? ""}
          onChange={(ev) => onDraftChange({ nombre_local: ev.target.value || null })}
          error={!!e("nombre_local")}
          helperText={e("nombre_local")}
          sx={{ mt: 2 }}
          fullWidth
        />
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)" },
            gap: 2,
            width: "100%",
            mt: 2,
          }}
        >
          <AppSelect
            appearance="glass"
            label="Rubro"
            value={draft.rubro_nombre ?? ""}
            onChange={(ev) => onDraftChange({ rubro_nombre: ev.target.value as string })}
            options={opts(["", ...catalogs.rubros])}
            disabled={ro("rubro_nombre")}
            error={!!e("rubro_nombre")}
            helperText={e("rubro_nombre")}
            fullWidth
          />
          <AppTextField
            appearance="glass"
            label="Doc. Nro"
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
      </Box>

      <BloqueEpicollectDetalleLectura
        draft={draft}
        otrosExpanded={epicollectOtrosExpanded}
        onToggleOtros={() => setEpicollectOtrosExpanded((v) => !v)}
      />

      <BloqueEvidenciasEpicollect draft={draft} />

      <BloqueIniciadorVacío />
    </>
  );

  return (
    <AppDialog
      open={open}
      onClose={(_ev, _reason) => handleClose()}
      onCloseButtonClick={handleClose}
      title={isEditing ? "Editar actuación" : documentalTitleRead}
      appearance="glass"
      maxWidth="md"
      fullWidth
      contentDividers
      contentSx={[
        formDialogContentStackSx,
        {
          maxHeight: "min(72vh, 720px)",
          overflowY: "auto",
          gap: isEditing ? 2.75 : 0,
          pt: isEditing ? undefined : 2,
          pb: isEditing ? undefined : 2,
        },
      ]}
      showCloseButton
      actions={
        <Box sx={docModalFooterRowSx}>
          <Typography variant="caption" component="div" sx={{ ...docModalFooterHintSx, flex: "1 1 200px" }}>
            {isEditing
              ? "Los cambios se guardan con el botón Guardar (canal actas)."
              : "Impresión: usa el menú del navegador si el diálogo no aparece en la vista previa."}
          </Typography>
          <Box sx={docModalFooterButtonsSx}>
            {!isEditing ? (
              <>
                <AppButton dsVariant="ghost" dsSize="sm" onClick={handleClose} disabled={saving}>
                  Cerrar
                </AppButton>
                {canEdit ? (
                  <AppButton dsVariant="secondary" dsSize="sm" onClick={() => setIsEditing(true)} disabled={saving}>
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
                <AppButton dsVariant="primary" dsSize="sm" onClick={() => void onSave()} loading={saving} disabled={saving}>
                  Guardar
                </AppButton>
              </>
            )}
          </Box>
        </Box>
      }
    >
      {!isEditing ? detalleVista : edicionVista}
    </AppDialog>
  );
}
