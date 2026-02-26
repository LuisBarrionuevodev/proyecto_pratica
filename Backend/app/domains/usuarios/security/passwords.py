from __future__ import annotations

from werkzeug.security import check_password_hash, generate_password_hash


def hash_password(plain_password: str) -> str:
    """
    Genera hash seguro para contraseña de usuario.

    Args:
        plain_password: contraseña en texto plano.

    Returns:
        Hash de contraseña compatible con Werkzeug.
    """
    return generate_password_hash(plain_password, method="pbkdf2:sha256", salt_length=16)


def verify_password(password_hash: str, plain_password: str) -> bool:
    """
    Verifica una contraseña plana contra su hash.

    Args:
        password_hash: hash persistido en DB.
        plain_password: contraseña en texto plano recibida.

    Returns:
        True si coincide, False en caso contrario.
    """
    return check_password_hash(password_hash, plain_password)

