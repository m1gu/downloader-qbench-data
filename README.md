# Downloader QBench Data

Aplicacion Python para descargar y mantener sincronizada la informacion de QBench en una base de datos PostgreSQL local. Actualmente cubre la descarga de **customers**, **orders**, **samples** y **batches** con soporte para cargas completas e incrementales, incluyendo checkpoints y manejo de errores.

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
├── docs/
│   └── roadmap.md            # Plan de trabajo y notas
├── scripts/
│   ├── run_sync_customers.py # Ejecuta la sincronizacion de clientes
│   ├── run_sync_orders.py    # Ejecuta la sincronizacion de ordenes
│   ├── run_sync_samples.py   # Ejecuta la sincronizacion de muestras
│   └── run_sync_batches.py   # Ejecuta la sincronizacion de batches
├── src/
│   └── downloader_qbench_data/
│       ├── clients/          # Cliente HTTP QBench
│       ├── config.py         # Carga de configuracion y .env
│       ├── ingestion/        # Pipelines de ingesta
│       └── storage/          # Modelos y acceso a base de datos
├── tests/                    # Pruebas unitarias
├── requirements.txt          # Dependencias del proyecto
├── README.md                 # Este archivo
└── .env.example              # Plantilla de variables de entorno
```

## Ejecucion
1. Asegurate de tener la base y credenciales configuradas en `.env`.
2. Activa el entorno virtual y ejecuta la sincronizacion deseada:
   ```bash
   # Full refresh de clientes
   python scripts/run_sync_customers.py --full

   # Sincronizacion incremental de clientes
   python scripts/run_sync_customers.py

   # Full refresh de ordenes (requiere clientes precargados)
   python scripts/run_sync_orders.py --full

   # Full refresh de samples (requiere ordenes cargadas previamente)
   python scripts/run_sync_samples.py --full

   # Full refresh de batches (requiere customers/orders cargados previamente)
   python scripts/run_sync_batches.py --full
   ```
   Todos los scripts muestran una barra de progreso por pagina (`tqdm`).

3. Verifica los registros en PostgreSQL (`customers`, `orders`, `samples`, `batches`, `sync_checkpoints`).

## Proximos pasos
- Completar pipelines para tests, assays y reports.
- Construir UI PySide6 con boton "ACTUALIZAR" y estado de ultimo sync.
- Exponer API REST con FastAPI para servir los datos a dashboards externos.

## Contribucion
1. Crea una rama: `git checkout -b feature/x`.
2. Ejecuta pruebas (`pytest`).
3. Abre PR describiendo cambios y resultados.

## Licencia
Proyecto interno; ajustar segun politicas de la empresa.

