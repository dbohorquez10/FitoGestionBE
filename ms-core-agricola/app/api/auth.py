"""
Router de Autenticación.
Login con email/contraseña usando Supabase Auth, retorna JWT.
Registro de usuarios con protección de rol admin.
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.core.supabase_client import get_supabase_client

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    """Credenciales para iniciar sesión."""
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    """Datos para registrar un nuevo usuario."""
    email: EmailStr
    password: str
    nombre: str
    apellido: str
    cedula: str
    rol: str = "productor"  # 'productor', 'tecnico', 'admin'
    telefono: str | None = None
    registro_ica: str | None = None
    departamento: str | None = None
    municipio: str | None = None
    vereda: str | None = None


class TokenResponse(BaseModel):
    """Respuesta con el token de sesión."""
    access_token: str
    token_type: str = "bearer"
    user: dict


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse, summary="Iniciar sesión")
def login(credentials: LoginRequest):
    """
    Autentica al usuario con email y contraseña.
    Retorna el access_token JWT de Supabase.
    """
    supabase = get_supabase_client()
    try:
        email_lower = credentials.email.lower()
        response = supabase.auth.sign_in_with_password(
            {"email": email_lower, "password": credentials.password}
        )
        session = response.session
        user = response.user
        if not session:
            raise HTTPException(status_code=401, detail="Credenciales inválidas")

        # Obtener perfil adicional del usuario desde la tabla usuarios
        perfil = supabase.table("usuarios").select("*").eq("email", email_lower).execute()
        perfil_data = perfil.data[0] if perfil.data else {}

        return TokenResponse(
            access_token=session.access_token,
            user={
                "id": user.id,
                "email": user.email,
                **perfil_data,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Error de autenticación: {str(e)}")


@router.post("/register", status_code=201, summary="Registrar usuario")
def register(data: RegisterRequest, authorization: Optional[str] = Header(None)):
    """
    Registra un nuevo usuario en Supabase Auth y crea su perfil
    en la tabla 'usuarios'.

    - Roles 'productor' y 'tecnico': registro público (sin autenticación).
    - Rol 'admin': requiere JWT de un usuario con rol 'admin' en el header Authorization.
    """
    supabase = get_supabase_client()

    # ── Protección: solo admins pueden crear admins ───────────────────────────
    if data.rol == "admin":
        if not authorization:
            raise HTTPException(
                status_code=403,
                detail="No autorizado: se requiere autenticación de administrador para crear cuentas admin."
            )
        try:
            token = authorization.replace("Bearer ", "")
            auth_user = supabase.auth.get_user(token)
            if not auth_user or not auth_user.user:
                raise HTTPException(status_code=403, detail="Token inválido o expirado.")

            # Verificar que el usuario autenticado tiene rol admin
            perfil = supabase.table("usuarios").select("rol").eq("email", auth_user.user.email).execute()
            if not perfil.data or perfil.data[0].get("rol") != "admin":
                raise HTTPException(
                    status_code=403,
                    detail="No autorizado: solo los administradores pueden crear cuentas de administrador."
                )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=403, detail=f"Error de autorización: {str(e)}")

    try:
        data.email = data.email.lower()
        # 1. Crear en Supabase Auth
        auth_response = supabase.auth.admin.create_user(
            {
                "email": data.email,
                "password": data.password,
                "email_confirm": True,
            }
        )
        user_id = auth_response.user.id

        # 2. Insertar perfil en tabla usuarios
        perfil = {
            "id": user_id,
            "nombre": data.nombre,
            "apellido": data.apellido,
            "email": data.email,
            "cedula": data.cedula,
            "rol": data.rol,
            "telefono": data.telefono,
            "registro_ica": data.registro_ica,
            "departamento": data.departamento,
            "municipio": data.municipio,
            "vereda": data.vereda,
        }
        supabase.table("usuarios").insert(perfil).execute()

        return {"message": "Usuario registrado exitosamente", "id": user_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al registrar usuario: {str(e)}")


@router.post("/logout", status_code=204, summary="Cerrar sesión")
def logout():
    """
    Invalida la sesión actual del usuario.
    El cliente debe eliminar el token localmente.
    """
    supabase = get_supabase_client()
    supabase.auth.sign_out()
    return None


@router.get("/me", summary="Obtener perfil del usuario autenticado")
def me(authorization: Optional[str] = Header(None)):
    """
    Retorna el perfil del usuario actual a partir del token JWT.
    El token debe enviarse en el header Authorization: Bearer <token>
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Se requiere token de autenticación")
    supabase = get_supabase_client()
    try:
        user = supabase.auth.get_user(authorization.replace("Bearer ", ""))
        if not user or not user.user:
            raise HTTPException(status_code=401, detail="Token inválido o expirado")
        perfil = supabase.table("usuarios").select("*").eq("email", user.user.email).execute()
        return perfil.data[0] if perfil.data else {"email": user.user.email}
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"No autorizado: {str(e)}")
