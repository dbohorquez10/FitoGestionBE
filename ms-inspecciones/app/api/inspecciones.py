"""
Router de Inspecciones.
Flujo transaccional completo para inspecciones fitosanitarias ICA.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from app.core.supabase_client import get_supabase_client
from io import BytesIO

# ReportLab imports
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

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
    razon_rechazo: Optional[str] = None


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


def post_process_inspecciones(inspecciones_list: list):
    if not inspecciones_list:
        return inspecciones_list
        
    supabase = get_supabase_client()
    
    # 1. Collect all tecnico_ids and predio_ids to fetch names in batch
    tecnico_ids = list({ins["tecnico_id"] for ins in inspecciones_list if ins.get("tecnico_id")})
    predio_ids = list({ins["predio_id"] for ins in inspecciones_list if ins.get("predio_id")})
    
    # Fetch technicians
    tecnicos_map = {}
    if tecnico_ids:
        try:
            tec_res = supabase.table("usuarios").select("id, nombre, apellido").in_("id", tecnico_ids).execute()
            for u in tec_res.data:
                tecnicos_map[u["id"]] = f"{u['nombre']} {u.get('apellido') or ''}".strip()
        except Exception as e:
            print("Error fetching tecnicos in batch:", e)
            
    # Fetch predios and their producers
    productores_map = {}
    if predio_ids:
        try:
            pred_res = supabase.table("predios").select("id, productor_id").in_("id", predio_ids).execute()
            pred_prod_map = {p["id"]: p["productor_id"] for p in pred_res.data}
            productor_ids = list({p["productor_id"] for p in pred_res.data if p.get("productor_id")})
            
            if productor_ids:
                prod_res = supabase.table("usuarios").select("id, nombre, apellido").in_("id", productor_ids).execute()
                prod_user_map = {u["id"]: f"{u['nombre']} {u.get('apellido') or ''}".strip() for u in prod_res.data}
                
                for pred_id, prod_id in pred_prod_map.items():
                    if prod_id in prod_user_map:
                        productores_map[pred_id] = prod_user_map[prod_id]
        except Exception as e:
            print("Error fetching predios/producers in batch:", e)
            
    # 2. Process each inspection
    for ins in inspecciones_list:
        tec_id = ins.get("tecnico_id")
        pred_id = ins.get("predio_id")
        
        # Inject technician/producer names
        ins["nombre_tecnico"] = tecnicos_map.get(tec_id) or ins.get("tecnico_nombre") or "No Asignado"
        ins["tecnico_nombre"] = ins["nombre_tecnico"] # Compatibility alias
        ins["nombre_productor"] = productores_map.get(pred_id) or "Desconocido"
        
        # Calculate aggregates
        subs = ins.get("sub_inspecciones") or []
        lote_ids = set()
        total_evaluadas = 0
        total_enfermas = 0
        
        for s in subs:
            lid = s.get("lote_id") or s.get("codigo_punto") or s.get("loteId")
            if lid:
                lote_ids.add(lid)
            # If sub_inspeccion doesn't have plants_evaluadas, use length of registro_plantas
            regs = s.get("registro_plantas") or []
            total_evaluadas += len(regs)
            for r in regs:
                if r.get("estado_planta") in ["enferma", "muerta"] or r.get("plaga_id"):
                    total_enfermas += 1
                    
        ins["lotes_count"] = len(lote_ids)
        ins["plantas_evaluadas"] = total_evaluadas
        ins["plantas_enfermas"] = total_enfermas
        
    return inspecciones_list


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/", summary="Listar inspecciones")
def listar_inspecciones(skip: int = 0, limit: int = 100):
    """Retorna todas las inspecciones registradas."""
    supabase = get_supabase_client()
    response = supabase.table("inspecciones").select("*, sub_inspecciones(*, registro_plantas(*))").order("fecha_inspeccion", desc=True).range(skip, skip + limit - 1).execute()
    return post_process_inspecciones(response.data)


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
    processed = post_process_inspecciones(response.data)
    return processed[0]


@router.get("/tecnico/{tecnico_id}", summary="Inspecciones por técnico")
def listar_inspecciones_por_tecnico(tecnico_id: str):
    """Retorna todas las inspecciones asignadas a un técnico."""
    supabase = get_supabase_client()
    response = (
        supabase.table("inspecciones")
        .select("*, sub_inspecciones(*, registro_plantas(*))")
        .eq("tecnico_id", tecnico_id)
        .order("fecha_inspeccion", desc=True)
        .execute()
    )
    return post_process_inspecciones(response.data)


@router.get("/predio/{predio_id}", summary="Inspecciones por predio")
def listar_inspecciones_por_predio(predio_id: str):
    """Retorna todas las inspecciones realizadas en un predio."""
    supabase = get_supabase_client()
    response = (
        supabase.table("inspecciones")
        .select("*, sub_inspecciones(*, registro_plantas(*))")
        .eq("predio_id", predio_id)
        .order("fecha_inspeccion", desc=True)
        .execute()
    )
    return post_process_inspecciones(response.data)


@router.post("/", status_code=201, summary="Crear una inspección")
def crear_inspeccion(inspeccion: InspeccionCreate):
    """
    Crea una nueva inspección fitosanitaria.
    Se inicializa con estado 'pendiente'.
    Filtra campos que no son columnas de la tabla antes de insertar.
    """
    if inspeccion.fecha_inspeccion < date.today():
        raise HTTPException(
            status_code=400,
            detail="La fecha sugerida no puede ser anterior al día de hoy."
        )
    supabase = get_supabase_client()
    data = inspeccion.model_dump()
    data["estado"] = "pendiente"
    data["fecha_inspeccion"] = str(data["fecha_inspeccion"])

    # Campos que no son columnas de la tabla inspecciones — excluirlos
    campos_excluidos = {"tecnico_nombre", "comentarios"}
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
    campos_excluidos = {"tecnico_nombre"}
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
    Actualiza tecnico_id y cambia el estado a 'en_progreso' para marcarla como aprobada/asignada.
    """
    supabase = get_supabase_client()
    response = (
        supabase.table("inspecciones")
        .update({
            "tecnico_id": asignacion.tecnico_id,
            "estado": "en_progreso"
        })
        .eq("id", inspeccion_id)
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Inspección no encontrada")
    return response.data[0]




class EvaluacionAprobacion(BaseModel):
    """Payload para evaluar la aprobación de una inspección."""
    estado_aprobacion: str
    justificacion: Optional[str] = None


def is_uuid(val):
    if not val:
        return False
    try:
        import uuid
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False


def get_punto_label(sub, idx):
    cod = sub.get("codigo_punto")
    if not cod or is_uuid(cod):
        return f"Punto {idx}"
    return f"Punto {idx} ({cod})"


def draw_header_footer(canvas, doc):
    canvas.saveState()
    # Header bar
    canvas.setFillColor(colors.HexColor("#1b4332")) # Verde oscuro ICA
    canvas.rect(0, 742, 612, 50, fill=True, stroke=False)
    
    # Header text
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(30, 769, "FITOGESTIÓN - INSTITUTO COLOMBIANO AGROPECUARIO (ICA)")
    canvas.setFont("Helvetica", 8)
    canvas.drawString(30, 754, "REPÚBLICA DE COLOMBIA - MINISTERIO DE AGRICULTURA Y DESARROLLO RURAL")
    
    # Footer line
    canvas.setStrokeColor(colors.HexColor("#2d6a4f"))
    canvas.setLineWidth(1)
    canvas.line(30, 45, 582, 45)
    
    # Footer text
    canvas.setFillColor(colors.HexColor("#4b5563"))
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(30, 32, "UmbraCode")
    canvas.setFont("Helvetica", 8)
    canvas.drawString(85, 32, "|  Desarrollado para el Sistema de Gestión Fitosanitaria de FitoGestión")
    canvas.drawRightString(582, 32, f"Página {doc.page}")
    canvas.restoreState()


@router.patch("/{inspeccion_id}/finalizar", summary="Finalizar una inspección completa")
def finalizar_inspeccion(inspeccion_id: str, observaciones: Optional[str] = None):
    """
    Marca la inspección como 'completada', calcula el estado de aprobación automáticamente
    en base al umbral de incidencia, y opcionalmente guarda observaciones.
    """
    supabase = get_supabase_client()
    
    # 1. Obtener la inspección actual
    resp_get = supabase.table("inspecciones").select("*").eq("id", inspeccion_id).execute()
    if not resp_get.data:
        raise HTTPException(status_code=404, detail="Inspección no encontrada")
    
    inspeccion = resp_get.data[0]
    
    # 2. Calcular la incidencia global en Python
    sub_resp = supabase.table("sub_inspecciones").select("id, plantas_evaluadas").eq("inspeccion_id", inspeccion_id).execute()
    total_evaluadas = sum(int(s.get("plantas_evaluadas") or 0) for s in sub_resp.data) if sub_resp.data else 0
    
    sub_ids = [s.get("id") for s in (sub_resp.data or []) if s.get("id")]
    
    total_enfermas = 0
    if sub_ids:
        plantas_resp = supabase.table("registro_plantas").select("id").in_("sub_inspeccion_id", sub_ids).in_("estado_planta", ["enferma", "muerta"]).execute()
        total_enfermas = len(plantas_resp.data) if plantas_resp.data else 0
        
    incidencia_global = (total_enfermas / total_evaluadas * 100.0) if total_evaluadas > 0 else 0.0
    
    estado_aprobacion = "pendiente"
    razon_rechazo = None
    if incidencia_global >= 15.0:
        estado_aprobacion = "rechazado"
        razon_rechazo = "Excede el umbral máximo de incidencia permitido (15.0%)."
        
    if incidencia_global >= 15.0:
        nivel_alerta = "Crítico (Cuarentena Recomendada)"
    elif incidencia_global >= 5.0:
        nivel_alerta = "Alerta (Tratamiento Requerido)"
    else:
        nivel_alerta = "Normal (Monitoreo)"
        
    data: dict = {
        "estado": "completada",
        "estado_aprobacion": estado_aprobacion,
        "incidencia_global_pct": round(incidencia_global, 2),
        "nivel_alerta": nivel_alerta
    }
    if razon_rechazo:
        data["razon_rechazo"] = razon_rechazo
    else:
        data["razon_rechazo"] = None
        
    if observaciones is not None:
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


@router.patch("/{inspeccion_id}/aprobacion", summary="Evaluar aprobación de una inspección (Admin)")
def evaluar_aprobacion(inspeccion_id: str, evaluacion: EvaluacionAprobacion):
    """
    Permite al administrador aprobar o rechazar una inspección fitosanitaria.
    """
    if evaluacion.estado_aprobacion not in ["aprobado", "rechazado"]:
        raise HTTPException(status_code=400, detail="Estado de aprobación inválido. Debe ser 'aprobado' o 'rechazado'")
        
    supabase = get_supabase_client()
    resp_get = supabase.table("inspecciones").select("*").eq("id", inspeccion_id).execute()
    if not resp_get.data:
        raise HTTPException(status_code=404, detail="Inspección no encontrada")
        
    inspeccion = resp_get.data[0]
    incidencia_global = float(inspeccion.get("incidencia_global_pct") or 0.0)
    
    if evaluacion.estado_aprobacion == "aprobado":
        if incidencia_global >= 15.0:
            raise HTTPException(
                status_code=400,
                detail="No se puede aprobar una inspección con incidencia global mayor o igual a 15.0%."
            )
        data = {
            "estado_aprobacion": "aprobado",
            "razon_rechazo": None
        }
    else: # rechazado
        if incidencia_global < 15.0:
            if not evaluacion.justificacion or not evaluacion.justificacion.strip():
                raise HTTPException(
                    status_code=400, 
                    detail="La justificación es obligatoria para rechazar una inspección con incidencia menor al 15.0%."
                )
            razon = evaluacion.justificacion.strip()
        else:
            razon = "Excede el umbral máximo de incidencia permitido (15.0%)."
            
        data = {
            "estado_aprobacion": "rechazado",
            "razon_rechazo": razon
        }
        
    response = (
        supabase.table("inspecciones")
        .update(data)
        .eq("id", inspeccion_id)
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=400, detail="Error al actualizar la aprobación")
    return response.data[0]


@router.get("/{inspeccion_id}/informe", summary="Generar Informe Fitosanitario")
def generar_informe_inspeccion(inspeccion_id: str):
    """
    Genera un informe consolidado de la inspección llamando a un Stored Procedure en Supabase.
    """
    supabase = get_supabase_client()
    try:
        response = supabase.rpc("fn_generar_informe_inspeccion", {"p_inspeccion_id": inspeccion_id}).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando informe: {str(e)}")


@router.get("/{inspeccion_id}/informe/pdf", summary="Generar Informe Fitosanitario en PDF")
def generar_informe_inspeccion_pdf(inspeccion_id: str):
    """
    Genera un informe fitosanitario detallado en formato PDF para descarga directa.
    """
    supabase = get_supabase_client()
    
    # 1. Fetch full inspection data
    ins_resp = (
        supabase.table("inspecciones")
        .select("*, sub_inspecciones(*, registro_plantas(*))")
        .eq("id", inspeccion_id)
        .execute()
    )
    if not ins_resp.data:
        raise HTTPException(status_code=404, detail="Inspección no encontrada")
    
    inspeccion = ins_resp.data[0]
    
    # 2. Fetch Predio
    predio = {}
    predio_id = inspeccion.get("predio_id")
    if predio_id:
        predio_resp = supabase.table("predios").select("*").eq("id", predio_id).execute()
        if predio_resp.data:
            predio = predio_resp.data[0]
            
    # 3. Fetch Producer (Usuario)
    productor = {}
    productor_id = predio.get("productor_id") if predio else None
    if productor_id:
        prod_resp = supabase.table("usuarios").select("*").eq("id", productor_id).execute()
        if prod_resp.data:
            productor = prod_resp.data[0]
            
    # 4. Fetch Technician (Usuario)
    tecnico = {}
    tecnico_id = inspeccion.get("tecnico_id")
    if tecnico_id:
        tec_resp = supabase.table("usuarios").select("*").eq("id", tecnico_id).execute()
        if tec_resp.data:
            tecnico = tec_resp.data[0]
            
    # 5. Fetch all plagas
    plagas_resp = supabase.table("plagas").select("id, nombre_comun").execute()
    plagas_map = {p["id"]: p["nombre_comun"] for p in plagas_resp.data} if plagas_resp.data else {}

    # 6. Fetch cultivos
    cultivos_resp = supabase.table("cultivos").select("id, nombre").execute()
    cultivos_map = {c["id"]: c["nombre"] for c in cultivos_resp.data} if cultivos_resp.data else {}

    # 7. Fetch lotes
    lotes_resp = supabase.table("lotes").select("id, nombre, cultivo_id").eq("predio_id", predio_id).execute()
    lotes_map = {l["id"]: l["nombre"] for l in lotes_resp.data} if lotes_resp.data else {}
    lotes_cultivo_map = {l["id"]: l["cultivo_id"] for l in lotes_resp.data} if lotes_resp.data else {}
    
    # 8. Start PDF Doc
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=100,
        bottomMargin=60
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor('#1b4332'),
        alignment=1,
        spaceAfter=15,
        spaceBefore=10
    )
    
    h2_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#1b4332'),
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1f2937')
    )
    
    body_bold = ParagraphStyle(
        'BodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    
    th_style = ParagraphStyle(
        'Th',
        parent=body_style,
        fontName='Helvetica-Bold',
        textColor=colors.white
    )
    
    story = [
        Paragraph("INFORME DE INSPECCIÓN FITOSANITARIA", title_style),
        Spacer(1, 5)
    ]
    
    # Metadata Table
    meta_data = [
        [Paragraph("<b>ID Inspección:</b>", body_bold), Paragraph(str(inspeccion.get("id")), body_style),
         Paragraph("<b>Fecha:</b>", body_bold), Paragraph(str(inspeccion.get("fecha_inspeccion")), body_style)],
        [Paragraph("<b>Tipo de Inspección:</b>", body_bold), Paragraph(str(inspeccion.get("tipo_inspeccion", "")).capitalize(), body_style),
         Paragraph("<b>Estado de Aprobación:</b>", body_bold), Paragraph(str(inspeccion.get("estado_aprobacion", "pendiente")).upper(), body_style)]
    ]
    t_meta = Table(meta_data, colWidths=[100, 166, 100, 166])
    t_meta.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f8f9fa')),
        ('BACKGROUND', (2,0), (2,-1), colors.HexColor('#f8f9fa')),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))
    
    # Predio & Productor Info
    story.append(Paragraph("Información General del Predio y Productor", h2_style))
    
    area_val = float(predio.get("area_total") or 0.0)
    area_str = f"{area_val:.2f} Hectáreas"
    lat_val = predio.get("latitud")
    lon_val = predio.get("longitud")
    coor_str = f"Lat: {lat_val}, Lon: {lon_val}" if lat_val is not None and lon_val is not None else "N/A"
    
    predio_data = [
        [Paragraph("<b>Predio:</b>", body_bold), Paragraph(str(predio.get("nombre", "N/A")), body_style),
         Paragraph("<b>Productor:</b>", body_bold), Paragraph(str(productor.get("nombre", "N/A")), body_style)],
        [Paragraph("<b>Registro ICA:</b>", body_bold), Paragraph(str(predio.get("numero_registro_ica") or "N/A"), body_style),
         Paragraph("<b>Contacto:</b>", body_bold), Paragraph(str(productor.get("email", "N/A")), body_style)],
        [Paragraph("<b>Ubicación:</b>", body_bold), Paragraph(f"{predio.get('departamento', 'N/A')} - {predio.get('municipio', 'N/A')}", body_style),
         Paragraph("<b>Vereda:</b>", body_bold), Paragraph(str(predio.get("vereda") or "N/A"), body_style)],
        [Paragraph("<b>Área Total:</b>", body_bold), Paragraph(area_str, body_style),
         Paragraph("<b>Coordenadas:</b>", body_bold), Paragraph(coor_str, body_style)]
    ]
    t_predio = Table(predio_data, colWidths=[100, 166, 100, 166])
    t_predio.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f8f9fa')),
        ('BACKGROUND', (2,0), (2,-1), colors.HexColor('#f8f9fa')),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_predio)
    story.append(Spacer(1, 10))
    
    # Data aggregation for epidemiological results
    sub_inspecciones = inspeccion.get("sub_inspecciones") or []
    total_evaluadas = sum(int(s.get("plantas_evaluadas") or 0) for s in sub_inspecciones)
    total_registradas = sum(len(s.get("registro_plantas") or []) for s in sub_inspecciones)
    if total_evaluadas < total_registradas:
        total_evaluadas = total_registradas
        
    total_afectadas = 0
    findings = {}
    
    # Get all cultivation types (cultivos) for this predio
    cultivos_set = set()
    if predio_id:
        predio_lotes = supabase.table("lotes").select("cultivo_id").eq("predio_id", predio_id).execute()
        if predio_lotes.data:
            for l in predio_lotes.data:
                c_id = l.get("cultivo_id")
                if c_id and c_id in cultivos_map:
                    cultivos_set.add(cultivos_map[c_id])
    cultivo_nombre = ", ".join(sorted(list(cultivos_set))) if cultivos_set else "N/A"
    
    for s in sub_inspecciones:
        reg = s.get("registro_plantas") or []
        for r in reg:
            if r.get("estado_planta") in ["enferma", "muerta"] or r.get("plaga_id"):
                plaga_id = r.get("plaga_id")
                if not plaga_id:
                    continue
                total_afectadas += 1
                if plaga_id not in findings:
                    findings[plaga_id] = {"afectadas": 0, "severidades": set(), "sintomas": set()}
                findings[plaga_id]["afectadas"] += 1
                if r.get("severidad"):
                    findings[plaga_id]["severidades"].add(r.get("severidad"))
                if r.get("sintoma"):
                    findings[plaga_id]["sintomas"].add(r.get("sintoma"))
                    
    # Macro Indicators Box
    story.append(Paragraph("Resultados Epidemiológicos Consolidados", h2_style))
    incidencia_global = float(inspeccion.get("incidencia_global_pct") or 0.0)
    nivel_alerta = str(inspeccion.get("nivel_alerta") or "Normal (Monitoreo)")
    
    macro_data = [
        [
            Paragraph("<b>Total Plantas Evaluadas:</b>", body_style), Paragraph(str(total_evaluadas), body_bold),
            Paragraph("<b>Plantas con Hallazgos:</b>", body_style), Paragraph(str(total_afectadas), body_bold)
        ],
        [
            Paragraph("<b>Incidencia Global:</b>", body_style), Paragraph(f"{incidencia_global:.2f}%", body_bold),
            Paragraph("<b>Nivel de Alerta:</b>", body_style), Paragraph(nivel_alerta, body_bold)
        ]
    ]
    t_macro = Table(macro_data, colWidths=[130, 120, 130, 152])
    t_macro.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#2d6a4f')),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0fdf4')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_macro)
    story.append(Spacer(1, 10))
    
    # Detailed Plagas Table
    if findings:
        plaga_table_data = [
            [
                Paragraph("Cultivo", th_style),
                Paragraph("Plaga / Enfermedad", th_style),
                Paragraph("Evaluadas", th_style),
                Paragraph("Afectadas", th_style),
                Paragraph("Incidencia", th_style),
                Paragraph("Severidades", th_style),
                Paragraph("Síntomas Reportados", th_style)
            ]
        ]
        for plaga_id, f_data in findings.items():
            plaga_name = plagas_map.get(plaga_id, "Desconocida")
            afectadas_count = f_data["afectadas"]
            plaga_incidencia = (afectadas_count / total_evaluadas * 100.0) if total_evaluadas > 0 else 0.0
            severidades_str = ", ".join(sorted(list(f_data["severidades"]))) if f_data["severidades"] else "Bajo"
            sintomas_str = ", ".join(sorted(list(f_data["sintomas"]))) if f_data["sintomas"] else "N/A"
            
            plaga_table_data.append([
                Paragraph(cultivo_nombre, body_style),
                Paragraph(plaga_name, body_style),
                Paragraph(str(total_evaluadas), body_style),
                Paragraph(str(afectadas_count), body_style),
                Paragraph(f"{plaga_incidencia:.2f}%", body_style),
                Paragraph(severidades_str, body_style),
                Paragraph(sintomas_str, body_style)
            ])
            
        t_plaga = Table(plaga_table_data, colWidths=[80, 80, 55, 55, 60, 75, 127])
        t_plaga.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1b4332')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('PADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(t_plaga)
    else:
        story.append(Paragraph("<i>No se encontraron plagas ni enfermedades registradas en esta inspección (Estado: Sin novedades fitosanitarias).</i>", body_style))
        
    story.append(Spacer(1, 10))
    
    # Points of Muestreo Table
    story.append(Paragraph("Evaluación por Lotes y Puntos de Muestreo", h2_style))
    if sub_inspecciones:
        points_data = [
            [
                Paragraph("Lote", th_style),
                Paragraph("Punto de Muestreo", th_style),
                Paragraph("Estado", th_style),
                Paragraph("Observaciones / Hallazgos", th_style)
            ]
        ]
        sorted_subs = sorted(sub_inspecciones, key=lambda x: x.get("codigo_punto") or "")
        for idx, s in enumerate(sorted_subs, 1):
            lote_id_sub = s.get("lote_id") or s.get("codigo_punto") or s.get("loteId")
            lote_name = lotes_map.get(lote_id_sub) or s.get("ubicacion_referencia") or "N/A"
            pt_label = get_punto_label(s, idx)
            s_obs = s.get("observaciones") or "Sin novedades particulares."
            points_data.append([
                Paragraph(lote_name, body_style),
                Paragraph(pt_label, body_style),
                Paragraph(str(s.get("estado", "completado")).capitalize(), body_style),
                Paragraph(s_obs, body_style)
            ])
        t_points = Table(points_data, colWidths=[100, 100, 70, 262])
        t_points.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2d6a4f')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('PADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(t_points)
    else:
        story.append(Paragraph("<i>No hay puntos de muestreo registrados.</i>", body_style))
    
    # Observations
    story.append(Spacer(1, 15))
    story.append(Paragraph("Observaciones Generales de la Inspección:", body_bold))
    obs_text = inspeccion.get("observaciones") or "Sin observaciones registradas."
    story.append(Paragraph(obs_text, body_style))
    
    # Signatures
    story.append(Spacer(1, 30))
    sig_data = [
        [
            Paragraph("_____________________________<br/><b>Inspector Autorizado ICA</b><br/>Firma y Sello", body_style),
            Paragraph("_____________________________<br/><b>Productor / Propietario</b><br/>Firma de Conformidad", body_style)
        ]
    ]
    t_sig = Table(sig_data, colWidths=[266, 266])
    t_sig.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(KeepTogether(t_sig))
    
    doc.build(story, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Informe_Fitosanitario_{inspeccion_id}.pdf"}
    )


@router.get("/{inspeccion_id}/certificado/pdf", summary="Generar Certificado Fitosanitario en PDF")
def generar_certificado_pdf(inspeccion_id: str):
    """
    Genera un Certificado de Conformidad Fitosanitaria oficial en formato PDF.
    Validará estrictamente que estado_aprobacion == 'aprobado'.
    """
    supabase = get_supabase_client()
    
    # 1. Fetch full inspection data
    ins_resp = (
        supabase.table("inspecciones")
        .select("*")
        .eq("id", inspeccion_id)
        .execute()
    )
    if not ins_resp.data:
        raise HTTPException(status_code=404, detail="Inspección no encontrada")
    
    inspeccion = ins_resp.data[0]
    
    # Validar que esté aprobado
    if inspeccion.get("estado_aprobacion") != "aprobado":
        raise HTTPException(
            status_code=400,
            detail="No se puede descargar el certificado de una inspección que no esté aprobada oficialmente."
        )
    
    # 2. Fetch Predio
    predio = {}
    predio_id = inspeccion.get("predio_id")
    if predio_id:
        predio_resp = supabase.table("predios").select("*").eq("id", predio_id).execute()
        if predio_resp.data:
            predio = predio_resp.data[0]
            
    # 3. Fetch Producer (Usuario)
    productor = {}
    productor_id = predio.get("productor_id") if predio else None
    if productor_id:
        prod_resp = supabase.table("usuarios").select("*").eq("id", productor_id).execute()
        if prod_resp.data:
            productor = prod_resp.data[0]
            
    # 4. Fetch Technician (Usuario)
    tecnico = {}
    tecnico_id = inspeccion.get("tecnico_id")
    if tecnico_id:
        tec_resp = supabase.table("usuarios").select("*").eq("id", tecnico_id).execute()
        if tec_resp.data:
            tecnico = tec_resp.data[0]

    # 5. Fetch all Lotes of this predio
    lotes_names = "Todos los lotes"
    if predio_id:
        lotes_resp = supabase.table("lotes").select("nombre").eq("predio_id", predio_id).execute()
        if lotes_resp.data:
            lotes_names = ", ".join([l.get("nombre") for l in lotes_resp.data if l.get("nombre")])
            
    # 6. Start PDF Doc
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=50,
        rightMargin=50,
        topMargin=110,
        bottomMargin=70
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CertTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=17,
        leading=22,
        textColor=colors.HexColor('#1b4332'),
        alignment=1,
        spaceAfter=15,
        spaceBefore=10
    )
    
    subtitle_style = ParagraphStyle(
        'CertSub',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#2d6a4f'),
        alignment=1,
        spaceAfter=25
    )
    
    body_style = ParagraphStyle(
        'CertBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=15,
        textColor=colors.HexColor('#1f2937'),
        alignment=4 # Justify
    )
    
    body_bold = ParagraphStyle(
        'CertBodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    
    story = [
        Paragraph("CERTIFICADO DE CONFORMIDAD FITOSANITARIA", title_style),
        Paragraph("REPÚBLICA DE COLOMBIA<br/>MINISTERIO DE AGRICULTURA Y DESARROLLO RURAL", subtitle_style),
        Spacer(1, 10)
    ]
    
    # Official statement
    declaration = (
        "El <b>INSTITUTO COLOMBIANO AGROPECUARIO (ICA)</b> y la plataforma <b>FitoGestión</b> certifican que "
        "el predio agrícola descrito a continuación ha sido evaluado bajo los lineamientos y normativas fitosanitarias vigentes, "
        "obteniendo un diagnóstico satisfactorio y cumpliendo con las regulaciones de sanidad vegetal correspondientes."
    )
    story.append(Paragraph(declaration, body_style))
    story.append(Spacer(1, 20))
    
    # Certificate Info Table
    incidencia_global = float(inspeccion.get("incidencia_global_pct") or 0.0)
    nivel_alerta = str(inspeccion.get("nivel_alerta") or "Normal (Monitoreo)")
    
    cert_data = [
        [Paragraph("<b>Nombre del Predio:</b>", body_style), Paragraph(str(predio.get("nombre", "N/A")), body_bold),
         Paragraph("<b>Registro ICA:</b>", body_style), Paragraph(str(predio.get("numero_registro_ica") or "N/A"), body_bold)],
        [Paragraph("<b>Productor / Propietario:</b>", body_style), Paragraph(str(productor.get("nombre", "N/A")), body_style),
         Paragraph("<b>Departamento / Municipio:</b>", body_style), Paragraph(f"{predio.get('departamento', 'N/A')} - {predio.get('municipio', 'N/A')}", body_style)],
        [Paragraph("<b>Lotes Certificados:</b>", body_style), Paragraph(lotes_names, body_bold),
         Paragraph("<b>Vereda:</b>", body_style), Paragraph(str(predio.get("vereda") or "N/A"), body_style)],
        [Paragraph("<b>ID de Inspección:</b>", body_style), Paragraph(str(inspeccion.get("id")), body_style),
         Paragraph("<b>Fecha de Evaluación:</b>", body_style), Paragraph(str(inspeccion.get("fecha_inspeccion")), body_style)],
        [Paragraph("<b>Inspector Evaluador:</b>", body_style), Paragraph(str(tecnico.get("nombre", "N/A")), body_style),
         Paragraph("<b>Incidencia Global:</b>", body_style), Paragraph(f"{incidencia_global:.2f}% ({nivel_alerta})", body_bold)]
    ]
    t_cert = Table(cert_data, colWidths=[120, 136, 120, 136])
    t_cert.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f8f9fa')),
        ('BACKGROUND', (2,0), (2,-1), colors.HexColor('#f8f9fa')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_cert)
    story.append(Spacer(1, 20))
    
    # Validity statement
    fecha_cierre_val = inspeccion.get("fecha_cierre") or inspeccion.get("fecha_inspeccion")
    validity_text = (
        "Se expide el presente certificado bajo la plataforma <b>FitoGestión</b> para fines comerciales, de movilización y exportación de productos agrícolas. "
        "Este certificado es válido y acredita el buen estado fitosanitario del lote evaluado, exhortando al productor a mantener las buenas prácticas agrícolas.<br/><br/>"
        f"<b>Fecha de Expedición:</b> {fecha_cierre_val}<br/>"
        "<b>Período de Vigencia:</b> 90 días calendario a partir de la fecha de expedición."
    )
    story.append(Paragraph(validity_text, body_style))
    story.append(Spacer(1, 40))
    
    # Signatures
    sig_data = [
        [
            Paragraph("_____________________________<br/><b>Director de Sanidad Vegetal ICA</b><br/>República de Colombia", body_style),
            Paragraph("_____________________________<br/><b>Inspector Autorizado ICA</b><br/>Firma y Sello Digital", body_style)
        ]
    ]
    t_sig = Table(sig_data, colWidths=[256, 256])
    t_sig.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(KeepTogether(t_sig))
    
    doc.build(story, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Certificado_Fitosanitario_{inspeccion_id}.pdf"}
    )


