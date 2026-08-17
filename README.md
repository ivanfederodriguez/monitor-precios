# Monitor de Precios

Dashboard en Streamlit para explorar la evolución semanal de precios por producto, supermercado y categoría. La aplicación consulta una base MySQL, prepara las series con pandas y presenta filtros, métricas resumidas y gráficos interactivos con Plotly.

## Qué demuestra

- Consulta relacional de precios, productos, supermercados y categorías.
- Validación y preparación de precios y fechas antes de graficar.
- Filtros interactivos por supermercado y categoría.
- Visualización de series temporales por producto.
- Configuración segura mediante secretos de Streamlit o variables de entorno.

## Arquitectura

```text
MySQL → consulta parametrizada → pandas → filtros Streamlit → Plotly + métricas
```

El repositorio contiene la capa de aplicación. La base de datos y sus credenciales no forman parte del código público.

## Puesta en marcha

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
streamlit run app.py
```

Completa `.streamlit/secrets.toml` con una cuenta de base de datos de solo lectura:

```toml
[mysql]
host = "db.example.org"
port = 3306
user = "readonly_user"
password = "replace_me"
database = "prices"
```

Como alternativa, define `MONITOR_DB_HOST`, `MONITOR_DB_PORT`, `MONITOR_DB_USER`, `MONITOR_DB_PASSWORD` y `MONITOR_DB_NAME`.

## Estructura

- `app.py`: conexión, consulta, transformación e interfaz.
- `requirements.txt`: dependencias mínimas.
- `.streamlit/secrets.toml.example`: plantilla sin credenciales.

## Alcance y privacidad

La aplicación necesita una fuente de datos privada y no incluye datos de producción. No subas `.streamlit/secrets.toml`; el archivo ya está excluido por `.gitignore`. Para un despliegue público, usa una cuenta MySQL con permisos mínimos y restringe el acceso de red.
