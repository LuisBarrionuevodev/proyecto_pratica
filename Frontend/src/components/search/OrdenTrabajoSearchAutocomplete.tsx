import { useEffect, useMemo, useRef, useState } from "react";
import { Autocomplete, CircularProgress, TextField } from "@mui/material";

import {
  searchOrdenesTrabajo,
  type IOrdenSearchItem,
} from "../../api/actuacionesSearchApi";
import { useDebouncedValue } from "../../utils/useDebouncedValue";

const MIN_CHARS = 1;

interface Props {
  value: string;
  onChange: (numeroActa: string) => void;
  onBlur?: () => void;
  disabled?: boolean;
  error?: boolean;
  helperText?: string;
  label?: string;
  placeholder?: string;
}

/**
 * Autocomplete para elegir OT por búsqueda remota; permite texto libre (freeSolo).
 */
export function OrdenTrabajoSearchAutocomplete({
  value,
  onChange,
  onBlur,
  disabled = false,
  error = false,
  helperText,
  label = "Orden de trabajo",
  placeholder = "Buscar OT por número…",
}: Props) {
  const [inputValue, setInputValue] = useState(value);
  const [options, setOptions] = useState<IOrdenSearchItem[]>([]);
  const [loading, setLoading] = useState(false);
  const debouncedInput = useDebouncedValue(inputValue, 300);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    setInputValue(value);
  }, [value]);

  const selectedOption = useMemo((): IOrdenSearchItem | string | null => {
    if (!value) return null;
    const hit = options.find((o) => o.numero_acta === value);
    if (hit) return hit;
    return value;
  }, [options, value]);

  const mergedOptions = useMemo(() => {
    if (typeof selectedOption === "object" && selectedOption && !options.some((o) => o.id === selectedOption.id)) {
      return [selectedOption, ...options];
    }
    return options;
  }, [options, selectedOption]);

  useEffect(() => {
    const q = debouncedInput.trim();
    if (q.length < MIN_CHARS) {
      abortRef.current?.abort();
      setOptions([]);
      setLoading(false);
      return;
    }

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);

    void searchOrdenesTrabajo(q, 20, controller.signal)
      .then((items) => {
        if (!controller.signal.aborted) setOptions(items);
      })
      .catch(() => {
        if (!controller.signal.aborted) setOptions([]);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [debouncedInput]);

  return (
    <Autocomplete
      size="small"
      fullWidth
      freeSolo
      disabled={disabled}
      options={mergedOptions}
      value={selectedOption}
      inputValue={inputValue}
      onInputChange={(_, next, reason) => {
        if (reason === "input" || reason === "clear") {
          setInputValue(next);
          onChange(next);
        }
      }}
      onChange={(_, next) => {
        if (typeof next === "string") {
          onChange(next);
          setInputValue(next);
        } else if (next) {
          onChange(next.numero_acta);
          setInputValue(next.numero_acta);
        } else {
          onChange("");
          setInputValue("");
        }
      }}
      onBlur={onBlur}
      getOptionLabel={(opt) => (typeof opt === "string" ? opt : opt.label)}
      isOptionEqualToValue={(a, b) => {
        if (typeof a === "string" || typeof b === "string") return a === b;
        return a.id === b.id;
      }}
      loading={loading}
      noOptionsText={debouncedInput.trim().length < MIN_CHARS ? "Ingresá un número" : "Sin resultados"}
      renderInput={(params) => (
        <TextField
          {...params}
          label={label}
          placeholder={placeholder}
          error={error}
          helperText={helperText}
          InputProps={{
            ...params.InputProps,
            endAdornment: (
              <>
                {loading ? <CircularProgress color="inherit" size={18} /> : null}
                {params.InputProps.endAdornment}
              </>
            ),
          }}
        />
      )}
    />
  );
}
