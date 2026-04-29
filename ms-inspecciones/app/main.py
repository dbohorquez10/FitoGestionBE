"""
MS Inspecciones — Punto de entrada principal.
Registra los routers de Inspecciones, Sub-inspecciones y Registro de Plantas.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import inspecciones, sub_inspecciones, registro_plantas

app = FastAPI(
    title="FitoGestión — MS Inspecciones",
    description="Microservicio para el flujo transaccional de Inspecciones fitosanitarias, Sub-inspecciones y Registro de Plantas.",
    version="0.1.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# NOTA: CORS es manejado globalmente por el API Gateway (Nginx).
# No añadir CORSMiddleware aquí para evitar duplicación de cabeceras.


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check():
    """Endpoint de verificación de salud del servicio."""
    return {"status": "ok", "service": "ms-inspecciones"}


# ── Registro de routers ──────────────────────────────────────────────────────
app.include_router(inspecciones.router, prefix="/inspecciones", tags=["Inspecciones"])
app.include_router(sub_inspecciones.router, prefix="/sub-inspecciones", tags=["Sub-Inspecciones"])
app.include_router(registro_plantas.router, prefix="/registro-plantas", tags=["Registro de Plantas"])
