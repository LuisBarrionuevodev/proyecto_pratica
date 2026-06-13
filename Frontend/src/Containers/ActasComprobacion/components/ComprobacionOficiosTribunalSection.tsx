import { memo, useCallback, useEffect, useMemo, useState } from "react";
import AddIcon from "@mui/icons-material/Add";
import { Alert, Box, Chip, CircularProgress, Stack, Typography } from "@mui/material";

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
  oficioOperativoChips,
} from "../utils/comprobacionOficiosUtils";
import {
  ComprobacionOficioAltaFields,
  OperativoOficioYRespuestaEditable,
  type ComprobacionOficioAltaPayload,
} from "./ComprobacionOficioOperativoDialog";
import { DocumentalBloque, DocumentalFila, parNumAnio, textoValor } from "./comprobacionOperativoBlocks";

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

const OficioComprobacionCard = memo(function OficioComprobacionCard({
  item,
  selected,
  onSelect,
}: {
  item: OficioComprobacionItem;
  selected: boolean;
  onSelect: () => void;
}) {
  const subtitulo = oficioComprobacionSubtituloIniciador(item);
  const chips = oficioOperativoChips(item);
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
      {(item.causa ?? "").toString().trim() ? (
        <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.5)", display: "block", mt: 0.35 }}>
          Causa: {String(item.causa).trim()}
        </Typography>
      ) : null}
    </Box>
  );
});

function OficioComprobacionSoloLectura({ item }: { item: OficioComprobacionItem }) {
  return (
    <Stack spacing={0.5}>
      <DocumentalFila
        etiqueta="N.º y año"
        valor={parNumAnio(item.numero_oficio ?? null, item.anio ?? null)}
      />
      <DocumentalFila etiqueta="Fecha de oficio" valor={textoValor(item.fecha_oficio)} />
      <DocumentalFila etiqueta="Causa" valor={textoValor(item.causa)} />
      <DocumentalFila etiqueta="Juzgado" valor={textoValor(item.tribunal)} />
      {!oficioComprobacionTieneBloqueCompleto(item) ? (
        <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.55)", pt: 0.5 }}>
          Expediente de respuesta no disponible en el listado.
        </Typography>
      ) : null}
    </Stack>
  );
}

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
};

/**
 * Sección «Oficios / respuestas del tribunal»: historial, selector y alta de oficios adicionales.
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
}: ComprobacionOficiosTribunalSectionProps) {
  const [selectedOficioId, setSelectedOficioId] = useState<number | null>(null);
  const [modoAlta, setModoAlta] = useState(false);

  const items = useMemo(
    () => mergeOficiosConLegacyDocumental(oficios, documentalLoading ? null : documental),
    [oficios, documental, documentalLoading]
  );

  const selectedItem = useMemo(
    () => (selectedOficioId != null ? items.find((o) => o.id === selectedOficioId) ?? null : null),
    [items, selectedOficioId]
  );

  const documentalSeleccionado = useMemo(() => {
    if (!documental || !selectedItem) return null;
    return documentalDesdeOficioItem(documental, selectedItem);
  }, [documental, selectedItem]);

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
    <DocumentalBloque overline="Oficios / respuestas del tribunal">
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
          <Stack spacing={1}>
            {items.map((item) => (
              <OficioComprobacionCard
                key={item.id}
                item={item}
                selected={!modoAlta && selectedOficioId === item.id}
                onSelect={() => handleSelectOficio(item.id)}
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
        ) : selectedItem && documentalSeleccionado ? (
          <OperativoOficioYRespuestaEditable
            open={open}
            actuacionId={actuacionId}
            documental={documentalSeleccionado}
            juzgados={juzgados}
            onDocumentalUpdated={onDocumentalUpdated}
            oficioEditable={selectedItem.editable}
            bloqueadoMotivo={selectedItem.bloqueado_motivo}
          />
        ) : selectedItem ? (
          <Stack spacing={0.5} sx={{ pt: 0.5 }}>
            <Typography variant="subtitle2" sx={{ color: "rgba(255,255,255,0.9)" }}>
              Detalle del oficio
            </Typography>
            <OficioComprobacionSoloLectura item={selectedItem} />
          </Stack>
        ) : null}

        {showAltaPrimeraVez ? null : showEmpty ? (
          <AgregarOficioButton onClick={handleAgregarOficio} disabled={saving} />
        ) : null}
      </Stack>
    </DocumentalBloque>
  );
});
