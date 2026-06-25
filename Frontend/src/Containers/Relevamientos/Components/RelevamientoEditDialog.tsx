/**
 * @deprecated Usar `RelevamientoCrudDialog` con `mode="edit"`.
 * Wrapper de compatibilidad para callers legacy (modo edición fijo).
 */
import {
  RelevamientoCrudDialog,
  type RelevamientoCrudDialogProps,
  type RelevamientoEditCatalogs,
} from "./RelevamientoCrudDialog";

export type { RelevamientoEditCatalogs };

export type RelevamientoEditDialogProps = Omit<RelevamientoCrudDialogProps, "mode" | "onModeChange">;

export function RelevamientoEditDialog(props: RelevamientoEditDialogProps) {
  return <RelevamientoCrudDialog {...props} mode="edit" />;
}
