import { Box, Typography, IconButton, Tooltip } from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import { MaterialReactTable, useMaterialReactTable, type MRT_ColumnDef } from "material-react-table";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import { deleteActuacion, updateActuacion } from "../../../api/actuacionesApi";
import { 
  fetchInspectores, 
  fetchMotivos, 
  fetchRubros 
} from "../../../api/gridApi";
import { TablaExportButtons } from "./TableButtons";
import { GridLegend } from "./GridLegend";
import { AnimatedTable, useTableRefresh } from "../../../animations";

// Estilos Neo-Brutalistas
import {
    loadingStyles,
    DARK_TABLE_CONFIG,
    COLORS,
} from "../styles/actuacionesTableStyles";

// Opciones de dropdowns
import { DROPDOWN_ENUMS, COMPROBACION_MOTIVOS } from "../../CargarActuaciones/config/dropdownOptions";

interface TablaActuacionesProps {
    data?: IActuacionListItem[];
    loading?: boolean;
    onRefresh?: () => void;
}

/**
 * Tabla de actuaciones con edición y eliminación.
 * Muestra TODAS las columnas del grid (muchas ocultas por defecto).
 * Permite editar todos los campos como en el grid de carga.
 */
const TablaActuaciones = ({ data: externalData, loading: externalLoading, onRefresh }: TablaActuacionesProps) => {

  const [data, setData] = useState<IActuacionListItem[]>(externalData || []);
  const loading = externalLoading || false;
  
  // Animación de refresh suave
  const { isRefreshing, triggerRefresh } = useTableRefresh();
  
  // Catálogos para dropdowns
  const [catalogInspectores, setCatalogInspectores] = useState<string[]>([]);
  const [catalogMotivos, setCatalogMotivos] = useState<string[]>([]);
  const [catalogRubros, setCatalogRubros] = useState<string[]>([]);

  useEffect(() => {
    if (externalData) {
      setData(externalData);
    }
  }, [externalData]);
  
  // Cargar catálogos al montar
  useEffect(() => {
    const loadCatalogs = async () => {
      try {
        const [inspectores, motivos, rubros] = await Promise.all([
          fetchInspectores(),
          fetchMotivos(),
          fetchRubros(),
        ]);
        
        setCatalogInspectores(inspectores.items.map((i: any) => i.nombre));
        setCatalogMotivos(motivos.items.map((m: any) => m.nombre));
        setCatalogRubros(rubros.items.map((r: any) => r.nombre));
      } catch (error) {
        console.error("Error cargando catálogos:", error);
      }
    };
    
    loadCatalogs();
  }, []);

  const handleDeleteRow = useCallback(async (id: number) => {
    if (!window.confirm("¿Estás seguro de eliminar este registro?")) return;
    const prev = [...data];
    setData(prevData => prevData.filter(item => item.id !== id));
    try {
      await deleteActuacion(id);
      if (onRefresh) {
        onRefresh();
      }
    } catch (error) {
      console.error("Error al eliminar:", error);
      alert("No se pudo eliminar el registro. Se restaurará la lista.");
      setData(prev);
    }
  }, [data, onRefresh]);

  const handleSaveRow = useCallback(async ({ exitEditingMode, row, values }: any) => {
    console.log("Guardando edición:", values);
    
    // Filtrar campos: solo enviar los que no sean null/undefined/vacíos
    // Comparar con valores originales para enviar solo lo que cambió
    const originalValues = row.original;
    const changedValues: Record<string, any> = {};
    
    Object.keys(values).forEach((key) => {
      const newValue = values[key];
      const oldValue = originalValues[key];
      
      // Solo incluir si:
      // 1. El valor cambió (newValue !== oldValue)
      // 2. El valor no es null/undefined (a menos que el original tampoco lo fuera)
      if (newValue !== oldValue) {
        // Si el nuevo valor no es null/undefined, incluirlo
        if (newValue !== null && newValue !== undefined && newValue !== '') {
          changedValues[key] = newValue;
        }
        // Si el nuevo valor es null/undefined PERO el original tenía un valor, incluirlo (limpieza)
        else if (oldValue !== null && oldValue !== undefined && oldValue !== '') {
          changedValues[key] = newValue;
        }
      }
    });
    
    console.log("Campos modificados:", changedValues);
    
    // Si no hay cambios, salir sin hacer request
    if (Object.keys(changedValues).length === 0) {
      console.log("No hay cambios para guardar");
      exitEditingMode();
      return;
    }
    
    try {
      await updateActuacion(Number(row.original.id), changedValues as any);
      
      exitEditingMode();
      
      // Trigger animación suave antes de refresh
      triggerRefresh();
      
      // Pequeño delay para que se vea la animación
      setTimeout(() => {
        if (onRefresh) {
          onRefresh();
        }
      }, 100);
    } catch (error: any) {
      console.error("Error al actualizar:", error);
      const errorMsg = error?.response?.data?.detail || "No se pudo actualizar el registro.";
      alert(errorMsg);
    }
  }, [onRefresh, triggerRefresh]);

  const columns = useMemo<MRT_ColumnDef<IActuacionListItem>[]>(() => [
    {
      accessorKey: "id",
      header: "ID",
      enableHiding: true,
      enableEditing: false,
      enableClickToCopy: true,
      size: 80,
    },
    {
      accessorKey: "orden_trabajo_numero",
      header: "OT",
      enableEditing: true,
      size: 100,
      muiEditTextFieldProps: {
        required: true,
      },
    },
    {
      accessorKey: "fecha_actuacion",
      header: "Fecha",
      enableEditing: true,
      size: 120,
      muiEditTextFieldProps: {
        type: 'date',
        required: true,
      },
    },
    {
      accessorKey: "tipo_actuacion",
      header: "Tipo",
      size: 180,
      editVariant: 'select',
      editSelectOptions: DROPDOWN_ENUMS["Tipo actuación"],
      muiEditTextFieldProps: {
        select: true,
      },
    },
    {
      accessorKey: "contraproducencia",
      header: "Contraproducencia",
      size: 180,
      editVariant: 'select',
      editSelectOptions: DROPDOWN_ENUMS["Contraproducencia"], // ✅ INCLUYE NO_HUBO ahora
      muiEditTextFieldProps: {
        select: true,
      },
    },
    {
      accessorKey: "rubro_nombre",
      header: "Rubro",
      size: 200,
      editVariant: 'select',
      editSelectOptions: ["", ...catalogRubros],
      muiEditTextFieldProps: {
        select: true,
      },
    },
    {
      accessorKey: "inspector1",
      header: "Inspector 1",
      size: 150,
      editVariant: 'select',
      editSelectOptions: ["", ...catalogInspectores],
      muiEditTextFieldProps: {
        select: true,
      },
    },
    {
      accessorKey: "inspector2",
      header: "Inspector 2",
      size: 150,
      editVariant: 'select',
      editSelectOptions: ["", ...catalogInspectores],
      muiEditTextFieldProps: {
        select: true,
      },
    },
    {
      accessorKey: "inspector3",
      header: "Inspector 3",
      size: 150,
      editVariant: 'select',
      editSelectOptions: ["", ...catalogInspectores],
      muiEditTextFieldProps: {
        select: true,
      },
    },
    {
      accessorKey: "calle",
      header: "Calle",
      size: 200,
    },
    {
      accessorKey: "numero",
      header: "Número",
      size: 100,
    },
    {
      accessorKey: "doc_nro",
      header: "Doc. Nro",
      size: 120,
    },
    {
      accessorKey: "contrib_apellido",
      header: "Contribuyente Apellido",
      size: 180,
    },
    {
      accessorKey: "contrib_nombre",
      header: "Contribuyente Nombre",
      size: 180,
    },
    {
      accessorKey: "acta_inspeccion_num",
      header: "Acta Inspección",
      size: 150,
    },
    {
      accessorKey: "acta_notificacion_num",
      header: "Acta Notificación",
      size: 150,
    },
    {
      accessorKey: "notificacion_motivo_1",
      header: "Motivo Notif. 1",
      size: 180,
      editVariant: 'select',
      editSelectOptions: ["", ...catalogMotivos],
      muiEditTextFieldProps: {
        select: true,
      },
    },
    {
      accessorKey: "notificacion_motivo_2",
      header: "Motivo Notif. 2",
      size: 180,
      editVariant: 'select',
      editSelectOptions: ["", ...catalogMotivos],
      muiEditTextFieldProps: {
        select: true,
      },
    },
    {
      accessorKey: "notificacion_motivo_3",
      header: "Motivo Notif. 3",
      size: 180,
      editVariant: 'select',
      editSelectOptions: ["", ...catalogMotivos],
      muiEditTextFieldProps: {
        select: true,
      },
    },
    {
      accessorKey: "acta_comprobacion_num",
      header: "Acta Comprobación",
      size: 150,
    },
    {
      accessorKey: "comprobacion_motivo",
      header: "Motivo Comprob.",
      size: 180,
      editVariant: 'select',
      editSelectOptions: COMPROBACION_MOTIVOS,
      muiEditTextFieldProps: {
        select: true,
      },
    },
    {
      accessorKey: "acta_clausura_num",
      header: "Acta Clausura",
      size: 150,
    },
    {
      accessorKey: "acta_decomiso_num",
      header: "Acta Decomiso",
      size: 150,
    },
    {
      accessorKey: "decomiso_kilos_total",
      header: "Kilos Decomisados",
      size: 150,
    },
    {
      accessorKey: "expediente_numero",
      header: "Expediente Nro",
      size: 150,
    },
    {
      accessorKey: "expediente_anio",
      header: "Expediente Año",
      size: 120,
    },
    {
      accessorKey: "oficio_numero",
      header: "Oficio Nro",
      size: 120,
    },
    {
      accessorKey: "oficio_anio",
      header: "Oficio Año",
      size: 120,
    },
    {
      accessorKey: "oficio_causa",
      header: "Oficio Causa",
      size: 180,
    },
    {
      accessorKey: "notificacion_previa_num",
      header: "Notificación Previa",
      size: 150,
    },
    {
      accessorKey: "comprobacion_previa_num",
      header: "Comprobación Previa",
      size: 150,
    },
  ], [catalogInspectores, catalogMotivos, catalogRubros]);

  const table = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    columns,
    data,
    enableEditing: true,
    editDisplayMode: 'row',
    enableSorting: true,
    enableColumnFilters: true,
    enableGlobalFilter: true,
    enableRowActions: true,
    positionActionsColumn: 'last',
    enableHiding: true, // Permitir ocultar columnas
    initialState: {
      columnVisibility: {
        id: false,
        // Ocultar por defecto columnas menos usadas
        inspector2: false,
        inspector3: false,
        doc_nro: false,
        contrib_apellido: false,
        contrib_nombre: false,
        notificacion_motivo_2: false,
        notificacion_motivo_3: false,
        comprobacion_motivo: false,
        acta_clausura_num: false,
        acta_decomiso_num: false,
        decomiso_kilos_total: false,
        expediente_numero: false,
        expediente_anio: false,
        oficio_numero: false,
        oficio_anio: false,
        oficio_causa: false,
        notificacion_previa_num: false,
        comprobacion_previa_num: false,
      },
      density: "compact",
    },
    onEditingRowSave: handleSaveRow,
    renderRowActions: ({ row, table }) => (
      <Box sx={{ display: "flex", gap: "0.5rem" }}>
        <Tooltip title="Editar">
          <IconButton
            sx={{
              color: COLORS.white,
              transition: "color 0.2s ease, background-color 0.2s ease",
              "&:hover": {
                color: COLORS.primary,
                backgroundColor: "rgba(1, 102, 255, 0.15)",
              },
            }}
            onClick={() => table.setEditingRow(row)}
          >
            <EditIcon />
          </IconButton>
        </Tooltip>
        <Tooltip title="Eliminar">
          <IconButton
            sx={{
              color: COLORS.white,
              transition: "color 0.2s ease, background-color 0.2s ease",
              "&:hover": {
                color: "#ff4444",
                backgroundColor: "rgba(255, 68, 68, 0.15)",
              },
            }}
            onClick={() => handleDeleteRow(Number(row.original.id))}
          >
            <DeleteIcon />
          </IconButton>
        </Tooltip>
      </Box>
    ),
    renderTopToolbarCustomActions: ({ table }) => (
      <TablaExportButtons data={data} table={table} />
    ),
  });

  if (loading) {
    return (
      <Box sx={{ padding: "40px", textAlign: "center" }}>
        <Typography sx={loadingStyles}>
          Cargando actuaciones...
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      <AnimatedTable isRefreshing={isRefreshing}>
        <MaterialReactTable table={table} />
      </AnimatedTable>
      <GridLegend />
    </Box>
  );
};

export default TablaActuaciones;
