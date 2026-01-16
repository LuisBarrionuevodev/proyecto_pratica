/**
 * Hook para operaciones de batch (start, validate, commit)
 * Maneja el ciclo de vida del batch y sus operaciones
 */

import { useState, useRef, useCallback } from "react";
import {
    startBatch,
    validateRow,
    validateBatch,
    commitRow,
    commitBatch,
    type GridRow,
} from "../../../api/gridApi";
import { extractDataColumns } from "../utils/gridHelpers";

// =============================================================================
// TIPOS
// =============================================================================

interface BatchState {
    batchId: string | null;
    isLoading: boolean;
    isValidating: boolean;
    isCommitting: boolean;
    error: string | null;
}

interface ValidateRowResult {
    ok: boolean;
    errors?: Record<string, string>;
    normalized?: GridRow;
}

// =============================================================================
// HOOK
// =============================================================================

/**
 * Hook para manejar operaciones de batch
 * Incluye: iniciar batch, validar filas, commit
 * 
 * @param onDataUpdate - Callback para actualizar datos después de validación/commit
 */
export function useBatchOperations(
    onDataUpdate: (updater: (prev: GridRow[]) => GridRow[]) => void
) {
    const [state, setState] = useState<BatchState>({
        batchId: null,
        isLoading: false,
        isValidating: false,
        isCommitting: false,
        error: null,
    });

    const startingBatchRef = useRef(false);

    // =========================================================================
    // INICIAR BATCH
    // =========================================================================

    /**
     * Inicia un nuevo batch si no existe uno activo
     * Se llama automáticamente al editar la primera celda
     */
    const ensureBatchStarted = useCallback(async () => {
        if (state.batchId || startingBatchRef.current) return;
        
        startingBatchRef.current = true;
        setState(prev => ({ ...prev, isLoading: true, error: null }));

        try {
            const response = await startBatch();
            setState(prev => ({
                ...prev,
                batchId: response.batch_id,
                isLoading: false,
            }));
            console.log("✅ Batch iniciado (auto):", response.batch_id);
        } catch (error: any) {
            console.error("❌ Error al iniciar batch:", error);
            const errorMsg =
                error?.response?.data?.message ||
                error?.message ||
                "Error al iniciar batch. Verifica que el backend esté corriendo.";
            setState(prev => ({
                ...prev,
                isLoading: false,
                error: errorMsg,
            }));
        } finally {
            startingBatchRef.current = false;
        }
    }, [state.batchId]);

    // =========================================================================
    // VALIDAR FILA INDIVIDUAL
    // =========================================================================

    /**
     * Valida una fila individual y auto-commitea si es válida
     */
    const validateAndCommitRow = useCallback(async (row: GridRow) => {
        if (!state.batchId) {
            console.warn("⚠️ No hay batch iniciado, omitiendo validación");
            return;
        }

        try {
            const dataColumns = extractDataColumns(row);
            const response = await validateRow({
                batch_id: state.batchId,
                row_id: row._rowId!,
                row: dataColumns,
            });

            console.log("✅ Validación fila:", response);

            // Actualizar estado de la fila
            onDataUpdate((prev) =>
                prev.map((r) =>
                    r._rowId === row._rowId
                        ? {
                              ...r,
                              _state: response.ok ? "OK" : "ERROR",
                              _cellErrors: response.errors || {},
                              _rowError: response.errors?._row || response.errors?.detail || null,
                              _normalized: response.normalized,
                          }
                        : r
                )
            );

            // Auto-confirmar fila si es válida
            if (response.ok && response.normalized) {
                await autoCommitRow(row._rowId!, response.normalized);
            }
        } catch (error: any) {
            console.error("❌ Error validando fila:", error);
            onDataUpdate((prev) =>
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
    }, [state.batchId, onDataUpdate]);

    // =========================================================================
    // AUTO-COMMIT
    // =========================================================================

    /**
     * Commit automático de una fila validada
     */
    const autoCommitRow = async (rowId: string, normalized: GridRow) => {
        if (!state.batchId) return;

        try {
            setState(prev => ({ ...prev, isCommitting: true }));
            const commitResp = await commitRow({
                batch_id: state.batchId,
                row_id: rowId,
                normalized,
            });
            processCommitResult(commitResp);
        } catch (error: any) {
            console.error("❌ Error en commit automático (fila):", error);
            setState(prev => ({
                ...prev,
                error: error?.response?.data?.message || "Error en commit automático",
            }));
        } finally {
            setState(prev => ({ ...prev, isCommitting: false }));
        }
    };

    // =========================================================================
    // VALIDAR BATCH COMPLETO
    // =========================================================================

    /**
     * Valida todas las filas del batch y auto-commitea las válidas
     */
    const validateAllRows = useCallback(async (rows: GridRow[]) => {
        if (!state.batchId) return;

        setState(prev => ({ ...prev, isValidating: true, error: null }));

        try {
            const rowsToValidate = rows.map((row) => ({
                row_id: row._rowId!,
                row: extractDataColumns(row),
            }));

            const response = await validateBatch({
                batch_id: state.batchId,
                rows: rowsToValidate,
            });

            console.log("✅ Validación batch completada:", response);

            // Actualizar estado de cada fila
            onDataUpdate((prev) =>
                prev.map((row) => {
                    const result = response.results.find((r) => r.row_id === row._rowId);
                    if (!result) return row;

                    return {
                        ...row,
                        _state: result.ok ? "OK" : "ERROR",
                        _cellErrors: result.errors || {},
                        _rowError: result.errors?._row || result.errors?.detail || null,
                        _normalized: result.normalized,
                    };
                })
            );

            // Auto-confirmar filas OK
            const okRows = response.results
                .filter((r) => r.ok && r.normalized)
                .map((r) => ({ row_id: r.row_id, normalized: r.normalized! }));

            if (okRows.length > 0) {
                await autoCommitBatch(okRows);
            }
        } catch (error: any) {
            console.error("❌ Error en validación batch:", error);
            setState(prev => ({
                ...prev,
                error: error?.response?.data?.message || "Error al validar batch",
            }));
        } finally {
            setState(prev => ({ ...prev, isValidating: false }));
        }
    }, [state.batchId, onDataUpdate]);

    // =========================================================================
    // AUTO-COMMIT BATCH
    // =========================================================================

    /**
     * Commit automático de múltiples filas validadas
     */
    const autoCommitBatch = async (rows: Array<{ row_id: string; normalized: GridRow }>) => {
        if (!state.batchId) return;

        try {
            setState(prev => ({ ...prev, isCommitting: true }));
            const commitResp = await commitBatch({ 
                batch_id: state.batchId, 
                rows 
            });
            
            // Procesar resultados
            commitResp.results.forEach(processCommitResult);
        } catch (error: any) {
            console.error("❌ Error en commit batch automático:", error);
            setState(prev => ({
                ...prev,
                error: error?.response?.data?.message || "Error en commit batch automático",
            }));
        } finally {
            setState(prev => ({ ...prev, isCommitting: false }));
        }
    };

    // =========================================================================
    // PROCESAR RESULTADO DE COMMIT
    // =========================================================================

    /**
     * Procesa el resultado de un commit individual
     */
    const processCommitResult = (result: any) => {
        onDataUpdate((prev) =>
            prev.map((row) => {
                if (row._rowId !== result.row_id) return row;

                if (result.ok && result.persisted?.id) {
                    return {
                        ...row,
                        ID: result.persisted.id,
                        _state: "OK" as const,
                        _cellErrors: {},
                        _rowError: null,
                    };
                } else if (!result.ok) {
                    return {
                        ...row,
                        _state: "ERROR" as const,
                        _cellErrors: result.errors || {},
                        _rowError: result.errors?.detail || result.errors?._row || "Error en commit",
                    };
                }
                return row;
            })
        );
    };

    // =========================================================================
    // CLEAR ERROR
    // =========================================================================

    const clearError = useCallback(() => {
        setState(prev => ({ ...prev, error: null }));
    }, []);

    // =========================================================================
    // RETURN
    // =========================================================================

    return {
        batchId: state.batchId,
        isLoading: state.isLoading,
        isValidating: state.isValidating,
        isCommitting: state.isCommitting,
        error: state.error,
        ensureBatchStarted,
        validateAndCommitRow,
        validateAllRows,
        clearError,
    };
}

export default useBatchOperations;
