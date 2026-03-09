import {
  setCalleCanon,
  setEsquinaCanon,
  setNumeroEsquina,
} from "../../../api/geolocalizacionApi";

export const useDomicilioNormalizationActions = () => {
  const guardarNormalizacion = async (payload: {
    domicilio_id: number;
    calle_catalogo_id?: number | null;
    esquina_catalogo_id?: number | null;
    numero?: string | null;
    numero_tipo?: string | null;
  }) => {
    const {
      domicilio_id,
      calle_catalogo_id,
      esquina_catalogo_id,
      numero,
      numero_tipo,
    } = payload;

    if (numero !== undefined && numero !== null && String(numero).trim() !== "") {
      await setNumeroEsquina(domicilio_id, String(numero), numero_tipo || null);
    }
    if (calle_catalogo_id) {
      await setCalleCanon(domicilio_id, Number(calle_catalogo_id));
    }
    if (numero_tipo === "ESQUINA" && esquina_catalogo_id) {
      await setEsquinaCanon(domicilio_id, Number(esquina_catalogo_id));
    }
  };

  return { guardarNormalizacion };
};
