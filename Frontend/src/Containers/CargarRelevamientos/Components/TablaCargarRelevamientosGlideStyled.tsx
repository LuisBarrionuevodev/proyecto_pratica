import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import DataEditor, {
  CompactSelection,
  type GridCell,
  GridCellKind,
  type GridColumn,
  type GridKeyEventArgs,
  type GridSelection,
  type Item,
  type EditableGridCell,
} from "@glideapps/glide-data-grid";
import "@glideapps/glide-data-grid/dist/index.css";
import { allCells } from "@glideapps/glide-data-grid-cells";
import "@glideapps/glide-data-grid-cells/dist/index.css";
import { Box, Typography, Alert, Button, CircularProgress } from "@mui/material";
import {
  startBatch,
  validateRow,
  validateBatch,
  commitBatch,
  type GridRow,
  fetchInspectores,
  fetchRubros,
} from "../../../api/gridApi";
import { ValidationErrorsRail, type ValidationRailEntry } from "./ValidationErrorsRail";

import {
  COLORS,
  titleStyles,
  alertBaseStyles,
  legendStyles,
  legendTitleStyles,
  legendTextStyles,
  kbdStyles,
  getStatusBadgeStyles,
} from "../../CargarActuaciones/styles/cargarActuacionesStyles";
import {
  containerStyles,
  wrapperStyles,
  gridContainerStyles,
  buttonMandarTodoStyles,
  calculateRelevamientoTableHeight,
} from "../styles/cargarRelevamientosStyles";
import { COLUMN_DEFINITIONS, GROUP_CONFIG } from "../config/columnDefinitions";
import {
  TURNO_DROPDOWN_LABELS,
  turnoDropdownLabelToStored,
  turnoStoredToDropdownLabel,
} from "../config/relevamientoTurnOptions";
import { formatFechaRelevamientoDisplay, parseFechaRelevamientoInput } from "../utils/relevamientoDateInput";
import { getDropdownOptions } from "../../CargarActuaciones/config/dropdownOptions";
import { gridTheme, GRID_DIMENSIONS } from "../../CargarActuaciones/config/gridTheme";
import {
  extractDataColumns,
  rowHasData,
  createEmptyRow,
  createEmptyRows,
  formatDateToISO,
} from "../../CargarActuaciones/utils/gridHelpers";

interface TablaCargarRelevamientosGlideStyledProps {
  showTitle?: boolean;
}

/** Con `rowMarkers="both"`, la primera columna de datos está desplazada en 1 respecto al canvas. */
const ROW_MARKERS_BOTH_OFFSET = 1;

const CELL_ERROR_META_KEYS = new Set(["_row", "detail", "_global"]);

/**
 * Construye entradas para el rail lateral a partir del mismo estado de grilla (`_cellErrors` / `_rowError`).
 * Prioriza mensajes por columna; si no hay, usa el resumen de fila.
 */
function buildValidationRailEntries(rows: GridRow[]): ValidationRailEntry[] {
  const out: ValidationRailEntry[] = [];
  rows.forEach((row, index) => {
    if (!rowHasData(row)) return;
    const ce = row._cellErrors || {};
    const cellLines = Object.entries(ce)
      .filter(([k]) => !CELL_ERROR_META_KEYS.has(k))
      .map(([k, v]) => (v ? `${k}: ${v}` : ""))
      .filter(Boolean) as string[];
    const lines = cellLines.length > 0 ? cellLines : row._rowError ? [row._rowError] : [];
    if (lines.length) out.push({ rowIndex: index, lines });
  });
  return out;
}

const TablaCargarRelevamientosGlideStyled = ({
  showTitle = true,
}: TablaCargarRelevamientosGlideStyledProps) => {
  const initialRows = useMemo(() => createEmptyRows(5), []);
  const [batchId, setBatchId] = useState<string | null>(null);
  const [data, setData] = useState<GridRow[]>(initialRows);
  const [isLoadingBatch, setIsLoadingBatch] = useState(false);
  const [isValidatingAll, setIsValidatingAll] = useState(false);
  const [isCommitting, setIsCommitting] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);
  const [catalogInspectores, setCatalogInspectores] = useState<string[]>([]);
  const [catalogRubros, setCatalogRubros] = useState<string[]>([]);
  const [gridSelection, setGridSelection] = useState<GridSelection | undefined>(undefined);

  const gridRef = useRef<any>(null);
  const debounceRef = useRef<Record<string, number>>({});
  const dataRef = useRef<GridRow[]>(initialRows);
  const batchValidateRef = useRef<number | undefined>(undefined);
  const startingBatchRef = useRef<boolean>(false);

  const catalogs = useMemo(
    () => ({
      inspectores: catalogInspectores,
      motivos: [],
      rubros: catalogRubros,
      tipos: [],
      contraproducencias: [],
      motivosComprobacion: [],
    }),
    [catalogInspectores, catalogRubros]
  );

  const ensureBatchStarted = useCallback(async (): Promise<string | null> => {
    if (batchId) return batchId;
    if (startingBatchRef.current) return null;
    startingBatchRef.current = true;
    try {
      setIsLoadingBatch(true);
      setGlobalError(null);
      const response = await startBatch("relevamientos");
      setBatchId(response.batch_id);
      return response.batch_id;
    } catch (error: any) {
      setGlobalError(error?.response?.data?.message || error?.message || "Error al iniciar batch");
      return null;
    } finally {
      setIsLoadingBatch(false);
      startingBatchRef.current = false;
    }
  }, [batchId]);

  useEffect(() => {
    dataRef.current = data;
  }, [data]);

  useEffect(() => {
    const loadCatalogs = async () => {
      try {
        const [inspectoresResp, rubrosResp] = await Promise.all([fetchInspectores(), fetchRubros()]);
        setCatalogInspectores([...new Set(inspectoresResp.items.map((i) => i.nombre))]);
        setCatalogRubros([...new Set(rubrosResp.items.map((r) => r.nombre))]);
      } catch (error: any) {
        setGlobalError("Error cargando catálogos (inspectores/rubros).");
      }
    };
    loadCatalogs();
  }, []);

  const buildRowErrorSummary = (errors?: Record<string, string>) => {
    if (!errors) return null;
    const messages: string[] = [];
    const topLevel = errors._row || errors.detail || errors._global;
    if (topLevel) messages.push(topLevel);
    Object.entries(errors)
      .filter(([key]) => !["_row", "detail", "_global"].includes(key))
      .forEach(([key, value]) => {
        if (value) messages.push(`${key}: ${value}`);
      });
    return messages.length ? messages.join(" | ") : null;
  };

  const validateBatchRows = useCallback(
    async (rows: GridRow[], batchIdValue?: string) => {
      const effectiveBatchId = batchIdValue || batchId;
      if (!effectiveBatchId) return null;

      const rowsWithData = rows.filter((row) => {
        const isCommitted = row.ID !== undefined && row.ID !== null;
        return rowHasData(row) && (row._touched || (!isCommitted && row._state !== "OK"));
      });
      if (rowsWithData.length === 0) return null;

      setData((prev) =>
        prev.map((row) => {
          const isCommitted = row.ID !== undefined && row.ID !== null;
          if (isCommitted && !row._touched) {
            return { ...row, _cellErrors: {}, _rowError: null };
          }
          return rowsWithData.some((r) => r._rowId === row._rowId)
            ? { ...row, _state: "VALIDANDO" }
            : row;
        })
      );

      const rowsToValidate = rowsWithData.map((row) => ({
        row_id: row._rowId!,
        row: extractDataColumns(row),
      }));

      try {
        const response = await validateBatch({ batch_id: effectiveBatchId, rows: rowsToValidate });
        setData((prev) =>
          prev.map((row) => {
            const result = response.results.find((r) => r.row_id === row._rowId);
            if (!result) return row;
            return {
              ...row,
              _state: result.ok ? "OK" : "ERROR",
              _cellErrors: result.errors || {},
              _rowError: buildRowErrorSummary(result.errors),
              _normalized: result.normalized,
              _touched: result.ok ? false : row._touched,
            };
          })
        );
        return response;
      } catch (error: any) {
        return null;
      }
    },
    [batchId]
  );

  const handleValidateRow = useCallback(
    async (row: GridRow) => {
      if (!batchId) return;
      if (!rowHasData(row)) return;

      setData((prev) =>
        prev.map((r) => (r._rowId === row._rowId ? { ...r, _state: "VALIDANDO" } : r))
      );

      try {
        const dataColumns = extractDataColumns(row);
        const response = await validateRow({
          batch_id: batchId,
          row_id: row._rowId!,
          row: dataColumns,
        });

        setData((prev) =>
          prev.map((r) =>
            r._rowId === row._rowId
              ? {
                  ...r,
                  _state: response.ok ? "OK" : "ERROR",
                  _cellErrors: response.errors || {},
                  _rowError: buildRowErrorSummary(response.errors),
                  _normalized: response.normalized,
                  _touched: response.ok ? false : r._touched,
                }
              : r
          )
        );
      } catch (error: any) {
        setData((prev) =>
          prev.map((r) =>
            r._rowId === row._rowId
              ? {
                  ...r,
                  _state: "ERROR",
                  _cellErrors: { _global: error?.response?.data?.message || "Error en validación" },
                  _rowError: error?.response?.data?.message || "Error en validación",
                }
              : r
          )
        );
      }
    },
    [batchId]
  );

  const handleCommitBatch = useCallback(async () => {
    const startedBatchId = await ensureBatchStarted();
    if (!startedBatchId) return;

    try {
      setIsValidatingAll(true);
      setGlobalError(null);

      setData((prev) =>
        prev.map((row) =>
          row.ID && !row._touched ? { ...row, _cellErrors: {}, _rowError: null } : row
        )
      );

      const rowsToValidate = dataRef.current.filter((row) => {
        const isCommitted = row.ID !== undefined && row.ID !== null;
        return rowHasData(row) && (row._needsCommit || (!isCommitted && row._state !== "OK"));
      });

      const response = await validateBatchRows(rowsToValidate, startedBatchId);
      const touchedRows = dataRef.current.filter((row) => rowHasData(row) && row._needsCommit);

      let okRows =
        response?.results
          .filter((r) => r.ok && r.normalized)
          .map((r) => ({ row_id: r.row_id, normalized: r.normalized! })) || [];

      const localOkRows = rowsToValidate
        .filter((row) => row._state === "OK" && row._normalized)
        .map((row) => ({ row_id: row._rowId!, normalized: row._normalized! }));

      if (localOkRows.length > 0) {
        const existing = new Set(okRows.map((r) => r.row_id));
        localOkRows.forEach((row) => {
          if (!existing.has(row.row_id)) okRows.push(row);
        });
      }

      if (!response) {
        okRows = localOkRows;
      }

      if (okRows.length === 0) {
        if (!response && touchedRows.length === 0) {
          setGlobalError(null);
          return;
        }
        setGlobalError(response ? "No hay filas válidas para confirmar." : "No hay filas para validar.");
        return;
      }

      setIsCommitting(true);
      const commitResp = await commitBatch({ batch_id: startedBatchId, rows: okRows });
      setData((prev) =>
        prev.map((row) => {
          const result = commitResp.results.find((r) => r.row_id === row._rowId);
          if (!result) return row;
          if (result.ok && result.persisted?.id) {
            return {
              ...row,
              ID: result.persisted.id,
              _state: "OK",
              _cellErrors: {},
              _rowError: null,
              _touched: false,
              _needsCommit: false,
            };
          }
          return {
            ...row,
            _state: "ERROR",
            _cellErrors: result.errors || {},
            _rowError: buildRowErrorSummary(result.errors) || "Error en commit",
          };
        })
      );
    } catch (error: any) {
      setGlobalError(error?.response?.data?.message || "Error en commit batch");
    } finally {
      setIsValidatingAll(false);
      setIsCommitting(false);
    }
  }, [ensureBatchStarted, validateBatchRows]);

  const handleCellEdit = useCallback(
    async ([col, row]: Item, newValue: EditableGridCell): Promise<void> => {
      if (row >= data.length) return;
      await ensureBatchStarted();

      const columnDef = COLUMN_DEFINITIONS[col];
      const columnId = columnDef.id;
      const rowData = data[row];

      let value: any;
      if (newValue.kind === GridCellKind.Custom) {
        const customData = (newValue as any).data;
        if (customData?.kind === "date-picker-cell") {
          value = formatDateToISO(customData.date);
        } else if (customData?.kind === "dropdown-cell") {
          const dropdownVal = customData.value;
          value = dropdownVal === "" || dropdownVal === null || dropdownVal === undefined ? null : dropdownVal;
        } else {
          value = customData?.value ?? customData;
        }
      } else if (newValue.kind === GridCellKind.Text) {
        value = newValue.data || null;
      } else {
        value = (newValue as any).data;
      }

      if (columnId === "Fecha") {
        if (value === "" || value === null || value === undefined) {
          value = null;
        } else if (typeof value === "string") {
          const parsed = parseFechaRelevamientoInput(value);
          value = parsed ?? value.trim();
        }
      }
      if (columnId === "Turno" && typeof value === "string") {
        const canon = turnoDropdownLabelToStored(value);
        value = canon === null ? null : canon;
      }

      let updatedRow: GridRow = {
        ...rowData,
        [columnId]: value,
        _rowError: null,
        _touched: true,
        _needsCommit: true,
      };

      if (!rowHasData(updatedRow)) {
        updatedRow = {
          ...updatedRow,
          _state: undefined,
          _cellErrors: {},
          _rowError: null,
          _normalized: undefined,
          _touched: false,
          _needsCommit: false,
        };
      } else if (updatedRow._state === "OK") {
        updatedRow = { ...updatedRow, _state: "PENDIENTE", _normalized: undefined };
      }

      setData((prev) => {
        const newData = [...prev];
        newData[row] = updatedRow;
        return newData;
      });

      const rowId = rowData._rowId;
      if (rowId && debounceRef.current[rowId] !== undefined) {
        clearTimeout(debounceRef.current[rowId]);
      }

      if (rowId) {
        debounceRef.current[rowId] = window.setTimeout(() => {
          if (batchId) {
            if (rowHasData(updatedRow)) {
              handleValidateRow(updatedRow);
            } else {
              validateRow({ batch_id: batchId, row_id: rowId, row: {} }).catch(() => {});
            }
          }
        }, 500);
      }

      if (batchId) {
        if (batchValidateRef.current) clearTimeout(batchValidateRef.current);
        batchValidateRef.current = window.setTimeout(() => {
          validateBatchRows(dataRef.current);
        }, 900);
      }
    },
    [data, batchId, ensureBatchStarted, handleValidateRow, validateBatchRows]
  );

  const handleAddRow = () => {
    setData((prev) => [...prev, createEmptyRow()]);
  };

  /**
   * Navegación tipo planilla: Tab en la última columna de datos ("Está abierto") pasa a la primera
   * columna de la fila siguiente; en la última fila útil, dispara appendRow (nueva fila + foco col 0).
   */
  /** Enfoca la grilla en la primera celda con error de la fila (o la primera columna de datos). */
  const focusRowInGrid = useCallback((rowIndex: number) => {
    const row = dataRef.current[rowIndex];
    let colGrid = ROW_MARKERS_BOTH_OFFSET;
    if (row && rowHasData(row)) {
      const ce = row._cellErrors || {};
      for (let i = 0; i < COLUMN_DEFINITIONS.length; i++) {
        const id = COLUMN_DEFINITIONS[i].id;
        if (ce[id]) {
          colGrid = ROW_MARKERS_BOTH_OFFSET + i;
          break;
        }
      }
    }
    setGridSelection({
      columns: CompactSelection.empty(),
      rows: CompactSelection.empty(),
      current: {
        cell: [colGrid, rowIndex],
        range: { x: colGrid, y: rowIndex, width: 1, height: 1 },
        rangeStack: [],
      },
    });
  }, []);

  const handleGridKeyDown = useCallback((event: GridKeyEventArgs) => {
    if (event.key !== "Tab" || event.shiftKey) return;
    const loc = event.location;
    if (loc === undefined) return;
    const [colGrid, row] = loc;
    const lastDataColGrid = ROW_MARKERS_BOTH_OFFSET + COLUMN_DEFINITIONS.length - 1;
    if (colGrid !== lastDataColGrid) return;

    event.cancel();
    event.preventDefault();
    event.stopPropagation();

    const numRows = dataRef.current.length;
    const isAtLastUsableRow = row >= numRows - 1;

    if (isAtLastUsableRow) {
      void gridRef.current?.appendRow(0, false);
      return;
    }

    setGridSelection({
      columns: CompactSelection.empty(),
      rows: CompactSelection.empty(),
      current: {
        cell: [0, row + 1],
        range: { x: 0, y: row + 1, width: 1, height: 1 },
        rangeStack: [],
      },
    });
  }, []);

  const columns = useMemo<GridColumn[]>(
    () =>
      COLUMN_DEFINITIONS.map((col) => {
        const groupConfig = col.group ? GROUP_CONFIG[col.group as keyof typeof GROUP_CONFIG] : undefined;
        return {
          title: col.title,
          id: col.id,
          width: col.width,
          /** Solo Calle crece: reduce presión de scroll horizontal en notebooks. */
          grow: col.id === "Calle" ? 1 : 0,
          group: col.group,
          icon: col.icon,
          themeOverride: groupConfig
            ? {
                bgHeader: groupConfig.color,
                bgHeaderHovered: "#3a3d44",
                textHeader: COLORS.white,
                fgIconHeader: COLORS.white,
                bgIconHeader: "transparent",
              }
            : undefined,
        };
      }),
    []
  );

  const getCellContent = useCallback(
    ([col, row]: Item): GridCell => {
      if (row >= data.length) {
        return { kind: GridCellKind.Text, data: "", displayData: "", allowOverlay: true };
      }

      const rowData = data[row];
      const columnDef = COLUMN_DEFINITIONS[col];
      const columnId = columnDef.id;
      const cellType = (columnDef as any).cellType || "text";
      const value = rowData[columnId as keyof GridRow];
      const cellErrors = (rowData._cellErrors || {}) as Record<string, string>;
      const hasError = cellErrors[columnId] !== undefined;
      const rowState = rowData._state;
      const hasData = rowHasData(rowData);

      let bgColor = COLORS.grayDark;
      let textColor = COLORS.white;

      if (hasData) {
        if (hasError) {
          bgColor = COLORS.errorLight;
          textColor = COLORS.errorText;
        } else if (rowState === "OK") {
          bgColor = COLORS.successLight;
          textColor = COLORS.successText;
        } else if (rowState === "PENDIENTE") {
          bgColor = COLORS.warningLight;
          textColor = COLORS.warningText;
        } else if (rowState === "VALIDANDO") {
          bgColor = COLORS.grayMedium;
          textColor = COLORS.white;
        }
      }

      const themeOverride = { bgCell: bgColor, textDark: textColor };

      if (columnId === "_rowError") {
        const rowError = hasData ? (rowData._rowError || "") : "";
        return {
          kind: GridCellKind.Text,
          data: rowError,
          displayData: rowError,
          allowOverlay: false,
          readonly: true,
          themeOverride: rowError
            ? { bgCell: COLORS.errorLight, textDark: COLORS.errorText }
            : { bgCell: "#1A1C20", textDark: "#666666" },
        };
      }

      if (columnId === "Fecha") {
        const raw = (value ?? "").toString().trim();
        const normalized = parseFechaRelevamientoInput(raw);
        const display = normalized ? formatFechaRelevamientoDisplay(normalized) : raw;
        const errorMsg = hasError ? (cellErrors[columnId] || "") : "";
        const displayFinal = errorMsg ? (raw ? `${display} (${errorMsg})` : errorMsg) : display;
        return {
          kind: GridCellKind.Text,
          data: raw,
          displayData: displayFinal,
          allowOverlay: true,
          themeOverride,
        };
      }

      if (cellType === "dropdown" && columnId === "Turno") {
        const options = [...TURNO_DROPDOWN_LABELS];
        const dropdownValue = turnoStoredToDropdownLabel(value ? value.toString() : null);
        return {
          kind: GridCellKind.Custom,
          allowOverlay: true,
          copyData: dropdownValue || "",
          data: { kind: "dropdown-cell", allowedValues: options, value: dropdownValue },
          themeOverride,
        } as any;
      }

      if (cellType === "dropdown") {
        const options = getDropdownOptions(columnId, catalogs);
        const dropdownValue = value ? value.toString() : null;
        return {
          kind: GridCellKind.Custom,
          allowOverlay: true,
          copyData: dropdownValue || "",
          data: { kind: "dropdown-cell", allowedValues: options, value: dropdownValue },
          themeOverride,
        } as any;
      }

      const strValue = value?.toString() || "";
      const errorMsg = hasError ? (cellErrors[columnId] || "") : "";
      const displayData = errorMsg ? (strValue ? `${strValue} (${errorMsg})` : errorMsg) : strValue;
      return {
        kind: GridCellKind.Text,
        data: strValue,
        displayData,
        allowOverlay: true,
        themeOverride,
      };
    },
    [data, catalogs]
  );

  const handleCellClicked = useCallback(() => {
    void ensureBatchStarted();
  }, [ensureBatchStarted]);

  const handleFinishedEditing = useCallback(
    (_newValue: GridCell | undefined, [col, row]: Item) => {
      if (row === data.length - 1 && col === COLUMN_DEFINITIONS.length - 1) {
        setTimeout(() => handleAddRow(), 100);
      }
    },
    [data]
  );

  const onRowAppended = useCallback(() => handleAddRow(), []);
  const rowsWithData = data.filter(rowHasData);
  const okCount = rowsWithData.filter((r) => r._state === "OK").length;
  const errorCount = rowsWithData.filter((r) => r._state === "ERROR").length;
  const pendingCount = rowsWithData.filter((r) => r._state === "PENDIENTE").length;
  const validatingCount = rowsWithData.filter((r) => r._state === "VALIDANDO").length;
  const validationRailEntries = useMemo(() => buildValidationRailEntries(data), [data]);

  const tableHeight = useMemo(() => calculateRelevamientoTableHeight(data.length), [data.length]);

  return (
    <Box sx={containerStyles}>
      <Box
        sx={{
          ...wrapperStyles,
          flexDirection: { xs: "column", lg: "row" },
          alignItems: "flex-start",
        }}
      >
        <Box
          sx={{
            flex: 1,
            minWidth: 0,
            width: { xs: "100%", lg: "auto" },
            display: "flex",
            flexDirection: "column",
            gap: 2,
            alignItems: "stretch",
          }}
        >
          {showTitle && <Typography sx={titleStyles}>Cargar iniciadores principales</Typography>}

          {!batchId && (
            <Alert severity="warning" sx={alertBaseStyles}>
              <strong>💡 TIP:</strong> Empieza a cargar datos. El batch se iniciará automáticamente.
            </Alert>
          )}

          {batchId && (
            <Alert severity="success" sx={alertBaseStyles}>
              <strong>BATCH ACTIVO:</strong> {batchId.slice(0, 13)}...
              {okCount > 0 && (
                <span style={{ color: COLORS.successText, fontWeight: 700, marginLeft: 8 }}>{okCount} OK</span>
              )}
              {errorCount > 0 && (
                <span style={{ color: COLORS.errorText, fontWeight: 700, marginLeft: 8 }}>{errorCount} ERROR</span>
              )}
              {validatingCount > 0 && (
                <span style={{ color: COLORS.white, fontWeight: 700, marginLeft: 8 }}>
                  {validatingCount} Validando...
                </span>
              )}
              {pendingCount > 0 && (
                <span style={{ color: COLORS.warningText, fontWeight: 700, marginLeft: 8 }}>
                  {pendingCount} Pendiente
                </span>
              )}
              {isLoadingBatch && <span style={{ marginLeft: 8 }}>⏳ Iniciando...</span>}
              {isCommitting && <span style={{ marginLeft: 8 }}>💾 Guardando...</span>}
            </Alert>
          )}

          <Box sx={{ display: "flex", gap: 2, mb: 0, width: "100%" }}>
            <Button
              variant="contained"
              onClick={handleCommitBatch}
              disabled={isValidatingAll || isCommitting || rowsWithData.length === 0}
              startIcon={(isValidatingAll || isCommitting) ? <CircularProgress size={16} /> : undefined}
              sx={buttonMandarTodoStyles}
            >
              MANDAR TODO (VALIDAR + CONFIRMAR)
            </Button>
          </Box>

          <Box sx={{ ...gridContainerStyles, height: tableHeight, minHeight: tableHeight, position: "relative" }}>
            <DataEditor
            ref={gridRef}
            width="100%"
            height={tableHeight}
            gridSelection={gridSelection}
            onGridSelectionChange={setGridSelection}
            getCellContent={getCellContent}
            columns={columns}
            rows={data.length}
            onCellEdited={handleCellEdit}
            onCellClicked={handleCellClicked}
            onKeyDown={handleGridKeyDown}
            onFinishedEditing={handleFinishedEditing}
            onRowAppended={onRowAppended}
            customRenderers={allCells}
            theme={gridTheme}
            smoothScrollX={true}
            smoothScrollY={true}
            trapFocus={true}
            rowMarkers="both"
            rowHeight={GRID_DIMENSIONS.rowHeight}
            headerHeight={GRID_DIMENSIONS.headerHeight}
            overscrollY={0}
            overscrollX={0}
            trailingRowOptions={{
              sticky: false,
              tint: true,
              hint: "Presiona Enter o haz clic para agregar fila...",
            }}
            getCellsForSelection={true}
            freezeColumns={0}
            keybindings={{ search: true }}
            getGroupDetails={(groupName) => {
              const config = GROUP_CONFIG[groupName as keyof typeof GROUP_CONFIG];
              return config
                ? {
                    name: groupName,
                    icon: config.icon,
                    overrideTheme: {
                      bgIconHeader: "transparent",
                      fgIconHeader: COLORS.white,
                      textGroupHeader: COLORS.white,
                    },
                  }
                : { name: groupName };
            }}
            groupHeaderHeight={GRID_DIMENSIONS.groupHeaderHeight}
            />
          </Box>

          <Box sx={legendStyles}>
            <Typography sx={legendTitleStyles}>CÓMO USAR:</Typography>
            <Typography sx={legendTextStyles} component="div">
              <strong>1.</strong> Doble click en una celda o presiona <span style={kbdStyles}>Enter</span><br />
              <strong>2.</strong> <span style={kbdStyles}>Tab</span> avanza por columnas; desde la última columna pasa a la
              fila siguiente (o crea una fila nueva al final).<br />
              <strong>3.</strong> Para agregar filas: también <span style={kbdStyles}>Enter</span> en la grilla<br />
              <strong>4.</strong> Fecha: escribir <span style={kbdStyles}>DD/MM/AAAA</span> o{" "}
              <span style={kbdStyles}>AAAA-MM-DD</span> y <span style={kbdStyles}>Enter</span> para confirmar.<br />
              <strong>5.</strong> Validación automática al editar<br />
              <strong>6.</strong> Confirmar todo: botón “Mandar todo”<br />
              <br />
              <strong>COLORES:</strong>{" "}
              <span style={getStatusBadgeStyles(COLORS.errorLight, COLORS.errorText)}>ERROR</span>
              <span style={getStatusBadgeStyles(COLORS.successLight, COLORS.successText)}>OK</span>
              <span style={getStatusBadgeStyles(COLORS.warningLight, COLORS.warningText)}>ADVERTENCIA</span>
              <span style={getStatusBadgeStyles("#1E2127", COLORS.white)}>PENDIENTE</span>
              <span style={getStatusBadgeStyles(COLORS.primary, COLORS.white)}>VALIDANDO</span>
            </Typography>
          </Box>
        </Box>

        <ValidationErrorsRail
          globalError={globalError}
          onDismissGlobal={() => setGlobalError(null)}
          entries={validationRailEntries}
          showEmptyHint={Boolean(batchId)}
          onGoToRow={focusRowInGrid}
        />
      </Box>
    </Box>
  );
};

export default TablaCargarRelevamientosGlideStyled;
