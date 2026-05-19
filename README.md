# 🌦️ SkyCast

> **Enterprise Climate Intelligence Platform**

> **Data Engineering | Data Science | Data Analytics**

Plataforma de monitorización climática en tiempo real para España. Integra datos oficiales de AEMET, analytics avanzado, dashboards interactivos y alertas inteligentes.

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.42+-red?logo=streamlit)](https://streamlit.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?logo=postgresql)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Supported-blue?logo=docker)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/Tests-24%20passing-brightgreen)](https://pytest.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 🎯 Funcionalidades Principales

### API REST — FastAPI + Pydantic
- **Autenticación industrial**: SHA-256 + salt único por usuario + JWT
- **Datos oficiales**: AEMET OpenData (85+ estaciones meteorológicas)
- **Geolocalización**: IP-API + Nominatim (OpenStreetMap) + Haversine
- **Rate limiting**: 30 req/min para `/clima`, 10 req/min para `/geo`
- **Caché offline**: 30 min para datos AEMET, 1hr para geocoding
- **Validación física**: Rangos -20/60°C, 0-100% humedad, 0-150 km/h viento
- **Documentación automática**: Swagger UI + ReDoc en `/docs`

### Dashboard BI — Streamlit + Plotly + Geopandas
- **5 páginas interactivas**: Ejecutivo, Científico, Auditoría, Mapa, Config
- **Análisis científico**: SMA 24h, correlación, detección de anomalías (2 std dev)
- **Mapas geoespaciales**: Folium + Geopandas con marcadores y heatmaps
- **Gráficos Plotly**: Líneas, áreas, boxplots, scatter, pie, geo-scatter
- **KPIs en tiempo real**: Temperatura, humedad, viento, lluvia, presión

### Data Engineering
- **ETL pipeline**: Extract → Transform (Pandas) → Load (SQLAlchemy)
- **Detección de anomalías**: Std deviation + IQR
- **Scheduler automático**: APScheduler (fetch AEMET cada 2h)
- **Base de datos**: PostgreSQL con schema normalizado (9 tablas, FK, índices)

---

## 🚀 Inicio Rápido

### Requisitos
- Python 3.11+
- PostgreSQL 16+ (o SQLite para desarrollo)
- Docker + Docker Compose (opcional)

### 1. Clonar y configurar

```bash
# Clonar el repositorio
git clone https://github.com/juandelaf1/SkyCast.git
cd SkyCast-Analytics

# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env y añadir tu AEMET_API_KEY
```

### 2. Obtener clave AEMET

1. Regístrate en [AEMET OpenData](https://opendata.aemet.es/centrodedescargas/obtencionAPIKey)
2. Añade tu clave en `.env`:
   ```
   AEMET_API_KEY=tu_clave_aemet
   SECRET_KEY=tu_clave_secreta_minimo_32_caracteres
   ```

### 3. Inicializar base de datos

```bash
python -m app.db
```

### 4. Ejecutar la API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Accede a:
- API: http://localhost:8000
- Swagger Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 5. Ejecutar el Dashboard

```bash
# En otra terminal
streamlit run app/dashboard/app.py --server.port 8501
```

Dashboard: http://localhost:8501

---

## 🐳 Docker (Producción)

```bash
cd docker
docker-compose up -d
```

| Servicio | Puerto | URL |
|----------|--------|-----|
| API | 8000 | http://localhost:8000/docs |
| Dashboard | 8501 | http://localhost:8501 |
| PostgreSQL | 5432 | localhost:5432 |

---

## 📡 API Endpoints

### Autenticación

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/register` | Registro de usuario |
| `POST` | `/api/v1/auth/login` | Inicio de sesión |
| `GET` | `/api/v1/auth/me` | Usuario actual |

### Clima

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/v1/clima` | Clima por coordenadas o IP |
| `GET` | `/api/v1/clima/{ciudad}` | Clima por nombre de ciudad |

### Geolocalización

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/v1/geo/{ciudad}` | Geocodificar ciudad |

### Sistema

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/v1/health` | Health check |
| `GET` | `/api/v1/health/stats` | Estadísticas de uso |

### Alertas

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/v1/alertas` | Obtener umbrales de alerta |
| `POST` | `/api/v1/alertas` | Crear/actualizar umbral |

### Registros

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/v1/registros` | Listar registros |
| `POST` | `/api/v1/registros` | Crear registro manual |

### Comparación

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/v1/comparar` | Comparar dato manual vs AEMET |

---

## 🏗️ Arquitectura

```
skycast/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── api/v1/              # REST endpoints (FastAPI)
│   │   ├── auth.py          # Register, login, me
│   │   ├── clima.py         # Weather data
│   │   ├── geo.py           # Geolocation
│   │   ├── health.py        # Health & stats
│   │   ├── alerts.py        # Alert thresholds
│   │   ├── records.py       # Manual records
│   │   └── comparison.py     # Manual vs AEMET
│   ├── auth/
│   │   └── jwt_auth.py      # JWT dependency
│   ├── services/
│   │   ├── aemet_service.py  # AEMET API integration
│   │   ├── geolocation_service.py  # IP + Nominatim
│   │   └── alert_service.py  # Alert generation
│   ├── db/
│   │   ├── models/          # 9 SQLAlchemy models
│   │   ├── session.py       # DB connection
│   │   └── seed.py          # Initial data
│   ├── etl/
│   │   ├── extract.py       # JSON extraction
│   │   ├── transform.py     # Pandas cleaning
│   │   ├── load.py          # DB insertion
│   │   └── anomaly_detector.py  # 2-std detection
│   ├── scheduler/
│   │   └── tasks.py         # APScheduler (2h fetch)
│   └── dashboard/           # Streamlit BI
│       ├── app.py           # Entry point
│       ├── pages/           # 5 dashboard pages
│       └── components/      # Chart components
├── docker/
├── tests/                   # 24 unit tests
└── scripts/
```

### Schema de base de datos

```
zonas ──1:N── municipios ──1:N── estaciones ──1:N── mediciones ──1:N── alertas
                                                        │
                                                        └──N:1── fuentes_dato
umbrales_alerta (catálogo independiente)
usuarios
```

---

## 🧪 Testing

```bash
# Ejecutar todos los tests
pytest -v

# Con coverage
pytest --cov=app --cov-report=html

# Tests específicos
pytest tests/test_core -v
pytest tests/test_services -v
```

**24 tests cubriendo**: validators, alerts, haversine, ETL.

---

## 📊 Tecnologías

| Capa | Tecnología |
|------|-----------|
| **Backend** | FastAPI + Uvicorn + Pydantic |
| **Database** | SQLite (dev) / PostgreSQL (prod) + SQLAlchemy |
| **Dashboard** | Streamlit + Plotly + Geopandas + Folium |
| **Data** | Pandas + NumPy |
| **Auth** | JWT + SHA-256 + Salt |
| **Scheduling** | APScheduler |
| **Geospatial** | Haversine + Nominatim + GeoJSON |
| **Containerization** | Docker + Docker Compose |
| **Testing** | Pytest + httpx |

---

## 🌦️ Sistema de Alertas

| Nivel | Color | Condición | Icono |
|-------|-------|-----------|-------|
| 🔴 ROJO | `#DC2626` | Temp >= 40°C, Viento >= 70 km/h, Lluvia >= 30mm, Humedad >= 90% | 🔥💨🌧️💧 |
| 🟠 NARANJA | `#EA580C` | Temp >= 35°C, Viento >= 50 km/h, Lluvia >= 15mm, Humedad >= 80% | 🟠💨🌧️💧 |
| 🟡 AMARILLO | `#FACC15` | Temp >= 30°C | 🌡️ |
| 🔵 AZUL | `#2563EB` | Temp <= 0°C | ❄️ |
| 🟢 VERDE | `#4ade80` | Sin alertas | ✅ |

---

## 📁 Datos de Estaciones (Seed)

El proyecto incluye datos iniciales de:
- **Madrid-Retiro** (3195)
- **Madrid-Golfo de Vizcaya** (3129)
- **Alcalá de Henares** (3170)
- **Getafe** (3200)
- **Torrejón de Ardoz** (3266)

Con 15 municipios de la Comunidad de Madrid y 5 zonas geográficas.

---

## 🔒 Seguridad

- **Contraseñas**: Hash SHA-256 con salt único por usuario (`secrets.token_hex(16)`)
- **Complejidad**: Mínimo 8 caracteres, 1 mayúscula, 1 minúscula, 1 dígito
- **Tokens**: JWT con expiración configurable (24h por defecto)
- **Validación**: Pydantic en todos los endpoints + validación física de rangos

---

## 📈 Roadmap

- [ ] Integración con más fuentes de datos (OpenWeather, weatherapi)
- [ ] Dashboard de métricas de anomalías en tiempo real
- [ ] Exportación a PDF/Excel de reports
- [ ] Notificaciones push (email/Telegram)
- [ ] Modelo predictivo de temperaturas
- [ ] Despliegue en cloud (Render/Railway/Fly.io)
- [ ] CI/CD con GitHub Actions

---

## 👤 Autor

**Juan de la Fuente**
- GitHub: [@juandelaf1](https://github.com/juandelaf1)

---

## 📄 Licencia

MIT © 2026 Juan de la Fuente

---

## 🌐 Evolución del Proyecto

Este repositorio es la **Fase 4 (Pre)** del ecosistema climático. Sirvió como puente entre Vortex y la versión Enterprise final.

| Fase | Proyecto | Estado |
|------|----------|--------|
| 🟣 | [← Vortex](https://github.com/juandelaf1/Vortex) | ETL + PostgreSQL + Lineage |
| 🟠 | **SkyCast V2 Pre ← (estás aquí)** | Analytics + JWT con salt + Docker |
| 🟢 | [SkyCast Enterprise →](https://github.com/juandelaf1/SkyCast) | Consolidación final |

**Lección aprendida:** JWT con SHA-256 + salt, detección de anomalías (std-dev + IQR), Docker Compose multicontenedor, dashboard Streamlit con 5 páginas, y rate limiting con slowapi.