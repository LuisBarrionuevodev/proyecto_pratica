from pydantic import BaseModel, EmailStr, field_validator


class UsuarioCreate(BaseModel):
    nombre: str
    email: EmailStr

    @field_validator("nombre")
    @classmethod
    def nombre_espacio(cls, valor: str) -> str:
        if " " not in valor:
            raise ValueError("Tiene que haber un espacio que separe nombre de apellido")
        return valor.upper()


class UsuarioResponse(BaseModel):
    id: int
    nombre: str
    email: EmailStr
    activo: bool
