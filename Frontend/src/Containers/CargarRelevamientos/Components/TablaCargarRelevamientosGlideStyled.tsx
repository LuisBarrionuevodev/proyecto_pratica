import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import DataEditor, {
  type GridCell,
  GridCellKind,
  type GridColumn,
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
  fetchContraproducencias,
} from "../../../api/gridApi";

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
} from "../styles/cargarRelevamientosStyles";
import { COLUMN_DEFINITIONS, GROUP_CONFIG } from "../config/columnDefinitions";
import { getDropdownOptions } from "../../CargarActuaciones/config/dropdownOptions";
import { gridTheme, calculateTableHeight, GRID_DIMENSIONS } from "../../CargarActuaciones/config/gridTheme";
import {
  extractDataColumns,
  rowHasData,
  createEmptyRow,
  createEmptyRows,
  parseDateValue,
  formatDateToISO,
} from "../../CargarActuaciones/utils/gridHelpers";

const TablaCargarRelevamientosGlideStyled = () => {
  const initialRows = useMemo(() => createEmptyRows(5), []);
  const [batchId, setBatchId] = useState<string | null>(null);
  const [data, setData] = useState<GridRow[]>(initialRows);
  const [isLoadingBatch, setIsLoadingBatch] = useState(false);
  const [isValidatingAll, setIsValidatingAll] = useState(false);
  const [isCommitting, setIsCommitting] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);
  const [catalogInspectores, setCatalogInspectores] = useState<string[]>([]);
  const [catalogRubros, setCatalogRubros] = useState<string[]>([]);
  const [catalogContras, setCatalogContras] = useState<string[]>([]);

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
      contraproducencias: catalogContras,
      motivosComprobacion: [],
    }),
    [catalogInspectores, catalogRubros, catalogContras]
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
        const [inspectoresResp, rubrosResp, contrasResp] = await Promise.all([
          fetchInspectores(),
          fetchRubros(),
          fetchContraproducencias(),
        ]);
        setCatalogInspectores([...new Set(inspectoresResp.items.map((i) => i.nombre))]);
        setCatalogRubros([...new Set(rubrosResp.items.map((r) => r.nombre))]);
        setCatalogContras([...new Set(contrasResp.items.map((c) => c.nombre))]);
      } catch (error: any) {
        setGlobalError("Error cargando catálogos (inspectores/rubros/contraproducencia).");
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

  const columns = useMemo<GridColumn[]>(
    () =>
      COLUMN_DEFINITIONS.map((col) => {
        const groupConfig = col.group ? GROUP_CONFIG[col.group as keyof typeof GROUP_CONFIG] : undefined;
        return {
          title: col.title,
          id: col.id,
          width: col.width,
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

      if (cellType === "date") {
        const { date, displayDate } = parseDateValue(value);
        return {
          kind: GridCellKind.Custom,
          allowOverlay: true,
          copyData: displayDate,
          data: { kind: "date-picker-cell", date, displayDate, format: "date" as const },
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
  const rowErrorText =
    data
      .map((row, index) => {
        if (!rowHasData(row) || !row._rowError) return null;
        return `Fila ${index + 1}: ${row._rowError}`;
      })
      .filter(Boolean)
      .filter((value, idx, arr) => arr.indexOf(value) === idx)
      .join(" | ") || null;

  const tableHeight = useMemo(() => calculateTableHeight(data.length), [data.length]);

  return (
    <Box sx={containerStyles}>
      <Box sx={wrapperStyles}>
        <Typography sx={titleStyles}>Carga de Relevamientos</Typography>

        {globalError && (
          <Alert severity="error" onClose={() => setGlobalError(null)} sx={alertBaseStyles}>
            {globalError}
          </Alert>
        )}

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
            {rowErrorText && (
              <div style={{ color: COLORS.errorText, textAlign: "center", marginTop: 8 }}>{rowErrorText}</div>
            )}
          </Alert>
        )}

        <Box sx={{ display: "flex", gap: 2, mb: 2 }}>
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

        <Box sx={{ ...gridContainerStyles, height: tableHeight }}>
          <DataEditor
            ref={gridRef}
            getCellContent={getCellContent}
            columns={columns}
            rows={data.length}
            onCellEdited={handleCellEdit}
            onCellClicked={handleCellClicked}
            onFinishedEditing={handleFinishedEditing}
            onRowAppended={onRowAppended}
            customRenderers={allCells}
            theme={gridTheme}
            smoothScrollX={true}
            smoothScrollY={true}
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
            <strong>2.</strong> Para agregar filas: presiona <span style={kbdStyles}>Enter</span><br />
            <strong>3.</strong> Validación automática al editar<br />
            <strong>4.</strong> Confirmar todo: botón “Mandar todo”<br />
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
    </Box>
  );
};

export default TablaCargarRelevamientosGlideStyled;
