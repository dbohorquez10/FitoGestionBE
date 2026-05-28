"""
Módulo de conexión a Supabase.
Proporciona un cliente reutilizable para todos los routers.
"""
from supabase import create_client, Client
from app.core.config import get_settings

def get_supabase_client() -> Client:
    """Retorna una nueva instancia del cliente de Supabase para evitar contaminación de estado de autenticación."""
    settings = get_settings()
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
