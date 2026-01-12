export interface IPoligono {
  id: number;
  nombre: string;
  descripcion: string;
  wkt: string;
}

export interface IPoligonoCreate {
  nombre: string;
  descripcion: string;
  wkt: string;
}

