import type { ReactNode } from "react";
import { Box, Chip, CircularProgress, Stack, Typography } from "@mui/material";

import type {
  IComprobacionRecorridoDetalle,
  IComprobacionRecorridoOficio,
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
  docModalSubheadingInCardSx,
  docModalSubtitleSx,
  docModalTitleSx,
} from "../../../styles/documentalModalTokens";
import { AppButton, AppDialog } from "../../../ui";
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

function actaComprobacionCabecera(listRow: IComprobacionRecorridoRow | null, detalle: IComprobacionRecorridoDetalle): string {
  const n =
    (listRow?.acta_comprobacion_num ?? "").trim() ||
    String(detalle.acta_comprobacion?.numero ?? "").trim();
  return n ? `Acta de comprobación Nº ${n}` : "Acta de comprobación";
}

function expedienteFilasEstructuradas(
  exp: Record<string, unknown> | null | undefined,
  sinRegistro: string,
  opts?: { numeroEtiqueta?: string }
): ReactNode {
  if (!exp || Object.keys(exp).length === 0) {
    return (
      <Typography variant="body2" sx={docModalEmptyStateSx}>
        {sinRegistro}
      </Typography>
    );
  }
  const numLbl = opts?.numeroEtiqueta ?? "Número";
  return (
    <>
      <DocumentalFila etiqueta="Fecha" valor={textoValor(exp.fecha)} />
      <DocumentalFila etiqueta="Año" valor={textoValor(exp.anio)} />
      <DocumentalFila etiqueta={numLbl} valor={textoValor(exp.numero)} />
      <DocumentalFila etiqueta="Tipo" valor={textoValor(exp.tipo)} />
    </>
  );
}

function expedienteRespuestaYOficioBloque(
  exp: Record<string, unknown> | null | undefined,
  ofi: IComprobacionRecorridoOficio | null
): ReactNode {
  const expVacio = !exp || Object.keys(exp).length === 0;
  const ofiVacio =
    !ofi ||
    (!ofi.numero_oficio &&
      ofi.anio == null &&
      !ofi.fecha_oficio &&
      !ofi.causa &&
      ofi.juzgado_id == null &&
      !ofi.juzgado_nombre);
  if (expVacio && ofiVacio) {
    return (
      <Typography variant="body2" sx={docModalEmptyStateSx}>
        Sin expediente de respuesta ni oficio registrados.
      </Typography>
    );
  }
  return (
    <>
      {!expVacio
        ? expedienteFilasEstructuradas(exp, "Sin expediente de respuesta registrado.", {
            numeroEtiqueta: "Número de expediente",
          })
        : null}
      {ofiVacio ? null : (
        <>
          {expVacio ? null : <Box sx={{ height: 8 }} />}
          {oficioAdministrativoFilas(ofi)}
        </>
      )}
    </>
  );
}

function oficioAdministrativoFilas(ofi: IComprobacionRecorridoOficio | null): ReactNode {
  if (!ofi) {
    return (
      <Typography variant="body2" sx={docModalEmptyStateSx}>
        Sin oficio registrado.
      </Typography>
    );
  }
  const vacio =
    !ofi.numero_oficio &&
    ofi.anio == null &&
    !ofi.fecha_oficio &&
    !ofi.causa &&
    ofi.juzgado_id == null &&
    !ofi.juzgado_nombre;
  if (vacio) {
    return (
      <Typography variant="body2" sx={docModalEmptyStateSx}>
        Sin oficio registrado.
      </Typography>
    );
  }
  const juz =
    (ofi.juzgado_nombre ?? "").trim() ||
    (ofi.juzgado_id != null ? `Id ${ofi.juzgado_id}` : "");
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

function reinspeccionPorOficioFilas(data: Record<string, unknown> | null | undefined): ReactNode {
  if (!data || Object.keys(data).length === 0) {
    return (
      <Typography variant="body2" sx={docModalEmptyStateSx}>
        Sin registro de reinspección por oficio.
      </Typography>
    );
  }
  const idIni = data.iniciador_id;
  const iniciadorTxt =
    idIni != null && idIni !== "" ? `#${String(idIni)}` : "—";
  return (
    <>
      <DocumentalFila etiqueta="Estado del iniciador" valor={textoValor(data.estado_iniciador)} />
      <DocumentalFila etiqueta="Fecha de origen" valor={textoValor(data.fecha_origen)} />
      <DocumentalFila etiqueta="Iniciador" valor={iniciadorTxt} />
    </>
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

  const titleNode =
    actuacionId != null && detalle ? (
      <Box sx={docModalHeaderStackSx}>
        <Chip label="Comprobación" size="small" sx={docModalChipSx} variant="outlined" />
        <Typography component="span" variant="h6" sx={docModalTitleSx}>
          Recorrido de la comprobación
        </Typography>
        <Typography variant="body2" sx={docModalSubtitleSx}>
          {actaComprobacionCabecera(listRow, detalle)}
        </Typography>
      </Box>
    ) : actuacionId != null ? (
      <Box sx={docModalHeaderStackSx}>
        <Chip label="Comprobación" size="small" sx={docModalChipSx} variant="outlined" />
        <Typography component="span" variant="h6" sx={docModalTitleSx}>
          Recorrido de la comprobación
        </Typography>
      </Box>
    ) : (
      "Recorrido"
    );

  const o = detalle?.origen;

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
          {listRow ? (
            <DocumentalBloque
              overline="Referencia"
              resumen="Contribuyente, documentación y domicilio según la fila del listado. La orden de trabajo figura en Inspección base."
            >
              <DocumentalFila etiqueta="Contribuyente / razón social" valor={contribTitular(listRow)} />
              <DocumentalFila etiqueta="Documento" valor={textoValor(listRow.doc_nro)} />
              <DocumentalFila etiqueta="Rubro" valor={textoValor(listRow.rubro_nombre)} />
              <DocumentalFila etiqueta="Domicilio" valor={domicilioLinea(listRow)} />
            </DocumentalBloque>
          ) : (
            <DocumentalBloque
              overline="Referencia"
              resumen="Abrir el detalle desde el listado Recorrido para ver domicilio y titular."
            >
              <Typography variant="body2" sx={docModalEmptyStateSx}>
                Sin fila de listado vinculada.
              </Typography>
            </DocumentalBloque>
          )}

          <DocumentalBloque
            overline="Inspección base"
            resumen="Visita, orden de trabajo, actas e iniciador con el que se originó la actuación (primera comprobación)."
          >
            <DocumentalFila
              etiqueta="Fecha de la actuación"
              valor={textoValor(listRow?.fecha_actuacion ?? o?.fecha_actuacion)}
            />
            <DocumentalFila
              etiqueta="Orden de trabajo"
              valor={textoValor(o?.orden_trabajo_numero ?? listRow?.orden_trabajo_numero)}
            />
            <DocumentalFila etiqueta="Acta de inspección (si consta)" valor={textoValor(listRow?.acta_inspeccion_num)} />
            <DocumentalFila etiqueta="Inspectores" valor={listRow ? inspectoresLinea(listRow) : "—"} />
            <DocumentalFila etiqueta="Tipo de actuación" valor={textoValor(listRow?.tipo_actuacion)} />
            {o?.iniciador ? (
              <>
                <DocumentalFila
                  etiqueta="Tipo de iniciador (origen de la actuación)"
                  valor={textoValor(o.iniciador.tipo_iniciador)}
                />
                <DocumentalFila etiqueta="Estado del iniciador (origen)" valor={textoValor(o.iniciador.estado_iniciador)} />
                <DocumentalFila etiqueta="Fecha de origen (iniciador)" valor={textoValor(o.iniciador.fecha_origen)} />
              </>
            ) : (
              <DocumentalFila etiqueta="Iniciador de origen" valor="—" />
            )}
          </DocumentalBloque>

          <DocumentalBloque overline="Acta de comprobación" resumen="Número y motivo del acta en el circuito.">
            <DocumentalFila etiqueta="Número" valor={textoValor(detalle.acta_comprobacion?.numero)} />
            <DocumentalFila etiqueta="Motivo" valor={textoValor(detalle.acta_comprobacion?.motivo)} />
          </DocumentalBloque>

          <DocumentalBloque
            overline="Etapas administrativas"
            resumen="Expediente de envío, oficio, respuesta y programación de reinspección."
          >
            <Typography component="div" sx={{ ...docModalSubheadingInCardSx, mt: 0.5, mb: 0.5 }}>
              Expediente de envío de comprobación
            </Typography>
            {expedienteFilasEstructuradas(
              detalle.expediente_comprobacion_envio as Record<string, unknown> | null,
              "Sin expediente de envío registrado."
            )}
            <Typography component="div" sx={{ ...docModalSubheadingInCardSx, mt: 1.25, mb: 0.5 }}>
              Expediente del oficio (respuesta)
            </Typography>
            {expedienteRespuestaYOficioBloque(
              detalle.expediente_respuesta_oficio as Record<string, unknown> | null,
              detalle.oficio
            )}
            <Typography component="div" sx={{ ...docModalSubheadingInCardSx, mt: 1.25, mb: 0.5 }}>
              Reinspección por oficio
            </Typography>
            {reinspeccionPorOficioFilas(detalle.reinspeccion_por_oficio as Record<string, unknown> | null)}
          </DocumentalBloque>

          <DocumentalBloque
            overline="Resultado final"
            resumen="Estado del recorrido, cumplimiento del oficio y tipo de actuación (ratificación, verificar e informar, etc.)."
          >
            <DocumentalFila
              etiqueta="Estado del recorrido"
              valor={textoValor(detalle.resultado_final?.estado_recorrido)}
            />
            <DocumentalFila
              etiqueta="Resultado cumplimiento oficio"
              valor={textoValor(detalle.resultado_final?.resultado_cumplimiento_oficio)}
            />
            <DocumentalFila
              etiqueta="Tipo de actuación"
              valor={textoValor(detalle.resultado_final?.tipo_actuacion)}
            />
          </DocumentalBloque>
        </Stack>
      )}
    </AppDialog>
  );
}
