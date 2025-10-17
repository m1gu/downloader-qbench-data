# Downloader QBench Data

Aplicacion Python para descargar y mantener sincronizada la informacion de QBench en una base de datos PostgreSQL local. Actualmente cubre la descarga de **customers**, **orders**, **samples**, **tests** y **batches** con soporte para cargas completas e incrementales, incluyendo checkpoints y manejo de errores.

## Tecnologias principales
- Python 3.12+
- [httpx](https://www.python-httpx.org/) para consumo de la API QBench
- [SQLAlchemy](https://www.sqlalchemy.org/) y PostgreSQL para persistencia
- [pandas](https://pandas.pydata.org/) (planeado para validaciones)
- [PySide6](https://doc.qt.io/qtforpython/) (fase posterior para UI manual)
- [FastAPI](https://fastapi.tiangolo.com/) (fase posterior para exponer los datos)

## Requisitos previos
1. Python 3.12 instalado y disponible en `PATH`.
2. PostgreSQL accesible (local o remoto) con el rol/base configurados.
3. Credenciales QBench validas (ID, secret y endpoint de token).
4. [git](https://git-scm.com/) si vas a clonar/colaborar.

## Instalacion y configuracion
```bash
# Crear y activar entorno virtual (Windows PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno (copiar .env.example)
copy .env.example .env
# editar .env con credenciales QBench y datos de PostgreSQL
```

## Estructura del proyecto
```
Downloader-Qbench-Data/
|-- docs/
|   `-- roadmap.md            # Plan de trabajo y notas
|-- scripts/
|   |-- run_sync_customers.py # Ejecuta la sincronizacion de clientes
|   |-- run_sync_orders.py    # Ejecuta la sincronizacion de ordenes
|   |-- run_sync_samples.py   # Ejecuta la sincronizacion de muestras
|   |-- run_sync_batches.py   # Ejecuta la sincronizacion de batches
|   |-- run_sync_all.py      # Orquesta todas las entidades
|   |-- run_api.py           # Levanta la API REST
|   `-- run_sync_tests.py    # Ejecuta la sincronizacion de tests
|-- src/
|   `-- downloader_qbench_data/
|       |-- clients/          # Cliente HTTP QBench
|       |-- config.py         # Carga de configuracion y .env
|       |-- ingestion/        # Pipelines de ingesta
|       `-- storage/          # Modelos y acceso a base de datos
|-- tests/                    # Pruebas unitarias
|-- requirements.txt          # Dependencias del proyecto
|-- README.md                 # Este archivo
`-- .env.example              # Plantilla de variables de entorno
```

## Ejecucion
1. Asegurate de tener la base y credenciales configuradas en `.env`.
2. Activa el entorno virtual antes de ejecutar cualquier script (`.\.venv\Scripts\Activate` en PowerShell).
3. Lanza la sincronizacion de la entidad necesaria. Ejemplos de full refresh:
   ```bash
   python scripts/run_sync_all.py --full     # ejecuta todas las entidades en secuencia
   python scripts/run_sync_customers.py --full
   python scripts/run_sync_orders.py --full      # requiere customers
   python scripts/run_sync_samples.py --full     # requiere orders
   python scripts/run_sync_batches.py --full     # requiere customers/orders/samples
   python scripts/run_sync_tests.py --full       # requiere samples y batches
   ```
   Omite `--full` para realizar sincronizaciones incrementales aprovechando el checkpoint almacenado.
   El comando `run_sync_all.py` acepta argumentos adicionales, por ejemplo:
   ```bash
   python scripts/run_sync_all.py                 # incremental de todas las entidades
   python scripts/run_sync_all.py --entity orders --entity samples
   ```
   Si se especifican entidades individuales, la sincronizacion respeta el orden y detiene la ejecucion ante el primer fallo para evitar inconsistencias.
4. Levanta la API REST si necesitas exponer los datos sincronizados:
   ```bash
   python scripts/run_api.py --host 0.0.0.0 --port 8000
   ```
   Esto publica la documentacion interactiva en `http://localhost:8000/api/docs` y los endpoints REST descritos abajo.
5. Lanza el dashboard PySide6 (carga por defecto los ultimos 7 dias):
   ```bash
   python scripts/run_dashboard.py
   ```
   Puedes ajustar el backend usando la variable `DASHBOARD_API_BASE_URL` si el servicio corre en otro host.
6. Verifica los registros en PostgreSQL (`customers`, `orders`, `samples`, `batches`, `tests`, `sync_checkpoints`).
### Sincronizacion de tests
- El pipeline usa el script `scripts/run_sync_tests.py` y crea/actualiza el checkpoint `sync_checkpoints.entity = 'tests'`.
- Solo se persistiran tests cuyo `sample_id` exista localmente; si falta se registra en el resumen y se omite.
- Durante la sincronizacion incremental se detiene automaticamente al encontrar registros ya sincronizados (`date_created` <= ultimo checkpoint).
- Cuando QBench no entrega metadatos clave (label, titulo, worksheet, bandera de reporte) el proceso realiza un `fetch_test` individual y guarda el contenido bruto en `tests.worksheet_raw`.
- Argumentos disponibles:
  - `--full``: fuerza un refresh completo, ignorando el checkpoint previo.
  - `--page-size``: sobrescribe el `page_size` configurado (maximo 50 por restricciones de la API).
- El script muestra progreso por pagina con `tqdm` y al finalizar imprime un resumen con totales procesados, omisiones y la ultima fecha sincronizada.
### API REST
- `GET /api/health`: verificacion rapida del servicio.
- `GET /api/v1/metrics/summary`: KPIs globales (samples, tests, customers, reports) y TAT promedio.
- `GET /api/v1/metrics/activity/daily`: serie diaria de samples/tests (con comparativo opcional del periodo previo).
- `GET /api/v1/metrics/samples/overview`: totales y distribuciones por estado/matrix filtrables por fecha, cliente y orden.
- `GET /api/v1/metrics/tests/overview`: conteos por estado y label de los tests con filtros opcionales por batch.
- `GET /api/v1/metrics/customers/new`: listado de clientes creados en el rango.
- `GET /api/v1/metrics/customers/top-tests`: top N clientes por tests en el rango.
- `GET /api/v1/metrics/tests/tat`: estadisticas de TAT (promedio, mediana, p95, distribucion y serie opcional por dia/semana).
- `GET /api/v1/metrics/tests/tat-breakdown`: detalle de TAT agrupado por label_abbr.
- `GET /api/v1/metrics/reports/overview`: resumen de reportes dentro/fuera del SLA.
- `GET /api/v1/metrics/tests/tat-daily`: serie diaria de TAT con desglose dentro/fuera de SLA y promedio m�vil.
- `GET /api/v1/metrics/common/filters`: catalogos basicos (clientes, estados) para poblar dashboards.
- `GET /api/v1/entities/samples/{sample_id}`: detalle de una muestra con orden/batches relacionados.
- `GET /api/v1/entities/tests/{test_id}`: detalle de un test con sample/batches.
