import { useEffect, useMemo, useState } from "react";
import { Box, Button, Paper, TextField, Typography } from "@mui/material";
import { MapContainer, Marker, TileLayer, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";
import { formatDomicilioLineaVisible } from "../../../utils/formatDomicilioLineaVisible";
import { searchAddress } from "../services/geocodeSearchProvider";
import {
  createPendingManualSave,
  shouldExecuteManualSave,
} from "../services/manualMapPanelSaveFlow";
import type { DomicilioPendienteItem } from "../types";
import ConfirmarUbicacionDialog from "./ConfirmarUbicacionDialog";

const defaultCenter: [number, number] = [-26.8241, -65.2226];

const manualPinIcon = L.divIcon({
  className: "",
  html: `
    <div style="
      width:20px;
      height:20px;
      background:#FF9800;
      border-radius:50% 50% 50% 0;
      transform: rotate(-45deg);
      border:2px solid white;
      box-shadow:0 4px 10px rgba(0,0,0,0.3);
    "></div>
  `,
  iconSize: [20, 20],
  iconAnchor: [10, 18],
});

const MapCenter = ({ center }: { center: [number, number] | null }) => {
  const map = useMap();
  useEffect(() => {
    if (center) {
      map.setView(center, 14);
    }
  }, [center, map]);
  return null;
};

const MapClickHandler = ({
  enabled,
  onClick,
}: {
  enabled: boolean;
  onClick: (lat: number, lng: number) => void;
}) => {
  useMapEvents({
    click: (e) => {
      if (!enabled) return;
      onClick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
};

interface ManualMapPanelProps {
  selected: DomicilioPendienteItem | null;
  onClose: () => void;
  onSave: (payload: { domicilio_id: number; lat: number; lng: number }) => Promise<void>;
}

const ManualMapPanel = ({ selected, onClose, onSave }: ManualMapPanelProps) => {
  const [pin, setPin] = useState<{ lat: number; lng: number } | null>(null);
  const [center, setCenter] = useState<[number, number] | null>(null);
  const [searchText, setSearchText] = useState("");
  const [saving, setSaving] = useState(false);
  const [searching, setSearching] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingSave, setPendingSave] = useState<ReturnType<typeof createPendingManualSave>>(null);

  useEffect(() => {
    if (!selected) {
      setPin(null);
      setCenter(null);
      setSearchText("");
      setConfirmOpen(false);
      setPendingSave(null);
      return;
    }
    const label = formatDomicilioLineaVisible(selected);
    setSearchText(label);
    if (selected.lat && selected.lng) {
      setPin({ lat: selected.lat, lng: selected.lng });
      setCenter([selected.lat, selected.lng]);
    } else {
      setPin(null);
      setCenter(defaultCenter);
    }
  }, [selected]);

  const selectedLabel = useMemo(() => {
    if (!selected) return "";
    return formatDomicilioLineaVisible(selected);
  }, [selected]);

  const onSearch = async () => {
    if (!searchText.trim()) return;
    setSearching(true);
    try {
      const result = await searchAddress(searchText);
      if (result) {
        setCenter([result.lat, result.lng]);
        setPin({ lat: result.lat, lng: result.lng });
      }
    } finally {
      setSearching(false);
    }
  };

  const handleRequestSave = () => {
    if (!selected) return;
    const pending = createPendingManualSave(selected.domicilio_id, pin);
    if (!pending) return;
    setPendingSave(pending);
    setConfirmOpen(true);
  };

  const handleCancelConfirm = () => {
    setConfirmOpen(false);
    setPendingSave(null);
  };

  const handleConfirmSave = async () => {
    if (!shouldExecuteManualSave(true, pendingSave)) return;
    setSaving(true);
    try {
      await onSave({
        domicilio_id: pendingSave.domicilio_id,
        lat: pendingSave.lat,
        lng: pendingSave.lng,
      });
      setConfirmOpen(false);
      setPendingSave(null);
    } finally {
      setSaving(false);
    }
  };

  if (!selected) return null;

  return (
    <Paper sx={{ p: 1, mt: 2 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1 }}>
        <Typography variant="subtitle2">
          Resolución manual: #{selected.domicilio_id} - {selectedLabel}
        </Typography>
        <Button variant="outlined" onClick={onClose}>
          Cerrar panel
        </Button>
      </Box>

      <Box sx={{ display: "flex", gap: 1, mb: 1, flexWrap: "wrap" }}>
        <TextField
          size="small"
          label="Buscar dirección"
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
        />
        <Button variant="outlined" disabled={searching} onClick={onSearch}>
          Buscar
        </Button>
        <Button variant="contained" disabled={!pin || saving} onClick={handleRequestSave}>
          Guardar punto
        </Button>
      </Box>

      <MapContainer center={defaultCenter} zoom={13} style={{ height: "min(36vh, 320px)", width: "100%" }}>
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <MapCenter center={center} />
        <MapClickHandler enabled onClick={(lat, lng) => setPin({ lat, lng })} />
        {pin && (
          <Marker
            position={[pin.lat, pin.lng]}
            icon={manualPinIcon}
            draggable
            eventHandlers={{
              dragend: (e) => {
                const latlng = (e.target as L.Marker).getLatLng();
                setPin({ lat: latlng.lat, lng: latlng.lng });
              },
            }}
          />
        )}
      </MapContainer>

      <ConfirmarUbicacionDialog
        open={confirmOpen}
        domicilioLinea={selectedLabel}
        lat={pendingSave?.lat ?? pin?.lat ?? defaultCenter[0]}
        lng={pendingSave?.lng ?? pin?.lng ?? defaultCenter[1]}
        onConfirm={handleConfirmSave}
        onClose={handleCancelConfirm}
        confirming={saving}
      />
    </Paper>
  );
};

export default ManualMapPanel;
