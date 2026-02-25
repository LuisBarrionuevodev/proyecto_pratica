import { MaterialReactTable, useMaterialReactTable } from "material-react-table";
import { useMemo } from "react";

const TableGestionDeUsuarios = () => {

type Inspector = {
  id: number;
  nombre: string;
  rol: "Administrador" | "Usuario" | "Viewer";
  contraseña: string;
};

const data = useMemo<Inspector[]>(
  () => [
    {
      id: 1,
      nombre: "Juan Pérez",
      rol: "Administrador",
      contraseña: "••••••••",
    },
    {
      id: 2,
      nombre: "María Gómez",
      rol: "Usuario",
      contraseña: "••••••••",
    },
    {
      id: 3,
      nombre: "Carlos Rodríguez",
      rol: "Viewer",
      contraseña: "••••••••",
    },
    {
      id: 4,
      nombre: "Lucía Fernández",
      rol: "Usuario",
      contraseña: "••••••••",
    },
    {
      id: 5,
      nombre: "Matías López",
      rol: "Viewer",
      contraseña: "••••••••",
    },
    {
      id: 6,
      nombre: "Sofía Ramírez",
      rol: "Administrador",
      contraseña: "••••••••",
    },
  ],
  []
);

    const columns = useMemo(
    () => [
      {
        accessorKey: "id",
        header: "#",
        size: 10,
      },
      {
        accessorKey: "nombre",
        header: "Inspector",
      },
      {
        accessorKey: "rol",
        header: "Inspecciones",
      },
      {
        accessorKey: "contraseña",
        header: "Contreseña",
      },
    ],
    []
  );

  const table = useMaterialReactTable({
    columns,
    data
  })

    return(
        <MaterialReactTable table={table}/>
    )
}

export default TableGestionDeUsuarios;