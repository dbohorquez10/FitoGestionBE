"""
Configuración central del microservicio ms-core-agricola.
Lee las variables de entorno para conectarse a Supabase.
"""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuración del microservicio cargada desde variables de entorno."""
    APP_NAME: str = "ms-core-agricola"
    DEBUG: bool = True
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    """Retorna la instancia cacheada de la configuración."""
    return Settings()
