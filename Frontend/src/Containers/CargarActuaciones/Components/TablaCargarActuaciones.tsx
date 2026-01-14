import {
    MaterialReactTable,
    useMaterialReactTable,
    type MRT_ColumnDef,
    type MRT_Row,
    type MRT_TableOptions,
} from "material-react-table";
import { useMemo, useRef, useState } from "react";
import { Box, Typography, Button, Stack, Chip, Alert, CircularProgress, Tooltip } from "@mui/material";
import { TableGeneralStyles, TableTitleStyles } from "../../../styles/TablasStyle";
import { TABLE_CREAR_ACTUACIONES } from "../../../constants/tableConfig";
import { TableButtonCreate } from "./TableButtonCreate";
import {
    startBatch,
    validateRow,
    validateBatch,
    commitRow,
    commitBatch,
    type GridRow,
} from "../../../api/gridApi";

// Generador de IDs únicos para filas
const generateRowId = (() => {
    let counter = 0;
    return () => `row_${Date.now()}_${counter++}`;
})();

const TablaCargarActuaciones = () => {
    const [batchId, setBatchId] = useState<string | null>(null);
    const [data, setData] = useState<GridRow[]>([]);
    const [isLoadingBatch, setIsLoadingBatch] = useState(false);
    const [isValidatingAll, setIsValidatingAll] = useState(false);
    const [isCommitting, setIsCommitting] = useState(false);
    const [globalError, setGlobalError] = useState<string | null>(null);

    const debounceRef = useRef<Record<string, number>>({});

    // ============= BATCH OPERATIONS =============

    const handleStartBatch = async () => {
        try {
            setIsLoadingBatch(true);
            setGlobalError(null);
            const response = await startBatch();
            setBatchId(response.batch_id);
            console.log("✅ Batch iniciado:", response.batch_id);
        } catch (error: any) {
            console.error("❌ Error al iniciar batch:", error);
            setGlobalError(error?.response?.data?.message || "Error al iniciar batch");
        } finally {
            setIsLoadingBatch(false);
        }
    };

    const handleValidateAll = async () => {
        if (!batchId) {
            setGlobalError("Debes iniciar un batch primero");
            return;
        }

        try {
            setIsValidatingAll(true);
            setGlobalError(null);

            const rowsToValidate = data.map((row) => ({
                row_id: row._rowId!,
                row: extractDataColumns(row),
            }));

            const response = await validateBatch({
                batch_id: batchId,
                rows: rowsToValidate,
            });

            console.log("✅ Validación batch completada:", response);

            // Actualizar estado de cada fila
            setData((prev) =>
                prev.map((row) => {
                    const result = response.results.find((r) => r.row_id === row._rowId);
                    if (!result) return row;

                    return {
                        ...row,
                        _state: result.ok ? "OK" : "ERROR",
                        _errors: result.errors
                            ? Object.entries(result.errors)
                                  .map(([col, msg]) => `${col}: ${msg}`)
                                  .join("; ")
                            : undefined,
                        _normalized: result.normalized,
                    };
                })
            );
        } catch (error: any) {
            console.error("❌ Error en validación batch:", error);
            setGlobalError(error?.response?.data?.message || "Error al validar batch");
        } finally {
            setIsValidatingAll(false);
        }
    };

    const handleCommitAll = async () => {
        if (!batchId) {
            setGlobalError("Debes iniciar un batch primero");
            return;
        }

        const okRows = data.filter((row) => row._state === "OK");

        if (okRows.length === 0) {
            setGlobalError("No hay filas válidas para confirmar. Valida primero.");
            return;
        }

        try {
            setIsCommitting(true);
            setGlobalError(null);

            const rowsToCommit = okRows.map((row) => ({
                row_id: row._rowId!,
                normalized: row._normalized || extractDataColumns(row), // Use normalized data from validation
            }));

            try {
                // Intentar commit batch
                const response = await commitBatch({
                    batch_id: batchId,
                    rows: rowsToCommit,
                });

                console.log("✅ Commit batch completado:", response);
                processCommitResults(response.results);
            } catch (error: any) {
                if (error.message === "FALLBACK_TO_INDIVIDUAL") {
                    // Fallback: commit uno por uno
                    console.log("⚠️ Usando commit individual...");
                    await commitIndividual(rowsToCommit);
                } else {
                    throw error;
                }
            }
        } catch (error: any) {
            console.error("❌ Error en commit:", error);
            setGlobalError(error?.response?.data?.message || "Error al confirmar carga");
        } finally {
            setIsCommitting(false);
        }
    };

    const commitIndividual = async (rows: Array<{ row_id: string; normalized: GridRow }>) => {
        const results = [];
        for (const { row_id, normalized } of rows) {
            try {
                const result = await commitRow({ batch_id: batchId!, row_id, normalized });
                results.push(result);
            } catch (error: any) {
                results.push({
                    batch_id: batchId!,
                    row_id,
                    ok: false,
                    errors: { _global: error?.response?.data?.message || "Error al confirmar" },
                });
            }
        }
        processCommitResults(results);
    };

    const processCommitResults = (results: Array<any>) => {
        setData((prev) =>
            prev.map((row) => {
                const result = results.find((r) => r.row_id === row._rowId);
                if (!result) return row;

                if (result.ok && result.persisted?.id) {
                    return {
                        ...row,
                        "ID": result.persisted.id,
                        _state: "OK",
                        _errors: undefined,
                    };
                } else if (!result.ok) {
                    return {
                        ...row,
                        _state: "ERROR",
                        _errors: result.errors
                            ? Object.entries(result.errors)
                                  .map(([col, msg]) => `${col}: ${msg}`)
                                  .join("; ")
                            : "Error desconocido",
                    };
                }
                return row;
            })
        );
    };

    // ============= ROW VALIDATION =============

    const handleValidateRow = async (row: GridRow) => {
        if (!batchId) {
            console.warn("⚠️ No hay batch iniciado, omitiendo validación");
            return;
        }

        try {
            const dataColumns = extractDataColumns(row);
            const response = await validateRow({
                batch_id: batchId,
                row_id: row._rowId!,
                row: dataColumns,
            });

            console.log("✅ Validación fila:", response);

            // Actualizar estado de la fila
            setData((prev) =>
                prev.map((r) =>
                    r._rowId === row._rowId
                        ? {
                              ...r,
                              _state: response.ok ? "OK" : "ERROR",
                              _errors: response.errors
                                  ? Object.entries(response.errors)
                                        .map(([col, msg]) => `${col}: ${msg}`)
                                        .join("; ")
                                  : undefined,
                              _normalized: response.normalized,
                          }
                        : r
                )
            );
        } catch (error: any) {
            console.error("❌ Error validando fila:", error);
            setData((prev) =>
                prev.map((r) =>
                    r._rowId === row._rowId
                        ? {
                              ...r,
                              _state: "ERROR",
                              _errors: error?.response?.data?.message || "Error en validación",
                          }
                        : r
                )
            );
        }
    };

    const handleChangeWithDebounce = (row: MRT_Row<GridRow>, columnId: string, value: any) => {
        // Actualizar el valor inmediatamente en el cache
        row._valuesCache[columnId] = value;

        // Limpiar timeout anterior para esta fila
        const rowId = row.original._rowId;
        if (rowId && debounceRef.current[rowId] !== undefined) {
            clearTimeout(debounceRef.current[rowId]);
        }

        // Programar validación con debounce
        if (rowId) {
            debounceRef.current[rowId] = window.setTimeout(() => {
                const updatedRow = {
                    ...row.original,
                    ...row._valuesCache,
                };
                handleValidateRow(updatedRow);
            }, 500);
        }
    };

    // ============= ROW CREATION =============

    const handleCreateNewRow: MRT_TableOptions<GridRow>["onCreatingRowSave"] = async ({
        values,
        table,
    }) => {
        const rowId = generateRowId();
        const newRow: GridRow = {
            ...values,
            _rowId: rowId,
            _state: "PENDIENTE",
        };

        setData((prev) => [...prev, newRow]);
        table.setCreatingRow(null);

        // Si hay batch iniciado, validar automáticamente
        if (batchId) {
            handleValidateRow(newRow);
        }

        // Reabrir formulario para siguiente fila
        setTimeout(() => table.setCreatingRow(true), 50);
    };

    // ============= HELPERS =============

    const extractDataColumns = (row: GridRow): GridRow => {
        const { _rowId, _state, _errors, _normalized, ...dataColumns } = row;
        return dataColumns;
    };

    const getRowStyle = (row: MRT_Row<GridRow>) => {
        const state = row.original._state;
        if (state === "ERROR") {
            return { backgroundColor: "#ffebee" }; // Rojo claro
        }
        if (state === "OK") {
            return { backgroundColor: "#e8f5e9" }; // Verde claro
        }
        return {};
    };

    // ============= COLUMNS DEFINITION =============

    const columns = useMemo<MRT_ColumnDef<GridRow>[]>(
        () => [
            {
                accessorKey: "_state",
                header: "Estado",
                enableEditing: false,
                size: 100,
                Cell: ({ row }) => {
                    const state = row.original._state;
                    if (state === "OK") return <Chip label="OK" color="success" size="small" />;
                    if (state === "ERROR") return <Chip label="ERROR" color="error" size="small" />;
                    return <Chip label="PENDIENTE" color="default" size="small" />;
                },
            },
            {
                accessorKey: "_errors",
                header: "Errores",
                enableEditing: false,
                size: 200,
                Cell: ({ row }) => {
                    const errors = row.original._errors;
                    if (!errors) return null;
                    return (
                        <Tooltip title={errors}>
                            <Typography
                                variant="caption"
                                sx={{
                                    color: "error.main",
                                    whiteSpace: "nowrap",
                                    overflow: "hidden",
                                    textOverflow: "ellipsis",
                                    display: "block",
                                    maxWidth: "200px",
                                }}
                            >
                                {errors}
                            </Typography>
                        </Tooltip>
                    );
                },
            },
            {
                accessorKey: "ID",
                header: "ID",
                enableEditing: false,
                size: 80,
            },
            {
                accessorKey: "Fecha actuación",
                header: "Fecha actuación",
                size: 150,
                muiEditTextFieldProps: ({ cell, row }) => ({
                    type: "date",
                    onChange: (e) =>
                        handleChangeWithDebounce(row, cell.column.id, e.target.value),
                }),
            },
            {
                accessorKey: "Tipo actuación",
                header: "Tipo actuación",
                size: 150,
                muiEditTextFieldProps: ({ cell, row }) => ({
                    onChange: (e) =>
                        handleChangeWithDebounce(row, cell.column.id, e.target.value),
                }),
            },
            {
                accessorKey: "Contraproducencia",
                header: "Contraproducencia",
                size: 150,
                muiEditTextFieldProps: ({ cell, row }) => ({
                    onChange: (e) =>
                        handleChangeWithDebounce(row, cell.column.id, e.target.value),
                }),
            },
            {
                accessorKey: "Orden de trabajo",
                header: "Orden de trabajo",
                size: 150,
                muiEditTextFieldProps: ({ cell, row }) => ({
                    onChange: (e) =>
                        handleChangeWithDebounce(row, cell.column.id, e.target.value),
                }),
            },
            {
                accessorKey: "Inspector 1",
                header: "Inspector 1",
                size: 150,
                muiEditTextFieldProps: ({ cell, row }) => ({
                    onChange: (e) =>
                        handleChangeWithDebounce(row, cell.column.id, e.target.value),
                }),
            },
            {
                accessorKey: "Inspector 2",
                header: "Inspector 2",
                size: 150,
                muiEditTextFieldProps: ({ cell, row }) => ({
                    onChange: (e) =>
                        handleChangeWithDebounce(row, cell.column.id, e.target.value),
                }),
            },
            {
                accessorKey: "Inspector 3",
                header: "Inspector 3",
                size: 150,
                muiEditTextFieldProps: ({ cell, row }) => ({
                    onChange: (e) =>
                        handleChangeWithDebounce(row, cell.column.id, e.target.value),
                }),
            },
            {
                accessorKey: "Calle",
                header: "Calle",
                size: 200,
                muiEditTextFieldProps: ({ cell, row }) => ({
                    onChange: (e) =>
                        handleChangeWithDebounce(row, cell.column.id, e.target.value),
                }),
            },
            {
                accessorKey: "Número",
                header: "Número",
                size: 100,
                muiEditTextFieldProps: ({ cell, row }) => ({
                    onChange: (e) =>
                        handleChangeWithDebounce(row, cell.column.id, e.target.value),
                }),
            },
            {
                accessorKey: "Rubro",
                header: "Rubro",
                size: 150,
                muiEditTextFieldProps: ({ cell, row }) => ({
                    onChange: (e) =>
                        handleChangeWithDebounce(row, cell.column.id, e.target.value),
                }),
            },
            {
                accessorKey: "Apellido",
                header: "Apellido",
                size: 150,
                muiEditTextFieldProps: ({ cell, row }) => ({
                    onChange: (e) =>
                        handleChangeWithDebounce(row, cell.column.id, e.target.value),
                }),
            },
            {
                accessorKey: "Nombre",
                header: "Nombre",
                size: 150,
                muiEditTextFieldProps: ({ cell, row }) => ({
                    onChange: (e) =>
                        handleChangeWithDebounce(row, cell.column.id, e.target.value),
                }),
            },
            {
                accessorKey: "DNI",
                header: "DNI",
                size: 120,
                muiEditTextFieldProps: ({ cell, row }) => ({
                    onChange: (e) =>
                        handleChangeWithDebounce(row, cell.column.id, e.target.value),
                }),
            },
            {
                accessorKey: "Acta inspección",
                header: "Acta inspección",
                size: 150,
                muiEditTextFieldProps: ({ cell, row }) => ({
                    onChange: (e) =>
                        handleChangeWithDebounce(row, cell.column.id, e.target.value),
                }),
            },
            {
                accessorKey: "Acta notificación",
                header: "Acta notificación",
                size: 150,
                muiEditTextFieldProps: ({ cell, row }) => ({
                    onChange: (e) =>
                        handleChangeWithDebounce(row, cell.column.id, e.target.value),
                }),
            },
            {
                accessorKey: "Motivo notif 1",
                header: "Motivo notif 1",
                size: 150,
                muiEditTextFieldProps: ({ cell, row }) => ({
                    onChange: (e) =>
                        handleChangeWithDebounce(row, cell.column.id, e.target.value),
                }),
            },
            {
                accessorKey: "Motivo notif 2",
                header: "Motivo notif 2",
                size: 150,
                muiEditTextFieldProps: ({ cell, row }) => ({
                    onChange: (e) =>
                        handleChangeWithDebounce(row, cell.column.id, e.target.value),
                }),
            },
            {
                accessorKey: "Motivo notif 3",
                header: "Motivo notif 3",
                size: 150,
                muiEditTextFieldProps: ({ cell, row }) => ({
                    onChange: (e) =>
                        handleChangeWithDebounce(row, cell.column.id, e.target.value),
                }),
            },
            {
                accessorKey: "Acta comprobación",
                header: "Acta comprobación",
                size: 150,
                muiEditTextFieldProps: ({ cell, row }) => ({
                    onChange: (e) =>
                        handleChangeWithDebounce(row, cell.column.id, e.target.value),
                }),
            },
            {
                accessorKey: "Motivo comprobación",
                header: "Motivo comprobación",
                size: 180,
                muiEditTextFieldProps: ({ cell, row }) => ({
                    onChange: (e) =>
                        handleChangeWithDebounce(row, cell.column.id, e.target.value),
                }),
            },
            {
                accessorKey: "Acta clausura",
                header: "Acta clausura",
                size: 150,
                muiEditTextFieldProps: ({ cell, row }) => ({
                    onChange: (e) =>
                        handleChangeWithDebounce(row, cell.column.id, e.target.value),
                }),
            },
            {
                accessorKey: "Acta decomiso",
                header: "Acta decomiso",
                size: 150,
                muiEditTextFieldProps: ({ cell, row }) => ({
                    onChange: (e) =>
                        handleChangeWithDebounce(row, cell.column.id, e.target.value),
                }),
            },
            {
                accessorKey: "Kilos decomiso",
                header: "Kilos decomiso",
                size: 120,
                muiEditTextFieldProps: ({ cell, row }) => ({
                    type: "number",
                    onChange: (e) =>
                        handleChangeWithDebounce(row, cell.column.id, e.target.value),
                }),
            },
            {
                accessorKey: "Acta notificación previa",
                header: "Acta notificación previa",
                size: 180,
                muiEditTextFieldProps: ({ cell, row }) => ({
                    onChange: (e) =>
                        handleChangeWithDebounce(row, cell.column.id, e.target.value),
                }),
            },
            {
                accessorKey: "Acta comprobación previa",
                header: "Acta comprobación previa",
                size: 180,
                muiEditTextFieldProps: ({ cell, row }) => ({
                    onChange: (e) =>
                        handleChangeWithDebounce(row, cell.column.id, e.target.value),
                }),
            },
            {
                accessorKey: "Expediente año",
                header: "Expediente año",
                size: 130,
                muiEditTextFieldProps: ({ cell, row }) => ({
                    type: "number",
                    onChange: (e) =>
                        handleChangeWithDebounce(row, cell.column.id, e.target.value),
                }),
            },
            {
                accessorKey: "Expediente número",
                header: "Expediente número",
                size: 150,
                muiEditTextFieldProps: ({ cell, row }) => ({
                    onChange: (e) =>
                        handleChangeWithDebounce(row, cell.column.id, e.target.value),
                }),
            },
            {
                accessorKey: "Oficio año",
                header: "Oficio año",
                size: 120,
                muiEditTextFieldProps: ({ cell, row }) => ({
                    type: "number",
                    onChange: (e) =>
                        handleChangeWithDebounce(row, cell.column.id, e.target.value),
                }),
            },
            {
                accessorKey: "Oficio número",
                header: "Oficio número",
                size: 130,
                muiEditTextFieldProps: ({ cell, row }) => ({
                    onChange: (e) =>
                        handleChangeWithDebounce(row, cell.column.id, e.target.value),
                }),
            },
            {
                accessorKey: "Oficio causa",
                header: "Oficio causa",
                size: 120,
                muiEditTextFieldProps: ({ cell, row }) => ({
                    type: "number",
                    onChange: (e) =>
                        handleChangeWithDebounce(row, cell.column.id, e.target.value),
                }),
            },
        ],
        []
    );

    const table = useMaterialReactTable({
        ...TABLE_CREAR_ACTUACIONES,
        columns,
        data: data,
        initialState: {
            columnVisibility: { ID: false },
        },
        editDisplayMode: "row",
        enableEditing: true,
        onCreatingRowSave: handleCreateNewRow,
        muiTableBodyRowProps: ({ row }) => ({
            sx: getRowStyle(row),
        }),
        renderTopToolbarCustomActions: ({ table }) => (
            <Stack direction="row" spacing={2} alignItems="center">
                <TableButtonCreate table={table} />

                <Button
                    variant="contained"
                    color="primary"
                    onClick={handleStartBatch}
                    disabled={isLoadingBatch || batchId !== null}
                    startIcon={isLoadingBatch ? <CircularProgress size={16} /> : undefined}
                >
                    {batchId ? `Batch: ${batchId.slice(0, 8)}...` : "Iniciar Batch"}
                </Button>

                <Button
                    variant="outlined"
                    color="secondary"
                    onClick={handleValidateAll}
                    disabled={!batchId || isValidatingAll || data.length === 0}
                    startIcon={isValidatingAll ? <CircularProgress size={16} /> : undefined}
                >
                    Validar Todo
                </Button>

                <Button
                    variant="contained"
                    color="success"
                    onClick={handleCommitAll}
                    disabled={!batchId || isCommitting || data.length === 0}
                    startIcon={isCommitting ? <CircularProgress size={16} /> : undefined}
                >
                    Confirmar Carga
                </Button>
            </Stack>
        ),
    });

    return (
        <Box sx={{ width: "100%" }}>
            <Box sx={{ ...TableGeneralStyles }}>
                <Typography sx={TableTitleStyles}>Creación de actuación (Batch Grid)</Typography>

                {globalError && (
                    <Alert severity="error" onClose={() => setGlobalError(null)} sx={{ mb: 2 }}>
                        {globalError}
                    </Alert>
                )}

                {batchId && (
                    <Alert severity="info" sx={{ mb: 2 }}>
                        Batch activo: <strong>{batchId}</strong> | Filas:{" "}
                        {data.filter((r) => r._state === "OK").length} OK /{" "}
                        {data.filter((r) => r._state === "ERROR").length} ERROR /{" "}
                        {data.filter((r) => r._state === "PENDIENTE").length} PENDIENTE
                    </Alert>
                )}

                <MaterialReactTable table={table} />
            </Box>
        </Box>
    );
};

export default TablaCargarActuaciones;
