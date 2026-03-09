import { Autocomplete, Box, TextField, ToggleButton, ToggleButtonGroup } from "@mui/material";
import { MaterialReactTable, type MRT_ColumnDef, useMaterialReactTable } from "material-react-table";
import { useMemo, useRef, useState } from "react";
import { TablePendientesStyle } from "../../../styles/MapStyles";
import { fetchCallesCatalogo, type CalleCatalogoItem } from "../../../api/geolocalizacionApi";
import type { DomicilioNomenclaturaEditCache, DomicilioPendienteItem } from "../types";

interface TabNomenclaturaTableProps {
  items: DomicilioPendienteItem[];
  loading: boolean;
  onGuardar: (payload: {
    domicilio_id: number;
    calle_catalogo_id?: number | null;
    esquina_catalogo_id?: number | null;
    numero?: string | null;
    numero_tipo?: string | null;
  }) => Promise<void>;
}

const TabNomenclaturaTable = ({
  items,
  loading,
  onGuardar,
}: TabNomenclaturaTableProps) => {
  const debounceTimers = useRef<Record<string, ReturnType<typeof setTimeout> | null>>({});
  const [calleOptionsByRow, setCalleOptionsByRow] = useState<Record<number, CalleCatalogoItem[]>>(
    {}
  );
  const [calleCatalogInputByRow, setCalleCatalogInputByRow] = useState<Record<number, string>>({});
  const [esquinaOptionsByRow, setEsquinaOptionsByRow] = useState<
    Record<number, CalleCatalogoItem[]>
  >({});
  const [esquinaCatalogInputByRow, setEsquinaCatalogInputByRow] = useState<Record<number, string>>(
    {}
  );

  const setRowCache = (
    row: any,
    updater: (prev: DomicilioNomenclaturaEditCache) => DomicilioNomenclaturaEditCache
  ) => {
    const prev = ((row as any)?._valuesCache || {}) as DomicilioNomenclaturaEditCache;
    (row as any)._valuesCache = updater(prev);
  };

  const selectedOptionFrom = (
    options: CalleCatalogoItem[],
    selectedId?: number | null,
    fallbackLabel?: string | null
  ): CalleCatalogoItem | null => {
    if (!selectedId) return null;
    return (
      options.find((o) => o.id === selectedId) || {
        id: selectedId,
        nombre: fallbackLabel || "",
      }
    );
  };

  const runRemoteSearch = (
    domicilioId: number,
    kind: "calle" | "esquina",
    text: string
  ) => {
    const timerKey = `${domicilioId}:${kind}`;
    if (debounceTimers.current[timerKey]) {
      clearTimeout(debounceTimers.current[timerKey]!);
    }

    debounceTimers.current[timerKey] = setTimeout(async () => {
      const q = text.trim();
      if (q.length < 2) {
        if (kind === "calle") {
          setCalleOptionsByRow((prev) => ({ ...prev, [domicilioId]: [] }));
        } else {
          setEsquinaOptionsByRow((prev) => ({ ...prev, [domicilioId]: [] }));
        }
        return;
      }
      try {
        const resp = await fetchCallesCatalogo(q, 30);
        if (kind === "calle") {
          setCalleOptionsByRow((prev) => ({ ...prev, [domicilioId]: resp.items || [] }));
        } else {
          setEsquinaOptionsByRow((prev) => ({ ...prev, [domicilioId]: resp.items || [] }));
        }
      } catch {
        if (kind === "calle") {
          setCalleOptionsByRow((prev) => ({ ...prev, [domicilioId]: [] }));
        } else {
          setEsquinaOptionsByRow((prev) => ({ ...prev, [domicilioId]: [] }));
        }
      }
    }, 300);
  };

  const columns = useMemo<MRT_ColumnDef<DomicilioPendienteItem>[]>(
    () => [
      {
        accessorKey: "calle_input",
        header: "Calle",
        size: 250,
        Cell: ({ row }) => {
          const cache = ((row as any)?._valuesCache || {}) as DomicilioNomenclaturaEditCache;
          return (
            cache.calleSearchText ||
            row.original.calle_normalizada ||
            row.original.calle_raw ||
            ""
          );
        },
        Edit: ({ row }) => {
          const domicilioId = row.original.domicilio_id;
          const cache = ((row as any)?._valuesCache || {}) as DomicilioNomenclaturaEditCache;
          return (
            <TextField
              size="small"
              label="Calle"
              value={cache.calleSearchText ?? row.original.calle_raw ?? ""}
              onChange={(e) => {
                const value = e.target.value;
                setRowCache(row, (prev) => ({
                  ...prev,
                  calleSearchText: value,
                  calle_catalogo_id: null,
                }));
                runRemoteSearch(domicilioId, "calle", value);
              }}
            />
          );
        },
      },
      {
        accessorKey: "calle_catalogo_id",
        header: "Calle catálogo",
        size: 260,
        Cell: ({ row }) => {
          const selectedId = row.original.calle_catalogo_id;
          const localOptions = calleOptionsByRow[row.original.domicilio_id] || [];
          const selected = selectedOptionFrom(
            localOptions,
            selectedId,
            row.original.calle_normalizada || row.original.calle_raw || ""
          );
          return selected?.nombre || "";
        },
        Edit: ({ row }) => {
          const domicilioId = row.original.domicilio_id;
          const cache = ((row as any)?._valuesCache || {}) as DomicilioNomenclaturaEditCache;
          const options = calleOptionsByRow[domicilioId] || [];
          const selectedId = cache.calle_catalogo_id ?? row.original.calle_catalogo_id;
          const selected = selectedOptionFrom(
            options,
            selectedId,
            row.original.calle_normalizada || row.original.calle_raw || ""
          );
          const inputValue = calleCatalogInputByRow[domicilioId] ?? selected?.nombre ?? "";

          return (
            <Autocomplete
              size="small"
              options={selected ? [selected, ...options.filter((o) => o.id !== selected.id)] : options}
              getOptionLabel={(option) => option.nombre}
              isOptionEqualToValue={(option, value) => option.id === value.id}
              filterOptions={(opts) => opts}
              value={selected}
              inputValue={inputValue}
              onInputChange={(_, value, reason) => {
                if (reason === "input") {
                  setCalleCatalogInputByRow((prev) => ({ ...prev, [domicilioId]: value }));
                  setRowCache(row, (prev) => ({
                    ...prev,
                    calle_catalogo_id: null,
                  }));
                  runRemoteSearch(domicilioId, "calle", value);
                } else if (reason === "clear") {
                  setCalleCatalogInputByRow((prev) => ({ ...prev, [domicilioId]: "" }));
                  setRowCache(row, (prev) => ({
                    ...prev,
                    calle_catalogo_id: null,
                  }));
                  runRemoteSearch(domicilioId, "calle", value);
                }
              }}
              onChange={(_, newValue) => {
                const selectedOption = typeof newValue === "string" || !newValue ? null : newValue;
                setCalleCatalogInputByRow((prev) => ({
                  ...prev,
                  [domicilioId]: selectedOption?.nombre ?? "",
                }));
                setRowCache(row, (prev) => ({
                  ...prev,
                  calle_catalogo_id: selectedOption?.id ?? null,
                  calleSearchText: selectedOption?.nombre ?? prev.calleSearchText,
                }));
              }}
              renderInput={(params) => <TextField {...params} label="Buscar calle catálogo" />}
            />
          );
        },
      },
      {
        accessorKey: "numero_tipo",
        header: "Tipo",
        size: 160,
        Cell: ({ row }) => {
          const cache = ((row as any)?._valuesCache || {}) as DomicilioNomenclaturaEditCache;
          return cache.numero_tipo ?? row.original.numero_tipo ?? "NUMERO";
        },
        Edit: ({ row }) => {
          const cache = ((row as any)?._valuesCache || {}) as DomicilioNomenclaturaEditCache;
          const currentMode = cache.numero_tipo ?? row.original.numero_tipo ?? "NUMERO";
          const currentEsquinaId = cache.esquina_catalogo_id ?? row.original.esquina_catalogo_id ?? null;
          return (
            <ToggleButtonGroup
              size="small"
              exclusive
              value={currentMode}
              onChange={(_, newMode) => {
                if (!newMode) return;
                const mode = newMode as "NUMERO" | "ESQUINA";
                setRowCache(row, (prev) => ({
                  ...prev,
                  numero_tipo: mode,
                  esquina_catalogo_id: mode === "NUMERO" ? null : currentEsquinaId,
                }));
              }}
            >
              <ToggleButton value="NUMERO">NUMERO</ToggleButton>
              <ToggleButton value="ESQUINA">ESQUINA</ToggleButton>
            </ToggleButtonGroup>
          );
        },
      },
      {
        accessorKey: "numero",
        header: "Número / Esquina",
        size: 260,
        Cell: ({ row }) => {
          const cache = ((row as any)?._valuesCache || {}) as DomicilioNomenclaturaEditCache;
          const mode = cache.numero_tipo ?? row.original.numero_tipo ?? "NUMERO";
          if (mode === "ESQUINA") {
            return cache.numero || row.original.esquina_normalizada || row.original.numero_raw || "";
          }
          return cache.numero || row.original.numero || row.original.numero_raw || "";
        },
        Edit: ({ row }) => {
          const cache = ((row as any)?._valuesCache || {}) as DomicilioNomenclaturaEditCache;
          const currentMode = cache.numero_tipo ?? row.original.numero_tipo ?? "NUMERO";
          return (
            <TextField
              size="small"
              label={currentMode === "ESQUINA" ? "Esquina ingresada" : "Número"}
              value={cache.numero ?? row.original.numero ?? row.original.numero_raw ?? ""}
              onChange={(e) => {
                setRowCache(row, (prev) => ({
                  ...prev,
                  numero_tipo: currentMode,
                  numero: e.target.value,
                  esquina_catalogo_id:
                    currentMode === "NUMERO" ? null : prev.esquina_catalogo_id ?? null,
                }));
              }}
            />
          );
        },
      },
      {
        accessorKey: "esquina_catalogo_id",
        header: "Esquina catálogo",
        size: 280,
        Cell: ({ row }) => {
          const cache = ((row as any)?._valuesCache || {}) as DomicilioNomenclaturaEditCache;
          const mode = cache.numero_tipo ?? row.original.numero_tipo ?? "NUMERO";
          if (mode !== "ESQUINA") return "";
          const options = esquinaOptionsByRow[row.original.domicilio_id] || [];
          const selected = selectedOptionFrom(
            options,
            cache.esquina_catalogo_id ?? row.original.esquina_catalogo_id,
            row.original.esquina_normalizada || row.original.numero_raw || ""
          );
          return selected?.nombre || "";
        },
        Edit: ({ row }) => {
          const domicilioId = row.original.domicilio_id;
          const cache = ((row as any)?._valuesCache || {}) as DomicilioNomenclaturaEditCache;
          const mode = cache.numero_tipo ?? row.original.numero_tipo ?? "NUMERO";
          const options = esquinaOptionsByRow[domicilioId] || [];
          const selected = selectedOptionFrom(
            options,
            cache.esquina_catalogo_id ?? row.original.esquina_catalogo_id,
            row.original.esquina_normalizada || row.original.numero_raw || ""
          );
          const inputValue = esquinaCatalogInputByRow[domicilioId] ?? selected?.nombre ?? "";

          return (
            <Autocomplete
              size="small"
              disabled={mode !== "ESQUINA"}
              options={selected ? [selected, ...options.filter((o) => o.id !== selected.id)] : options}
              getOptionLabel={(option) => option.nombre}
              isOptionEqualToValue={(option, value) => option.id === value.id}
              filterOptions={(opts) => opts}
              value={selected}
              inputValue={inputValue}
              onInputChange={(_, value, reason) => {
                setEsquinaCatalogInputByRow((prev) => ({ ...prev, [domicilioId]: value }));
                if ((reason === "input" || reason === "clear") && mode === "ESQUINA") {
                  runRemoteSearch(domicilioId, "esquina", value);
                }
              }}
              onChange={(_, newValue) => {
                const selectedOption = typeof newValue === "string" || !newValue ? null : newValue;
                setEsquinaCatalogInputByRow((prev) => ({
                  ...prev,
                  [domicilioId]: selectedOption?.nombre ?? "",
                }));
                setRowCache(row, (prev) => ({
                  ...prev,
                  numero_tipo: "ESQUINA",
                  esquina_catalogo_id: selectedOption?.id ?? null,
                  numero: selectedOption?.nombre ?? prev.numero ?? "",
                }));
              }}
              renderInput={(params) => <TextField {...params} label="Buscar esquina catálogo" />}
            />
          );
        },
      },
    ],
    [items, calleOptionsByRow, esquinaOptionsByRow, calleCatalogInputByRow, esquinaCatalogInputByRow]
  );

  const table = useMaterialReactTable({
    ...TablePendientesStyle,
    columns,
    data: items,
    enableEditing: true,
    editDisplayMode: "row",
    onEditingRowSave: async ({ row, values, exitEditingMode }) => {
      const cache = ((row as any)?._valuesCache || {}) as DomicilioNomenclaturaEditCache;
      const editedNumeroTipo =
        values.numero_tipo ??
        cache.numero_tipo ??
        row.original.numero_tipo ??
        "NUMERO";
      const editedEsquinaCatalogoId =
        editedNumeroTipo === "ESQUINA"
          ? values.esquina_catalogo_id ??
            cache.esquina_catalogo_id ??
            row.original.esquina_catalogo_id
          : null;

      await onGuardar({
        domicilio_id: row.original.domicilio_id,
        calle_catalogo_id:
          values.calle_catalogo_id ??
          cache.calle_catalogo_id ??
          row.original.calle_catalogo_id,
        esquina_catalogo_id: editedEsquinaCatalogoId,
        numero:
          values.numero ??
          cache.numero ??
          row.original.numero ??
          row.original.numero_raw,
        numero_tipo: editedNumeroTipo,
      });
      exitEditingMode();
    },
    state: { isLoading: loading },
  });

  return <MaterialReactTable table={table} />;
};

export default TabNomenclaturaTable;
