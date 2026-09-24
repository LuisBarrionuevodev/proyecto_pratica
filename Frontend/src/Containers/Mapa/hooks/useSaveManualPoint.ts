import { saveManualGeocode } from "../../../api/mapApi";

export const useSaveManualPoint = () => {
  const saveManualPoint = async (payload: {
    domicilio_id: number;
    lat: number;
    lng: number;
    do_reverse?: boolean;
  }) => {
    return saveManualGeocode(payload);
  };

  return { saveManualPoint };
};
