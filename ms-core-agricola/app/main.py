"""
MS Core Agrícola — Punto de entrada principal.
Registra los routers de Usuarios, Catálogos, Predios y Lotes.
"""
from fastapi import FastAPI
from app.api import usuarios, catalogos, predios, lotes

app = FastAPI(
    title="FitoGestión — MS Core Agrícola",
    description="Microservicio para la gestión de Usuarios, Catálogos (Plagas/Cultivos), Predios y Lotes.",
    version="0.1.0",
)


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check():
    """Endpoint de verificación de salud del servicio."""
    return {"status": "ok", "service": "ms-core-agricola"}


# ── Registro de routers ──────────────────────────────────────────────────────
app.include_router(usuarios.router, prefix="/usuarios", tags=["Usuarios"])
app.include_router(catalogos.router, prefix="/catalogos", tags=["Catálogos"])
app.include_router(predios.router, prefix="/predios", tags=["Predios"])
app.include_router(lotes.router, prefix="/lotes", tags=["Lotes"])
