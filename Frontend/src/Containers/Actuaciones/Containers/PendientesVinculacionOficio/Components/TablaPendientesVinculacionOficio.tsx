import { useEffect, useState } from "react";
import { usePendientes } from "../../../../../hooks/usePendientes";
import type { IActuacion } from "../../../../../types/actuaciones";
import { MaterialReactTable, useMaterialReactTable, type MRT_ColumnDef } from "material-react-table";
import { BASE_TABLE_CONFIG } from "../../../../../constants/tableConfig";
import { TablaExportButtons } from "../../../Components/TableButtons";
import { TableGeneralStyles, TableLoadingStyles, TableTitleStyles } from "../../../../../styles/TablasStyle";
import { Box, Typography } from "@mui/material";
import CardsExpedientes from "../../../Components/CardsExpedientes";
import BasicModal from "./ModalPendientesOficio";

const TablaPendientesVinculacionOficio = () => {
    
    // Despues hay que colocar el get correspondiente, por ahora ponemos este
    const { pendientes, setPendientes, loading } = usePendientes();
    const [data, setData] = useState<IActuacion[]>([]);

    useEffect(() => {
        setData(pendientes ?? []);
    }, [pendientes]
    );

    const columns: MRT_ColumnDef<IActuacion>[] = [
        {
            accessorKey: "id",
            header: "ID",
            enableHiding: true,
            enableClickToCopy: true,
        },
        {
            accessorKey: "orden_trabajo_numero", header: "OT", 
        },
        {
            accessorKey: "fecha_actuacion", header: "Fecha", 
        },
        {
            accessorKey: "rubro_nombre", header: "Rubro", 
        },
        {
            accessorKey: "inspector1", header: "Inspector 1", 
        },
        {
            accessorKey: "inspector2", header: "Inspector 2", 
        },
        {
            accessorKey: "inspector3", header: "Inspector 3", 
        },
        {
            accessorKey: "calle", header: "Calle", 
        },
        {
            accessorKey: "numero", header: "Numero", 
        },
        {
            accessorKey: "tipo_actuacion", header: "Tipo de Actuacion", 
        },
        {
            accessorKey: "contraproducencia", header: "Contraproducencia", 
        },
        {
            accessorKey: "doc_tipo_codigo", header: "Tipo de Documento", 
        },
        {
            accessorKey: "doc_nro", header: "Numero de Documento", 
        },
        {
            accessorKey: "contrib_apellido", header: "Apellido Contribuidor", 
        },
        {
            accessorKey: "contrib_nombre", header: "Nombre Contribuidor", 
        },
        {
            accessorKey: "acta_inspeccion_num", header: "Acta Inspeccion", 
        },
        {
            accessorKey: "acta_notificacion_num", header: "Acta Notificacion", 
        },
        {
            accessorKey: "notificacion_motivo_1", header: "Motivo 1", 
        },
        {
            accessorKey: "notificacion_motivo_2", header: "Motivo 2", 
        },
        {
            accessorKey: "notificacion_motivo_3", header: "Motivo 3", 
        },
        {
            accessorKey: "acta_comprobacion_num", header: "Acta Comprobacion", 
        },
        {
            accessorKey: "comprobacion_motivo", header: "Comprobacion Motivo", 
        },
        {
            accessorKey: "acta_clausura_num", header: "Acta Clausura", 
        },
        {
            accessorKey: "clausura_motivo", header: "Clausura Motivo", 
        },
        {
            accessorKey: "acta_decomiso_num", header: "Acta Decomiso", 
        },
        {
            accessorKey: "decomiso_kilos_total", header: "Kilos Decomisados", 
        },
        {
            accessorKey: "expediente_numero", header: "Expediente", 
        },
        {
            accessorKey: "expediente_anio", header: "Año de Expediente", 
        },
        {
            accessorKey: "oficio_numero", header: "Oficio", 
        },
        {
            accessorKey: "oficio_anio", header: "Año de Oficio", 
        },
        {
            accessorKey: "oficio_causa", header: "Causa de Oficio", 
        },
        {
            accessorKey: "notificacion_previa_num", header: "Notificacion Previa", 
        },
        {
            accessorKey: "comprobacion_previa_num", header: "Comprobacion Previa", 
        },
    ]

    const table = useMaterialReactTable({
        ...BASE_TABLE_CONFIG,
        columns,
        data,
        enableEditing: false,
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
                <Typography sx={TableTitleStyles}>Gestión de Pendientes de Vinculacion con Oficio</Typography>
                <CardsExpedientes />
                <BasicModal/>
                <MaterialReactTable table={table} />
            </Box>
        </Box>
    );
};

export default TablaPendientesVinculacionOficio;