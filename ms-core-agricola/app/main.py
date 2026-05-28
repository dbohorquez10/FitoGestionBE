"""
MS Core Agrícola — Punto de entrada principal.
Registra los routers de Usuarios, Catálogos, Predios y Lotes.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import usuarios, catalogos, predios, lotes, auth, lugares, notificaciones

app = FastAPI(
    title="FitoGestión — MS Core Agrícola",
    description="Microservicio para la gestión de Usuarios, Catálogos (Plagas/Cultivos), Predios y Lotes.",
    version="0.1.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# NOTA: CORS es manejado globalmente por el API Gateway (Nginx).
# No añadir CORSMiddleware aquí para evitar duplicación de cabeceras.


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check():
    """Endpoint de verificación de salud del servicio."""
    return {"status": "ok", "service": "ms-core-agricola"}


# ── Registro de routers ──────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/auth", tags=["Autenticación"])
app.include_router(usuarios.router, prefix="/usuarios", tags=["Usuarios"])
app.include_router(catalogos.router, prefix="/catalogos", tags=["Catálogos"])
app.include_router(predios.router, prefix="/predios", tags=["Predios"])
app.include_router(lugares.router, prefix="/lugares", tags=["Lugares de Producción"])
app.include_router(lotes.router, prefix="/lotes", tags=["Lotes"])
app.include_router(notificaciones.router, prefix="/notificaciones", tags=["Notificaciones"])
