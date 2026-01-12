import { useMapEvents } from "react-leaflet";

export default function MapClickHandler({ mode, setNewPos, setOpenAdd }: any) {
  useMapEvents({
    click(e) {
      if (mode === "addLocal") {
        setNewPos({ lat: e.latlng.lat, lng: e.latlng.lng });
        setOpenAdd(true);
      }
    }
  });
  return null;
}
