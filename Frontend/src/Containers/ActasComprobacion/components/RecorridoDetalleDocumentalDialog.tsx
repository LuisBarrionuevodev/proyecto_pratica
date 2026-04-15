import type { ReactNode } from "react";
import { Box, Chip, CircularProgress, Stack, Typography } from "@mui/material";

import type {
  IComprobacionRecorridoDetalle,
  IComprobacionRecorridoRow,
} from "../../../api/actuacionesComprobacionActasApi";
import { formDialogContentStackSx } from "../../../styles/formDialogStyles";
import {
  DOC_MODAL_BLOCK_STACK_SPACING,
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
import { AppButton, AppDialog } from "../../../ui";
import { COLORS } from "../../Actuaciones/styles/filtroStyles";

/** Etiquetas legibles para claves de expediente / oficio / reinspección (DTO detalle). */
const CAMPO_ETIQUETA: Record<string, string> = {
  descripcion: "Descripción",
  fecha_actuacion: "Fecha de actuación",
  orden_trabajo_numero: "Orden de trabajo",
  numero: "Número",
  motivo: "Motivo",
  id: "ID interno",
  anio: "Año",
  fecha: "Fecha",
  tipo: "Tipo",
  numero_oficio: "Número de oficio",
  fecha_oficio: "Fecha de oficio",
  iniciador_id: "Iniciador",
  estado_iniciador: "Estado del iniciador",
  fecha_origen: "Fecha de origen",
  resultado_cumplimiento_oficio: "Resultado cumplimiento oficio",
  estado_recorrido: "Estado del recorrido",
};

function etiquetaCampo(clave: string): string {
  return CAMPO_ETIQUETA[clave] ?? clave.replace(/_/g, " ");
}

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

function contribTitular(row: IComprobacionRecorridoRow): string {
  const rs = (row.razon_social ?? "").trim();
  if (rs) return rs;
  const a = (row.contrib_apellido ?? "").trim();
  const n = (row.contrib_nombre ?? "").trim();
  const t = [a, n].filter(Boolean).join(", ");
  return t || "—";
}

function domicilioLinea(row: IComprobacionRecorridoRow): string {
  const c = (row.calle ?? "").trim();
  const n = (row.numero ?? "").trim();
  const t = [c, n].filter(Boolean).join(" ");
  return t || "—";
}

function inspectoresLinea(row: IComprobacionRecorridoRow): string {
  const t = (row.inspectores_texto ?? "").trim();
  if (t) return t;
  const parts = [row.inspector1, row.inspector2, row.inspector3]
    .map((s) => (s ?? "").trim())
    .filter(Boolean);
  return parts.length ? parts.join(" · ") : "—";
}

function renderKvBloque(data: Record<string, unknown> | null | undefined): ReactNode {
  const vacio = data == null || Object.keys(data).length === 0;
  if (vacio) {
    return (
      <Typography variant="body2" sx={docModalEmptyStateSx}>
        Sin registro en esta etapa.
      </Typography>
    );
  }
  return (
    <Stack spacing={0}>
      {Object.entries(data).map(([k, v]) => (
        <DocumentalFila key={k} etiqueta={etiquetaCampo(k)} valor={textoValor(v)} />
      ))}
    </Stack>
  );
}

export type RecorridoDetalleDocumentalDialogProps = {
  open: boolean;
  onClose: () => void;
  actuacionId: number | null;
  /** Fila del listado (misma actuación); opcional pero recomendada para domicilio e inspectores. */
  listRow: IComprobacionRecorridoRow | null;
  detalle: IComprobacionRecorridoDetalle | null;
  loading: boolean;
};

/**
 * Modal de detalle consultivo del recorrido documental (comprobación → oficio → reinspección).
 * Combina `GET .../comprobacion/recorrido/:id` con la fila del listado para domicilio, titular e inspectores.
 */
export function RecorridoDetalleDocumentalDialog({
  open,
  onClose,
  actuacionId,
  listRow,
  detalle,
  loading,
}: RecorridoDetalleDocumentalDialogProps) {
  const handleClose = () => {
    onClose();
  };

  const actaNum =
    (listRow?.acta_comprobacion_num ?? "").trim() ||
    textoValor(detalle?.acta_comprobacion?.numero).replace(/^—$/, "");

  const tituloPrincipal =
    actaNum && actaNum !== "—" ? `Acta de comprobación Nº ${actaNum}` : "Acta de comprobación";

  const fechaCab =
    (listRow?.fecha_actuacion ?? "").trim() ||
    textoValor(detalle?.origen?.fecha_actuacion).replace(/^—$/, "");
  const domCab = listRow ? domicilioLinea(listRow) : "—";
  const titCab = listRow ? contribTitular(listRow) : "—";
  const subtituloCabecera = [fechaCab || "—", domCab, titCab].join(" · ");

  const titleNode =
    actuacionId != null ? (
      <Box sx={docModalHeaderStackSx}>
        <Chip label="Comprobación" size="small" sx={docModalChipSx} variant="outlined" />
        <Typography component="span" variant="h6" sx={docModalTitleSx}>
          {tituloPrincipal}
        </Typography>
        <Typography variant="body2" sx={docModalSubtitleSx}>
          {subtituloCabecera}
        </Typography>
        <Typography variant="caption" sx={docModalReferenceSx}>
          Actuación #{actuacionId}
        </Typography>
      </Box>
    ) : (
      "Recorrido"
    );

  const origen = detalle?.origen as Record<string, unknown> | undefined;
  const descripcionOrigen = textoValor(origen?.descripcion);

  return (
    <AppDialog
      open={open}
      onClose={() => handleClose()}
      onCloseButtonClick={handleClose}
      title={titleNode}
      fullWidth
      maxWidth="md"
      appearance="glass"
      contentDividers
      contentSx={{ ...formDialogContentStackSx, pt: 2, pb: 2 }}
      actions={
        <Box sx={docModalFooterRowSx}>
          <Typography variant="caption" component="div" sx={docModalFooterHintSx}>
            Vista solo lectura. Los datos reflejan el circuito cargado en el sistema al momento de la consulta.
          </Typography>
          <Box sx={docModalFooterButtonsSx}>
            <AppButton dsVariant="primary" dsSize="sm" onClick={handleClose}>
              Cerrar
            </AppButton>
          </Box>
        </Box>
      }
    >
      {loading && (
        <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
          <CircularProgress sx={{ color: COLORS.primary }} />
        </Box>
      )}
      {!loading && detalle && (
        <Stack
          component="section"
          spacing={DOC_MODAL_BLOCK_STACK_SPACING}
          aria-label="Detalle del recorrido por etapas"
        >
          <Typography variant="body2" sx={docModalIntroParagraphSx}>
            Circuito administrativo desde el acta de comprobación. Domicilio e inspectores provienen de la misma fila
            del listado cuando está disponible.
          </Typography>

          {listRow ? (
            <DocumentalBloque
              overline="Domicilio y titular"
              resumen="Ubicación, titular o razón social, documento y rubro según la actuación."
            >
              <DocumentalFila etiqueta="Calle y número" valor={domicilioLinea(listRow)} />
              <DocumentalFila etiqueta="Contribuyente / razón social" valor={contribTitular(listRow)} />
              <DocumentalFila etiqueta="Documento" valor={textoValor(listRow.doc_nro)} />
              <DocumentalFila etiqueta="Rubro" valor={textoValor(listRow.rubro_nombre)} />
            </DocumentalBloque>
          ) : (
            <DocumentalBloque overline="Domicilio y titular" resumen="Abrir el detalle desde el listado Recorrido para ver estos datos.">
              <Typography variant="body2" sx={docModalEmptyStateSx}>
                Sin fila de listado vinculada.
              </Typography>
            </DocumentalBloque>
          )}

          <DocumentalBloque
            overline="Inspección base"
            resumen="Visita y equipo según el registro de la actuación; el origen del circuito resume el contexto documental."
          >
            <DocumentalFila
              etiqueta="Fecha de la actuación (visita registrada)"
              valor={textoValor(listRow?.fecha_actuacion ?? origen?.fecha_actuacion)}
            />
            <DocumentalFila
              etiqueta="Acta de inspección (si consta)"
              valor={textoValor(listRow?.acta_inspeccion_num)}
            />
            <DocumentalFila etiqueta="Inspectores" valor={listRow ? inspectoresLinea(listRow) : "—"} />
            <DocumentalFila
              etiqueta="Orden de trabajo"
              valor={textoValor(listRow?.orden_trabajo_numero ?? origen?.orden_trabajo_numero)}
            />
            <DocumentalFila etiqueta="Tipo de actuación" valor={textoValor(listRow?.tipo_actuacion)} />
            <DocumentalFila etiqueta="Origen del circuito (descripción)" valor={descripcionOrigen} />
          </DocumentalBloque>

          <DocumentalBloque overline="Acta de comprobación" resumen="Número, motivo y fecha de la visita de comprobación.">
            <DocumentalFila etiqueta="Número" valor={textoValor(detalle.acta_comprobacion?.numero)} />
            <DocumentalFila etiqueta="Motivo" valor={textoValor(detalle.acta_comprobacion?.motivo)} />
            <DocumentalFila
              etiqueta="Fecha (actuación)"
              valor={textoValor(listRow?.fecha_actuacion ?? origen?.fecha_actuacion)}
            />
          </DocumentalBloque>

          <DocumentalBloque
            overline="Etapas administrativas"
            resumen="Expediente de envío, oficio, expediente de respuesta y programación de reinspección."
          >
            <Typography component="div" sx={{ ...docModalSubheadingInCardSx, mt: 0.5, mb: 0.5 }}>
              Expediente de envío (comprobación)
            </Typography>
            {renderKvBloque(detalle.expediente_comprobacion_envio as Record<string, unknown> | null)}
            <Typography component="div" sx={{ ...docModalSubheadingInCardSx, mt: 1.25, mb: 0.5 }}>
              Oficio
            </Typography>
            {renderKvBloque(detalle.oficio as Record<string, unknown> | null)}
            <Typography component="div" sx={{ ...docModalSubheadingInCardSx, mt: 1.25, mb: 0.5 }}>
              Expediente del oficio (respuesta)
            </Typography>
            {renderKvBloque(detalle.expediente_respuesta_oficio as Record<string, unknown> | null)}
            <Typography component="div" sx={{ ...docModalSubheadingInCardSx, mt: 1.25, mb: 0.5 }}>
              Reinspección por oficio
            </Typography>
            {renderKvBloque(detalle.reinspeccion_por_oficio as Record<string, unknown> | null)}
          </DocumentalBloque>

          <DocumentalBloque overline="Resultado final" resumen="Estado del recorrido y resultado consolidado del cumplimiento.">
            {renderKvBloque(detalle.resultado_final as Record<string, unknown>)}
          </DocumentalBloque>
        </Stack>
      )}
    </AppDialog>
  );
}
