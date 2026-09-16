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
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import { Box, Tooltip, Typography, CircularProgress, LinearProgress } from "@mui/material";
import {
  startBatch,
  validateRow,
  validateBatch,
  commitBatch,
  type GridRow,
  fetchRelevadores,
  type CatalogItem,
} from "../../../api/gridApi";
import {
  fetchRubrosCatalogoCached,
  rubroItemsToNombres,
} from "../../../utils/rubrosCatalogCache";
import { ValidationErrorsRail, type ValidationRailEntry } from "./ValidationErrorsRail";

import { COLORS, titleStyles } from "../../CargarActuaciones/styles/cargarActuacionesStyles";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { AppButton } from "../../../ui/AppButton";
import {
  containerStyles,
  wrapperStyles,
  gridContainerStyles,
  calculateRelevamientoTableHeight,
} from "../styles/cargarRelevamientosStyles";
import {
  COLUMN_DEFINITIONS,
  GROUP_CONFIG,
  RELEVAMIENTO_COLUMN_HEADER_TOOLTIPS,
} from "../config/columnDefinitions";
import {
  TURNO_DROPDOWN_LABELS,
  turnoDropdownLabelToStored,
  turnoStoredToDropdownLabel,
} from "../config/relevamientoTurnOptions";
import {
  extractDataColumns,
  rowHasData,
  createEmptyRow,
  createEmptyRows,
} from "../../CargarActuaciones/utils/gridHelpers";
import { getDropdownOptions } from "../../CargarActuaciones/config/dropdownOptions";
import { gridTheme, GRID_DIMENSIONS } from "../../CargarActuaciones/config/gridTheme";
import {
  formatRelevamientoRailCellLine,
  translateRelevamientoValidationMessage,
} from "../utils/relevamientoGridUxMessages";
import {
  buildInitialRelevamientoGridData,
  readRelevamientoDrafts,
  syncRelevadorIdsOnRow,
  syncRelevamientoDraftsAfterGridChange,
  writeRelevamientoDrafts,
} from "../utils/relevamientoDraftSessionStorage";
import {
  relevamientoDataColGridCell,
  relevamientoInspectorDataCol,
  relevamientoInspectorGridCell,
  relevamientoLastEditableGridCell,
  relevamientoResolveTabDataCol,
  RELEVAMIENTO_FIRST_EDITABLE_COL_INDEX,
  resolveRelevamientoShiftTabBackwardStep,
  resolveRelevamientoTabForwardStep,
} from "../utils/relevamientoGridNavigation";
import {
  normalizarAnguloEsquinaFrontend,
  normalizarNombreFantasiaFrontend,
  relevamientoAnguloEsAplicable,
} from "../../Relevamientos/utils/relevamientoCamposForm";
import { useAppSession } from "../../../auth/AppSessionProvider";

interface TablaCargarRelevamientosGlideStyledProps {
  showTitle?: boolean;
}

const CELL_ERROR_META_KEYS = new Set(["_row", "detail", "_global"]);
const RELEVAMIENTO_DRAFT_SAVE_DEBOUNCE_MS = 300;

/** Campos mínimos solo para color “lista para enviar” en UI — sin llamadas al backend. */
const MIN_VISUAL_FIELD_IDS = ["Relevador", "Calle", "Numero", "Rubro"] as const;

/**
 * True si la fila tiene los datos mínimos cargados (sin llamadas al backend).
 */
function relevamientoRowMinimumCompleteForVisual(row: GridRow): boolean {
  const strOk = (v: unknown) => {
    if (v === null || v === undefined) return false;
    return String(v).trim().length > 0;
  };
  return MIN_VISUAL_FIELD_IDS.every((id) => strOk(row[id as keyof GridRow]));
}

function rowHasBackendWideError(rowData: GridRow, cellErrors: Record<string, string>): boolean {
  if (rowData._state === "ERROR") return true;
  if (rowData._rowError) return true;
  return Boolean(cellErrors._row || cellErrors.detail || cellErrors._global);
}

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
      .map(([k, v]) => (v ? formatRelevamientoRailCellLine(k, v) : ""))
      .filter(Boolean) as string[];
    const lines =
      cellLines.length > 0
        ? cellLines
        : row._rowError
          ? [translateRelevamientoValidationMessage(row._rowError)]
          : [];
    if (lines.length) out.push({ rowIndex: index, lines });
  });
  return out;
}

const TablaCargarRelevamientosGlideStyled = ({
  showTitle = true,
}: TablaCargarRelevamientosGlideStyledProps) => {
  const session = useAppSession();
  const initialRows = useMemo(() => createEmptyRows(5), []);
  const [batchId, setBatchId] = useState<string | null>(null);
  const [data, setData] = useState<GridRow[]>(initialRows);
  const [isValidatingAll, setIsValidatingAll] = useState(false);
  const [isCommitting, setIsCommitting] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);
  const [catalogRelevadores, setCatalogRelevadores] = useState<CatalogItem[]>([]);
  const [catalogRubros, setCatalogRubros] = useState<string[]>([]);
  const [gridSelection, setGridSelection] = useState<GridSelection | undefined>(undefined);

  const gridRef = useRef<any>(null);
  const gridSelectionRef = useRef<GridSelection | undefined>(undefined);
  const dataRef = useRef<GridRow[]>(initialRows);
  const startingBatchRef = useRef<boolean>(false);
  const draftsHydratedRef = useRef(false);
  const draftSaveTimerRef = useRef<ReturnType<typeof window.setTimeout> | null>(null);
  const sessionUsernameRef = useRef(session.username);

  const catalogRelevadorNombres = useMemo(
    () => [...new Set(catalogRelevadores.map((i) => i.nombre))],
    [catalogRelevadores]
  );

  const catalogs = useMemo(
    () => ({
      inspectores: [],
      relevadores: catalogRelevadorNombres,
      motivos: [],
      rubros: catalogRubros,
      tipos: [],
      contraproducencias: [],
      motivosComprobacion: [],
    }),
    [catalogRelevadorNombres, catalogRubros]
  );

  const ensureBatchStarted = useCallback(async (): Promise<string | null> => {
    if (batchId) return batchId;
    if (startingBatchRef.current) return null;
    startingBatchRef.current = true;
    try {
      setGlobalError(null);
      const response = await startBatch("relevamientos");
      setBatchId(response.batch_id);
      return response.batch_id;
    } catch (error: any) {
      setGlobalError(error?.response?.data?.message || error?.message || "Error al iniciar batch");
      return null;
    } finally {
      startingBatchRef.current = false;
    }
  }, [batchId]);

  useEffect(() => {
    dataRef.current = data;
  }, [data]);

  useEffect(() => {
    gridSelectionRef.current = gridSelection;
  }, [gridSelection]);

  useEffect(() => {
    sessionUsernameRef.current = session.username;
  }, [session.username]);

  const flushRelevamientoDraftsToSession = useCallback(() => {
    if (!draftsHydratedRef.current) return;
    const username = sessionUsernameRef.current;
    if (!username) return;
    if (draftSaveTimerRef.current !== null) {
      window.clearTimeout(draftSaveTimerRef.current);
      draftSaveTimerRef.current = null;
    }
    writeRelevamientoDrafts(username, dataRef.current);
  }, []);

  const scheduleRelevamientoDraftSave = useCallback(() => {
    if (!draftsHydratedRef.current) return;
    if (session.status !== "ready" || !session.username) return;
    if (draftSaveTimerRef.current !== null) {
      window.clearTimeout(draftSaveTimerRef.current);
    }
    draftSaveTimerRef.current = window.setTimeout(() => {
      draftSaveTimerRef.current = null;
      writeRelevamientoDrafts(session.username, dataRef.current);
    }, RELEVAMIENTO_DRAFT_SAVE_DEBOUNCE_MS);
  }, [session.status, session.username]);

  useEffect(() => {
    if (session.status === "loading") return;
    if (draftsHydratedRef.current) return;
    draftsHydratedRef.current = true;
    const drafts = readRelevamientoDrafts(session.username);
    if (drafts.length > 0) {
      setData(buildInitialRelevamientoGridData(drafts, catalogRelevadores));
    }
  }, [session.status, session.username, catalogRelevadores]);

  useEffect(() => {
    scheduleRelevamientoDraftSave();
  }, [data, scheduleRelevamientoDraftSave]);

  useEffect(() => {
    const onPageHide = () => flushRelevamientoDraftsToSession();
    window.addEventListener("pagehide", onPageHide);
    return () => {
      window.removeEventListener("pagehide", onPageHide);
      flushRelevamientoDraftsToSession();
    };
  }, [flushRelevamientoDraftsToSession]);

  useEffect(() => {
    const loadCatalogs = async () => {
      try {
        const [relevadoresResp, rubrosItems] = await Promise.all([
          fetchRelevadores(),
          fetchRubrosCatalogoCached(),
        ]);
        setCatalogRelevadores(relevadoresResp.items);
        setCatalogRubros(rubroItemsToNombres(rubrosItems));
      } catch (error: any) {
        setGlobalError("Error cargando catálogos (relevadores/rubros).");
      }
    };
    loadCatalogs();
  }, []);

  const buildRowErrorSummary = (errors?: Record<string, string>) => {
    if (!errors) return null;
    const messages: string[] = [];
    const topLevel = errors._row || errors.detail || errors._global;
    if (topLevel) messages.push(translateRelevamientoValidationMessage(topLevel));
    Object.entries(errors)
      .filter(([key]) => !["_row", "detail", "_global"].includes(key))
      .forEach(([key, value]) => {
        if (value) messages.push(formatRelevamientoRailCellLine(key, value));
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
        /** Si el lote ya devolvió errores por fila, no duplicar un mensaje global en el rail. */
        const batchHadInvalidRows = Boolean(response?.results?.some((r) => !r.ok));
        if (batchHadInvalidRows) {
          setGlobalError(null);
          return;
        }
        setGlobalError(response ? "No hay filas válidas para confirmar." : "No hay filas para validar.");
        return;
      }

      setIsCommitting(true);
      const commitResp = await commitBatch({ batch_id: startedBatchId, rows: okRows });
      // Future: hook global de notificaciones cuando exista el sistema unificado (éxito parcial/total).
      setData((prev) => {
        const next = prev.map((row) => {
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
        });
        syncRelevamientoDraftsAfterGridChange(session.username, next);
        return next;
      });
    } catch (error: any) {
      setGlobalError(error?.response?.data?.message || "Error en commit batch");
    } finally {
      setIsValidatingAll(false);
      setIsCommitting(false);
    }
  }, [ensureBatchStarted, session.username, validateBatchRows]);

  const handleCellEdit = useCallback(
    async ([col, row]: Item, newValue: EditableGridCell): Promise<void> => {
      if (row >= data.length) return;
      const batchSessionId = await ensureBatchStarted();

      const columnDef = COLUMN_DEFINITIONS[col];
      const columnId = columnDef.id;
      const cellType = (columnDef as { cellType?: string }).cellType || "text";
      const rowData = data[row];

      let value: any;
      if (newValue.kind === GridCellKind.Custom) {
        const customData = (newValue as any).data;
        if (customData?.kind === "dropdown-cell") {
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

      if (columnId === "Turno" && typeof value === "string") {
        const canon = turnoDropdownLabelToStored(value);
        value = canon === null ? null : canon;
      }
      if (columnId === "Nombre fantasía" && typeof value === "string") {
        value = normalizarNombreFantasiaFrontend(value);
      }
      if (columnId === "Ángulo esquina") {
        const ang = normalizarAnguloEsquinaFrontend(
          value === null || value === undefined ? null : String(value),
          { numero: (rowData.Numero as string) ?? null }
        );
        value = ang.value;
      }

      let updatedRow: GridRow = {
        ...rowData,
        [columnId]: value,
        _rowError: null,
        _cellErrors: {},
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
      } else if (updatedRow._state === "ERROR") {
        updatedRow = { ...updatedRow, _state: "PENDIENTE", _normalized: undefined };
      }

      if (columnId === "Relevador") {
        updatedRow = syncRelevadorIdsOnRow(updatedRow, catalogRelevadores);
      }

      setData((prev) => {
        const newData = [...prev];
        newData[row] = updatedRow;
        return newData;
      });

      const rowId = rowData._rowId;
      if (rowId && batchSessionId && !rowHasData(updatedRow)) {
        void validateRow({ batch_id: batchSessionId, row_id: rowId, row: {} }).catch(() => {});
      }
    },
    [data, ensureBatchStarted, catalogRelevadores]
  );

  const focusGridCell = useCallback((dataCol: number, rowIndex: number) => {
    const applySelection = () => {
      setGridSelection({
        columns: CompactSelection.empty(),
        rows: CompactSelection.empty(),
        current: {
          cell: [dataCol, rowIndex],
          range: { x: dataCol, y: rowIndex, width: 1, height: 1 },
          rangeStack: [],
        },
      });
    };
    applySelection();
    requestAnimationFrame(() => {
      applySelection();
      gridRef.current?.focus?.();
    });
  }, []);

  /** Enfoca la grilla en la primera celda con error de la fila (o Relevador). */
  const focusRowInGrid = useCallback(
    (rowIndex: number) => {
      const row = dataRef.current[rowIndex];
      let dataCol = relevamientoInspectorDataCol();
      if (row && rowHasData(row)) {
        const ce = row._cellErrors || {};
        for (let i = 0; i < COLUMN_DEFINITIONS.length; i++) {
          const id = COLUMN_DEFINITIONS[i].id;
          if (ce[id]) {
            dataCol = i;
            break;
          }
        }
      }
      focusGridCell(dataCol, rowIndex);
    },
    [focusGridCell]
  );

  const handleGridKeyDown = useCallback(
    (event: GridKeyEventArgs) => {
      if (event.key !== "Tab") return;
      const active = relevamientoResolveTabDataCol(
        event.location,
        gridSelectionRef.current?.current?.cell
      );
      if (!active) return;
      const { dataCol, row } = active;

      if (event.shiftKey) {
        const back = resolveRelevamientoShiftTabBackwardStep(dataCol, row);
        if (!back) return;
        event.cancel();
        if (back.type === "prev-col") {
          const [targetDataCol, targetRow] = relevamientoDataColGridCell(back.dataCol, back.row);
          focusGridCell(targetDataCol, targetRow);
          return;
        }
        const [targetDataCol, targetRow] = relevamientoLastEditableGridCell(back.row);
        focusGridCell(targetDataCol, targetRow);
        return;
      }

      const forward = resolveRelevamientoTabForwardStep(dataCol, row, dataRef.current.length);
      if (!forward) return;

      event.cancel();
      event.preventDefault();
      event.stopPropagation();

      if (forward.type === "next-col") {
        const [targetDataCol, targetRow] = relevamientoDataColGridCell(forward.dataCol, forward.row);
        focusGridCell(targetDataCol, targetRow);
        return;
      }

      if (forward.type === "append-row-first-col") {
        void gridRef.current?.appendRow(relevamientoInspectorDataCol(), true);
        return;
      }

      const [targetDataCol, targetRow] = relevamientoInspectorGridCell(forward.row);
      focusGridCell(targetDataCol, targetRow);
    },
    [focusGridCell]
  );

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
      const cellType = (columnDef as { cellType?: string }).cellType || "text";
      const value = rowData[columnId as keyof GridRow];
      const cellErrors = (rowData._cellErrors || {}) as Record<string, string>;
      const hasError = cellErrors[columnId] !== undefined;
      const rowState = rowData._state;
      const hasData = rowHasData(rowData);
      const backendWideError = rowHasBackendWideError(rowData, cellErrors);
      const cellShowsBackendError = Boolean(cellErrors[columnId]) || backendWideError;
      const localMinimumOk = hasData && relevamientoRowMinimumCompleteForVisual(rowData);

      let bgColor = COLORS.grayDark;
      let textColor = COLORS.white;

      if (hasData) {
        if (cellShowsBackendError) {
          bgColor = COLORS.errorLight;
          textColor = COLORS.errorText;
        } else if (rowState === "VALIDANDO") {
          bgColor = COLORS.grayMedium;
          textColor = COLORS.white;
        } else if (rowState === "OK") {
          bgColor = COLORS.successLight;
          textColor = COLORS.successText;
        } else if (localMinimumOk) {
          bgColor = COLORS.successLight;
          textColor = COLORS.successText;
        } else if (rowState === "PENDIENTE" || rowState === undefined) {
          bgColor = COLORS.warningLight;
          textColor = COLORS.warningText;
        } else {
          bgColor = COLORS.warningLight;
          textColor = COLORS.warningText;
        }
      }

      const themeOverride = { bgCell: bgColor, textDark: textColor };

      if (columnId === "_rowError") {
        const rowErrorRaw = hasData ? (rowData._rowError || "") : "";
        const rowError = rowErrorRaw ? translateRelevamientoValidationMessage(rowErrorRaw) : "";
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

      if (cellType === "dropdown" && columnId === "Ángulo esquina") {
        const anguloAplica = relevamientoAnguloEsAplicable({
          numero: (rowData.Numero as string) ?? null,
        });
        if (!anguloAplica) {
          return {
            kind: GridCellKind.Text,
            data: "",
            displayData: "—",
            allowOverlay: false,
            readonly: true,
            themeOverride: { bgCell: bgColor, textDark: "#666666" },
          };
        }
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
      const errorMsgRaw = hasError ? (cellErrors[columnId] || "") : "";
      const errorMsg = errorMsgRaw ? translateRelevamientoValidationMessage(errorMsgRaw) : "";
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

  const onRowAppended = useCallback(() => {
    setData((prev) => [...prev, createEmptyRow()]);
    requestAnimationFrame(() => {
      const rowIdx = dataRef.current.length - 1;
      const [dataCol] = relevamientoInspectorGridCell(rowIdx);
      focusGridCell(dataCol, rowIdx);
    });
  }, [focusGridCell]);
  const rowsWithData = data.filter(rowHasData);
  const validationRailEntries = useMemo(() => buildValidationRailEntries(data), [data]);

  const tableHeight = useMemo(() => calculateRelevamientoTableHeight(data.length), [data.length]);
  const overlayBusy = isValidatingAll || isCommitting;
  const overlayLabel = isCommitting ? "Guardando relevamientos…" : "Validando relevamientos…";

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

          <Box sx={{ display: "flex", gap: 2, mb: 0, width: "100%", alignItems: "center" }}>
            <AppButton
              dsVariant="primary"
              dsSize="md"
              loading={overlayBusy}
              onClick={handleCommitBatch}
              disabled={overlayBusy || rowsWithData.length === 0}
              sx={{
                fontFamily: '"Tactic Sans", sans-serif',
                fontWeight: 600,
                textTransform: "none",
                borderRadius: "10px",
                px: 3,
              }}
            >
              Mandar todo (validar y guardar)
            </AppButton>
          </Box>

          <Box
            sx={{
              display: "flex",
              flexWrap: "wrap",
              gap: 2,
              justifyContent: "flex-end",
              alignItems: "center",
            }}
            aria-hidden={false}
          >
            {(["Numero", "Ángulo esquina"] as const).map((columnId) => {
              const tooltip = RELEVAMIENTO_COLUMN_HEADER_TOOLTIPS[columnId];
              const title = COLUMN_DEFINITIONS.find((c) => c.id === columnId)?.title;
              if (!tooltip || !title) return null;
              return (
                <Tooltip key={columnId} title={tooltip} arrow describeChild>
                  <Box
                    component="span"
                    sx={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 0.5,
                      color: GLASS_COLORS.textMuted,
                      fontSize: "0.75rem",
                      cursor: "help",
                    }}
                    aria-label={`Ayuda: ${title}. ${tooltip}`}
                  >
                    <InfoOutlinedIcon sx={{ fontSize: 14 }} aria-hidden />
                    {title}
                  </Box>
                </Tooltip>
              );
            })}
          </Box>

          <Box sx={{ ...gridContainerStyles, height: tableHeight, minHeight: tableHeight, position: "relative" }}>
            {overlayBusy ? (
              <Box
                sx={{
                  position: "absolute",
                  inset: 0,
                  zIndex: 6,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 2,
                  px: 3,
                  bgcolor: "rgba(10, 12, 18, 0.72)",
                  backdropFilter: "blur(8px)",
                  WebkitBackdropFilter: "blur(8px)",
                  pointerEvents: "all",
                }}
              >
                <LinearProgress
                  sx={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    right: 0,
                    height: 3,
                    borderRadius: 0,
                    bgcolor: "rgba(255,255,255,0.06)",
                    "& .MuiLinearProgress-bar": { bgcolor: GLASS_COLORS.primary },
                  }}
                  variant="indeterminate"
                />
                <CircularProgress size={36} thickness={4} sx={{ color: GLASS_COLORS.primary }} />
                <Typography
                  sx={{
                    fontFamily: '"Tactic Sans", sans-serif',
                    fontWeight: 600,
                    fontSize: "0.95rem",
                    color: GLASS_COLORS.textPrimary,
                    textAlign: "center",
                  }}
                >
                  {overlayLabel}
                </Typography>
              </Box>
            ) : null}
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
              hint: "Presioná Enter o hacé clic para agregar una fila…",
              targetColumn: RELEVAMIENTO_FIRST_EDITABLE_COL_INDEX,
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
