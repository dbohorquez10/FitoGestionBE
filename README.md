# FitoGestión Backend - API RESTful y Motor Transaccional para el ICA

FitoGestión Backend es la infraestructura de servicios y el motor transaccional que proporciona soporte al Sistema de Gestión Fitosanitaria del **Instituto Colombiano Agropecuario (ICA)**. Esta API RESTful está diseñada para gestionar con alta disponibilidad, seguridad y rendimiento el censo de predios, cultivos, lotes y el registro de inspecciones epidemiológicas en el campo colombiano.

---

## 🏗️ Arquitectura y Tecnologías

El sistema backend adopta un enfoque moderno de **Microservicios distribuidos**, orquestados a través de un Gateway reverso que unifica el punto de entrada para los clientes.

### Tecnologías Principales:
* **FastAPI (Python 3.11+)**: Framework web asíncrono de alto rendimiento utilizado para construir las APIs debido a su velocidad (al nivel de Go y NodeJS) y su soporte nativo para programación concurrente/asíncrona (`async/await`).
* **Supabase / PostgreSQL**: Base de datos relacional de nivel empresarial con soporte geoespacial que actúa como el backend-as-a-service (BaaS), proporcionando almacenamiento persistente y lógica en base de datos.
* **Nginx**: Gateway de API centralizado que actúa como proxy reverso, gestionando el enrutamiento de peticiones, la terminación SSL y las políticas de CORS.
* **Docker & Docker Compose**: Contenedorización completa de cada microservicio y del proxy reverso para garantizar la portabilidad y la paridad entre los entornos de desarrollo, pruebas y producción.

### Topología de Microservicios:

```
                  ┌───────────────────────┐
                  │   Cliente (Angular)   │
                  └───────────┬───────────┘
                              │ HTTP / HTTPS
                              ▼
                  ┌───────────────────────┐
                  │    Nginx (Gateway)    │ (Puerto 8080)
                  └──────┬─────────┬──────┘
                         │         │
        /api/core/*      │         │ /api/inspeccion/*
                         ▼         ▼
  ┌────────────────────────┐     ┌────────────────────────┐
  │   ms-core-agricola     │     │    ms-inspecciones     │
  │     (Puerto 8001)      │     │     (Puerto 8002)      │
  └──────────┬─────────────┘     └─────────────┬──────────┘
             │                                 │
             └───────────────┬─────────────────┘
                             ▼
                 ┌───────────────────────┐
                 │ Supabase (PostgreSQL) │
                 └───────────────────────┘
```

1. **`ms-core-agricola`**: Microservicio encargado del dominio geográfico e identitario. Administra los registros de usuarios (Productores, Técnicos, Administradores), catálogo fitosanitario de plagas y cultivos, predios (lugares de producción) y sus respectivos lotes agrícolas.
2. **`ms-inspecciones`**: Microservicio enfocado en el flujo transaccional de campo. Administra el ciclo de vida de las visitas técnicas (solicitudes, asignaciones, ejecuciones y cierres), sub-inspecciones por lote y el censo detallado de plantas afectadas, además de la generación de reportes oficiales en formato PDF.

---

## 🔐 Seguridad y Control de Acceso (RBAC)

El sistema implementa un modelo estricto de **Control de Acceso Basado en Roles (RBAC - Role-Based Access Control)** acoplado a la verificación de tokens criptográficos **JWT (JSON Web Tokens)**.

### Flujo de Autenticación y Autorización:
1. **Inyección de Dependencias de Seguridad**: FastAPI valida el token JWT en cada solicitud entrante mediante el extractor de dependencias `get_current_user`.
2. **Validación de Identidad**: El token extraído de la cabecera `Authorization: Bearer <token>` se verifica directamente contra el servicio de autenticación de Supabase. Si es válido y el usuario está marcado como `activo = True`, se recupera su perfil completo de la base de datos.
3. **Control de Acceso de Ruta (`require_role`)**: Se protegen las rutas críticas utilizando decoradores basados en dependencias que limitan la ejecución a roles específicos (`admin`, `tecnico`, `productor`).

```python
# Ejemplo de protección de endpoint con require_role
@router.patch("/{inspeccion_id}/aprobacion")
def evaluar_aprobacion(inspeccion_id: str, 
                       evaluacion: EvaluacionAprobacion,
                       current_user: dict = Depends(require_role(['admin']))):
    # Solo los usuarios con rol 'admin' pueden ejecutar esta acción
    ...
```

### Roles y Permisos Definidos:
* **Administrador (`admin`)**: Acceso global de lectura/escritura. Es el único rol facultado para gestionar catálogos de cultivos y plagas (aprobar sugerencias), crear o suspender usuarios, eliminar registros e inspecciones, y emitir evaluaciones de aprobación oficiales sobre inspecciones críticas.
* **Técnico ICA (`tecnico`)**: Permiso para visualizar su agenda de visitas asignadas, iniciar e inspeccionar lotes (crear sub-inspecciones y registros de plantas), proponer nuevas plagas al catálogo, y finalizar inspecciones de campo.
* **Productor (`productor`)**: Acceso restringido a su propia información de producción. Puede dar de alta sus predios y lotes, solicitar inspecciones fitosanitarias para sus tierras, y descargar los informes PDF aprobados por el ICA.

---

## ⚡ Lógica de Negocio y Rendimiento

Para asegurar la robustez de los datos y un alto desempeño ante consultas masivas, el backend aprovecha la validación tipada en la capa de aplicación y la delegación de cómputo pesado a la base de datos.

### 1. Validación Estricta con Pydantic
Cada entrada de datos es validada en tiempo de ejecución por esquemas de **Pydantic**. Esto previene la inyección de datos malformados y asegura que se cumplan las restricciones lógicas básicas (como expresiones regulares para campos de severidad o rangos flotantes para tasas de incidencia):

```python
class RegistroPlantaCreate(BaseModel):
    sub_inspeccion_id: str
    numero_planta: int
    plaga_id: Optional[str] = None
    sintoma: Optional[str] = None
    severidad: Optional[str] = Field(None, pattern="^(leve|moderado|severo)$")
    incidencia: Optional[float] = Field(None, ge=0.0, le=100.0)
    estado_planta: str = Field("sana", pattern="^(sana|enferma|muerta)$")
    observaciones: Optional[str] = None
```

### 2. Optimización con Procedimientos Almacenados (RPC)
Para evitar el cuello de botella que supone procesar miles de registros de plantas en la capa de aplicación (efecto *N+1 queries*), los cálculos analíticos complejos y masivos se delegan a **Procedimientos Almacenados (Stored Procedures)** programados directamente en PL/pgSQL dentro de la base de datos PostgreSQL, los cuales son invocados mediante Remote Procedure Calls (RPC):
* **`fn_alerta_fitosanitaria`**: Calcula dinámicamente y en milisegundos el nivel de alerta epidemiológico de un cultivo y plaga específicos (Bajo, Medio, Crítico), evaluando los datos históricos de todas las inspecciones realizadas en la zona sin necesidad de transferir millones de filas por la red.
* **`fn_generar_informe_inspeccion`**: Consolida todas las sub-inspecciones y conteos de plantas enfermas en un solo objeto JSON estructurado, listo para el consumo del generador de PDF.

---

## 🚀 Guía de Despliegue

### Requisitos Previos:
* Python 3.11 o superior instalado.
* Docker y Docker Compose instalados.
* Cuenta activa en Supabase (PostgreSQL).

### 1. Configuración de Variables de Entorno (Local)
Duplique el archivo `.env.example` en la raíz de cada microservicio y configure los valores correspondientes:

```bash
cp .env.example .env
```

El archivo `.env` debe incluir las variables de conexión a su proyecto de Supabase:
```ini
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_ANON_KEY=tu-anon-key-publica
SUPABASE_SERVICE_ROLE_KEY=tu-service-role-key-privada
```

### 2. Inicialización de la Base de Datos
Acceda al **SQL Editor** de su consola de Supabase y ejecute el contenido del archivo `sql/init_db.sql` y las migraciones subsiguientes de la carpeta `sql/` para levantar el esquema de tablas, restricciones de integridad referencial, roles por defecto y procedimientos almacenados (RPC).

### 3. Ejecución Local con Docker Compose
Para iniciar toda la infraestructura localmente (microservicios y gateway proxy Nginx), ejecute en la raíz del proyecto:

```bash
docker compose up --build
```

Una vez iniciados los contenedores, los servicios estarán disponibles en:
* **Gateway Unificado**: `http://localhost:8080`
* **Swagger ms-core-agricola**: `http://localhost:8080/api/core/docs`
* **Swagger ms-inspecciones**: `http://localhost:8080/api/inspeccion/docs`

### 4. Despliegue en Producción (Railway)
Para desplegar la API en producción utilizando la plataforma **Railway**:
1. Conecte su repositorio de GitHub a Railway.
2. Cree servicios independientes para cada microservicio (`ms-core-agricola` y `ms-inspecciones`) y para el gateway de Nginx.
3. Configure las variables de entorno en la sección *Variables* de Railway. Es mandatorio establecer:
   * `SUPABASE_URL`: URL del proyecto Supabase.
   * `SUPABASE_SERVICE_ROLE_KEY`: Clave de rol de servicio (Service Role Key) para permitir modificaciones administrativas autorizadas.

---

✒️ Autores
Darwing Yailang Bohórquez Jaimes
Karen Rocío Cristancho Fajardo
Jhonatan Arturo Castro Arguello
Estudiantes de Ingeniería de Sistemas – V Semestre
Universidad de Investigación y Desarrollo (UDI)
📅 2026
