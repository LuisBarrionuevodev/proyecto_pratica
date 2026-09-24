export type TipoActuacion =
    | "INSPECCION"
    | "REINSPECCION"
    | "RATIFICACION"
    | "VERIFICAR E INFORMAR";


export interface IActuacion {
    id: number;
    orden_trabajo_numero: string;
    fecha_actuacion: string;
    rubro_nombre: string;
    inspector1: string;
    inspector2: string;
    inspector3: string;
    calle: string;
    numero: string;
    numero_tipo?: string | null;
    tipo_actuacion: TipoActuacion;
    contraproducencia?: string | null;
    doc_tipo_codigo: string;
    doc_nro: string;
    contrib_apellido: string;
    contrib_nombre?: string | null;
    acta_inspeccion_num?: string | null;
    acta_notificacion_num?: string | null;
    notificacion_motivo_1?: string | null;
    notificacion_motivo_2?: string | null;
    notificacion_motivo_3?: string | null;
    acta_comprobacion_num?: string | null;
    comprobacion_motivo?: string | null;
    acta_clausura_num?: string | null;
    clausura_motivo?: string | null;
    acta_decomiso_num?: string | null;
    decomiso_kilos_total?: number | null;
    expediente_numero?: string | null;
    expediente_anio?: number | null;
    oficio_numero?: string | null;
    oficio_anio?: number | null;
    oficio_causa?: number | null;
    notificacion_previa_num?: string | null;
    comprobacion_previa_num?: string | null;
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
    [key: string]: string | number | null | undefined;
}

export interface IActuacionListado {
    id: number;
    orden_trabajo_numero: string | null;
    fecha_actuacion: string;
    rubro_nombre: string | null;
    inspector1: string;
    inspector2: string;
    inspector3: string;
    calle: string | null;
    numero: string | null;
    numero_tipo?: string | null;
    tipo_actuacion: TipoActuacion;
    contraproducencia?: string | null;
    doc_tipo_codigo: string | null;
    doc_nro: string | null;
    contrib_apellido: string | null;
    contrib_nombre?: string | null;
    acta_inspeccion_num?: string | null;
    acta_notificacion_num?: string | null;
    notificacion_motivo_1?: string | null;
    notificacion_motivo_2?: string | null;
    notificacion_motivo_3?: string | null;
    acta_comprobacion_num?: string | null;
    comprobacion_motivo?: string | null;
    acta_clausura_num?: string | null;
    clausura_motivo?: string | null;
    acta_decomiso_num?: string | null;
    decomiso_kilos_total?: number | null;
    expediente_numero?: string | null;
    expediente_anio?: number | null;
    oficio_numero?: string | null;
    oficio_anio?: number | null;
    oficio_causa?: number | null;
    notificacion_previa_num?: string | null;
    comprobacion_previa_num?: string | null;
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
    establecimiento_domicilio_id?: number | null;
    created_at: string | null;
    updated_at: string | null;
}