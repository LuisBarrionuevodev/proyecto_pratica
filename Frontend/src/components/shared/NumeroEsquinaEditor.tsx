import {
  Autocomplete,
  Box,
  CircularProgress,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
} from "@mui/material";
import { useCallback, useEffect, useMemo, useRef, useState, type MouseEvent } from "react";

import { fetchCallesCatalogo } from "../../api/geolocalizacionApi";

type EditorMode = "NUMERO" | "ESQUINA";

const hasLetters = (value: string) => /[a-zA-ZáéíóúñÁÉÍÓÚÑ]/.test(value);
const isOnlyDigits = (value: string) => /^\d+$/.test(value);

const CALLES_DEBOUNCE_MS = 280;

interface NumeroEsquinaEditorProps {
  value: string | null;
  onChange: (newValue: string | null) => void;
  /**
   * Opciones extra (ej. calles sugeridas desde el mapa). El listado principal sale del catálogo DB
   * con búsqueda por texto (`fetchCallesCatalogo`).
   */
  extraCalles?: string[];
  /**
   * @deprecated Usar `extraCalles`. Se fusiona con `extraCalles` por compatibilidad.
   */
  calles?: string[];
  label?: string;
  error?: boolean;
  helperText?: string;
  allowFreeSolo?: boolean;
  onModeChange?: (mode: "NUMERO" | "ESQUINA") => void;
  initialMode?: "NUMERO" | "ESQUINA";
}

const NumeroEsquinaEditor = ({
  value,
  onChange,
  extraCalles = [],
  calles = [],
  label = "Número",
  error = false,
  helperText = "",
  allowFreeSolo = false,
  onModeChange,
  initialMode: initialModeProp,
}: NumeroEsquinaEditorProps) => {
  const supplementary = useMemo(
    () => Array.from(new Set([...extraCalles, ...calles].filter(Boolean))),
    [extraCalles, calles]
  );

  const initialMode: EditorMode = useMemo(() => {
    if (initialModeProp) return initialModeProp;
    if (!value) return "NUMERO";
    return hasLetters(value) ? "ESQUINA" : "NUMERO";
  }, [value, initialModeProp]);

  const [mode, setMode] = useState<EditorMode>(initialMode);
  const [inputValue, setInputValue] = useState(value ?? "");
  const [options, setOptions] = useState<string[]>([]);
  const [loadingCalles, setLoadingCalles] = useState(false);
  const fetchSeq = useRef(0);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const mergeOptions = useCallback(
    (fromDb: string[], query: string) => {
      const q = query.trim().toLowerCase();
      const extraFiltered = supplementary.filter(
        (n) => !q || n.toLowerCase().includes(q)
      );
      return Array.from(new Set([...fromDb, ...extraFiltered]));
    },
    [supplementary]
  );

  const runCallesFetch = useCallback(
    async (query: string) => {
      const seq = ++fetchSeq.current;
      setLoadingCalles(true);
      try {
        const resp = await fetchCallesCatalogo(query.trim() || undefined, 30);
        if (seq !== fetchSeq.current) return;
        const names = resp.items.map((i) => i.nombre).filter(Boolean);
        setOptions(mergeOptions(names, query));
      } catch {
        if (seq !== fetchSeq.current) return;
        setOptions(mergeOptions([], query));
      } finally {
        if (seq === fetchSeq.current) setLoadingCalles(false);
      }
    },
    [mergeOptions]
  );

  useEffect(() => {
    setMode(initialMode);
    setInputValue(value ?? "");
  }, [initialMode, value]);

  /**
   * Sincroniza el modo con el padre. NO incluir `onModeChange` en dependencias: si el padre pasa
   * un callback inline nuevo en cada render, el efecto se re-ejecuta en bucle (setState → re-render → …).
   */
  const onModeChangeRef = useRef(onModeChange);
  onModeChangeRef.current = onModeChange;
  useEffect(() => {
    onModeChangeRef.current?.(mode);
  }, [mode]);

  useEffect(() => {
    if (mode !== "ESQUINA") return;
    void runCallesFetch("");
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [mode, runCallesFetch]);

  const scheduleFetch = useCallback(
    (raw: string) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        debounceRef.current = null;
        void runCallesFetch(raw);
      }, CALLES_DEBOUNCE_MS);
    },
    [runCallesFetch]
  );

  const optionsWithCurrent = useMemo(() => {
    const v = value?.trim();
    if (!v) return options;
    if (options.includes(v)) return options;
    return [...options, v];
  }, [options, value]);

  const handleModeChange = (_: MouseEvent<HTMLElement>, newMode: EditorMode | null) => {
    if (!newMode) return;
    setMode(newMode);
    onModeChange?.(newMode);
    if (!value) return;

    if (newMode === "NUMERO" && !isOnlyDigits(value)) {
      onChange(null);
    }
    if (newMode === "ESQUINA" && isOnlyDigits(value)) {
      onChange(null);
    }
  };

  return (
    <Box sx={{ display: "flex", gap: 1, alignItems: "center", width: "100%" }}>
      <ToggleButtonGroup
        size="small"
        exclusive
        value={mode}
        onChange={handleModeChange}
        aria-label="modo numero esquina"
      >
        <ToggleButton value="NUMERO">Número</ToggleButton>
        <ToggleButton value="ESQUINA">Esquina</ToggleButton>
      </ToggleButtonGroup>

      {mode === "NUMERO" ? (
        <TextField
          label={label}
          size="small"
          value={value ?? ""}
          error={error}
          helperText={helperText}
          inputProps={{ inputMode: "numeric", pattern: "[0-9]*" }}
          onChange={(event) => {
            const digitsOnly = event.target.value.replace(/\D+/g, "");
            onChange(digitsOnly.length > 0 ? digitsOnly : null);
          }}
          sx={{ flex: 1 }}
        />
      ) : (
        <Autocomplete
          size="small"
          freeSolo={allowFreeSolo}
          options={optionsWithCurrent}
          loading={loadingCalles}
          filterOptions={(x) => x}
          openOnFocus
          autoHighlight
          value={value}
          inputValue={inputValue}
          onOpen={() => {
            void runCallesFetch(inputValue);
          }}
          onInputChange={(_, newInputValue, reason) => {
            setInputValue(newInputValue);
            if (reason === "clear") {
              onChange(null);
              void runCallesFetch("");
              return;
            }
            if (reason === "input") {
              onChange(newInputValue.length > 0 ? newInputValue : null);
              scheduleFetch(newInputValue);
            }
            if (reason === "reset") {
              setInputValue(value ?? "");
            }
          }}
          onChange={(_, newValue) => {
            const next = typeof newValue === "string" ? newValue : newValue ?? "";
            onChange(next.length > 0 ? next : null);
          }}
          renderInput={(params) => (
            <TextField
              {...params}
              label={`${label} (esquina)`}
              error={error}
              helperText={helperText}
              InputProps={{
                ...params.InputProps,
                endAdornment: (
                  <>
                    {loadingCalles ? <CircularProgress color="inherit" size={16} /> : null}
                    {params.InputProps.endAdornment}
                  </>
                ),
              }}
            />
          )}
          sx={{ flex: 1 }}
        />
      )}
    </Box>
  );
};

export default NumeroEsquinaEditor;
