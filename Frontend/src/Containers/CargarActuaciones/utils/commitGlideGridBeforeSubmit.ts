import type { RefObject } from "react";

import { flushActiveElementBeforeAction } from "../../../utils/flushActiveElementBeforeAction";

type GlideGridRef = RefObject<{ focus?: () => void } | null>;

/**
 * Antes de validar/guardar un lote Glide: commitea la celda activa (blur) y
 * deja que React/`dataRef` reflejen el último valor editado.
 */
export async function commitGlideGridBeforeSubmit(_gridRef?: GlideGridRef): Promise<void> {
  await flushActiveElementBeforeAction();
}
