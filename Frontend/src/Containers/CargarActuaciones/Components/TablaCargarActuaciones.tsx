import {
    MaterialReactTable,
    useMaterialReactTable,
    type MRT_ColumnDef,
    type MRT_Row,
    type MRT_TableOptions,
} from "material-react-table";
import { validateActuacion } from "../../../utils/validations";
import { useMemo, useRef, useState } from "react";
import { createActuacion } from "../../../api/actuacionesApi";
import type { IActuacion } from "../../../types/actuaciones";
import { Box, Typography } from "@mui/material";
import { TableGeneralStyles, TableTitleStyles } from "../../../styles/TablasStyle";
import { TABLE_CREAR_ACTUACIONES } from "../../../constants/tableConfig";
import { TableButtonCreate } from "../../CargarActuaciones/Components/TableButtonCreate";

const TablaCargarActuaciones = () => {
    const [validationErrors, setValidationErrors] = useState<Record<string, string | undefined>>({});
    const [data, setData] = useState<IActuacion[]>([]);

    const debounceRef = useRef<number | null>(null);

    const handleChangeWithDebounce = (
        row: any,
        columnId: string,
        value: any
    ) => {
        // Guardar el valor en el _valuesCache primero
        row._valuesCache[columnId] = value;

        // Debounce
        if (debounceRef.current !== null) {
            clearTimeout(debounceRef.current);
        }

        debounceRef.current = window.setTimeout(() => {
            validateRow(row);
        }, 300);
    };


    const validateRow = (row: MRT_Row<IActuacion>) => {
        setValidationErrors(validateActuacion(row._valuesCache));
    };
    
    const emptyStringsToNull = <T extends object>(obj: T): T => {
        const result = {} as T;
        (Object.keys(obj) as (keyof T)[]).forEach((key) => {
            const v = obj[key];
            result[key] = (v === "" ? (null as any) : v) as T[typeof key];
        });
        return result;
    };


    const handleCreateNewRow: MRT_TableOptions<IActuacion>["onCreatingRowSave"] =
        async ({ values, table }) => {

            console.log("VALUES RECIBIDOS:", values);

            const errors = validateActuacion(values as IActuacion);
            console.log("ERRORES:", errors);

            if (Object.values(errors).some((e) => e)) {
                console.log("❌ Bloqueado por validación");
                setValidationErrors(errors);
                return;
            }

            try {
                console.log("➡️ Enviando al backend...");
                const payload = emptyStringsToNull(values as any );
                const nuevaActuacion = await createActuacion(payload);
                console.log("✔ RESPUESTA:", nuevaActuacion);

                table.setCreatingRow(null);
                setValidationErrors({});
                setData(prev => [...prev, nuevaActuacion]);

                setTimeout(() => table.setCreatingRow(true), 50);

            } catch (error) {
                console.error("❌ Error en petición:", error);
            }
        };

    const columns = useMemo<MRT_ColumnDef<IActuacion>[]>(() => [
        {
            accessorKey: "id",
            header: "ID",
            enableEditing: false,
        },
        {
            accessorKey: "orden_trabajo_numero",
            header: "OT",
            muiEditTextFieldProps: ({ cell, row }) => ({
                autoFocus: cell.column.id === "orden_trabajo_numero",
                error: !!validationErrors[cell.column.id],
                helperText: validationErrors[cell.column.id],
                onChange: (e) => {
                    row._valuesCache[cell.column.id] = e.target.value;
                    handleChangeWithDebounce(
                        row,
                        cell.column.id,
                        e.target.value
                    );
                },
            }),
        },
        {
            accessorKey: "fecha_actuacion",
            header: "Fecha (DD/MM/YY)",
            muiEditTextFieldProps: ({ cell, row }) => ({
                type: "date",
                error: !!validationErrors[cell.column.id],
                helperText: validationErrors[cell.column.id],
                onChange: (e) => {
                    row._valuesCache[cell.column.id] = e.target.value;
                    handleChangeWithDebounce(
                        row,
                        cell.column.id,
                        e.target.value
                    );
                },
            }),
        },
        {
            accessorKey: "rubro_nombre",
            header: "Rubro",
            muiEditTextFieldProps: ({ cell, row }) => ({
                error: !!validationErrors[cell.column.id],
                helperText: validationErrors[cell.column.id],
                onChange: (e) => {
                    row._valuesCache[cell.column.id] = e.target.value;
                    handleChangeWithDebounce(
                        row,
                        cell.column.id,
                        e.target.value
                    );
                },
            }),
        },
        {
            accessorKey: "inspector1",
            header: "Inspector 1",
            muiEditTextFieldProps: ({ cell, row }) => ({
                error: !!validationErrors[cell.column.id],
                helperText: validationErrors[cell.column.id],
                onChange: (e) => {
                    row._valuesCache[cell.column.id] = e.target.value;
                    handleChangeWithDebounce(
                        row,
                        cell.column.id,
                        e.target.value
                    );
                },
            }),
        },
        {
            accessorKey: "inspector2",
            header: "Inspector 2",
            muiEditTextFieldProps: ({ cell, row }) => ({
                error: !!validationErrors[cell.column.id],
                helperText: validationErrors[cell.column.id],
                onChange: (e) => {
                    row._valuesCache[cell.column.id] = e.target.value;
                    handleChangeWithDebounce(
                        row,
                        cell.column.id,
                        e.target.value
                    );
                },
            }),
        },
        {
            accessorKey: "inspector3",
            header: "Inspector 3",
            muiEditTextFieldProps: ({ cell, row }) => ({
                error: !!validationErrors[cell.column.id],
                helperText: validationErrors[cell.column.id],
                onChange: (e) => {
                    row._valuesCache[cell.column.id] = e.target.value;
                    handleChangeWithDebounce(
                        row,
                        cell.column.id,
                        e.target.value
                    );
                },
            }),
        },
        {
            accessorKey: "calle",
            header: "Calle",
            muiEditTextFieldProps: ({ cell, row }) => ({
                error: !!validationErrors[cell.column.id],
                helperText: validationErrors[cell.column.id],
                onChange: (e) => {
                    row._valuesCache[cell.column.id] = e.target.value;
                    handleChangeWithDebounce(
                        row,
                        cell.column.id,
                        e.target.value
                    );
                },
            }),
        },
        {
            accessorKey: "numero",
            header: "Número",
            muiEditTextFieldProps: ({ cell, row }) => ({
                error: !!validationErrors[cell.column.id],
                helperText: validationErrors[cell.column.id],
                onChange: (e) => {
                    row._valuesCache[cell.column.id] = e.target.value;
                    handleChangeWithDebounce(
                        row,
                        cell.column.id,
                        e.target.value
                    );
                },
            }),
        },
        {
            accessorKey: "tipo_actuacion",
            header: "Tipo de actuación",
            muiEditTextFieldProps: ({ cell, row }) => ({
                error: !!validationErrors[cell.column.id],
                helperText: validationErrors[cell.column.id],
                onChange: (e) => {
                    row._valuesCache[cell.column.id] = e.target.value;
                    handleChangeWithDebounce(
                        row,
                        cell.column.id,
                        e.target.value
                    );
                },
            }),
        },
        {
            accessorKey: "contraproducencia",
            header: "Contraproducencia",
            muiEditTextFieldProps: ({ cell, row }) => ({
                error: !!validationErrors[cell.column.id],
                helperText: validationErrors[cell.column.id],
                onChange: (e) => {
                    row._valuesCache[cell.column.id] = e.target.value;
                    handleChangeWithDebounce(
                        row,
                        cell.column.id,
                        e.target.value
                    );
                },
            }),
        },
        {
            accessorKey: "doc_tipo_codigo",
            header: "Tipo de Documento",
            muiEditTextFieldProps: ({ cell, row }) => ({
                error: !!validationErrors[cell.column.id],
                helperText: validationErrors[cell.column.id],
                onChange: (e) => {
                    row._valuesCache[cell.column.id] = e.target.value;
                    handleChangeWithDebounce(
                        row,
                        cell.column.id,
                        e.target.value
                    );
                },
            }),
        },
        {
            accessorKey: "doc_nro",
            header: "Num de Documento",
            muiEditTextFieldProps: ({ cell, row }) => ({
                error: !!validationErrors[cell.column.id],
                helperText: validationErrors[cell.column.id],
                onChange: (e) => {
                    row._valuesCache[cell.column.id] = e.target.value;
                    handleChangeWithDebounce(
                        row,
                        cell.column.id,
                        e.target.value
                    );
                },
            }),
        },
        {
            accessorKey: "contrib_apellido",
            header: "Apellido Contribuyente",
            muiEditTextFieldProps: ({ cell, row }) => ({
                error: !!validationErrors[cell.column.id],
                helperText: validationErrors[cell.column.id],
                onChange: (e) => {
                    row._valuesCache[cell.column.id] = e.target.value;
                    handleChangeWithDebounce(
                        row,
                        cell.column.id,
                        e.target.value
                    );
                },
            }),
        },
        {
            accessorKey: "contrib_nombre",
            header: "Nombre Contribuyente",
            muiEditTextFieldProps: ({ cell, row }) => ({
                error: !!validationErrors[cell.column.id],
                helperText: validationErrors[cell.column.id],
                onChange: (e) => {
                    row._valuesCache[cell.column.id] = e.target.value;
                    handleChangeWithDebounce(
                        row,
                        cell.column.id,
                        e.target.value
                    );
                },
            }),
        },
        {
            accessorKey: "acta_inspeccion_num",
            header: "Acta inspección",
            muiEditTextFieldProps: ({ cell, row }) => ({
                error: !!validationErrors[cell.column.id],
                helperText: validationErrors[cell.column.id],
                onChange: (e) => {
                    row._valuesCache[cell.column.id] = e.target.value;
                    handleChangeWithDebounce(
                        row,
                        cell.column.id,
                        e.target.value
                    );
                },
            }),
        },
        {
            accessorKey: "acta_notificacion_num",
            header: "Acta Notificación",
            muiEditTextFieldProps: ({ cell, row }) => ({
                error: !!validationErrors[cell.column.id],
                helperText: validationErrors[cell.column.id],
                onChange: (e) => {
                    row._valuesCache[cell.column.id] = e.target.value;
                    handleChangeWithDebounce(
                        row,
                        cell.column.id,
                        e.target.value
                    );
                },
            }),
        },
        {
            accessorKey: "notificacion_motivo_1",
            header: "Motivo Notificación 1",
            muiEditTextFieldProps: ({ cell, row }) => ({
                error: !!validationErrors[cell.column.id],
                helperText: validationErrors[cell.column.id],
                onChange: (e) => {
                    row._valuesCache[cell.column.id] = e.target.value;
                    handleChangeWithDebounce(
                        row,
                        cell.column.id,
                        e.target.value
                    );
                },
            }),
        },
        {
            accessorKey: "notificacion_motivo_2",
            header: "Motivo Notificación 2",
            muiEditTextFieldProps: ({ cell, row }) => ({
                error: !!validationErrors[cell.column.id],
                helperText: validationErrors[cell.column.id],
                onChange: (e) => {
                    row._valuesCache[cell.column.id] = e.target.value;
                    handleChangeWithDebounce(
                        row,
                        cell.column.id,
                        e.target.value
                    );
                },
            }),
        },
        {
            accessorKey: "notificacion_motivo_3",
            header: "Motivo Notificación 3",
            muiEditTextFieldProps: ({ cell, row }) => ({
                error: !!validationErrors[cell.column.id],
                helperText: validationErrors[cell.column.id],
                onChange: (e) => {
                    row._valuesCache[cell.column.id] = e.target.value;
                    handleChangeWithDebounce(
                        row,
                        cell.column.id,
                        e.target.value
                    );
                },
            }),
        },
        {
            accessorKey: "acta_comprobacion_num",
            header: "Acta Comprobación",
            muiEditTextFieldProps: ({ cell, row }) => ({
                error: !!validationErrors[cell.column.id],
                helperText: validationErrors[cell.column.id],
                onChange: (e) => {
                    row._valuesCache[cell.column.id] = e.target.value;
                    handleChangeWithDebounce(
                        row,
                        cell.column.id,
                        e.target.value
                    );
                },
            }),
        },
        {
            accessorKey: "comprobacion_motivo",
            header: "Motivo Comprobación",
            muiEditTextFieldProps: ({ cell, row }) => ({
                error: !!validationErrors[cell.column.id],
                helperText: validationErrors[cell.column.id],
                onChange: (e) => {
                    row._valuesCache[cell.column.id] = e.target.value;
                    handleChangeWithDebounce(
                        row,
                        cell.column.id,
                        e.target.value
                    );
                },
            }),
        },
        {
            accessorKey: "acta_clausura_num",
            header: "Acta Clausura",
            muiEditTextFieldProps: ({ cell, row }) => ({
                error: !!validationErrors[cell.column.id],
                helperText: validationErrors[cell.column.id],
                onChange: (e) => {
                    row._valuesCache[cell.column.id] = e.target.value;
                    handleChangeWithDebounce(
                        row,
                        cell.column.id,
                        e.target.value
                    );
                },
            }),
        },
        {
            accessorKey: "clausura_motivo",
            header: "Motivo Clausura",
            muiEditTextFieldProps: ({ cell, row }) => ({
                error: !!validationErrors[cell.column.id],
                helperText: validationErrors[cell.column.id],
                onChange: (e) => {
                    row._valuesCache[cell.column.id] = e.target.value;
                    handleChangeWithDebounce(
                        row,
                        cell.column.id,
                        e.target.value
                    );
                },
            }),
        },
        {
            accessorKey: "acta_decomiso_num",
            header: "Acta Decomiso",
            muiEditTextFieldProps: ({ cell, row }) => ({
                error: !!validationErrors[cell.column.id],
                helperText: validationErrors[cell.column.id],
                onChange: (e) => {
                    row._valuesCache[cell.column.id] = e.target.value;
                    handleChangeWithDebounce(
                        row,
                        cell.column.id,
                        e.target.value
                    );
                },
            }),
        },
        {
            accessorKey: "decomiso_kilos_total",
            header: "KG Decomiso",
            muiEditTextFieldProps: ({ cell, row }) => ({
                type: "number",
                error: !!validationErrors[cell.column.id],
                helperText: validationErrors[cell.column.id],
                onChange: (e) => {
                    row._valuesCache[cell.column.id] = e.target.value;
                    handleChangeWithDebounce(
                        row,
                        cell.column.id,
                        e.target.value
                    );
                },
            }),
        },
        {
            accessorKey: "expediente_numero",
            header: "Expediente Número",
            muiEditTextFieldProps: ({ cell, row }) => ({
                error: !!validationErrors[cell.column.id],
                helperText: validationErrors[cell.column.id],
                onChange: (e) => {
                    row._valuesCache[cell.column.id] = e.target.value;
                    handleChangeWithDebounce(
                        row,
                        cell.column.id,
                        e.target.value
                    );
                },
            }),
        },
        {
            accessorKey: "expediente_anio",
            header: "Expediente Año",
            muiEditTextFieldProps: ({ cell, row }) => ({
                type: "number",
                error: !!validationErrors[cell.column.id],
                helperText: validationErrors[cell.column.id],
                onChange: (e) => {
                    row._valuesCache[cell.column.id] = e.target.value;
                    handleChangeWithDebounce(
                        row,
                        cell.column.id,
                        e.target.value
                    );
                },
            }),
        },
        {
            accessorKey: "oficio_numero",
            header: "Oficio Numero",
            muiEditTextFieldProps: ({ cell, row }) => ({
                error: !!validationErrors[cell.column.id],
                helperText: validationErrors[cell.column.id],
                onChange: (e) => {
                    row._valuesCache[cell.column.id] = e.target.value;
                    handleChangeWithDebounce(
                        row,
                        cell.column.id,
                        e.target.value
                    );
                },
            }),
        },
        {
            accessorKey: "oficio_anio",
            header: "Oficio Año",
            muiEditTextFieldProps: ({ cell, row }) => ({
                type: "number",
                error: !!validationErrors[cell.column.id],
                helperText: validationErrors[cell.column.id],
                onChange: (e) => {
                    row._valuesCache[cell.column.id] = e.target.value;
                    handleChangeWithDebounce(
                        row,
                        cell.column.id,
                        e.target.value
                    );
                },
            }),
        },
        {
            accessorKey: "oficio_causa",
            header: "Oficio Causa",
            muiEditTextFieldProps: ({ cell, row }) => ({
                type: "number",
                error: !!validationErrors[cell.column.id],
                helperText: validationErrors[cell.column.id],
                onChange: (e) => {
                    row._valuesCache[cell.column.id] = e.target.value;
                    handleChangeWithDebounce(
                        row,
                        cell.column.id,
                        e.target.value
                    );
                },
            }),
        },
        {
            accessorKey: "notificacion_previa_num",
            header: "Notificacion Previa",
            muiEditTextFieldProps: ({ cell, row }) => ({
                error: !!validationErrors[cell.column.id],
                helperText: validationErrors[cell.column.id],
                onChange: (e) => {
                    row._valuesCache[cell.column.id] = e.target.value;
                    handleChangeWithDebounce(
                        row,
                        cell.column.id,
                        e.target.value
                    );
                },
            }),
        },
        {
            accessorKey: "comprobacion_previa_num",
            header: "Comprobacion Previa",
            muiEditTextFieldProps: ({ row, cell, table }) => ({
                error: !!validationErrors[cell.column.id],
                helperText: validationErrors[cell.column.id],
                onChange: (e) => {
                    row._valuesCache[cell.column.id] = e.target.value;
                    handleChangeWithDebounce(
                        row,
                        cell.column.id,
                        e.target.value
                    );
                },
                // ENTER ENVIA AUTOMATICAMENTE
                onKeyDown: (e) => {
                    if (e.key === "Enter") {
                        table.options.onCreatingRowSave?.({
                            values: row.getAllCells().reduce((acc, c) => {
                                acc[c.column.id] = row._valuesCache[c.column.id];
                                return acc;
                            }, {} as any),
                            table,
                        } as any);
                    }
                },
            }),
        },
    ], [validationErrors])

    const table = useMaterialReactTable({
        ...TABLE_CREAR_ACTUACIONES,
        columns,
        data: data,
        initialState: {
            columnVisibility: { id: false },
        },
        editDisplayMode: "row",
        enableEditing: true,
        onCreatingRowSave: handleCreateNewRow,
        renderTopToolbarCustomActions: ({ table }) => (
            <TableButtonCreate table={table} />
        ),
    });



    return (
        <Box sx={{ width: "100%" }}>
            <Box sx={{ ...TableGeneralStyles, }}>
                <Typography sx={TableTitleStyles}>Creación de actuación</Typography>
                <MaterialReactTable table={table} />
            </Box>
        </Box>
    );
};

export default TablaCargarActuaciones;