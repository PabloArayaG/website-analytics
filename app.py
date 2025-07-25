import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import calendar

# Configuración de la página
st.set_page_config(
    page_title="Analizador de CTR - Google Analytics",
    page_icon="📊",
    layout="wide"
)

# Estilos CSS personalizados
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stTitle {
        color: #1E88E5;
        font-size: 2.5rem !important;
        font-weight: 700 !important;
    }
    .upload-section {
        background-color: #f0f2f6;
        padding: 2rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .result-section {
        background-color: white;
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .metric-card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    .month-section {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid #1E88E5;
    }
    </style>
    """, unsafe_allow_html=True)

def read_csv_with_header_detection_and_clean(file):
    """
    Lee un CSV detectando automáticamente la fila donde empiezan los encabezados y filtra solo filas válidas.
    Maneja tanto formato de 2 columnas (page_path, valor) como 3 columnas (fuente, page_path, valor).
    """
    import io
    import csv
    lines = file.getvalue().decode('utf-8').splitlines()
    header_row = None
    for i, line in enumerate(lines):
        # Busca la fila que contiene los nombres de columnas típicos
        if (
            ('page_path' in line.lower() or 'pagina' in line.lower() or 'url' in line.lower() or 'ruta' in line.lower())
            and (',' in line or ';' in line)
        ):
            header_row = i
            break
    if header_row is None:
        raise ValueError("No se encontró la fila de encabezados en el archivo CSV. Asegúrate de que exista una fila con los nombres de las columnas.")
    
    # Detectar delimitador
    delimiter = ',' if lines[header_row].count(',') >= lines[header_row].count(';') else ';'
    
    # Obtener nombres de columnas del encabezado
    header = [h.strip().lower() for h in lines[header_row].split(delimiter)]
    
    # Determinar si es formato de 2 o 3 columnas
    has_source = len(header) >= 3 and any(col in header for col in ['fuente', 'fuente de la sesión', 'source', 'canal', 'channel', 'medium'])
    
    # Leer solo las filas válidas (ignorando totales y vacíos)
    data = []
    reader = csv.reader(lines[header_row+1:], delimiter=delimiter)
    for row in reader:
        if has_source:
            # Formato de 3 columnas: fuente, page_path, valor
            if len(row) < 3:
                continue
            source, page, value = row[0].strip(), row[1].strip(), row[2].strip()
            # Ignorar filas vacías, totales o encabezados
            if not page or page.lower() == 'total' or page.lower() == 'totales' or page == '':
                continue
            if value.lower() == 'total' or value.lower() == 'totales':
                continue
            data.append([source, page, value])
        else:
            # Formato de 2 columnas: page_path, valor
            if len(row) < 2:
                continue
            page, value = row[0].strip(), row[1].strip()
            # Ignorar filas vacías, totales o encabezados
            if not page or page.lower() == 'total' or page.lower() == 'totales' or page == '':
                continue
            if value.lower() == 'total' or value.lower() == 'totales':
                continue
            data.append([page, value])
    
    # Crear DataFrame con las columnas correctas
    if has_source:
        df = pd.DataFrame(data, columns=header[:3])
    else:
        df = pd.DataFrame(data, columns=header[:2])
    
    return df, has_source

def clean_column(df, col):
    # Elimina espacios, convierte a string y a minúsculas
    return df[col].astype(str).str.strip().str.lower()

def find_column(df, options):
    for col in df.columns:
        if col in options:
            return col
    return None

def process_monthly_data(monthly_files, data_type):
    """
    Procesa los archivos mensuales y devuelve un DataFrame consolidado
    """
    all_monthly_data = []
    has_source_data = False
    
    for month_name, file in monthly_files.items():
        if file is not None:
            try:
                df, has_source = read_csv_with_header_detection_and_clean(file)
                if has_source:
                    has_source_data = True
                df.columns = [col.strip().lower() for col in df.columns]
                
                # Encontrar columnas relevantes según el tipo de datos
                page_col = find_column(df, ['page_path', 'pagina', 'url', 'ruta'])
                source_col = find_column(df, ['fuente', 'fuente de la sesión', 'source', 'canal', 'channel', 'medium']) if has_source else None
                
                if data_type == 'cta':
                    value_col = find_column(df, ['cta_clicks', 'clicks', 'clics', 'clicks_cta', 'total de usuarios', 'total_usuarios'])
                    col_name = 'cta_clicks'
                elif data_type == 'users':
                    value_col = find_column(df, ['total_usuarios', 'usuarios', 'total users', 'total de usuarios', 'usuarios únicos', 'usuarios_unicos'])
                    col_name = 'total_users'
                
                if page_col and value_col:
                    if has_source and source_col:
                        month_df = df[[source_col, page_col, value_col]].copy()
                        month_df.columns = ['fuente', 'landing_page', col_name]
                        month_df['fuente'] = clean_column(month_df, 'fuente')
                    else:
                        month_df = df[[page_col, value_col]].copy()
                        month_df.columns = ['landing_page', col_name]
                        month_df['fuente'] = 'no especificado'  # Valor por defecto
                    
                    month_df['landing_page'] = clean_column(month_df, 'landing_page')
                    month_df = month_df.dropna(subset=['landing_page', col_name])
                    month_df[col_name] = pd.to_numeric(month_df[col_name], errors='coerce').fillna(0).astype(int)
                    month_df['mes'] = month_name
                    all_monthly_data.append(month_df)
                    
            except Exception as e:
                st.error(f"Error procesando archivo de {month_name}: {e}")
                continue
    
    if all_monthly_data:
        result_df = pd.concat(all_monthly_data, ignore_index=True)
        return result_df, has_source_data
    return pd.DataFrame(), False

def create_trend_chart(df, metric, title):
    """
    Crea un gráfico de tendencias mensuales
    """
    monthly_avg = df.groupby('mes')[metric].mean().reset_index()
    
    # Ordenar por mes
    month_order = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 
                   'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    monthly_avg['mes'] = pd.Categorical(monthly_avg['mes'], categories=month_order, ordered=True)
    monthly_avg = monthly_avg.sort_values('mes')
    
    fig = px.line(monthly_avg, x='mes', y=metric, 
                  title=title,
                  markers=True,
                  line_shape='spline')
    
    fig.update_layout(
        xaxis_title="Mes",
        yaxis_title=f"{metric} (%)" if 'CTR' in metric else metric,
        hovermode='x unified'
    )
    
    return fig

def create_source_trend_chart(df, metric, title):
    """
    Crea un gráfico de tendencias mensuales por fuente
    """
    # Agrupar por mes y fuente
    source_monthly = df.groupby(['mes', 'fuente'])[metric].mean().reset_index()
    
    # Ordenar por mes
    month_order = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 
                   'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    source_monthly['mes'] = pd.Categorical(source_monthly['mes'], categories=month_order, ordered=True)
    source_monthly = source_monthly.sort_values('mes')
    
    fig = px.line(source_monthly, x='mes', y=metric, color='fuente',
                  title=title,
                  markers=True)
    
    fig.update_layout(
        xaxis_title="Mes",
        yaxis_title=f"{metric} (%)" if 'CTR' in metric else metric,
        hovermode='x unified'
    )
    
    return fig

def create_source_performance_chart(df, title):
    """
    Crea un gráfico de barras del CTR promedio por fuente
    """
    source_performance = df.groupby('fuente').agg({
        'CTR': 'mean',
        'total_users': 'sum',
        'cta_clicks': 'sum'
    }).round(2).reset_index()
    
    source_performance = source_performance.sort_values('CTR', ascending=True)
    
    fig = px.bar(source_performance, 
                 x='CTR', 
                 y='fuente', 
                 orientation='h',
                 title=title,
                 color='CTR',
                 color_continuous_scale='Blues',
                 hover_data=['total_users', 'cta_clicks'])
    
    fig.update_layout(
        yaxis_title="Fuente de Tráfico",
        xaxis_title="CTR Promedio (%)",
        height=400
    )
    
    return fig

def create_monthly_volume_chart(df, title):
    """
    Crea un gráfico de barras para volúmenes mensuales
    """
    monthly_totals = df.groupby('mes').agg({
        'total_users': 'sum',
        'cta_clicks': 'sum'
    }).reset_index()
    
    # Ordenar por mes
    month_order = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 
                   'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    monthly_totals['mes'] = pd.Categorical(monthly_totals['mes'], categories=month_order, ordered=True)
    monthly_totals = monthly_totals.sort_values('mes')
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Total Usuarios',
        x=monthly_totals['mes'],
        y=monthly_totals['total_users'],
        marker_color='lightblue',
        yaxis='y'
    ))
    
    fig.add_trace(go.Bar(
        name='Clicks CTA',
        x=monthly_totals['mes'],
        y=monthly_totals['cta_clicks'],
        marker_color='orange',
        yaxis='y2'
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Mes",
        yaxis=dict(title="Total Usuarios", side="left"),
        yaxis2=dict(title="Clicks CTA", side="right", overlaying="y"),
        hovermode='x unified',
        barmode='group'
    )
    
    return fig

def create_heatmap(df, metric, title):
    """
    Crea un heatmap de landing pages vs meses
    """
    # Tomar solo las top 10 landing pages por rendimiento promedio
    top_pages = df.groupby('landing_page')[metric].mean().nlargest(10).index
    filtered_df = df[df['landing_page'].isin(top_pages)]
    
    pivot_data = filtered_df.pivot_table(
        values=metric, 
        index='landing_page', 
        columns='mes', 
        fill_value=0
    )
    
    # Ordenar columnas por mes
    month_order = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 
                   'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    available_months = [month for month in month_order if month in pivot_data.columns]
    pivot_data = pivot_data[available_months]
    
    fig = px.imshow(pivot_data, 
                    title=title,
                    aspect='auto',
                    color_continuous_scale='Blues')
    
    fig.update_layout(
        xaxis_title="Mes",
        yaxis_title="Landing Page"
    )
    
    return fig

def create_source_heatmap(df, metric, title):
    """
    Crea un heatmap de fuentes vs meses
    """
    pivot_data = df.pivot_table(
        values=metric, 
        index='fuente', 
        columns='mes', 
        fill_value=0
    )
    
    # Ordenar columnas por mes
    month_order = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 
                   'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    available_months = [month for month in month_order if month in pivot_data.columns]
    pivot_data = pivot_data[available_months]
    
    fig = px.imshow(pivot_data, 
                    title=title,
                    aspect='auto',
                    color_continuous_scale='Viridis')
    
    fig.update_layout(
        xaxis_title="Mes",
        yaxis_title="Fuente de Tráfico"
    )
    
    return fig

def create_top_performers_chart(df, metric, title, top_n=10):
    """
    Crea un gráfico de barras horizontales para top performers
    """
    top_data = df.nlargest(top_n, metric)
    
    fig = px.bar(top_data, 
                 x=metric, 
                 y='landing_page', 
                 orientation='h',
                 title=title,
                 color=metric,
                 color_continuous_scale='Blues')
    
    fig.update_layout(
        yaxis_title="Landing Page",
        xaxis_title=f"{metric} (%)" if 'CTR' in metric else metric,
        height=400
    )
    
    return fig

def create_scatter_plot(df, title):
    """
    Crea un scatter plot de usuarios vs clicks con CTR como color
    """
    fig = px.scatter(df, 
                     x='total_users', 
                     y='cta_clicks',
                     color='CTR',
                     size='total_users',
                     hover_data=['landing_page'],
                     title=title,
                     color_continuous_scale='Viridis')
    
    fig.update_layout(
        xaxis_title="Total Usuarios",
        yaxis_title="Clicks CTA"
    )
    
    return fig

def create_ctr_distribution(df, title):
    """
    Crea un histograma de distribución del CTR
    """
    fig = px.histogram(df, 
                       x='CTR', 
                       nbins=20,
                       title=title,
                       color_discrete_sequence=['skyblue'])
    
    fig.update_layout(
        xaxis_title="CTR (%)",
        yaxis_title="Número de Landing Pages",
        showlegend=False
    )
    
    # Añadir línea de promedio
    mean_ctr = df['CTR'].mean()
    fig.add_vline(x=mean_ctr, line_dash="dash", line_color="red", 
                  annotation_text=f"Promedio: {mean_ctr:.2f}%")
    
    return fig

def create_traffic_distribution(df, title):
    """
    Crea un gráfico de pastel para distribución de tráfico
    """
    # Tomar top 8 + Others
    top_8 = df.nlargest(8, 'total_users')
    others_sum = df[~df.index.isin(top_8.index)]['total_users'].sum()
    
    if others_sum > 0:
        others_row = pd.DataFrame({
            'landing_page': ['Otros'],
            'total_users': [others_sum]
        })
        pie_data = pd.concat([top_8[['landing_page', 'total_users']], others_row])
    else:
        pie_data = top_8[['landing_page', 'total_users']]
    
    fig = px.pie(pie_data, 
                 values='total_users', 
                 names='landing_page',
                 title=title)
    
    return fig

def create_source_distribution(df, title):
    """
    Crea un gráfico de pastel para distribución de tráfico por fuente
    """
    source_totals = df.groupby('fuente')['total_users'].sum().reset_index()
    
    fig = px.pie(source_totals, 
                 values='total_users', 
                 names='fuente',
                 title=title)
    
    return fig

def create_gauge_chart(value, title):
    """
    Crea un gráfico de gauge para CTR promedio
    """
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = value,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': title},
        delta = {'reference': 2.5},  # CTR promedio esperado
        gauge = {
            'axis': {'range': [None, 10]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 2], 'color': "lightgray"},
                {'range': [2, 4], 'color': "yellow"},
                {'range': [4, 10], 'color': "green"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 2.5
            }
        }
    ))
    
    return fig

def create_consolidated_analysis(df, has_source_analysis):
    """
    Crea un análisis consolidado por landing page, sumando todas las fuentes
    """
    if has_source_analysis:
        # Consolidar por landing page sumando todas las fuentes
        consolidated = df.groupby(['mes', 'landing_page']).agg({
            'total_users': 'sum',
            'cta_clicks': 'sum'
        }).reset_index()
        
        # Calcular CTR consolidado
        consolidated['CTR'] = (consolidated['cta_clicks'] / consolidated['total_users'] * 100).round(2)
        
        return consolidated
    else:
        # Ya está consolidado si no hay fuente
        return df

def create_source_analysis_section(merged_monthly, complete_months):
    """
    Crea la sección completa de análisis por fuente
    """
    st.subheader("🎯 Análisis Detallado por Fuente de Tráfico")
    st.info("💡 **Análisis granular**: Aquí puedes ver el rendimiento específico de cada canal (Facebook, Google, etc.)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico de tendencias por fuente
        fig_source_ctr = create_source_trend_chart(merged_monthly, 'CTR', 'Evolución del CTR por Fuente y Mes')
        st.plotly_chart(fig_source_ctr, use_container_width=True)
    
    with col2:
        # Performance por fuente
        fig_source_performance = create_source_performance_chart(merged_monthly, 'CTR Promedio por Fuente de Tráfico')
        st.plotly_chart(fig_source_performance, use_container_width=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Distribución de tráfico por fuente
        fig_source_dist = create_source_distribution(merged_monthly, 'Distribución de Usuarios por Fuente')
        st.plotly_chart(fig_source_dist, use_container_width=True)
    
    with col2:
        # Heatmap por fuente
        fig_source_heatmap = create_source_heatmap(merged_monthly, 'CTR', 'Heatmap CTR: Fuentes vs Meses')
        st.plotly_chart(fig_source_heatmap, use_container_width=True)
    
    # Filtro por fuente
    st.subheader("🔍 Análisis Filtrado por Fuente")
    available_sources = ['Todas'] + list(merged_monthly['fuente'].unique())
    selected_source = st.selectbox("Selecciona una fuente específica:", available_sources)
    
    if selected_source != 'Todas':
        filtered_monthly = merged_monthly[merged_monthly['fuente'] == selected_source]
        st.write(f"**📊 Análisis específico para: {selected_source}**")
        
        # Métricas específicas de la fuente
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Usuarios", f"{filtered_monthly['total_users'].sum():,}")
        with col2:
            st.metric("Total Clicks CTA", f"{filtered_monthly['cta_clicks'].sum():,}")
        with col3:
            st.metric("CTR Promedio", f"{filtered_monthly['CTR'].mean():.2f}%")
        
        # Tabla específica por fuente
        st.write("**Detalle por landing page:**")
        source_detail = filtered_monthly[['mes', 'landing_page', 'total_users', 'cta_clicks', 'CTR']].copy()
        source_detail.columns = ['Mes', 'Landing Page', 'Total Usuarios', 'Clicks CTA', 'CTR (%)']
        
        st.dataframe(
            source_detail.style.format({
                'Total Usuarios': '{:,.0f}',
                'Clicks CTA': '{:,.0f}',
                'CTR (%)': '{:.2f}%'
            }),
            use_container_width=True
        )

def main():
    # Título y descripción
    st.title("📊 Analizador Temporal de CTR - Google Analytics")
    st.markdown("""
    Esta herramienta analiza la evolución temporal del Click Through Rate (CTR) de tus landing pages, con **análisis inteligente** que muestra primero los datos consolidados y luego permite profundizar por fuente de tráfico.
    """)

    # Selector de modo de análisis
    analysis_mode = st.radio(
        "Selecciona el tipo de análisis:",
        ["📅 Análisis Temporal (Por Meses)", "📊 Análisis Puntual (Un período)"],
        index=0
    )

    if analysis_mode == "📅 Análisis Temporal (Por Meses)":
        st.markdown("---")
        st.subheader("🗓️ Carga de Datos Mensuales")
        
        # Información sobre formatos soportados
        with st.expander("ℹ️ Formatos de archivos CSV soportados"):
            st.markdown("""
            **🎯 Análisis Inteligente:**
            - **Análisis Principal**: Datos consolidados por landing page (sumando todas las fuentes)
            - **Análisis Detallado**: Desglose específico por fuente de tráfico (opcional)
            
            **Formato con fuente de tráfico (recomendado):**
            - `Fuente de la sesión` | `page_path` | `Total de usuarios`
            - Ejemplo: `facebook` | `/landing-page` | `1250`
            
            **Formato básico:**
            - `page_path` | `Total de usuarios`
            - Ejemplo: `/landing-page` | `1250`
            
            ⚡ **La app detecta automáticamente** el formato de tus archivos.
            """)
        
        # Crear tabs para cada tipo de archivo
        tab1, tab2 = st.tabs(["📈 Clicks CTA", "👥 Usuarios"])
        
        # Diccionarios para almacenar archivos mensuales
        monthly_cta_files = {}
        monthly_users_files = {}
        
        months = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 
                 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
        
        with tab1:
            st.markdown("**Carga los archivos CSV de clicks CTA por mes:**")
            for month in months:
                monthly_cta_files[month] = st.file_uploader(
                    f"Clicks CTA - {month.capitalize()}", 
                    type=['csv'], 
                    key=f"cta_{month}"
                )
        
        with tab2:
            st.markdown("**Carga los archivos CSV de usuarios por mes:**")
            for month in months:
                monthly_users_files[month] = st.file_uploader(
                    f"Usuarios - {month.capitalize()}", 
                    type=['csv'], 
                    key=f"users_{month}"
                )
        
        # Verificar qué meses tienen datos completos
        complete_months = []
        for month in months:
            if (monthly_cta_files[month] is not None and 
                monthly_users_files[month] is not None):
                complete_months.append(month)
        
        if len(complete_months) >= 2:
            st.success(f"✅ Datos completos para {len(complete_months)} meses: {', '.join(complete_months)}")
            
            with st.spinner('Procesando datos mensuales...'):
                # Procesar datos por tipo
                cta_data, has_source_cta = process_monthly_data(monthly_cta_files, 'cta')
                users_data, has_source_users = process_monthly_data(monthly_users_files, 'users')
                
                # Determinar si tenemos datos de fuente
                has_source_analysis = has_source_cta or has_source_users
                
                if not cta_data.empty and not users_data.empty:
                    # Consolidar todos los datos
                    if has_source_analysis:
                        merged_monthly = users_data.merge(cta_data, on=['landing_page', 'mes', 'fuente'], how='left')
                    else:
                        merged_monthly = users_data.merge(cta_data, on=['landing_page', 'mes'], how='left')
                    
                    # Rellenar valores nulos
                    merged_monthly['cta_clicks'] = merged_monthly['cta_clicks'].fillna(0).astype(int)
                    
                    # Calcular CTR
                    merged_monthly['CTR'] = (merged_monthly['cta_clicks'] / merged_monthly['total_users'] * 100).round(2)
                    
                    # *** ANÁLISIS PRINCIPAL CONSOLIDADO ***
                    consolidated_data = create_consolidated_analysis(merged_monthly, has_source_analysis)
                    
                    # Mostrar información sobre el análisis
                    if has_source_analysis:
                        sources_found = merged_monthly['fuente'].unique()
                        st.info(f"🎯 **Análisis inteligente activado!** Detectadas {len(sources_found)} fuentes: {', '.join(sources_found[:3])}{'...' if len(sources_found) > 3 else ''}")
                        st.success("💡 **Mostrando análisis principal consolidado por landing page.** El análisis detallado por fuente está disponible más abajo.")
                    
                    # Análisis temporal consolidado
                    st.markdown("---")
                    st.subheader("📈 Análisis Principal - Consolidado por Landing Page") 
                    
                    # Métricas resumen por mes (consolidadas)
                    monthly_summary = consolidated_data.groupby('mes').agg({
                        'total_users': 'sum',
                        'cta_clicks': 'sum', 
                        'CTR': 'mean'
                    }).round(2)
                    
                    # Ordenar por mes
                    month_order = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 
                                  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
                    monthly_summary = monthly_summary.reindex([m for m in month_order if m in monthly_summary.index])
                    
                    # Mostrar tabla resumen mensual
                    st.subheader("📊 Resumen Mensual (Todos los Canales)")
                    st.dataframe(
                        monthly_summary.style.format({
                            'total_users': '{:,.0f}',
                            'cta_clicks': '{:,.0f}',
                            'CTR': '{:.2f}%'
                        }),
                        use_container_width=True
                    )
                    
                    # Gráficos principales consolidados
                    st.subheader("📈 Visualizaciones Principales")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Gráfico de tendencias CTR consolidado
                        fig_ctr = create_trend_chart(consolidated_data, 'CTR', 'Evolución del CTR Consolidado por Mes')
                        st.plotly_chart(fig_ctr, use_container_width=True)
                    
                    with col2:
                        # Gauge Chart CTR Promedio
                        avg_ctr = consolidated_data['CTR'].mean()
                        fig_gauge = create_gauge_chart(avg_ctr, f'CTR Promedio General: {avg_ctr:.2f}%')
                        st.plotly_chart(fig_gauge, use_container_width=True)
                    
                    # Gráfico de volúmenes mensuales consolidados
                    fig_volume = create_monthly_volume_chart(consolidated_data, 'Volúmenes Mensuales Consolidados: Usuarios vs Clicks CTA')
                    st.plotly_chart(fig_volume, use_container_width=True)
                    
                    # Heatmap de landing pages consolidado
                    st.subheader("🔥 Mapa de Calor - Top 10 Landing Pages (Consolidado)")
                    fig_heatmap_ctr = create_heatmap(consolidated_data, 'CTR', 'Heatmap CTR Consolidado por Landing Page y Mes')
                    st.plotly_chart(fig_heatmap_ctr, use_container_width=True)
                    
                    # *** ANÁLISIS DETALLADO POR FUENTE (OPCIONAL) ***
                    if has_source_analysis:
                        st.markdown("---")
                        create_source_analysis_section(merged_monthly, complete_months)
                    
                    # Análisis de rendimiento consolidado
                    st.markdown("---")
                    st.subheader("🏆 Análisis de Rendimiento (Consolidado)")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write("**🏅 Mejor Mes por CTR:**")
                        best_ctr_month = monthly_summary['CTR'].idxmax()
                        best_ctr_value = monthly_summary.loc[best_ctr_month, 'CTR']
                        st.metric("Mes", best_ctr_month.capitalize(), f"{best_ctr_value:.2f}%")
                    
                    with col2:
                        st.write("**📉 Peor Mes por CTR:**")
                        worst_ctr_month = monthly_summary['CTR'].idxmin()
                        worst_ctr_value = monthly_summary.loc[worst_ctr_month, 'CTR']
                        st.metric("Mes", worst_ctr_month.capitalize(), f"{worst_ctr_value:.2f}%")
                    
                    with col3:
                        st.write("**📊 Crecimiento CTR:**")
                        if len(monthly_summary) >= 2:
                            first_month_ctr = monthly_summary['CTR'].iloc[0]
                            last_month_ctr = monthly_summary['CTR'].iloc[-1]
                            growth = ((last_month_ctr - first_month_ctr) / first_month_ctr * 100)
                            st.metric("Crecimiento", f"{growth:+.1f}%", f"vs {monthly_summary.index[0]}")
                    
                    # Tabla detallada consolidada
                    st.subheader("📋 Datos Detallados Consolidados por Landing Page")
                    
                    # Filtro por mes
                    selected_month = st.selectbox("Filtrar por mes:", ['Todos'] + complete_months)
                    
                    # Aplicar filtro
                    if selected_month != 'Todos':
                        filtered_data = consolidated_data[consolidated_data['mes'] == selected_month]
                    else:
                        filtered_data = consolidated_data
                    
                    # Mostrar datos consolidados
                    display_columns = ['mes', 'landing_page', 'total_users', 'cta_clicks', 'CTR']
                    display_df = filtered_data[display_columns].copy()
                    display_df.columns = ['Mes', 'Landing Page', 'Total Usuarios', 'Clicks CTA', 'CTR (%)']
                    
                    st.dataframe(
                        display_df.style.format({
                            'Total Usuarios': '{:,.0f}',
                            'Clicks CTA': '{:,.0f}',
                            'CTR (%)': '{:.2f}%'
                        }),
                        use_container_width=True
                    )
                    
                    # Descargar datos
                    col1, col2 = st.columns(2)
                    with col1:
                        st.download_button(
                            label="📥 Descargar análisis consolidado como CSV",
                            data=consolidated_data.to_csv(index=False),
                            file_name=f"analisis_consolidado_ctr_{datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv",
                            help="Descarga el análisis consolidado por landing page"
                        )
                    
                    if has_source_analysis:
                        with col2:
                            st.download_button(
                                label="📥 Descargar análisis detallado (con fuentes) como CSV",
                                data=merged_monthly.to_csv(index=False),
                                file_name=f"analisis_detallado_con_fuentes_{datetime.now().strftime('%Y%m%d')}.csv",
                                mime="text/csv",
                                help="Descarga el análisis detallado con información de fuentes"
                            )
        
        elif len(complete_months) == 1:
            st.info(f"📊 Tienes datos completos para 1 mes ({complete_months[0]}). Para análisis temporal necesitas al menos 2 meses.")
        
        else:
            st.info("📁 Carga los archivos CSV para al menos 2 meses para comenzar el análisis temporal.")

    else:
        # Análisis puntual original con lógica similar
        st.markdown("---")
        st.subheader("📊 Análisis de Un Período Específico")
        
        # Información sobre los archivos requeridos
        with st.expander("ℹ️ Información sobre los archivos CSV requeridos"):
            st.markdown("""
            **🎯 Análisis Inteligente:**
            - **Análisis Principal**: Datos consolidados por landing page (más claro y útil)
            - **Análisis Detallado**: Desglose por fuente de tráfico (para profundizar)
            
            **Formato con fuente de tráfico (recomendado):**
            - `Fuente de la sesión` | `page_path` | `Total de usuarios`
            - Permite identificar el origen del "(not set)" y analizar por canal
            
            **Formato básico:**
            - `page_path` | `Total de usuarios`
            - Análisis general sin segmentación por fuente
            
            **Métrica calculada:**
            - **CTR**: (Clicks CTA / Total Usuarios) × 100
            """)
        
        # Sección de carga de archivos
        st.markdown('<div class="upload-section">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📈 Datos de Clicks CTA (CSV)")
            cta_file = st.file_uploader("Carga el CSV de clicks CTA", type=['csv'], key="cta_single")
            if cta_file:
                st.success("✅ Archivo de clicks CTA cargado correctamente")
        
        with col2:
            st.subheader("👥 Datos de Usuarios (CSV)")
            users_file = st.file_uploader("Carga el CSV de usuarios", type=['csv'], key="users_single")
            if users_file:
                st.success("✅ Archivo de usuarios cargado correctamente")
        
        st.markdown('</div>', unsafe_allow_html=True)

        if cta_file and users_file:
            with st.spinner('Procesando archivos...'):
                try:
                    cta_df, has_source_cta = read_csv_with_header_detection_and_clean(cta_file)
                    users_df, has_source_users = read_csv_with_header_detection_and_clean(users_file)
                    
                    # Determinar si tenemos análisis por fuente
                    has_source_analysis = has_source_cta or has_source_users
                    
                except Exception as e:
                    st.error(f"Error al leer los archivos CSV: {e}")
                    return

                # Normalizar nombres de columnas
                cta_df.columns = [col.strip().lower() for col in cta_df.columns]
                users_df.columns = [col.strip().lower() for col in users_df.columns]

                # Buscar columnas
                cta_page_col = find_column(cta_df, ['page_path', 'pagina', 'url', 'ruta'])
                cta_clicks_col = find_column(cta_df, ['cta_clicks', 'clicks', 'clics', 'clicks_cta', 'total de usuarios', 'total_usuarios'])
                users_page_col = find_column(users_df, ['page_path', 'pagina', 'url', 'ruta'])
                users_total_col = find_column(users_df, ['total_usuarios', 'usuarios', 'total users', 'total de usuarios', 'usuarios únicos', 'usuarios_unicos'])
                
                # Buscar columnas de fuente si existen
                cta_source_col = find_column(cta_df, ['fuente', 'fuente de la sesión', 'source', 'canal', 'channel', 'medium']) if has_source_cta else None
                users_source_col = find_column(users_df, ['fuente', 'fuente de la sesión', 'source', 'canal', 'channel', 'medium']) if has_source_users else None

                if not all([cta_page_col, cta_clicks_col, users_page_col, users_total_col]):
                    st.error("No se encontraron las columnas necesarias en los archivos CSV.")
                    return

                # Procesar datos según el formato
                if has_source_analysis:
                    # Formato con fuente
                    if has_source_cta and cta_source_col:
                        cta_df = cta_df[[cta_source_col, cta_page_col, cta_clicks_col]].copy()
                        cta_df.columns = ['fuente', 'landing_page', 'cta_clicks']
                    else:
                        cta_df = cta_df[[cta_page_col, cta_clicks_col]].copy()
                        cta_df.columns = ['landing_page', 'cta_clicks']
                        cta_df['fuente'] = 'no especificado'
                    
                    if has_source_users and users_source_col:
                        users_df = users_df[[users_source_col, users_page_col, users_total_col]].copy()
                        users_df.columns = ['fuente', 'landing_page', 'total_users']
                    else:
                        users_df = users_df[[users_page_col, users_total_col]].copy()
                        users_df.columns = ['landing_page', 'total_users']
                        users_df['fuente'] = 'no especificado'
                    
                    # Limpiar datos
                    cta_df['landing_page'] = clean_column(cta_df, 'landing_page')
                    cta_df['fuente'] = clean_column(cta_df, 'fuente')
                    users_df['landing_page'] = clean_column(users_df, 'landing_page')
                    users_df['fuente'] = clean_column(users_df, 'fuente')
                    
                    # Merge con fuente
                    merged_df = pd.merge(users_df, cta_df, on=['landing_page', 'fuente'], how='left')
                    
                else:
                    # Formato básico sin fuente
                    cta_df = cta_df[[cta_page_col, cta_clicks_col]].copy()
                    users_df = users_df[[users_page_col, users_total_col]].copy()
                    
                    cta_df.columns = ['landing_page', 'cta_clicks']
                    users_df.columns = ['landing_page', 'total_users']
                    
                    # Limpiar datos
                    cta_df['landing_page'] = clean_column(cta_df, 'landing_page')
                    users_df['landing_page'] = clean_column(users_df, 'landing_page')
                    
                    # Merge básico
                    merged_df = pd.merge(users_df, cta_df, on='landing_page', how='left')

                # Limpiar datos
                merged_df = merged_df.dropna(subset=['landing_page'])
                merged_df['cta_clicks'] = pd.to_numeric(merged_df['cta_clicks'], errors='coerce').fillna(0).astype(int)
                merged_df['total_users'] = pd.to_numeric(merged_df['total_users'], errors='coerce').fillna(0).astype(int)
                
                # Calcular CTR
                merged_df['CTR'] = (merged_df['cta_clicks'] / merged_df['total_users'] * 100).round(2)
                
                # *** CREAR ANÁLISIS CONSOLIDADO ***
                if has_source_analysis:
                    consolidated_df = merged_df.groupby('landing_page').agg({
                        'total_users': 'sum',
                        'cta_clicks': 'sum'
                    }).reset_index()
                    consolidated_df['CTR'] = (consolidated_df['cta_clicks'] / consolidated_df['total_users'] * 100).round(2)
                    
                    sources_found = merged_df['fuente'].unique()
                    st.info(f"🎯 **Análisis inteligente activado!** Detectadas {len(sources_found)} fuentes: {', '.join(sources_found[:3])}{'...' if len(sources_found) > 3 else ''}")
                    st.success("💡 **Mostrando análisis principal consolidado por landing page.** El análisis detallado por fuente está disponible más abajo.")
                else:
                    consolidated_df = merged_df

            # *** MÉTRICAS PRINCIPALES CONSOLIDADAS ***
            st.markdown('<div class="result-section">', unsafe_allow_html=True)
            st.subheader("📊 Métricas Principales - Consolidadas por Landing Page")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Landing Pages", len(consolidated_df))
            with col2:
                st.metric("Total Clicks CTA", f"{consolidated_df['cta_clicks'].sum():,}")
            with col3:
                st.metric("CTR Promedio", f"{consolidated_df['CTR'].mean():.2f}%")

            # *** VISUALIZACIONES PRINCIPALES CONSOLIDADAS ***
            st.subheader("📈 Análisis Visual Consolidado")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Top performers consolidado
                fig_top = create_top_performers_chart(consolidated_df, 'CTR', 'Top 10 Landing Pages por CTR (Consolidado)')
                st.plotly_chart(fig_top, use_container_width=True)
            
            with col2:
                # Distribución de tráfico consolidado
                fig_traffic = create_traffic_distribution(consolidated_df, 'Distribución de Tráfico Consolidado por Landing Page')
                st.plotly_chart(fig_traffic, use_container_width=True)

            # *** TABLA DE RESULTADOS CONSOLIDADA ***
            st.subheader("📋 Resultados Consolidados por Landing Page")
            
            display_df = consolidated_df[['landing_page', 'total_users', 'cta_clicks', 'CTR']].copy()
            display_df.columns = ['Landing Page', 'Total Usuarios', 'Clicks CTA', 'CTR (%)']
            
            st.dataframe(
                display_df.style.format({
                    'Total Usuarios': '{:,.0f}',
                    'Clicks CTA': '{:,.0f}',
                    'CTR (%)': '{:.2f}%'
                }),
                use_container_width=True
            )

            # Top 5 Landing Pages por CTR consolidado
            st.subheader("🏆 Top 5 Landing Pages por CTR (Consolidado)")
            top_ctr_consolidated = consolidated_df.nlargest(5, 'CTR')[['landing_page', 'CTR']].copy()
            top_ctr_consolidated.columns = ['Landing Page', 'CTR (%)']
            st.dataframe(top_ctr_consolidated.style.format({'CTR (%)': '{:.2f}%'}))

            # *** ANÁLISIS DETALLADO POR FUENTE (SI ESTÁ DISPONIBLE) ***
            if has_source_analysis:
                st.markdown("---")
                st.subheader("🎯 Análisis Detallado por Fuente de Tráfico")
                st.info("💡 **Análisis granular**: Aquí puedes ver el rendimiento específico de cada canal (Facebook, Google, etc.)")
                
                # Métricas detalladas
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Registros Detallados", len(merged_df))
                with col2:
                    st.metric("Clicks CTA Detallado", f"{merged_df['cta_clicks'].sum():,}")
                with col3:
                    st.metric("CTR Detallado", f"{merged_df['CTR'].mean():.2f}%")
                with col4:
                    st.metric("Fuentes de Tráfico", len(merged_df['fuente'].unique()))
                
                # Visualizaciones por fuente
                col1, col2 = st.columns(2)
                
                with col1:
                    # Performance por fuente
                    fig_source_performance = create_source_performance_chart(merged_df, 'CTR Promedio por Fuente de Tráfico')
                    st.plotly_chart(fig_source_performance, use_container_width=True)
                
                with col2:
                    # Distribución por fuente
                    fig_source_dist = create_source_distribution(merged_df, 'Distribución de Usuarios por Fuente')
                    st.plotly_chart(fig_source_dist, use_container_width=True)
                
                # Filtro por fuente
                st.subheader("🔍 Análisis Filtrado por Fuente")
                available_sources = ['Todas'] + list(merged_df['fuente'].unique())
                selected_source = st.selectbox("Selecciona una fuente específica:", available_sources, key="single_source")
                
                if selected_source != 'Todas':
                    filtered_df = merged_df[merged_df['fuente'] == selected_source]
                    st.write(f"**📊 Análisis específico para: {selected_source}**")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Landing Pages", len(filtered_df))
                    with col2:
                        st.metric("Total Usuarios", f"{filtered_df['total_users'].sum():,}")
                    with col3:
                        st.metric("CTR Promedio", f"{filtered_df['CTR'].mean():.2f}%")
                    
                    # Tabla detallada por fuente
                    st.write("**Detalle por landing page:**")
                    source_detail_df = filtered_df[['fuente', 'landing_page', 'total_users', 'cta_clicks', 'CTR']].copy()
                    source_detail_df.columns = ['Fuente', 'Landing Page', 'Total Usuarios', 'Clicks CTA', 'CTR (%)']
                    
                    st.dataframe(
                        source_detail_df.style.format({
                            'Total Usuarios': '{:,.0f}',
                            'Clicks CTA': '{:,.0f}',
                            'CTR (%)': '{:.2f}%'
                        }),
                        use_container_width=True
                    )

            # *** INSIGHTS ADICIONALES ***
            st.subheader("🔍 Insights Adicionales")
            
            if has_source_analysis:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        "Mejor CTR Consolidado", 
                        f"{consolidated_df['CTR'].max():.2f}%",
                        f"Landing: {consolidated_df.loc[consolidated_df['CTR'].idxmax(), 'landing_page'][:15]}..."
                    )
                
                with col2:
                    best_source = merged_df.groupby('fuente')['CTR'].mean().idxmax()
                    best_source_ctr = merged_df.groupby('fuente')['CTR'].mean().max()
                    st.metric(
                        "Mejor Fuente", 
                        f"{best_source}",
                        f"{best_source_ctr:.2f}% CTR promedio"
                    )
                
                with col3:
                    st.metric(
                        "Mediana CTR", 
                        f"{consolidated_df['CTR'].median():.2f}%",
                        f"50% están por encima"
                    )
                
                with col4:
                    high_performers = len(consolidated_df[consolidated_df['CTR'] > consolidated_df['CTR'].mean()])
                    st.metric(
                        "Sobre Promedio", 
                        f"{high_performers}",
                        f"de {len(consolidated_df)} landing pages"
                    )
            else:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        "Mejor CTR", 
                        f"{consolidated_df['CTR'].max():.2f}%",
                        f"Landing: {consolidated_df.loc[consolidated_df['CTR'].idxmax(), 'landing_page'][:20]}..."
                    )
                
                with col2:
                    st.metric(
                        "Mediana CTR", 
                        f"{consolidated_df['CTR'].median():.2f}%",
                        f"50% están por encima"
                    )
                
                with col3:
                    high_performers = len(consolidated_df[consolidated_df['CTR'] > consolidated_df['CTR'].mean()])
                    st.metric(
                        "Sobre Promedio", 
                        f"{high_performers}",
                        f"de {len(consolidated_df)} landing pages"
                    )

            # *** OPCIONES DE DESCARGA ***
            st.subheader("📥 Descargar Resultados")
            
            if has_source_analysis:
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        label="📊 Descargar análisis consolidado como CSV",
                        data=consolidated_df.to_csv(index=False),
                        file_name="ctr_analysis_consolidado.csv",
                        mime="text/csv",
                        help="Análisis principal consolidado por landing page"
                    )
                with col2:
                    st.download_button(
                        label="🔍 Descargar análisis detallado (con fuentes) como CSV",
                        data=merged_df.to_csv(index=False),
                        file_name="ctr_analysis_detallado_fuentes.csv",
                        mime="text/csv",
                        help="Análisis detallado con información de fuentes"
                    )
            else:
                st.download_button(
                    label="📥 Descargar resultados como CSV",
                    data=consolidated_df.to_csv(index=False),
                    file_name="ctr_analysis_single.csv",
                    mime="text/csv"
                )
            
            st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main() 