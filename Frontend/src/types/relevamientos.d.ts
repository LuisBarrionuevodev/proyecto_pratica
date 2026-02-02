export interface IRelevamiento {
  id: number;
  fecha: string | null;
  inspector: string | null;
  calle: string | null;
  numero: string | null;
  numero_tipo?: string | null;
  rubro: string | null;
  contraproducencia: string | null;
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
}
