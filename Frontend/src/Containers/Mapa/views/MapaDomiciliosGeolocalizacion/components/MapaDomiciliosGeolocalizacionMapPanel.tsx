import { useEffect } from "react";
import { Box, Stack } from "@mui/material";
import { MapContainer, Marker, Popup, TileLayer, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";
import type { GestionDomiciliosMapPoint, GestionDomiciliosRow } from "../../../../../api/gestionDomiciliosApi";
import { AppButton, AppTextField } from "../../../../../ui";
import {
  filtroButtonPrimaryStyles,
  filtroButtonSecondaryStyles,
} from "../../../../Actuaciones/styles/filtroStyles";
import { moduleFiltersSurfaceSx } from "../../../../../styles/GlassStyles";
import { useMapaEdicionManual } from "../hooks/useMapaEdicionManual";
import ConfirmarUbicacionDialog from "./ConfirmarUbicacionDialog";
import { GESTION_MAP_DEFAULT_CENTER } from "../mapaDomiciliosMapConstants";

export { GESTION_MAP_DEFAULT_CENTER };

const pointIcon = L.divIcon({
  className: "",
  html: `<div style="width:14px;height:14px;background:#1976d2;border-radius:50%;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.35);"></div>`,
  iconSize: [14, 14],
  iconAnchor: [7, 7],
});

const selectedIcon = L.divIcon({
  className: "",
  html: `<div style="width:18px;height:18px;background:#FF9800;border-radius:50%;border:2px solid white;box-shadow:0 3px 8px rgba(0,0,0,0.4);"></div>`,
  iconSize: [18, 18],
  iconAnchor: [9, 9],
});

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

function MapViewport({
  points,
  editMode,
  focusCenter,
  editFocusCenter,
}: {
  points: GestionDomiciliosMapPoint[];
  editMode: boolean;
  focusCenter: [number, number] | null;
  editFocusCenter: [number, number] | null;
}) {
  const map = useMap();

  useEffect(() => {
    if (editMode && editFocusCenter) {
      map.setView(editFocusCenter, 15);
      return;
    }
    if (focusCenter) {
      map.setView(focusCenter, 15);
      return;
    }
    if (points.length === 0) {
      map.setView(GESTION_MAP_DEFAULT_CENTER, 13);
      return;
    }
    if (points.length === 1) {
      map.setView([points[0].lat, points[0].lng], 15);
      return;
    }
    const bounds = L.latLngBounds(points.map((p) => [p.lat, p.lng] as [number, number]));
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });
  }, [editFocusCenter, editMode, focusCenter, map, points]);

  return null;
}

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

type Props = {
  mapPoints: GestionDomiciliosMapPoint[];
  selectedId: number | null;
  focusCenter: [number, number] | null;
  onSelectPoint: (point: GestionDomiciliosMapPoint) => void;
  height?: string | number;
  editRow?: GestionDomiciliosRow | null;
  onCloseEdit?: () => void;
  onSavePoint?: (payload: { domicilio_id: number; lat: number; lng: number }) => Promise<void>;
};

/** Mapa operativo PR6C.6/7: vista + overlay de edición sin segundo mapa. */
export function MapaDomiciliosGeolocalizacionMapPanel({
  mapPoints,
  selectedId,
  focusCenter,
  onSelectPoint,
  height = "100%",
  editRow = null,
  onCloseEdit,
  onSavePoint,
}: Props) {
  const editMode = editRow != null && onSavePoint != null;
  const edit = useMapaEdicionManual(editMode ? editRow : null, onSavePoint ?? (async () => {}));

  return (
    <Box sx={{ position: "relative", borderRadius: 2, overflow: "hidden", height, minHeight: 320 }}>
      {editMode ? (
        <Box
          sx={{
            position: "absolute",
            top: 10,
            left: 10,
            right: 56,
            zIndex: 1000,
            ...moduleFiltersSurfaceSx,
            p: 1.25,
            borderRadius: 2,
          }}
        >
          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
            <AppTextField
              appearance="dense"
              label="Domicilio"
              value={edit.searchText}
              onChange={(e) => edit.setSearchText(e.target.value)}
              sx={{ flex: 1, minWidth: 160 }}
              onKeyDown={(e) => {
                if (e.key === "Enter") void edit.onSearch();
              }}
            />
            <AppButton
              dsVariant="secondary"
              dsSize="sm"
              disabled={edit.searching}
              onClick={() => void edit.onSearch()}
              sx={filtroButtonSecondaryStyles}
            >
              Buscar
            </AppButton>
            <AppButton
              dsVariant="primary"
              dsSize="sm"
              disabled={!edit.pin || edit.saving}
              onClick={edit.handleRequestSave}
              sx={filtroButtonPrimaryStyles}
            >
              Guardar
            </AppButton>
            {onCloseEdit ? (
              <AppButton dsVariant="secondary" dsSize="sm" onClick={onCloseEdit} sx={filtroButtonSecondaryStyles}>
                Cerrar
              </AppButton>
            ) : null}
          </Stack>
        </Box>
      ) : null}

      <MapContainer
        center={GESTION_MAP_DEFAULT_CENTER}
        zoom={13}
        style={{ height: "100%", width: "100%", minHeight: 320 }}
      >
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <MapViewport
          points={mapPoints}
          editMode={editMode}
          focusCenter={editMode ? null : focusCenter}
          editFocusCenter={editMode ? edit.editFocusCenter : null}
        />
        {editMode ? (
          <>
            <MapClickHandler enabled onClick={(lat, lng) => edit.setPin({ lat, lng })} />
            {edit.pin ? (
              <Marker
                position={[edit.pin.lat, edit.pin.lng]}
                icon={manualPinIcon}
                draggable
                eventHandlers={{
                  dragend: (e) => {
                    const latlng = (e.target as L.Marker).getLatLng();
                    edit.setPin({ lat: latlng.lat, lng: latlng.lng });
                  },
                }}
              />
            ) : null}
          </>
        ) : (
          mapPoints.map((point) => (
            <Marker
              key={point.domicilio_id}
              position={[point.lat, point.lng]}
              icon={point.domicilio_id === selectedId ? selectedIcon : pointIcon}
              eventHandlers={{
                click: () => onSelectPoint(point),
              }}
            >
              <Popup>{point.label}</Popup>
            </Marker>
          ))
        )}
      </MapContainer>

      {editMode ? (
        <ConfirmarUbicacionDialog
          open={edit.confirmOpen}
          onConfirm={() => void edit.handleConfirmSave()}
          onClose={edit.handleCancelConfirm}
          confirming={edit.saving}
        />
      ) : null}
    </Box>
  );
}
