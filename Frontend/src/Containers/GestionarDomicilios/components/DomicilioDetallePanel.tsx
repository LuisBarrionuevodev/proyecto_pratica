import { Box, Button, Divider, Stack, Typography } from "@mui/material";
import { formatDomicilioLineaVisible } from "../../../utils/formatDomicilioLineaVisible";
import {
  labelGeocodeEstado,
  labelNomenclaturaEstado,
} from "../domicilioClasificacionLabels";
import { labelMatchStrategy, scoreDisplayWithStrategy } from "../domicilioMatchStrategyLabels";
import { labelPriorityBand, priorityBandFromScore } from "../domicilioPriorityLabels";
import { sliceSupportsNomenclaturaEdit } from "../domicilioSliceTabs";
import type { DomicilioPendienteItem, DomiciliosSlice } from "../types";

type Props = {
  item: DomicilioPendienteItem | null;
  onClose?: () => void;
  onGeolocalizar?: (item: DomicilioPendienteItem) => void;
  onPinManual?: (item: DomicilioPendienteItem) => void;
  onRetryGeocode?: (item: DomicilioPendienteItem) => void;
  onEditNomenclatura?: (item: DomicilioPendienteItem) => void;
  retryLoading?: boolean;
};

function itemSlice(item: DomicilioPendienteItem): DomiciliosSlice | undefined {
  return (item.slice as DomiciliosSlice | undefined) ?? undefined;
}

/** Panel lateral de detalle PR6B (My Maps). */
export function DomicilioDetallePanel({
  item,
  onClose,
  onGeolocalizar,
  onPinManual,
  onRetryGeocode,
  onEditNomenclatura,
  retryLoading = false,
}: Props) {
  if (!item) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography variant="body2" color="text.secondary">
          Seleccioná un punto o fila del mapa para ver detalle y acciones.
        </Typography>
      </Box>
    );
  }

  const domicilioLinea = formatDomicilioLineaVisible(item) || item.calle_raw || "—";
  const slice = itemSlice(item);
  const canEditNomenclatura =
    slice != null
      ? sliceSupportsNomenclaturaEdit(slice)
      : item.nomenclatura_estado === "NOMENCLATURA_PENDIENTE" ||
        item.calle_status === "PENDIENTE" ||
        item.calle_status === "REVIEW";
  const priority = priorityBandFromScore(item.score_unificado);
  const matchLabel = labelMatchStrategy(item.match_strategy, item.confidence_reason);

  return (
    <Box sx={{ p: 2, minWidth: 0 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" gap={1}>
        <Typography variant="subtitle1" fontWeight={600}>
          #{item.domicilio_id}
        </Typography>
        {onClose ? (
          <Button size="small" onClick={onClose}>
            Cerrar
          </Button>
        ) : null}
      </Stack>

      <Typography variant="body2" sx={{ mt: 0.5, mb: 1.5 }}>
        {domicilioLinea}
      </Typography>

      <Stack spacing={0.75} sx={{ mb: 1.5 }}>
        <Row label="Calle sugerida" value={item.calle_normalizada ?? "—"} />
        <Row
          label="Nomenclatura"
          value={labelNomenclaturaEstado(item.nomenclatura_estado ?? item.calle_status)}
        />
        <Row label="Geocode" value={labelGeocodeEstado(item.geocode_estado ?? item.geo_status)} />
        <Row
          label="Score"
          value={scoreDisplayWithStrategy(
            item.score_unificado,
            item.match_strategy,
            item.confidence_reason
          )}
        />
        <Row label="Prioridad" value={labelPriorityBand(priority)} />
        <Row label="Match" value={matchLabel} />
        {item.confidence_reason ? (
          <Row label="Confianza" value={item.confidence_reason} />
        ) : null}
        {item.error_msg ? <Row label="Detalle error" value={item.error_msg} /> : null}
      </Stack>

      <Divider sx={{ my: 1.5 }} />

      <Stack direction="row" flexWrap="wrap" gap={1} useFlexGap>
        {onRetryGeocode ? (
          <Button
            size="small"
            variant="outlined"
            disabled={retryLoading}
            onClick={() => onRetryGeocode(item)}
          >
            Re-geolocalizar
          </Button>
        ) : null}
        {onGeolocalizar ? (
          <Button size="small" variant="outlined" onClick={() => onGeolocalizar(item)}>
            Geolocalizar
          </Button>
        ) : null}
        {onPinManual ? (
          <Button size="small" variant="contained" onClick={() => onPinManual(item)}>
            Pin manual
          </Button>
        ) : null}
        {canEditNomenclatura && onEditNomenclatura ? (
          <Button size="small" variant="outlined" onClick={() => onEditNomenclatura(item)}>
            Corregir nomenclatura
          </Button>
        ) : null}
      </Stack>
    </Box>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary" display="block">
        {label}
      </Typography>
      <Typography variant="body2">{value}</Typography>
    </Box>
  );
}
