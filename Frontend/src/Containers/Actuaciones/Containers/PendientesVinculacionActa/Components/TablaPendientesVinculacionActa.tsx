import { MaterialReactTable, useMaterialReactTable, type MRT_ColumnDef } from "material-react-table";
import type { IActuacion } from "../../../../../types/actuaciones";
import { BASE_TABLE_CONFIG } from "../../../../../constants/tableConfig";
import { TablaExportButtons } from "../../../Components/TableButtons";
import { Box, Typography } from "@mui/material";
import { TableGeneralStyles, TableLoadingStyles, TableTitleStyles } from "../../../../../styles/TablasStyle";
import CardsExpedientes from "../../../Components/CardsExpedientes";
import { useCallback, useEffect, useState } from "react";
import { usePendientes } from "../../../../../hooks/usePendientes";
import { updateActuacion } from "../../../../../api/actuacionesApi";

const TablaPendientesVinculacionActa = () => {

    // Despues hay que colocar el get correspondiente, por ahora ponemos este
    const { pendientes, setPendientes, loading } = usePendientes();
    const [data, setData] = useState<IActuacion[]>([]);

    useEffect(() => {
        setData(pendientes ?? []);
    }, [pendientes]
    );

    const handleEditCell = useCallback(
        async (id: number, key: keyof IActuacion, value: any) => {
            let updatedRow: IActuacion | undefined;
            setData((prev) => {
                const idx = prev.findIndex((r) => r.id === id);
                if (idx === -1) return prev;
                updatedRow = { ...prev[idx], [key]: value }; // guardamos fila actualizada
                const newData = [...prev];
                newData[idx] = updatedRow!;
                return newData;
            });

            if (!updatedRow) return;

            const payload: IActuacion = {
                ...updatedRow,
            };

            //  Validación 
            if (!payload.expediente_numero || !payload.expediente_anio) {
                alert("Algunos campos no son válidos. Corrigelos antes de guardar.");
                return;
            }

            // Llamada Axios
            try {
                await updateActuacion(id, payload);
            } catch (error) {
                console.error("Error al actualizar:", error);
                alert("No se pudo actualizar el registro.");
            }
        },
        []
    );

    const columns: MRT_ColumnDef<IActuacion>[] = [
        {
            accessorKey: "id",
            header: "ID",
            enableHiding: true,
            enableEditing: false,
            enableClickToCopy: true,
        },
        {
            accessorKey: "orden_trabajo_numero", header: "OT", enableEditing: false
        },
        {
            accessorKey: "fecha_actuacion", header: "Fecha", enableEditing: false
        },
        {
            accessorKey: "rubro_nombre", header: "Rubro", enableEditing: false
        },
        {
            accessorKey: "inspector1", header: "Inspector 1", enableEditing: false
        },
        {
            accessorKey: "inspector2", header: "Inspector 2", enableEditing: false
        },
        {
            accessorKey: "inspector3", header: "Inspector 3", enableEditing: false
        },
        {
            accessorKey: "calle", header: "Calle", enableEditing: false
        },
        {
            accessorKey: "numero", header: "Numero", enableEditing: false
        },
        {
            accessorKey: "tipo_actuacion", header: "Tipo de Actuacion", enableEditing: false
        },
        {
            accessorKey: "contraproducencia", header: "Contraproducencia", enableEditing: false
        },
        {
            accessorKey: "doc_tipo_codigo", header: "Tipo de Documento", enableEditing: false
        },
        {
            accessorKey: "doc_nro", header: "Numero de Documento", enableEditing: false
        },
        {
            accessorKey: "contrib_apellido", header: "Apellido Contribuidor", enableEditing: false
        },
        {
            accessorKey: "contrib_nombre", header: "Nombre Contribuidor", enableEditing: false
        },
        {
            accessorKey: "acta_inspeccion_num", header: "Acta Inspeccion", enableEditing: false
        },
        {
            accessorKey: "acta_notificacion_num", header: "Acta Notificacion", enableEditing: false
        },
        {
            accessorKey: "notificacion_motivo_1", header: "Motivo 1", enableEditing: false
        },
        {
            accessorKey: "notificacion_motivo_2", header: "Motivo 2", enableEditing: false
        },
        {
            accessorKey: "notificacion_motivo_3", header: "Motivo 3", enableEditing: false
        },
        {
            accessorKey: "acta_comprobacion_num", header: "Acta Comprobacion", enableEditing: false
        },
        {
            accessorKey: "comprobacion_motivo", header: "Comprobacion Motivo", enableEditing: false
        },
        {
            accessorKey: "acta_clausura_num", header: "Acta Clausura", enableEditing: false
        },
        {
            accessorKey: "clausura_motivo", header: "Clausura Motivo", enableEditing: false
        },
        {
            accessorKey: "acta_decomiso_num", header: "Acta Decomiso", enableEditing: false
        },
        {
            accessorKey: "decomiso_kilos_total", header: "Kilos Decomisados", enableEditing: false
        },
        {
            accessorKey: "expediente_numero", header: "Expediente",
            muiEditTextFieldProps: ({ row }) => ({
                onBlur: (e) => handleEditCell(row.original.id, "expediente_numero", e.target.value),
            })
        },
        {
            accessorKey: "expediente_anio", header: "Año de Expediente",
            muiEditTextFieldProps: ({ row }) => ({
                onBlur: (e) => handleEditCell(row.original.id, "expediente_anio", e.target.value),
            })
        },
        {
            accessorKey: "oficio_numero", header: "Oficio", enableEditing: false
        },
        {
            accessorKey: "oficio_anio", header: "Año de Oficio", enableEditing: false
        },
        {
            accessorKey: "oficio_causa", header: "Causa de Oficio", enableEditing: false
        },
        {
            accessorKey: "notificacion_previa_num", header: "Notificacion Previa", enableEditing: false
        },
        {
            accessorKey: "comprobacion_previa_num", header: "Comprobacion Previa", enableEditing: false
        },
    ]

    const table = useMaterialReactTable({
        ...BASE_TABLE_CONFIG,
        columns,
        data,
        initialState: {
            columnVisibility: {
                id: false, rubro_nombre: false,
                inspector1: false, inspector2: false,
                inspector3: false, tipo_actuacion: false,
                contraproducencia: false, doc_tipo_codigo: false,
                doc_nro: false, contrib_apellido: false,
                contrib_nombre: false, acta_inspeccion_num: false,
                notificacion_motivo_1: false, notificacion_motivo_2: false,
                notificacion_motivo_3: false,
                comprobacion_motivo: false, acta_clausura_num: false,
                clausura_motivo: false, acta_decomiso_num: false,
                decomiso_kilos_total: false, oficio_numero: false,
                calle: false, numero: false,
                oficio_anio: false, oficio_causa: false, acta_notificacion_num: false,
                notificacion_previa_num: false, comprobacion_previa_num: false
            },

        },
        renderTopToolbarCustomActions: ({ table }) => (
            <TablaExportButtons data={data} table={table} />
        ),
    });

    if (loading) return <Typography sx={TableLoadingStyles}>Cargando Pendientes...</Typography>;

    return (
        <Box sx={{ width: "100%" }}>
            <Box
                sx={{
                    ...TableGeneralStyles,
                    "& .MuiBox-root.css-wsew38": {
                        display: "flex",
                        flexDirection: { xs: "column", md: "row" },
                        gap: 2,
                    },
                }}
            >
                <Typography sx={TableTitleStyles}>Gestión de Pendientes de Vinculacion con Acta</Typography>
                <CardsExpedientes />
                <MaterialReactTable table={table} />
            </Box>
        </Box>
    );
};

export default TablaPendientesVinculacionActa;