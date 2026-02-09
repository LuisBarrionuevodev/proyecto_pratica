import { setCalleCanon, setEsquinaCanon, setNumeroEsquina } from "../../../api/geolocalizacionApi";

export interface UpdateDomicilioPayload {
  domicilio_id: number;
  calle_catalogo_id?: number | null;
  esquina_catalogo_id?: number | null;
  numero?: string | null;
  numero_tipo?: string | null;
}

export const useUpdateDomicilio = () => {
  const updateDomicilio = async (payload: UpdateDomicilioPayload) => {
    const { domicilio_id, calle_catalogo_id, esquina_catalogo_id, numero, numero_tipo } = payload;
    if (numero !== undefined && numero !== null) {
      await setNumeroEsquina(domicilio_id, String(numero), numero_tipo || null);
    }
    if (calle_catalogo_id) {
      await setCalleCanon(domicilio_id, Number(calle_catalogo_id));
    }
    if (esquina_catalogo_id) {
      await setEsquinaCanon(domicilio_id, Number(esquina_catalogo_id));
    }
  };

  return { updateDomicilio };
};
