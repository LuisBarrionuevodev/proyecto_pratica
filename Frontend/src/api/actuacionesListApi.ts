import { apiClient } from "./apiClient";

// ============= TYPES =============

/**
 * Tipo completo para una actuación (formato grid con todas las columnas)
 */
export interface IActuacionListItem {
    id: number;
    orden_trabajo_numero: string | null;
    fecha_actuacion: string | null;
    rubro_nombre: string | null;
    inspector1: string | null;
    inspector2: string | null;
    inspector3: string | null;
    calle: string | null;
    numero: string | null;
    numero_esquina?: string | null;
    numero_tipo?: string | null;
    calle_ingresada?: string | null;
    tipo_actuacion: string | null;
    contraproducencia: string | null;
    /** Presente en respuesta API (reinspección por oficio, etc.). */
    resultado_cumplimiento_oficio?: string | null;
    doc_nro: string | null;
    contrib_apellido: string | null;
    contrib_nombre: string | null;
    acta_inspeccion_num: string | null;
    acta_notificacion_num: string | null;
    notificacion_motivo_1: string | null;
    notificacion_motivo_2: string | null;
    notificacion_motivo_3: string | null;
    acta_comprobacion_num: string | null;
    comprobacion_motivo: string | null;
    acta_clausura_num: string | null;
    acta_decomiso_num: string | null;
    decomiso_kilos_total: number | null;
    expediente_numero: string | null;
    expediente_anio: number | null;
    oficio_numero: string | null;
    oficio_anio: number | null;
    oficio_causa: string | null;
    /** Presente en respuesta API; opcional en UI de bandeja. */
    nombre_local?: string | null;
    notificacion_previa_num: string | null;
    comprobacion_previa_num: string | null;
    domicilio_id?: number | null;
    calle_normalizada?: string | null;
    esquina_normalizada?: string | null;
    esquina_catalogo_id?: number | null;
    esquina_status?: string | null;
    esquina_score?: number | null;
    calle_estado?: string | null;
    calle_score?: number | null;
    calle_sugerida?: string | null;
    calle_mostrar?: string | null;
    calle_catalogo_id?: number | null;
    /** false si la notificación ya tiene expediente(s); la grilla no debe editar esos campos. */
    notificacion_editable?: boolean;
    /** false si la comprobación ya tiene expediente de envío. */
    comprobacion_editable?: boolean;
}

export interface IActuacionesListMeta {
    total: number;
    page: number;
    page_size: number;
    desde: string | null;
    hasta: string | null;
    tipo: string | null;
    contraproducencia: string | null;
    orden_trabajo: string | null;
}

export interface IActuacionesListResponse {
    items: IActuacionListItem[];
    meta: IActuacionesListMeta;
}

export interface IActuacionesListFilters {
    desde?: string | null;
    hasta?: string | null;
    tipo?: string | null;
    contraproducencia?: string | null;
    orden_trabajo?: string | null;
    page?: number;
    page_size?: number;
}

// ============= API FUNCTIONS =============

/**
 * Lista actuaciones con filtros opcionales.
 * 
 * @param filters - Filtros de búsqueda (desde, hasta, tipo, etc.)
 * @returns Lista de actuaciones con metadata de paginación
 */
export const getActuacionesFiltered = async (
    filters?: IActuacionesListFilters
): Promise<IActuacionesListResponse> => {
    const params: Record<string, string> = {};
    
    if (filters?.desde) params.desde = filters.desde;
    if (filters?.hasta) params.hasta = filters.hasta;
    if (filters?.tipo) params.tipo = filters.tipo;
    if (filters?.contraproducencia) params.contraproducencia = filters.contraproducencia;
    if (filters?.orden_trabajo) params.orden_trabajo = filters.orden_trabajo;
    if (filters?.page) params.page = String(filters.page);
    if (filters?.page_size) params.page_size = String(filters.page_size);

    const { data } = await apiClient.get<IActuacionesListResponse>("/actuaciones", { params });
    return data;
};
