/**
 * Política visual de errores OT en la card de asignación (PR11.1g-b).
 * OT consumida: solo error inline debajo del campo, sin alert lateral duplicado.
 */

export type OtItemCardErrorDisplay = {
  showInlineError: boolean;
  inlineMessage: string;
  showSideOtConsumidaAlert: boolean;
};

/**
 * Deriva qué elementos visuales mostrar para un error de guardado OT en la card.
 */
export function otItemCardErrorDisplay(input: {
  inlineMessage?: string;
  otConsumida?: boolean;
}): OtItemCardErrorDisplay {
  const inlineMessage = input.inlineMessage?.trim() ?? "";
  const showInlineError = inlineMessage.length > 0;
  return {
    showInlineError,
    inlineMessage,
    showSideOtConsumidaAlert: false,
  };
}
