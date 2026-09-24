/**
 * Flujo guardar punto manual: confirmación antes de persistir (PR6C.5).
 */

export type PendingManualSave = {
  domicilio_id: number;
  lat: number;
  lng: number;
};

export function createPendingManualSave(
  domicilio_id: number,
  pin: { lat: number; lng: number } | null
): PendingManualSave | null {
  if (!pin) return null;
  return {
    domicilio_id,
    lat: pin.lat,
    lng: pin.lng,
  };
}

/** True solo si el usuario confirmó y hay payload pendiente. */
export function shouldExecuteManualSave(
  confirmed: boolean,
  pending: PendingManualSave | null
): pending is PendingManualSave {
  return confirmed && pending !== null;
}
