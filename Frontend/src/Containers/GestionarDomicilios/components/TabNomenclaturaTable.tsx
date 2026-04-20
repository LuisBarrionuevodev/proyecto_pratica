import { Autocomplete, TextField, ToggleButton, ToggleButtonGroup, Typography } from "@mui/material";
import { MaterialReactTable, type MRT_ColumnDef, useMaterialReactTable } from "material-react-table";
import { useMemo, useRef, useState } from "react";
import type { GuardarNomenclaturaBody } from "../../../api/geolocalizacionApi";
import { fetchCallesCatalogo, type CalleCatalogoItem } from "../../../api/geolocalizacionApi";
import { TablePendientesStyle } from "../../../styles/MapStyles";
import type {
  DomicilioNomenclaturaEditCache,
  DomicilioPendienteItem,
  NomenclaturaCalleMode,
  NomenclaturaEsquinaMode,
} from "../types";

interface TabNomenclaturaTableProps {
  items: DomicilioPendienteItem[];
  loading: boolean;
  onGuardar: (payload: GuardarNomenclaturaBody & { domicilio_id: number }) => Promise<void>;
}

function effectiveCalleMode(
  cache: DomicilioNomenclaturaEditCache,
  row: DomicilioPendienteItem
): NomenclaturaCalleMode {
  return cache.calleMode ?? (row.calle_catalogo_id ? "CATALOGO" : "MANUAL");
}

function effectiveEsquinaMode(
  cache: DomicilioNomenclaturaEditCache,
  row: DomicilioPendienteItem,
  numeroTipo: "NUMERO" | "ESQUINA"
): NomenclaturaEsquinaMode {
  if (numeroTipo !== "ESQUINA") return "MANUAL";
  return cache.esquinaMode ?? (row.esquina_catalogo_id ? "CATALOGO" : "MANUAL");
}

function formatSaveErrorDetail(detail: unknown): string {
  if (detail == null) return "Error al guardar.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg?: string }).msg);
        }
        return JSON.stringify(item);
      })
      .join("\n");
  }
  if (typeof detail === "object") return JSON.stringify(detail);
  return String(detail);
}

function buildNomenclaturaPayload(
  row: DomicilioPendienteItem,
  cache: DomicilioNomenclaturaEditCache,
  values: Record<string, unknown>
): GuardarNomenclaturaBody {
  const editedNumeroTipo = (values.numero_tipo ??
    cache.numero_tipo ??
    row.numero_tipo ??
    "NUMERO") as "NUMERO" | "ESQUINA";
  const nt = editedNumeroTipo === "ESQUINA" ? "ESQUINA" : "NUMERO";

  const numeroRaw =
    (values.numero as string | undefined) ??
    cache.numero ??
    row.numero ??
    row.numero_raw ??
    "";
  const numero = String(numeroRaw).trim();
  if (!numero) {
    throw new Error("El número o la esquina (texto) es obligatorio.");
  }

  const calleM = effectiveCalleMode(cache, row);
  let calle: GuardarNomenclaturaBody["calle"];
  if (calleM === "CATALOGO") {
    const id =
      (values.calle_catalogo_id as number | null | undefined) ??
      cache.calle_catalogo_id ??
      row.calle_catalogo_id;
    if (!id) {
      throw new Error('Modo calle "Catálogo": seleccione una calle del catálogo.');
    }
    calle = { mode: "CATALOGO", calle_catalogo_id: Number(id) };
  } else {
    const texto = (
      cache.calleSearchText ??
      row.calle_raw ??
      row.calle_normalizada ??
      ""
    ).trim();
    if (!texto) {
      throw new Error('Modo calle "Manual": ingrese el nombre de la calle en la columna Calle.');
    }
    calle = { mode: "MANUAL", calle_texto: texto };
  }

  if (nt === "NUMERO") {
    return { calle, numero, numero_tipo: "NUMERO" };
  }

  const esqM = effectiveEsquinaMode(cache, row, "ESQUINA");
  if (esqM === "CATALOGO") {
    const eid =
      (values.esquina_catalogo_id as number | null | undefined) ??
      cache.esquina_catalogo_id ??
      row.esquina_catalogo_id;
    if (!eid) {
      throw new Error('Modo esquina "Catálogo": seleccione la calle de esquina en el catálogo.');
    }
    return {
      calle,
      numero,
      numero_tipo: "ESQUINA",
      esquina: { mode: "CATALOGO", esquina_catalogo_id: Number(eid) },
    };
  }

  return {
    calle,
    numero,
    numero_tipo: "ESQUINA",
    esquina: { mode: "MANUAL" },
  };
}

const TabNomenclaturaTable = ({ items, loading, onGuardar }: TabNomenclaturaTableProps) => {
  const debounceTimers = useRef<Record<string, ReturnType<typeof setTimeout> | null>>({});
  /**
   * MRT no re-renderiza las celdas en edición cuando solo se muta `row._valuesCache`.
   * Sin un `setState`, los ToggleButtonGroup y el resto de editores leen valores viejos.
   */
  const [nomenclaturaEditRevision, setNomenclaturaEditRevision] = useState(0);
  const bumpNomenclaturaEditors = () => setNomenclaturaEditRevision((n) => n + 1);

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

  const runRemoteSearch = (domicilioId: number, kind: "calle" | "esquina", text: string) => {
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
        id: "calle_modo",
        header: "Calle · modo",
        size: 150,
        Cell: ({ row }) => {
          const cache = ((row as any)?._valuesCache || {}) as DomicilioNomenclaturaEditCache;
          const m = effectiveCalleMode(cache, row.original);
          return m === "CATALOGO" ? "Catálogo" : "Manual";
        },
        Edit: ({ row }) => {
          const domicilioId = row.original.domicilio_id;
          const cache = ((row as any)?._valuesCache || {}) as DomicilioNomenclaturaEditCache;
          const m = effectiveCalleMode(cache, row.original);
          return (
            <ToggleButtonGroup
              size="small"
              exclusive
              value={m}
              onChange={(_, v: NomenclaturaCalleMode | null) => {
                if (!v) return;
                if (v === "MANUAL") {
                  setRowCache(row, (prev) => ({
                    ...prev,
                    calleMode: "MANUAL",
                    calle_catalogo_id: null,
                    calleSearchText:
                      prev.calleSearchText ??
                      row.original.calle_raw ??
                      row.original.calle_normalizada ??
                      "",
                  }));
                  setCalleCatalogInputByRow((prev) => ({ ...prev, [domicilioId]: "" }));
                  bumpNomenclaturaEditors();
                  return;
                }
                const labelHint =
                  row.original.calle_normalizada || row.original.calle_raw || "";
                setRowCache(row, (prev) => ({
                  ...prev,
                  calleMode: "CATALOGO",
                  calle_catalogo_id: row.original.calle_catalogo_id ?? null,
                  calleSearchText: labelHint,
                }));
                setCalleCatalogInputByRow((prev) => ({
                  ...prev,
                  [domicilioId]: labelHint,
                }));
                bumpNomenclaturaEditors();
              }}
            >
              <ToggleButton value="CATALOGO">Catálogo</ToggleButton>
              <ToggleButton value="MANUAL">Manual</ToggleButton>
            </ToggleButtonGroup>
          );
        },
      },
      {
        accessorKey: "calle_input",
        header: "Calle",
        size: 220,
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
          const calleM = effectiveCalleMode(cache, row.original);
          const options = calleOptionsByRow[domicilioId] || [];
          const selectedId = cache.calle_catalogo_id ?? row.original.calle_catalogo_id;
          const selected = selectedOptionFrom(
            options,
            selectedId,
            row.original.calle_normalizada || row.original.calle_raw || ""
          );
          const readOnlyCalle =
            selected?.nombre || row.original.calle_normalizada || row.original.calle_raw || "";

          if (calleM === "CATALOGO") {
            return (
              <TextField
                size="small"
                label="Calle"
                fullWidth
                disabled
                value={readOnlyCalle}
              />
            );
          }

          return (
            <TextField
              size="small"
              label="Calle"
              fullWidth
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
          const calleM = effectiveCalleMode(cache, row.original);
          if (calleM === "MANUAL") {
            return (
              <Typography variant="body2" color="text.disabled" sx={{ pl: 0.5 }}>
                —
              </Typography>
            );
          }
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
              renderInput={(params) => <TextField {...params} label="Catálogo" />}
            />
          );
        },
      },
      {
        accessorKey: "numero_tipo",
        header: "Tipo",
        size: 140,
        Cell: ({ row }) => {
          const cache = ((row as any)?._valuesCache || {}) as DomicilioNomenclaturaEditCache;
          return cache.numero_tipo ?? row.original.numero_tipo ?? "NUMERO";
        },
        Edit: ({ row }) => {
          const cache = ((row as any)?._valuesCache || {}) as DomicilioNomenclaturaEditCache;
          const currentMode = (cache.numero_tipo ?? row.original.numero_tipo ?? "NUMERO") as
            | "NUMERO"
            | "ESQUINA";
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
                  esquinaMode: mode === "NUMERO" ? undefined : prev.esquinaMode,
                }));
                if (mode === "NUMERO") {
                  const did = row.original.domicilio_id;
                  setEsquinaCatalogInputByRow((p) => ({ ...p, [did]: "" }));
                }
                bumpNomenclaturaEditors();
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
        size: 220,
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
          const currentMode = (cache.numero_tipo ?? row.original.numero_tipo ?? "NUMERO") as
            | "NUMERO"
            | "ESQUINA";
          return (
            <TextField
              size="small"
              label={currentMode === "ESQUINA" ? "Esquina" : "Número"}
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
        id: "esquina_modo",
        header: "Esquina · modo",
        size: 150,
        Cell: ({ row }) => {
          const cache = ((row as any)?._valuesCache || {}) as DomicilioNomenclaturaEditCache;
          const nt = (cache.numero_tipo ?? row.original.numero_tipo ?? "NUMERO") as "NUMERO" | "ESQUINA";
          if (nt !== "ESQUINA") return "—";
          const m = effectiveEsquinaMode(cache, row.original, "ESQUINA");
          return m === "CATALOGO" ? "Catálogo" : "Manual";
        },
        Edit: ({ row }) => {
          const domicilioId = row.original.domicilio_id;
          const cache = ((row as any)?._valuesCache || {}) as DomicilioNomenclaturaEditCache;
          const nt = (cache.numero_tipo ?? row.original.numero_tipo ?? "NUMERO") as "NUMERO" | "ESQUINA";
          if (nt !== "ESQUINA") {
            return (
              <Typography variant="body2" color="text.disabled" sx={{ pl: 0.5 }}>
                —
              </Typography>
            );
          }
          const m = effectiveEsquinaMode(cache, row.original, "ESQUINA");
          return (
            <ToggleButtonGroup
              size="small"
              exclusive
              value={m}
              onChange={(_, v: NomenclaturaEsquinaMode | null) => {
                if (!v) return;
                if (v === "MANUAL") {
                  setRowCache(row, (prev) => ({
                    ...prev,
                    esquinaMode: "MANUAL",
                    esquina_catalogo_id: null,
                    numero_tipo: "ESQUINA",
                  }));
                  setEsquinaCatalogInputByRow((prev) => ({ ...prev, [domicilioId]: "" }));
                  bumpNomenclaturaEditors();
                  return;
                }
                const esqHint =
                  row.original.esquina_normalizada || row.original.numero_raw || "";
                setRowCache(row, (prev) => ({
                  ...prev,
                  esquinaMode: "CATALOGO",
                  esquina_catalogo_id: row.original.esquina_catalogo_id ?? null,
                  numero_tipo: "ESQUINA",
                }));
                setEsquinaCatalogInputByRow((prev) => ({
                  ...prev,
                  [domicilioId]: esqHint,
                }));
                bumpNomenclaturaEditors();
              }}
            >
              <ToggleButton value="CATALOGO">Catálogo</ToggleButton>
              <ToggleButton value="MANUAL">Manual</ToggleButton>
            </ToggleButtonGroup>
          );
        },
      },
      {
        accessorKey: "esquina_catalogo_id",
        header: "Esquina catálogo",
        size: 260,
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
          const mode = (cache.numero_tipo ?? row.original.numero_tipo ?? "NUMERO") as "NUMERO" | "ESQUINA";
          const esqM = effectiveEsquinaMode(cache, row.original, mode);

          if (mode !== "ESQUINA") {
            return <Typography variant="body2" color="text.disabled">—</Typography>;
          }

          if (esqM === "MANUAL") {
            return (
              <Typography variant="body2" color="text.disabled" sx={{ pl: 0.5 }}>
                —
              </Typography>
            );
          }

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
              renderInput={(params) => <TextField {...params} label="Catálogo" />}
            />
          );
        },
      },
    ],
    [
      items,
      calleOptionsByRow,
      esquinaOptionsByRow,
      calleCatalogInputByRow,
      esquinaCatalogInputByRow,
      nomenclaturaEditRevision,
    ]
  );

  const table = useMaterialReactTable({
    ...TablePendientesStyle,
    columns,
    data: items,
    enableEditing: true,
    editDisplayMode: "row",
    onEditingRowSave: async ({ row, values, exitEditingMode }) => {
      const cache = ((row as any)?._valuesCache || {}) as DomicilioNomenclaturaEditCache;
      try {
        const body = buildNomenclaturaPayload(row.original, cache, values as Record<string, unknown>);
        await onGuardar({ domicilio_id: row.original.domicilio_id, ...body });
        exitEditingMode();
      } catch (e: unknown) {
        const detail =
          e && typeof e === "object" && "response" in e
            ? (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail
            : undefined;
        const fromApi =
          detail !== undefined
            ? formatSaveErrorDetail(detail)
            : e instanceof Error
              ? e.message
              : "No se pudo guardar la nomenclatura.";
        window.alert(fromApi);
      }
    },
    state: { isLoading: loading },
  });

  return <MaterialReactTable table={table} />;
};

export default TabNomenclaturaTable;
