import { memo, useCallback, useEffect, useState } from "react";

import { AppTextField } from "../../../ui";
import { commitActaNumInputValue } from "../validations/actuacionFormNormalize";

export type ActaNumFieldLazyProps = {
  label?: string;
  value: string | null | undefined;
  disabled?: boolean;
  saving?: boolean;
  error?: boolean;
  helperText?: string;
  appearance?: "glass" | "dense";
  onCommit: (value: string | null) => void;
  /** Registra flush de valor pendiente (p. ej. antes de guardar sin blur). */
  registerFlush?: (flush: () => void) => () => void;
};

/**
 * Input de número de acta con estado local: no propaga al draft en cada tecla.
 * Normaliza con padStart(6) solo al salir del campo (blur) o al flush explícito.
 */
export const ActaNumFieldLazy = memo(function ActaNumFieldLazy({
  label = "Número de acta",
  value,
  disabled,
  saving,
  error,
  helperText,
  appearance = "glass",
  onCommit,
  registerFlush,
}: ActaNumFieldLazyProps) {
  const [local, setLocal] = useState(() => value ?? "");

  useEffect(() => {
    setLocal(value ?? "");
  }, [value]);

  const flushLocal = useCallback(() => {
    if (disabled) return;
    const committed = commitActaNumInputValue(local);
    if (committed == null) {
      onCommit(null);
      setLocal("");
      return;
    }
    onCommit(committed);
    setLocal(committed);
  }, [disabled, local, onCommit]);

  useEffect(() => {
    if (!registerFlush) return;
    return registerFlush(flushLocal);
  }, [registerFlush, flushLocal]);

  const handleBlur = useCallback(() => {
    flushLocal();
  }, [flushLocal]);

  return (
    <AppTextField
      appearance={appearance}
      label={label}
      value={local}
      onChange={(ev) => setLocal(ev.target.value)}
      onBlur={handleBlur}
      disabled={disabled || saving}
      error={error}
      helperText={helperText}
      fullWidth
    />
  );
});
