# FitoGestión — Backend (Microservicios)

Arquitectura de Microservicios para el sistema de Gestión Fitosanitaria ICA.

## 🏗️ Arquitectura

```
Cliente (Angular :4200)
       │
       ▼
   Nginx Gateway (:8080)
       │
       ├──► /api/core/        →  ms-core-agricola (:8001)
       └──► /api/inspeccion/  →  ms-inspecciones  (:8002)
                                       │
                                       ▼
                                   Supabase (PostgreSQL)
```

## 📋 Servicios

| Servicio | Puerto | Descripción |
|---|---|---|
| **Gateway (Nginx)** | 8080 | Proxy reverso, enrutamiento y CORS |
| **ms-core-agricola** | 8001 | Usuarios, Catálogos (Plagas/Cultivos), Predios, Lotes |
| **ms-inspecciones** | 8002 | Inspecciones, Sub-inspecciones, Registro de Plantas |

## 🚀 Inicio Rápido

### 1. Configurar variables de entorno
```bash
cp .env.example .env
# Editar .env con las credenciales de Supabase
```

### 2. Crear tablas en Supabase
Ejecutar el script `sql/init_db.sql` en el **SQL Editor** de Supabase.

### 3. Levantar los servicios
```bash
docker compose up --build
```

### 4. Verificar
- Gateway: http://localhost:8080
- MS Core Docs: http://localhost:8080/api/core/docs
- MS Inspecciones Docs: http://localhost:8080/api/inspeccion/docs

## 🛠️ Stack Tecnológico

- **Python** 3.11+
- **FastAPI** — Framework web asíncrono
- **Supabase** — PostgreSQL como servicio (BaaS)
- **Nginx** — Gateway / Reverse Proxy
- **Docker & Docker Compose** — Contenedorización
