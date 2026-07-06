import { Box, List, ListItemButton, ListItemText, Paper, Typography } from "@mui/material";
import { useMemo, useState } from "react";
import { retryGeo } from "../../../api/geoApi";
import { useAppFeedback } from "../../../components/feedback";
import { moduleFiltersSurfaceSx } from "../../../styles/GlassStyles";
import { formatDomicilioLineaVisible } from "../../../utils/formatDomicilioLineaVisible";
import type { DomicilioPendienteItem, DomiciliosSlice } from "../types";
import { DomicilioDetallePanel } from "./DomicilioDetallePanel";
import { DomicilioOperativoMap } from "./DomicilioOperativoMap";
import { DomicilioSliceFilterChips } from "./DomicilioSliceFilterChips";
import ManualMapPanel from "./ManualMapPanel";

type Props = {
  items: DomicilioPendienteItem[];
  loading: boolean;
  emptyMessage: string;
  filterSlice: DomiciliosSlice | "all";
  onFilterSliceChange: (value: DomiciliosSlice | "all") => void;
  onRefresh: () => Promise<void>;
  onEditNomenclatura: (item: DomicilioPendienteItem) => void;
  onSaveManualPoint: (payload: {
    domicilio_id: number;
    lat: number;
    lng: number;
  }) => Promise<void>;
};

/** Vista mapa protagonista PR6B (My Maps). */
export default function TabMapaOperativoView({
  items,
  loading,
  emptyMessage,
  filterSlice,
  onFilterSliceChange,
  onRefresh,
  onEditNomenclatura,
  onSaveManualPoint,
}: Props) {
  const { showSuccess, showError } = useAppFeedback();
  const [selected, setSelected] = useState<DomicilioPendienteItem | null>(null);
  const [manualTarget, setManualTarget] = useState<DomicilioPendienteItem | null>(null);
  const [retryLoading, setRetryLoading] = useState(false);

  const listItems = useMemo(() => {
    if (!selected) return items;
    const rest = items.filter((i) => i.domicilio_id !== selected.domicilio_id);
    return [selected, ...rest];
  }, [items, selected]);

  const handleRetry = async (item: DomicilioPendienteItem) => {
    setRetryLoading(true);
    try {
      await retryGeo(item.domicilio_id);
      showSuccess("Re-geolocalización encolada.");
      await onRefresh();
    } catch {
      showError("No se pudo re-geolocalizar el domicilio.");
    } finally {
      setRetryLoading(false);
    }
  };

  if (!loading && items.length === 0) {
    return (
      <>
        <DomicilioSliceFilterChips
          view="mapa"
          value={filterSlice}
          onChange={onFilterSliceChange}
        />
        <Typography variant="body2" color="text.secondary" sx={{ py: 4, textAlign: "center" }}>
          {emptyMessage}
        </Typography>
      </>
    );
  }

  return (
    <>
      <DomicilioSliceFilterChips view="mapa" value={filterSlice} onChange={onFilterSliceChange} />

      <Box
        sx={{
          display: "flex",
          flexDirection: { xs: "column", lg: "row" },
          gap: 2,
          minHeight: 0,
          alignItems: "stretch",
        }}
      >
        <Box sx={{ flex: { lg: "1 1 62%" }, minWidth: 0, display: "flex", flexDirection: "column" }}>
          <DomicilioOperativoMap
            items={items}
            selectedId={selected?.domicilio_id ?? null}
            onSelect={(item) => {
              setSelected(item);
              setManualTarget(null);
            }}
          />
        </Box>

        <Paper
          elevation={0}
          sx={{
            ...moduleFiltersSurfaceSx,
            flex: { lg: "0 0 340px" },
            maxWidth: { lg: 360 },
            width: "100%",
            display: "flex",
            flexDirection: "column",
            minHeight: 0,
            borderRadius: 2,
          }}
        >
          <Typography variant="subtitle2" sx={{ px: 2, pt: 1.5, pb: 0.5 }}>
            Puntos ({items.length})
          </Typography>
          <List dense sx={{ flex: "0 0 auto", maxHeight: 180, overflow: "auto" }}>
            {listItems.map((item) => (
              <ListItemButton
                key={item.domicilio_id}
                selected={selected?.domicilio_id === item.domicilio_id}
                onClick={() => {
                  setSelected(item);
                  setManualTarget(null);
                }}
              >
                <ListItemText
                  primary={`#${item.domicilio_id} · ${formatDomicilioLineaVisible(item) || item.calle_raw || "—"}`}
                  secondary={item.calle_normalizada ?? undefined}
                  primaryTypographyProps={{ noWrap: true, variant: "body2" }}
                  secondaryTypographyProps={{ noWrap: true, variant: "caption" }}
                />
              </ListItemButton>
            ))}
          </List>

          <Box sx={{ flex: 1, overflow: "auto", borderTop: 1, borderColor: "divider" }}>
            <DomicilioDetallePanel
              item={selected}
              onClose={() => setSelected(null)}
              onRetryGeocode={handleRetry}
              onGeolocalizar={(item) => setManualTarget(item)}
              onPinManual={(item) => setManualTarget(item)}
              onEditNomenclatura={onEditNomenclatura}
              retryLoading={retryLoading}
            />
          </Box>
        </Paper>
      </Box>

      {manualTarget ? (
        <ManualMapPanel
          selected={manualTarget}
          onClose={() => setManualTarget(null)}
          onSave={async (payload) => {
            await onSaveManualPoint(payload);
            setManualTarget(null);
            await onRefresh();
          }}
        />
      ) : null}
    </>
  );
}
