import streamlit as st
import pymysql
import pandas as pd
import plotly.graph_objects as go

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Monitor de Precios", layout="wide")

# --- GESTIÓN DE SECRETOS Y CONEXIÓN ---
def get_db_connection():
    # Intenta obtener la contraseña de los secretos de Streamlit (Nube)
    # Si no existe (estás en local), usa la contraseña directa (PELIGROSO PARA GITHUB)
    try:
        db_password = st.secrets["db_password"]
    except FileNotFoundError:
        # Fallback para pruebas locales rápidas (No recomendado subir esto a GitHub)
        db_password = "Estadistica2024!!" 

    config_semanal = {
        'host': '54.94.131.196',
        'user': 'estadistica',
        'password': db_password,
        'database': 'canasta_basica_supermercados'
    }
    return pymysql.connect(**config_semanal)

# --- CACHÉ DE DATOS ---
@st.cache_data(ttl=3600)
def cargar_datos(fecha_inicio, fecha_fin):
    query = f"""
    SELECT 
        p.id_link_producto, p.precio_normal, p.fecha_extraccion,
        s.nombre AS nombre_supermercado, c.nombre AS nombre_categoria
    FROM precios_productos p
    INNER JOIN link_productos l ON p.id_link_producto = l.id_link_producto
    INNER JOIN supermercados s ON l.id_supermercado = s.id_super
    INNER JOIN categorias c ON l.id_categoria = c.id_categoria
    WHERE p.fecha_extraccion BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
      AND p.id_extraccion NOT IN (1, 4, 5, 6);
    """
    try:
        conn = get_db_connection()
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return pd.DataFrame()

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