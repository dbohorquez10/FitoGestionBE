# 🟢 **FitoGestión Backend – Sistema de Control Fitosanitario**

### Proyecto Integrador – Ingeniería de Sistemas
**Universidad de Investigación y Desarrollo (UDI)**
**Entrega Final – Backend (FastAPI & PostgreSQL)**

---

# 🎥 Video del prototipo funcionando

🔗 [https://www.youtube.com/watch?v=tu_video_aqui](https://www.youtube.com/watch?v=tu_video_aqui)

---

# 📌 Descripción general

El backend de **FitoGestión** está diseñado bajo una arquitectura orientada a microservicios autónomos (`ms-core-agricola` y `ms-inspecciones`), construidos con **FastAPI** y **Python**. Sirve como el motor central transaccional y de seguridad para la plataforma del **Instituto Colombiano Agropecuario (ICA)**.

El sistema garantiza alta concurrencia, validación estricta de datos y control de accesos mediante la integración segura con **Supabase (PostgreSQL y Auth)**.

* ✔ **Control de Acceso basado en Roles (RBAC)** aplicado a nivel de endpoints.
* ✔ Lógica inteligente de **asignación de inspecciones** (prevención de colisiones de agenda).
* ✔ **Gestión integral de activos:** Predios, lotes (con límites lógicos) y catálogos de cultivos/plagas.
* ✔ Optimización de rendimiento mediante **Procedimientos Almacenados (RPC)** en Base de Datos.
* ✔ Arquitectura de base de datos relacional con integridad referencial estricta.

---

# 🎯 Objetivos del sistema

* Proveer una API RESTful rápida y segura para el consumo desde aplicaciones web y móviles.
* Garantizar la consistencia de los datos agrícolas y fitosanitarios evitando inserciones anómalas (ej. hectáreas negativas, coordenadas inválidas).
* Centralizar la lógica de negocio de las inspecciones, delegando el cómputo pesado a la base de datos mediante funciones SQL.
* Proteger la información sensible asegurando que cada rol solo acceda y modifique sus propios recursos.

---

## 🗂️ Estructura del Código Fuente

```plaintext
FitoGestionBE/
│
├── ms-core-agricola/             # Microservicio de gestión de usuarios y predios
│   ├── app/
│   │   ├── api/                  # Endpoints (auth.py, predios.py, catalogos.py)
│   │   ├── core/                 # Lógica de seguridad y RBAC (security.py)
│   │   └── schemas/              # Modelos de validación estricta (Pydantic)
│   └── main.py
│
├── ms-inspecciones/              # Microservicio de ejecución de visitas técnicas
│   ├── app/
│   │   └── api/                  # Endpoints (inspecciones.py, registro_plantas.py)
│   └── main.py
│
└── sql/
    └── init_db.sql               # Esquemas relacionales, Triggers y funciones RPC
```

---

# 🔐 Roles del sistema (API)

### 🟩 **ADMINISTRADOR**
Acceso total a los recursos del sistema:
* Aprueba o rechaza solicitudes de inspección manuales.
* Modifica y aprueba plagas sugeridas en los catálogos globales.
* Administra usuarios (CRUD de técnicos y productores).

### 🟦 **TECNICO ICA**
Permisos de escritura limitados a la operación en campo:
* Registra plantas evaluadas e incidencias fitosanitarias.
* Sugiere nuevas plagas (`estado: pendiente`) durante las visitas.
* Finaliza inspecciones asignadas a su perfil.

### 🟧 **PRODUCTOR**
Acceso restringido a su propia información:
* Lee, crea y elimina *únicamente* sus propios predios y lotes.
* Solicita inspecciones de sus cultivos.

---

# 🗄️ Base de datos y Despliegue

Conexión utilizada mediante entorno Cloud:

| Parámetro    | Valor                   |
| ------------ | ----------------------- |
| Motor DB     | PostgreSQL (Supabase)   |
| Autenticación| Supabase Auth (JWT)     |
| Hosting API  | Railway                 |
| Servidor     | Uvicorn                 |

---

# 🚨 Lógica clave implementada

## **1️⃣ Control de Roles Dinámico (RBAC)**
Protección de rutas mediante Inyección de Dependencias en FastAPI.
```python
@router.delete("/{predio_id}", status_code=204)
def eliminar_predio(
    predio_id: str,
    current_user: dict = Depends(require_role(['productor', 'admin']))
):
    # Lógica que verifica que el predio pertenece al usuario actual
    pass
```

## **2️⃣ Optimización de Consultas (RPC)**
Cálculo en vivo de alertas fitosanitarias delegando la carga a Supabase para evitar cuellos de botella (N+1).
```python
@router.get("/alerta/{cultivo_id}/{plaga_id}")
def obtener_alerta_fitosanitaria(cultivo_id: str, plaga_id: str):
    result = supabase.rpc("fn_alerta_fitosanitaria", {
        "p_cultivo_id": cultivo_id,
        "p_plaga_id": plaga_id
    }).execute()
    return result.data
```

---

# 📊 Estado del proyecto (FINAL)

| Módulo                 | Estado                   |
| ---------------------- | ------------------------ |
| Conexión Supabase      | ✔                        |
| Auth y RBAC (JWT)      | ✔                        |
| CRUD Cultivos/Plagas   | ✔                        |
| CRUD Productores/Tecs  | ✔                        |
| CRUD Predios/Lotes     | ✔                        |
| Prevención Colisiones  | ✔                        |
| Inspecciones (Bulk)    | ✔                        |
| Alertas Fitosanitarias | ✔                        |
| Validaciones Pydantic  | ✔                        |

---

# 🛠️ Tecnologías utilizadas

| Categoría    | Tecnología         |
| ------------ | ------------------ |
| Lenguaje     | Python 3.10+       |
| Framework    | FastAPI            |
| Validación   | Pydantic v2        |
| BD           | PostgreSQL         |
| BaaS / Auth  | Supabase           |
| Arquitectura | Microservicios     |

---

# 🚀 Mejoras futuras

* Panel estadístico avanzado (cultivos más afectados, zonas críticas).
* Integración directa con servicios web heredados del ICA.
* Exportación automatizada de reportes a PDF desde el backend.

---

# ✒️ Autores

**Darwing Yailang Bohórquez Jaimes** **Karen Rocío Cristancho Fajardo** **Jhonatan Arturo Castro Arguello** Estudiantes de Ingeniería de Sistemas – V Semestre  
**Universidad de Investigación y Desarrollo (UDI)** 📅 2026
