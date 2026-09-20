"""Ítems de acta de inspección aprobados (seed canónico: 6)."""



from __future__ import annotations



from typing import Literal, TypedDict



TipoRespuestaItemInspeccion = Literal["ESTADO", "SI_NO"]





class ItemInspeccionCanonico(TypedDict):

    codigo: str

    nombre: str

    orden: int

    tipo_respuesta: TipoRespuestaItemInspeccion





ITEMS_INSPECCION_CANONICOS: tuple[ItemInspeccionCanonico, ...] = (

    {"codigo": "TIENE_BANO", "nombre": "Baño", "orden": 1, "tipo_respuesta": "ESTADO"},

    {"codigo": "TIENE_SALON", "nombre": "Salón", "orden": 2, "tipo_respuesta": "ESTADO"},

    {"codigo": "TIENE_DEPOSITO", "nombre": "Depósito", "orden": 3, "tipo_respuesta": "ESTADO"},

    {

        "codigo": "TIENE_COCINA_MESA_TRABAJO",

        "nombre": "Cocina / mesa de trabajo",

        "orden": 4,

        "tipo_respuesta": "ESTADO",

    },

    {"codigo": "VAJILLA_MANTEL", "nombre": "Vajilla / mantel", "orden": 5, "tipo_respuesta": "ESTADO"},

    {

        "codigo": "TIENE_HABILITACION",

        "nombre": "Tiene habilitación",

        "orden": 6,

        "tipo_respuesta": "SI_NO",

    },

)


