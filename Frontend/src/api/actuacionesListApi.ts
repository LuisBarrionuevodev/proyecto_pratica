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
    /** Lista canónica de nombres (misma semántica que PUT); sin tope de cantidad. */
    inspectores?: string[] | null;
    /** Nombres concatenados (presenter); útil para tabla/exportación. */
    inspectores_texto?: string | null;
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
    /** Persona jurídica; editable en canal actas; persiste en contribuyente. */
    razon_social?: string | null;
    /** EpiCollect5; solo lectura en UI; no se envía en PUT canal actas. */
    ec5_uuid?: string | null;
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
    /** Ficha operativa (mismo domicilio canónico); null si aún no vinculada. */
    establecimiento_operativo_id?: number | null;
    /** Cantidad de actuaciones con la misma ficha (incluye la actual). */
    establecimiento_actuaciones_en_ficha?: number | null;
    /** Snapshot no-media importado desde EpiCollect (`actuacion_epicollect_detalle`). */
    has_epicollect_detalle?: boolean;
    /** Cantidad de claves en `payload_non_media.data` (sin campos de media). */
    epicollect_non_media_field_count?: number;
    /** Sectores / condiciones (SI-NO) con etiquetas legibles; solo claves con valor. */
    epicollect_sectores_condiciones?: { field_id: string; label: string; value_preview: string }[];
    /** Resto de campos no-media, orden alfabético por field_id. */
    epicollect_otros_preview?: { field_id: string; value_preview: string }[];
    /** Compat: primeras 5 de `epicollect_otros_preview`. */
    epicollect_preview?: { field_id: string; value_preview: string }[];
    /** Medios importados desde EpiCollect, agrupados por `categoria` (solo `epicollect.*`). */
    epicollect_evidencias_total?: number;
    epicollect_evidencias_grupos?: {
        categoria: string;
        label: string;
        count: number;
        items: { url: string; orden: number; mime_type?: string | null }[];
    }[];

    /** F2.2 — contexto documental (solo lectura; coherente con backend). */
    documentacion_contexto?: {
        circuito:
            | "COMUN_NOTIFICACION"
            | "COMUN_COMPROBACION"
            | "REINSPECCION_OFICIO"
            | "REINSPECCION_NOTIFICACION"
            | "DESCONOCIDO";
        propia: {
            expediente_numero?: string | null;
            expediente_anio?: string | number | null;
            notificacion_plazo_dias?: number | null;
            notificacion_prorroga_dias?: number | null;
            notificacion_fecha_vencimiento?: string | null;
        };
    };
    origen_reinspeccion_oficio?: {
        comprobacion_acta_numero?: string | null;
        comprobacion_acta_anio?: number | null;
        expediente_numero?: string | null;
        expediente_anio?: string | number | null;
        oficio_numero?: string | null;
        oficio_anio?: number | null;
        oficio_causa?: string | null;
    } | null;
    origen_reinspeccion_notificacion?: {
        notificacion_acta_numero?: string | null;
        notificacion_acta_anio?: number | null;
        expediente_numero?: string | null;
        expediente_anio?: string | number | null;
        plazo_dias?: number | null;
        prorroga_dias?: number | null;
        fecha_vencimiento?: string | null;
    } | null;
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
    actuacion_id?: number | null;
    q?: string | null;
    busqueda_global?: boolean;
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
    actuacion_id?: number | null;
    q?: string | null;
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
    if (filters?.actuacion_id) params.actuacion_id = String(filters.actuacion_id);
    if (filters?.q) params.q = filters.q;
    if (filters?.page) params.page = String(filters.page);
    if (filters?.page_size) params.page_size = String(filters.page_size);

    const { data } = await apiClient.get<IActuacionesListResponse>("/actuaciones", { params });
    return data;
};

export const ACTA_CANAL_QUITAR_TIPOS = ["INSPECCION", "NOTIFICACION", "COMPROBACION", "CLAUSURA", "DECOMISO"] as const;
export type ActaCanalQuitarTipo = (typeof ACTA_CANAL_QUITAR_TIPOS)[number];

/** Quita un acta operativa vinculada (POST canal actas). Devuelve la fila grilla actualizada. */
export async function postQuitarActaCanalActas(
    actuacionId: number,
    tipo: ActaCanalQuitarTipo
): Promise<IActuacionListItem> {
    const { data } = await apiClient.post<IActuacionListItem>(`/actuaciones/${actuacionId}/quitar-acta`, { tipo });
    return data;
}
