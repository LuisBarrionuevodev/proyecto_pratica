export interface ILocal {
  id: number;
  nombre: string;
  lat: number;
  lng: number;
  descripcion?: string;
  distrito?: string;
  archivos?: { id?: number; url: string; nombre?: string }[];
}
