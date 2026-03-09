import { useSaveManualPoint } from "../../Mapa/hooks/useSaveManualPoint";

export const useDomicilioGeolocalizacionActions = () => {
  const { saveManualPoint } = useSaveManualPoint();

  const guardarPuntoManual = async (payload: {
    domicilio_id: number;
    lat: number;
    lng: number;
    do_reverse?: boolean;
  }) => {
    await saveManualPoint(payload);
  };

  return { guardarPuntoManual };
};
