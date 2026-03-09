import { useEffect, useMemo, useState } from "react";
import { Box, Button, Paper, TextField, Typography } from "@mui/material";
import { MapContainer, Marker, TileLayer, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";
import type { DomicilioPendienteItem } from "../types";

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

  useEffect(() => {
    if (!selected) {
      setPin(null);
      setCenter(null);
      return;
    }
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
    const numero = selected.numero || selected.numero_raw || "";
    if (selected.numero_tipo === "ESQUINA" && selected.esquina_normalizada) {
      return `${selected.calle_normalizada || selected.calle_raw || ""} y ${selected.esquina_normalizada}`;
    }
    return `${selected.calle_normalizada || selected.calle_raw || ""} ${numero}`.trim();
  }, [selected]);

  const onSearch = async () => {
    if (!searchText.trim()) return;
    setSearching(true);
    try {
      const q = encodeURIComponent(searchText.trim());
      const url = `https://nominatim.openstreetmap.org/search?format=json&q=${q}&limit=1`;
      const resp = await fetch(url, { headers: { "Accept-Language": "es" } });
      const data = await resp.json();
      if (Array.isArray(data) && data[0]) {
        const lat = parseFloat(data[0].lat);
        const lng = parseFloat(data[0].lon);
        if (!Number.isNaN(lat) && !Number.isNaN(lng)) {
          setCenter([lat, lng]);
          setPin({ lat, lng });
        }
      }
    } finally {
      setSearching(false);
    }
  };

  const handleSave = async () => {
    if (!selected || !pin) return;
    setSaving(true);
    try {
      await onSave({
        domicilio_id: selected.domicilio_id,
        lat: pin.lat,
        lng: pin.lng,
      });
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
        <Button variant="contained" disabled={!pin || saving} onClick={handleSave}>
          Guardar punto
        </Button>
      </Box>

      <MapContainer center={defaultCenter} zoom={13} style={{ height: "52vh", width: "100%" }}>
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
                const latlng = (e.target as any).getLatLng();
                setPin({ lat: latlng.lat, lng: latlng.lng });
              },
            }}
          />
        )}
      </MapContainer>
    </Paper>
  );
};

export default ManualMapPanel;
