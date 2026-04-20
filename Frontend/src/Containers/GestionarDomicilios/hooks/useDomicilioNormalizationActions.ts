import type { GuardarNomenclaturaBody } from "../../../api/geolocalizacionApi";
import { guardarNomenclaturaHibrida } from "../../../api/geolocalizacionApi";

export const useDomicilioNormalizationActions = () => {
  /**
   * Persiste nomenclatura vía endpoint híbrido (calle y esquina en modo catálogo o manual).
   *
   * Parámetros:
   *   payload: cuerpo ``GuardarNomenclaturaBody`` más ``domicilio_id``.
   *
   * Retorno:
   *   Respuesta del backend.
   *
   * Errores:
   *   Propaga errores de Axios (4xx/5xx).
   */
  const guardarNormalizacion = async (
    payload: GuardarNomenclaturaBody & { domicilio_id: number }
  ) => {
    const { domicilio_id, ...body } = payload;
    return guardarNomenclaturaHibrida(domicilio_id, body);
  };

  return { guardarNormalizacion };
};
