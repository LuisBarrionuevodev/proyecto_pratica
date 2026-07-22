import { memo, useCallback, useEffect, useMemo, useState } from "react";
import AddIcon from "@mui/icons-material/Add";
import { Alert, Box, Chip, CircularProgress, Stack, Typography } from "@mui/material";

import type { IComprobacionRecorridoResultadoFinal } from "../../../api/actuacionesComprobacionActasApi";
import type {
  IComprobacionDocumentalResponse,
  IJuzgadoCatalogItem,
  OficioComprobacionItem,
} from "../../../api/actuacionesPendientesApi";
import { documentalGlassAlertSx, docModalEmptyStateSx } from "../../../styles/documentalModalTokens";
import { AppButton } from "../../../ui";
import { humanizarEstadoIniciador } from "../utils/documentalLabelFormat";
import {
  documentalDesdeOficioItem,
  mergeOficiosConLegacyDocumental,
  oficioComprobacionEtiquetaCompacta,
  oficioComprobacionSubtituloIniciador,
  oficioComprobacionTieneBloqueCompleto,
  oficioMuestraEjecucionReinspeccion,
  oficioOperativoChips,
  type EjecucionReinspeccionPorOficioCtx,
} from "../utils/comprobacionOficiosUtils";
import {
  ComprobacionOficioAltaFields,
  OperativoOficioYRespuestaEditable,
  type ComprobacionOficioAltaPayload,
} from "./ComprobacionOficioOperativoDialog";
import { DocumentalBloque, DocumentalFila, parNumAnio, textoValor } from "./comprobacionOperativoBlocks";
import { OficioComprobacionReinspeccionEnCard } from "./OficioComprobacionReinspeccionEnCard";

const agregarOficioButtonSx = { fontWeight: 700 } as const;

function AgregarOficioButton({
  onClick,
  disabled,
  tieneOficios,
}: {
  onClick: () => void;
  disabled?: boolean;
  tieneOficios?: boolean;
}) {
  return (
    <AppButton
      dsVariant="primary"
      dsSize="sm"
      startIcon={<AddIcon fontSize="small" />}
      onClick={onClick}
      disabled={disabled}
      sx={agregarOficioButtonSx}
    >
      {tieneOficios ? "Agregar otro oficio" : "Agregar oficio"}
    </AppButton>
  );
}

function chipColorForIniciador(estado: string | null | undefined): "default" | "success" | "warning" | "info" {
  const u = (estado ?? "").toUpperCase();
  if (u === "CUMPLIDO") return "success";
  if (u === "PENDIENTE") return "warning";
  if (u === "EN_EJECUCION" || u === "EN CURSO") return "info";
  return "default";
}

function OficioComprobacionDetalleLectura({ item }: { item: OficioComprobacionItem }) {
  const expNum = parNumAnio(item.expediente_numero ?? null, item.expediente_anio ?? null);
  const expFecha = textoValor(item.fecha_expediente_respuesta);
  return (
    <Box sx={{ display: "grid", gap: 1.25, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" }, width: "100%", mt: 1 }}>
      {expNum !== "—" ? <DocumentalFila etiqueta="Expediente de respuesta" valor={expNum} /> : null}
      {expFecha !== "—" ? <DocumentalFila etiqueta="Fecha expediente" valor={expFecha} /> : null}
      <DocumentalFila etiqueta="N.º y año de oficio" valor={parNumAnio(item.numero_oficio ?? null, item.anio ?? null)} />
      <DocumentalFila etiqueta="Fecha de oficio" valor={textoValor(item.fecha_oficio)} />
      <DocumentalFila etiqueta="Causa" valor={textoValor(item.causa)} />
      <DocumentalFila etiqueta="Juzgado" valor={textoValor(item.tribunal)} />
      {!oficioComprobacionTieneBloqueCompleto(item) ? (
        <Box sx={{ gridColumn: "1 / -1" }}>
          <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.55)" }}>
            Expediente de respuesta no disponible en el listado.
          </Typography>
        </Box>
      ) : null}
    </Box>
  );
}

const OficioComprobacionCard = memo(function OficioComprobacionCard({
  item,
  selected,
  onSelect,
  actuacionId,
  documental,
  open,
  juzgados,
  onDocumentalUpdated,
  ejecucionReinspeccion,
  resultadoCircuito,
  ejecucionCtx,
}: {
  item: OficioComprobacionItem;
  selected: boolean;
  onSelect: () => void;
  actuacionId: number;
  documental: IComprobacionDocumentalResponse | null;
  open: boolean;
  juzgados: IJuzgadoCatalogItem[];
  onDocumentalUpdated: () => Promise<void>;
  ejecucionReinspeccion: Record<string, unknown> | null;
  resultadoCircuito: IComprobacionRecorridoResultadoFinal | null | undefined;
  ejecucionCtx: EjecucionReinspeccionPorOficioCtx;
}) {
  const subtitulo = oficioComprobacionSubtituloIniciador(item);
  const chips = oficioOperativoChips(item);
  const documentalItem = useMemo(() => {
    if (!documental) return null;
    return documentalDesdeOficioItem(documental, item);
  }, [documental, item]);

  const ejecucionItem =
    item.ejecucion_reinspeccion != null && typeof item.ejecucion_reinspeccion === "object"
      ? (item.ejecucion_reinspeccion as Record<string, unknown>)
      : null;
  const muestraReinspeccionGlobal =
    ejecucionReinspeccion != null && oficioMuestraEjecucionReinspeccion(item, ejecucionCtx);
  const ejecucionCard = ejecucionItem ?? (muestraReinspeccionGlobal ? ejecucionReinspeccion : null);

  const otResumen = (item.orden_trabajo_numero ?? item.orden_trabajo ?? "").toString().trim();
  const concResumen = (item.conclusion ?? "").toString().trim();

  return (
    <Box
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect();
        }
      }}
      sx={{
        cursor: "pointer",
        borderRadius: 1.5,
        px: 1.5,
        py: 1.25,
        border: selected ? "1px solid rgba(255,255,255,0.35)" : "1px solid rgba(255,255,255,0.1)",
        backgroundColor: selected ? "rgba(255,255,255,0.08)" : "rgba(255,255,255,0.03)",
        transition: "border-color 0.15s, background-color 0.15s",
        "&:hover": {
          borderColor: "rgba(255,255,255,0.22)",
          backgroundColor: "rgba(255,255,255,0.06)",
        },
      }}
    >
      <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
        <Typography variant="body2" fontWeight={600} sx={{ color: "rgba(255,255,255,0.92)" }}>
          {oficioComprobacionEtiquetaCompacta(item)}
        </Typography>
        {chips.length > 0
          ? chips.map((chip) => (
              <Chip
                key={chip.label}
                size="small"
                label={chip.label}
                color={chip.color}
                variant="outlined"
                sx={{ height: 22, fontSize: "0.7rem" }}
              />
            ))
          : item.iniciador_estado ? (
              <Chip
                size="small"
                label={humanizarEstadoIniciador(item.iniciador_estado)}
                color={chipColorForIniciador(item.iniciador_estado)}
                variant="outlined"
                sx={{ height: 22, fontSize: "0.7rem" }}
              />
            ) : null}
      </Stack>
      {subtitulo && chips.length === 0 && !item.iniciador_estado ? (
        <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.55)", display: "block", mt: 0.5 }}>
          {subtitulo}
        </Typography>
      ) : null}

      <Box onClick={(e) => e.stopPropagation()} sx={{ mt: 0.5 }}>
        {selected && documentalItem ? (
          <OperativoOficioYRespuestaEditable
            open={open}
            actuacionId={actuacionId}
            documental={documentalItem}
            juzgados={juzgados}
            onDocumentalUpdated={onDocumentalUpdated}
            oficioEditable={item.editable}
            bloqueadoMotivo={item.bloqueado_motivo}
            embedEnCard
          />
        ) : (
          <OficioComprobacionDetalleLectura item={item} />
        )}

        {ejecucionCard ? (
          <OficioComprobacionReinspeccionEnCard
            ejecucion={ejecucionCard}
            resultadoCircuito={ejecucionItem ? null : resultadoCircuito}
          />
        ) : otResumen || concResumen ? (
          <Box sx={{ mt: 1.25, pt: 1.25, borderTop: "1px solid rgba(255,255,255,0.1)" }}>
            <DocumentalFila etiqueta="OT" valor={otResumen || "Sin OT"} />
            <DocumentalFila etiqueta="Conclusión" valor={concResumen || "Sin conclusión"} />
          </Box>
        ) : null}
      </Box>
    </Box>
  );
});

export type ComprobacionOficiosTribunalSectionProps = {
  open: boolean;
  actuacionId: number;
  documental: IComprobacionDocumentalResponse | null;
  documentalLoading: boolean;
  oficios: OficioComprobacionItem[];
  oficiosLoading: boolean;
  oficiosError: string | null;
  juzgados: IJuzgadoCatalogItem[];
  defaultFechaAlta: string;
  modalApiError: string | null;
  modalFieldErrors?: Record<string, string>;
  saving: boolean;
  onGuardarAlta: (payload: ComprobacionOficioAltaPayload) => void | Promise<void>;
  onDocumentalUpdated: () => Promise<void>;
  /** Oficio a preseleccionar al abrir (p. ej. fila de bandeja reinspección). */
  initialOficioId?: number | null;
  /**
   * Ejecución de reinspección del detalle de recorrido (un solo oficio en API actual).
   * Se muestra solo en la card que coincide por ``oficioId`` / ``iniciadorId``.
   */
  ejecucionReinspeccion?: Record<string, unknown> | null;
  ejecucionReinspeccionCtx?: EjecucionReinspeccionPorOficioCtx | null;
  resultadoCircuito?: IComprobacionRecorridoResultadoFinal | null;
};

/**
 * Sección «Oficios / respuestas del tribunal»: cada card con su detalle documental y reinspección (si aplica).
 */
export const ComprobacionOficiosTribunalSection = memo(function ComprobacionOficiosTribunalSection({
  open,
  actuacionId,
  documental,
  documentalLoading,
  oficios,
  oficiosLoading,
  oficiosError,
  juzgados,
  defaultFechaAlta,
  modalApiError,
  modalFieldErrors = {},
  saving,
  onGuardarAlta,
  onDocumentalUpdated,
  initialOficioId,
  ejecucionReinspeccion = null,
  ejecucionReinspeccionCtx = null,
  resultadoCircuito = null,
}: ComprobacionOficiosTribunalSectionProps) {
  const [selectedOficioId, setSelectedOficioId] = useState<number | null>(null);
  const [modoAlta, setModoAlta] = useState(false);

  const items = useMemo(
    () => mergeOficiosConLegacyDocumental(oficios, documentalLoading ? null : documental),
    [oficios, documental, documentalLoading]
  );

  const ejecucionCtx: EjecucionReinspeccionPorOficioCtx = ejecucionReinspeccionCtx ?? {
    oficioId: null,
    iniciadorId: null,
  };

  useEffect(() => {
    if (!open) {
      setModoAlta(false);
      setSelectedOficioId(null);
      return;
    }
    if (items.length === 0) {
      setSelectedOficioId(null);
      setModoAlta(true);
      return;
    }
    setSelectedOficioId((prev) => {
      if (prev != null && items.some((o) => o.id === prev)) return prev;
      if (initialOficioId != null && items.some((o) => o.id === initialOficioId)) return initialOficioId;
      return items[items.length - 1]?.id ?? null;
    });
    setModoAlta(false);
  }, [open, items, initialOficioId]);

  const handleAgregarOficio = useCallback(() => {
    setModoAlta(true);
    setSelectedOficioId(null);
  }, []);

  const handleSelectOficio = useCallback((id: number) => {
    setSelectedOficioId(id);
    setModoAlta(false);
  }, []);

  const showEmpty = !oficiosLoading && !documentalLoading && items.length === 0 && !modoAlta;
  const showAltaPrimeraVez = !oficiosLoading && !documentalLoading && items.length === 0 && modoAlta;

  return (
    <DocumentalBloque overline="Oficios / respuestas del tribunal" layout="stack">
      <Stack spacing={1.5}>
        {oficiosError ? (
          <Alert severity="warning" sx={documentalGlassAlertSx}>
            <Typography variant="body2">{oficiosError}</Typography>
          </Alert>
        ) : null}

        {oficiosLoading || documentalLoading ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 2 }}>
            <CircularProgress size={28} />
          </Box>
        ) : showEmpty ? (
          <Typography variant="body2" sx={docModalEmptyStateSx}>
            Sin oficios cargados para esta acta de comprobación.
          </Typography>
        ) : items.length > 0 ? (
          <Stack spacing={1.25}>
            {items.map((item) => (
              <OficioComprobacionCard
                key={item.id}
                item={item}
                selected={!modoAlta && selectedOficioId === item.id}
                onSelect={() => handleSelectOficio(item.id)}
                actuacionId={actuacionId}
                documental={documental}
                open={open}
                juzgados={juzgados}
                onDocumentalUpdated={onDocumentalUpdated}
                ejecucionReinspeccion={ejecucionReinspeccion}
                resultadoCircuito={resultadoCircuito}
                ejecucionCtx={ejecucionCtx}
              />
            ))}
          </Stack>
        ) : null}

        {!oficiosLoading && !documentalLoading && items.length > 0 ? (
          <Box>
            <AgregarOficioButton
              onClick={handleAgregarOficio}
              disabled={saving || modoAlta}
              tieneOficios
            />
          </Box>
        ) : null}

        {modoAlta ? (
          <ComprobacionOficioAltaFields
            open={open}
            defaultFechaAlta={defaultFechaAlta}
            juzgados={juzgados}
            modalApiError={modalApiError}
            fieldErrors={modalFieldErrors}
            saving={saving}
            onGuardarAlta={onGuardarAlta}
          />
        ) : null}

        {showAltaPrimeraVez ? null : showEmpty ? (
          <AgregarOficioButton onClick={handleAgregarOficio} disabled={saving} />
        ) : null}
      </Stack>
    </DocumentalBloque>
  );
});
