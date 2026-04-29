"""
Router de Inspecciones.
Flujo transaccional completo para inspecciones fitosanitarias ICA.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from app.core.supabase_client import get_supabase_client

router = APIRouter()

# ── Schemas ───────────────────────────────────────────────────────────────────

class InspeccionCreate(BaseModel):
    """Esquema para crear una inspección fitosanitaria."""
    tecnico_id: Optional[str] = None      # Si es asignación automática puede ser null
    tecnico_nombre: Optional[str] = None  # Nombre de texto (compatibilidad frontend)
    predio_id: str
    lote_id: Optional[str] = None         # Puede referir al primer lote o ser null
    fecha_inspeccion: date
    tipo_inspeccion: str = "rutinaria"    # 'rutinaria', 'seguimiento', 'emergencia'
    modo_asignacion: str = "automatica"   # 'automatica', 'preferencia'
    comentarios: Optional[str] = None
    observaciones: Optional[str] = None


class InspeccionUpdate(BaseModel):
    """Esquema para actualizar una inspección."""
    tecnico_id: Optional[str] = None
    tecnico_nombre: Optional[str] = None
    modo_asignacion: Optional[str] = None
    estado: Optional[str] = None  # 'pendiente', 'en_progreso', 'completada', 'cancelada'
    observaciones: Optional[str] = None
    resultado_general: Optional[str] = None  # 'sin_novedad', 'con_hallazgos', 'critico'
    fecha_cierre: Optional[date] = None


class InspeccionResponse(BaseModel):
    """Esquema de respuesta de una inspección."""
    id: str
    tecnico_id: str
    predio_id: str
    lote_id: str
    fecha_inspeccion: date
    tipo_inspeccion: str
    estado: str
    observaciones: Optional[str] = None
    resultado_general: Optional[str] = None
    created_at: Optional[datetime] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/", summary="Listar inspecciones")
def listar_inspecciones():
    """Retorna todas las inspecciones registradas."""
    supabase = get_supabase_client()
    response = supabase.table("inspecciones").select("*").order("fecha_inspeccion", desc=True).execute()
    return response.data


# ── Rutas estáticas ANTES de las dinámicas (evitar conflicto con /{inspeccion_id}) ──

@router.get("/estado/pendientes", summary="Listar inspecciones pendientes")
def listar_inspecciones_pendientes():
    """
    Retorna todas las inspecciones con estado 'pendiente'.
    Equivale a getInspeccionesPendientes() del frontend.
    NOTA: Esta ruta debe estar ANTES de /{inspeccion_id} para evitar conflictos.
    """
    supabase = get_supabase_client()
    response = (
        supabase.table("inspecciones")
        .select("*, sub_inspecciones(*)")
        .eq("estado", "pendiente")
        .order("fecha_inspeccion")
        .execute()
    )
    return response.data


@router.get("/{inspeccion_id}", summary="Obtener una inspección por ID")
def obtener_inspeccion(inspeccion_id: str):
    """Retorna una inspección con sus sub-inspecciones y registros de plantas."""
    supabase = get_supabase_client()
    response = (
        supabase.table("inspecciones")
        .select("*, sub_inspecciones(*, registro_plantas(*))")
        .eq("id", inspeccion_id)
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Inspección no encontrada")
    return response.data[0]


@router.get("/tecnico/{tecnico_id}", summary="Inspecciones por técnico")
def listar_inspecciones_por_tecnico(tecnico_id: str):
    """Retorna todas las inspecciones asignadas a un técnico."""
    supabase = get_supabase_client()
    response = (
        supabase.table("inspecciones")
        .select("*")
        .eq("tecnico_id", tecnico_id)
        .order("fecha_inspeccion", desc=True)
        .execute()
    )
    return response.data


@router.get("/predio/{predio_id}", summary="Inspecciones por predio")
def listar_inspecciones_por_predio(predio_id: str):
    """Retorna todas las inspecciones realizadas en un predio."""
    supabase = get_supabase_client()
    response = (
        supabase.table("inspecciones")
        .select("*")
        .eq("predio_id", predio_id)
        .order("fecha_inspeccion", desc=True)
        .execute()
    )
    return response.data


@router.post("/", status_code=201, summary="Crear una inspección")
def crear_inspeccion(inspeccion: InspeccionCreate):
    """
    Crea una nueva inspección fitosanitaria.
    Se inicializa con estado 'pendiente'.
    Filtra campos que no son columnas de la tabla antes de insertar.
    """
    supabase = get_supabase_client()
    data = inspeccion.model_dump()
    data["estado"] = "pendiente"
    data["fecha_inspeccion"] = str(data["fecha_inspeccion"])

    # Campos que no son columnas de la tabla inspecciones — excluirlos
    campos_excluidos = {"tecnico_nombre", "modo_asignacion", "comentarios"}
    data_limpia = {k: v for k, v in data.items() if k not in campos_excluidos and v is not None}

    # Si no se envió lote_id, intentar asignar el primer lote del predio
    if not data_limpia.get("lote_id"):
        lotes = supabase.table("lotes").select("id").eq("predio_id", data_limpia["predio_id"]).limit(1).execute()
        if lotes.data:
            data_limpia["lote_id"] = lotes.data[0]["id"]
        else:
            raise HTTPException(
                status_code=400,
                detail="El predio no tiene lotes. Debe crear al menos un lote antes de solicitar una inspección."
            )

    response = supabase.table("inspecciones").insert(data_limpia).execute()
    return response.data[0]


@router.put("/{inspeccion_id}", summary="Actualizar una inspección")
def actualizar_inspeccion(inspeccion_id: str, inspeccion: InspeccionUpdate):
    """Actualiza el estado o datos de una inspección existente."""
    supabase = get_supabase_client()
    data = {k: v for k, v in inspeccion.model_dump().items() if v is not None}
    if "fecha_cierre" in data:
        data["fecha_cierre"] = str(data["fecha_cierre"])
    # Excluir campos que no son columnas de la tabla
    campos_excluidos = {"tecnico_nombre", "modo_asignacion"}
    data = {k: v for k, v in data.items() if k not in campos_excluidos}
    response = supabase.table("inspecciones").update(data).eq("id", inspeccion_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Inspección no encontrada")
    return response.data[0]


@router.delete("/{inspeccion_id}", status_code=204, summary="Eliminar una inspección")
def eliminar_inspeccion(inspeccion_id: str):
    """Elimina una inspección y sus registros asociados (cascade)."""
    supabase = get_supabase_client()
    supabase.table("inspecciones").delete().eq("id", inspeccion_id).execute()
    return None


class AsignacionTecnico(BaseModel):
    """Payload para asignar un técnico a una inspección."""
    tecnico_id: str


@router.patch("/{inspeccion_id}/asignar-tecnico", summary="Asignar técnico a una inspección")
def asignar_tecnico(inspeccion_id: str, asignacion: AsignacionTecnico):
    """
    Asigna o reasigna un técnico a una inspección existente.
    Solo actualiza tecnico_id (campo real de la tabla).
    """
    supabase = get_supabase_client()
    response = (
        supabase.table("inspecciones")
        .update({"tecnico_id": asignacion.tecnico_id})
        .eq("id", inspeccion_id)
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Inspección no encontrada")
    return response.data[0]




@router.patch("/{inspeccion_id}/finalizar", summary="Finalizar una inspección completa")
def finalizar_inspeccion(inspeccion_id: str, observaciones: Optional[str] = None):
    """
    Marca la inspección como 'completada' y opcionalmente guarda las observaciones finales.
    Equivale a finalizarInspeccionCompleta() del frontend.
    """
    supabase = get_supabase_client()
    data: dict = {"estado": "completada"}
    if observaciones:
        data["observaciones"] = observaciones
    from datetime import date as dt
    data["fecha_cierre"] = str(dt.today())
    response = (
        supabase.table("inspecciones")
        .update(data)
        .eq("id", inspeccion_id)
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Inspección no encontrada")
    return response.data[0]

