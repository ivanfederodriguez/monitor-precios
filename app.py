import os

import streamlit as st
import pymysql
import pandas as pd
import plotly.graph_objects as go

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Monitor de Precios", layout="wide")

# --- GESTIÓN DE SECRETOS Y CONEXIÓN ---
def get_db_config():
    """Load database settings without embedding credentials in source code."""
    try:
        mysql = st.secrets["mysql"]
        return {
            "host": mysql["host"],
            "user": mysql["user"],
            "password": mysql["password"],
            "database": mysql["database"],
            "port": int(mysql.get("port", 3306)),
        }
    except Exception:
        env_config = {
            "host": os.getenv("MONITOR_DB_HOST"),
            "user": os.getenv("MONITOR_DB_USER"),
            "password": os.getenv("MONITOR_DB_PASSWORD"),
            "database": os.getenv("MONITOR_DB_NAME"),
            "port": int(os.getenv("MONITOR_DB_PORT", "3306")),
        }
        missing = [key for key in ("host", "user", "password", "database") if not env_config[key]]
        if missing:
            raise RuntimeError(
                "Database configuration is missing. Add the [mysql] settings "
                "to .streamlit/secrets.toml or define the MONITOR_DB_* environment variables."
            )
        return env_config


def get_db_connection():
    return pymysql.connect(**get_db_config())

# --- CACHÉ DE DATOS ---
@st.cache_data(ttl=3600)
def cargar_datos(fecha_inicio, fecha_fin):
    query = """
    SELECT 
        p.id_link_producto, p.precio_normal, p.fecha_extraccion,
        s.nombre AS nombre_supermercado, c.nombre AS nombre_categoria
    FROM precios_productos p
    INNER JOIN link_productos l ON p.id_link_producto = l.id_link_producto
    INNER JOIN supermercados s ON l.id_supermercado = s.id_super
    INNER JOIN categorias c ON l.id_categoria = c.id_categoria
    WHERE p.fecha_extraccion BETWEEN %s AND %s
      AND p.id_extraccion NOT IN (1, 4, 5, 6);
    """
    conn = None
    try:
        conn = get_db_connection()
        return pd.read_sql(query, conn, params=(fecha_inicio, fecha_fin))
    except Exception:
        st.error("No se pudieron cargar los datos. Revisa la configuración y disponibilidad de la base.")
        return pd.DataFrame()
    finally:
        if conn is not None:
            conn.close()

# --- INTERFAZ PRINCIPAL ---
st.title("📊 Dinámica de Precios Semanal")
st.markdown("Monitor interactivo de evolución de precios por supermercado y categoría.")

# Fechas fijas según tu script original
FECHA_INICIO = '2026-02-02'
FECHA_FIN = '2026-02-13'

with st.spinner('Conectando a base de datos...'):
    df = cargar_datos(FECHA_INICIO, FECHA_FIN)

if not df.empty:
    # --- PREPROCESAMIENTO ---
    df['precio_normal'] = pd.to_numeric(df['precio_normal'], errors='coerce')
    df = df[(df['precio_normal'].notna()) & (df['precio_normal'] > 0)]
    df['fecha_extraccion'] = pd.to_datetime(df['fecha_extraccion'])
    
    # Crear etiqueta para el gráfico
    df['producto_label'] = (
        df['nombre_categoria'] + ' | ' +
        df['nombre_supermercado'] + ' | ID:' +
        df['id_link_producto'].astype(str)
    )

    # --- BARRA LATERAL (FILTROS) ---
    st.sidebar.header("Filtros")
    
    categorias = sorted(df['nombre_categoria'].unique().tolist())
    supermercados = sorted(df['nombre_supermercado'].unique().tolist())
    
    cat_sel = st.sidebar.selectbox("Categoría", ['Todas'] + categorias)
    super_sel = st.sidebar.selectbox("Supermercado", ['Todos'] + supermercados)

    # --- APLICAR FILTROS ---
    df_filtered = df.copy()
    if cat_sel != 'Todas':
        df_filtered = df_filtered[df_filtered['nombre_categoria'] == cat_sel]
    if super_sel != 'Todos':
        df_filtered = df_filtered[df_filtered['nombre_supermercado'] == super_sel]

    # --- VISUALIZACIÓN ---
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if df_filtered.empty:
            st.warning("No hay datos para esta combinación de filtros.")
        else:
            fig = go.Figure()
            for _, grupo in df_filtered.groupby('id_link_producto'):
                grupo = grupo.sort_values('fecha_extraccion')
                fig.add_trace(go.Scatter(
                    x=grupo['fecha_extraccion'],
                    y=grupo['precio_normal'],
                    mode='lines+markers',
                    name=grupo['producto_label'].iloc[0],
                    hovertemplate='<b>%{text}</b><br>Fecha: %{x|%d/%m}<br>Precio: $%{y:.2f}',
                    text=grupo['producto_label']
                ))
            
            fig.update_layout(
                title=f"Evolución de Precios ({len(df_filtered['id_link_producto'].unique())} productos)",
                xaxis_title="Fecha",
                yaxis_title="Precio ($)",
                template="plotly_white",
                hovermode="x unified",
                height=600,
                showlegend=False # Ocultar leyenda si hay muchos productos para limpieza
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Resumen")
        st.metric("Total Productos", df_filtered['id_link_producto'].nunique())
        if not df_filtered.empty:
            promedio = df_filtered['precio_normal'].mean()
            st.metric("Precio Promedio", f"${promedio:,.2f}")

else:
    st.error("No se pudieron cargar los datos. Verifica la conexión.")
