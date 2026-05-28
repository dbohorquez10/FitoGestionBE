"""
Módulo de seguridad y control de accesos (JWT & RBAC).
"""
from fastapi import Header, HTTPException, Depends
from app.core.supabase_client import get_supabase_client
from typing import Optional

def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    Dependency para extraer y validar el token JWT desde la cabecera Authorization.
    Retorna el perfil completo del usuario si está activo.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Se requiere token de autenticación")
    
    try:
        token = authorization.replace("Bearer ", "")
        supabase = get_supabase_client()
        auth_response = supabase.auth.get_user(token)
        if not auth_response or not auth_response.user:
            raise HTTPException(status_code=401, detail="Token inválido o expirado")
        
        user_id = auth_response.user.id
        
        # Obtener el perfil adicional de la tabla usuarios
        perfil = supabase.table("usuarios").select("*").eq("id", user_id).execute()
        if not perfil.data:
            # Retorno básico si no tiene perfil creado aún (flujo de registro)
            return {
                "id": user_id,
                "email": auth_response.user.email,
                "rol": "productor",
                "activo": True
            }
        
        user_data = perfil.data[0]
        if not user_data.get("activo", True):
            raise HTTPException(status_code=403, detail="Usuario inactivo o suspendido")
            
        return user_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"No autorizado: {str(e)}")

def require_role(roles_permitidos: list[str]):
    """
    Retorna una dependency que valida si el usuario posee uno de los roles permitidos.
    """
    def dependency(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user.get("rol") not in roles_permitidos:
            raise HTTPException(
                status_code=403,
                detail="Acceso denegado: no tienes el rol requerido para esta acción"
            )
        return current_user
    return dependency
