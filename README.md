# Downloader QBench Data

Aplicación Python para descargar y mantener sincronizada la información de QBench en una base de datos PostgreSQL local. Actualmente cubre la descarga de **customers**, **orders** y **batches** con soporte para cargas completas e incrementales, incluyendo checkpoints y manejo de errores.

## Tecnologías principales
- Python 3.12+
- [httpx](https://www.python-httpx.org/) para consumo de la API QBench
- [SQLAlchemy](https://www.sqlalchemy.org/) y PostgreSQL para persistencia
- [pandas](https://pandas.pydata.org/) (planeado para validaciones)
- [PySide6](https://doc.qt.io/qtforpython/) (fase posterior para UI manual)
- [FastAPI](https://fastapi.tiangolo.com/) (fase posterior para exponer los datos)

## Requisitos previos
1. Python 3.12 instalado y disponible en `PATH`.
2. PostgreSQL accesible (local o remoto) con el rol/base configurados.
3. Credenciales QBench válidas (ID, secret y endpoint de token).
4. [git](https://git-scm.com/) si vas a clonar/colaborar.

## Instalación y configuración
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
├── scripts/\n│   ├── run_sync_customers.py # Ejecuta la sincronización de clientes\n│   ├── run_sync_orders.py    # Ejecuta la sincronización de órdenes\n│   └── run_sync_batches.py   # Ejecuta la sincronización de batches
├── src/
│   └── downloader_qbench_data/
│       ├── clients/          # Cliente HTTP QBench
│       ├── config.py         # Carga de configuración y .env
│       ├── ingestion/        # Pipelines de ingesta
│       └── storage/          # Modelos y acceso a base de datos
├── tests/                    # Pruebas unitarias
├── requirements.txt          # Dependencias del proyecto
├── README.md                 # Este archivo
└── .env.example              # Plantilla de variables de entorno
```

## Ejecución
1. Asegúrate de tener la base y credenciales configuradas en `.env`.
2. Activa el entorno virtual y ejecuta la sincronización deseada:
   ```bash
   # Full refresh de clientes
   python scripts/run_sync_customers.py --full

   # Sincronización incremental de clientes
   python scripts/run_sync_customers.py

   # Full refresh de órdenes (requiere clientes precargados)\n   python scripts/run_sync_orders.py --full\n\n   # Full refresh de batches (requiere customers/orders cargados previamente)\n   python scripts/run_sync_batches.py --full
   ```
   Ambas herramientas muestran una barra de progreso por página (`tqdm`).

3. Verifica los registros en PostgreSQL (`customers`, `orders`, `sync_checkpoints`).





