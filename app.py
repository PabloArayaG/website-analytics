import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import calendar

# Configuración de la página
st.set_page_config(
    page_title="Analizador de CTR y Conversión - Google Analytics",
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
    # Leer solo las filas válidas (ignorando totales y vacíos)
    data = []
    reader = csv.reader(lines[header_row+1:], delimiter=delimiter)
    for row in reader:
        # Tomar solo las dos primeras columnas si hay más
        row = row[:2]
        if len(row) < 2:
            continue
        page, value = row[0].strip(), row[1].strip()
        # Ignorar filas vacías, totales o encabezados
        if not page or page.lower() == 'total' or page.lower() == 'totales' or page == ',' or page == '' or page == ' ':
            continue
        if value.lower() == 'total' or value.lower() == 'totales':
            continue
        data.append([page, value])
    # Obtener nombres de columnas del encabezado
    header = [h.strip().lower() for h in lines[header_row].split(delimiter)[:2]]
    df = pd.DataFrame(data, columns=header)
    return df

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
    
    for month_name, file in monthly_files.items():
        if file is not None:
            try:
                df = read_csv_with_header_detection_and_clean(file)
                df.columns = [col.strip().lower() for col in df.columns]
                
                # Encontrar columnas relevantes según el tipo de datos
                page_col = find_column(df, ['page_path', 'pagina', 'url', 'ruta'])
                
                if data_type == 'cta':
                    value_col = find_column(df, ['cta_clicks', 'clicks', 'clics', 'clicks_cta', 'total de usuarios', 'total_usuarios'])
                    col_name = 'cta_clicks'
                elif data_type == 'users':
                    value_col = find_column(df, ['total_usuarios', 'usuarios', 'total users', 'total de usuarios', 'usuarios únicos', 'usuarios_unicos'])
                    col_name = 'total_users'
                elif data_type == 'forms':
                    value_col = find_column(df, ['form_submit', 'formularios', 'envios', 'formularios_enviados', 'total de usuarios', 'total_usuarios', 'usuarios'])
                    col_name = 'form_submissions'
                
                if page_col and value_col:
                    month_df = df[[page_col, value_col]].copy()
                    month_df.columns = ['landing_page', col_name]
                    month_df['landing_page'] = clean_column(month_df, 'landing_page')
                    month_df = month_df.dropna(subset=['landing_page', col_name])
                    month_df[col_name] = pd.to_numeric(month_df[col_name], errors='coerce').fillna(0).astype(int)
                    month_df['mes'] = month_name
                    all_monthly_data.append(month_df)
                    
            except Exception as e:
                st.error(f"Error procesando archivo de {month_name}: {e}")
                continue
    
    if all_monthly_data:
        return pd.concat(all_monthly_data, ignore_index=True)
    return pd.DataFrame()

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
        yaxis_title=f"{metric} (%)" if 'CTR' in metric or 'Conversión' in metric else metric,
        hovermode='x unified'
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

def main():
    # Título y descripción
    st.title("📊 Analizador Temporal de CTR y Conversión Efectiva - Google Analytics")
    st.markdown("""
    Esta herramienta analiza la evolución temporal del rendimiento de tus landing pages, permitiendo cargar datos mensuales desde enero para obtener insights profundos sobre tendencias y estacionalidad.
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
        
        # Crear tabs para cada tipo de archivo
        tab1, tab2, tab3 = st.tabs(["📈 Clicks CTA", "👥 Usuarios", "📝 Formularios"])
        
        # Diccionarios para almacenar archivos mensuales
        monthly_cta_files = {}
        monthly_users_files = {}
        monthly_forms_files = {}
        
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
        
        with tab3:
            st.markdown("**Carga los archivos CSV de formularios enviados por mes:**")
            for month in months:
                monthly_forms_files[month] = st.file_uploader(
                    f"Formularios - {month.capitalize()}", 
                    type=['csv'], 
                    key=f"forms_{month}"
                )
        
        # Verificar qué meses tienen datos completos
        complete_months = []
        for month in months:
            if (monthly_cta_files[month] is not None and 
                monthly_users_files[month] is not None and 
                monthly_forms_files[month] is not None):
                complete_months.append(month)
        
        if len(complete_months) >= 2:
            st.success(f"✅ Datos completos para {len(complete_months)} meses: {', '.join(complete_months)}")
            
            with st.spinner('Procesando datos mensuales...'):
                # Procesar datos por tipo
                cta_data = process_monthly_data(monthly_cta_files, 'cta')
                users_data = process_monthly_data(monthly_users_files, 'users')
                forms_data = process_monthly_data(monthly_forms_files, 'forms')
                
                if not cta_data.empty and not users_data.empty and not forms_data.empty:
                    # Consolidar todos los datos
                    merged_monthly = users_data.merge(cta_data, on=['landing_page', 'mes'], how='left')
                    merged_monthly = merged_monthly.merge(forms_data, on=['landing_page', 'mes'], how='left')
                    
                    # Rellenar valores nulos
                    merged_monthly['cta_clicks'] = merged_monthly['cta_clicks'].fillna(0).astype(int)
                    merged_monthly['form_submissions'] = merged_monthly['form_submissions'].fillna(0).astype(int)
                    
                    # Calcular métricas
                    merged_monthly['CTR'] = (merged_monthly['cta_clicks'] / merged_monthly['total_users'] * 100).round(2)
                    merged_monthly['Conversión_Efectiva'] = (merged_monthly['form_submissions'] / merged_monthly['total_users'] * 100).round(2)
                    
                    # Análisis temporal
                    st.markdown("---")
                    st.subheader("📈 Análisis de Tendencias Temporales")
                    
                    # Métricas resumen por mes
                    monthly_summary = merged_monthly.groupby('mes').agg({
                        'total_users': 'sum',
                        'cta_clicks': 'sum', 
                        'form_submissions': 'sum',
                        'CTR': 'mean',
                        'Conversión_Efectiva': 'mean'
                    }).round(2)
                    
                    # Ordenar por mes
                    month_order = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 
                                  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
                    monthly_summary = monthly_summary.reindex([m for m in month_order if m in monthly_summary.index])
                    
                    # Mostrar tabla resumen mensual
                    st.subheader("📊 Resumen Mensual")
                    st.dataframe(
                        monthly_summary.style.format({
                            'total_users': '{:,.0f}',
                            'cta_clicks': '{:,.0f}',
                            'form_submissions': '{:,.0f}',
                            'CTR': '{:.2f}%',
                            'Conversión_Efectiva': '{:.2f}%'
                        }),
                        use_container_width=True
                    )
                    
                    # Gráficos de tendencias
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        fig_ctr = create_trend_chart(merged_monthly, 'CTR', 'Evolución del CTR por Mes')
                        st.plotly_chart(fig_ctr, use_container_width=True)
                    
                    with col2:
                        fig_conversion = create_trend_chart(merged_monthly, 'Conversión_Efectiva', 'Evolución de la Conversión Efectiva por Mes')
                        st.plotly_chart(fig_conversion, use_container_width=True)
                    
                    # Heatmaps
                    st.subheader("🔥 Mapas de Calor - Top 10 Landing Pages")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        fig_heatmap_ctr = create_heatmap(merged_monthly, 'CTR', 'Heatmap CTR por Landing Page y Mes')
                        st.plotly_chart(fig_heatmap_ctr, use_container_width=True)
                    
                    with col2:
                        fig_heatmap_conv = create_heatmap(merged_monthly, 'Conversión_Efectiva', 'Heatmap Conversión Efectiva por Landing Page y Mes')
                        st.plotly_chart(fig_heatmap_conv, use_container_width=True)
                    
                    # Análisis de mejor y peor rendimiento
                    st.subheader("🏆 Análisis de Rendimiento")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write("**🏅 Mejor Mes por CTR:**")
                        best_ctr_month = monthly_summary['CTR'].idxmax()
                        best_ctr_value = monthly_summary.loc[best_ctr_month, 'CTR']
                        st.metric("Mes", best_ctr_month.capitalize(), f"{best_ctr_value:.2f}%")
                    
                    with col2:
                        st.write("**🏅 Mejor Mes por Conversión:**")
                        best_conv_month = monthly_summary['Conversión_Efectiva'].idxmax()
                        best_conv_value = monthly_summary.loc[best_conv_month, 'Conversión_Efectiva']
                        st.metric("Mes", best_conv_month.capitalize(), f"{best_conv_value:.2f}%")
                    
                    with col3:
                        st.write("**📊 Crecimiento CTR:**")
                        if len(monthly_summary) >= 2:
                            first_month_ctr = monthly_summary['CTR'].iloc[0]
                            last_month_ctr = monthly_summary['CTR'].iloc[-1]
                            growth = ((last_month_ctr - first_month_ctr) / first_month_ctr * 100)
                            st.metric("Crecimiento", f"{growth:+.1f}%", f"vs {monthly_summary.index[0]}")
                    
                    # Tabla detallada completa
                    st.subheader("📋 Datos Detallados por Mes y Landing Page")
                    
                    # Filtro por mes
                    selected_month = st.selectbox("Filtrar por mes:", ['Todos'] + complete_months)
                    
                    if selected_month != 'Todos':
                        filtered_data = merged_monthly[merged_monthly['mes'] == selected_month]
                    else:
                        filtered_data = merged_monthly
                    
                    # Mostrar datos filtrados
                    display_columns = ['mes', 'landing_page', 'total_users', 'cta_clicks', 'CTR', 'form_submissions', 'Conversión_Efectiva']
                    display_df = filtered_data[display_columns].copy()
                    display_df.columns = ['Mes', 'Landing Page', 'Total Usuarios', 'Clicks CTA', 'CTR (%)', 'Formularios Enviados', 'Conversión Efectiva (%)']
                    
                    st.dataframe(
                        display_df.style.format({
                            'Total Usuarios': '{:,.0f}',
                            'Clicks CTA': '{:,.0f}',
                            'CTR (%)': '{:.2f}%',
                            'Formularios Enviados': '{:,.0f}',
                            'Conversión Efectiva (%)': '{:.2f}%'
                        }),
                        use_container_width=True
                    )
                    
                    # Descargar datos completos
                    st.download_button(
                        label="📥 Descargar análisis temporal completo como CSV",
                        data=merged_monthly.to_csv(index=False),
                        file_name=f"analisis_temporal_ctr_conversion_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        help="Descarga todos los datos del análisis temporal"
                    )
        
        elif len(complete_months) == 1:
            st.info(f"📊 Tienes datos completos para 1 mes ({complete_months[0]}). Para análisis temporal necesitas al menos 2 meses.")
        
        else:
            st.info("📁 Carga los archivos CSV para al menos 2 meses para comenzar el análisis temporal.")

    else:
        # Análisis puntual original
        st.markdown("---")
        st.subheader("📊 Análisis de Un Período Específico")
        
        # Sección de carga de archivos
        st.markdown('<div class="upload-section">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        
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
        
        with col3:
            st.subheader("📝 Datos de Formularios Enviados (CSV)")
            form_file = st.file_uploader("Carga el CSV de formularios enviados", type=['csv'], key="forms_single")
            if form_file:
                st.success("✅ Archivo de formularios enviados cargado correctamente")
        
        st.markdown('</div>', unsafe_allow_html=True)

        if cta_file and users_file and form_file:
            with st.spinner('Procesando archivos...'):
                try:
                    cta_df = read_csv_with_header_detection_and_clean(cta_file)
                    users_df = read_csv_with_header_detection_and_clean(users_file)
                    form_df = read_csv_with_header_detection_and_clean(form_file)
                except Exception as e:
                    st.error(f"Error al leer los archivos CSV: {e}")
                    return

                # Normalizar nombres de columnas para evitar errores por mayúsculas/minúsculas
                cta_df.columns = [col.strip().lower() for col in cta_df.columns]
                users_df.columns = [col.strip().lower() for col in users_df.columns]
                form_df.columns = [col.strip().lower() for col in form_df.columns]

                cta_page_col = find_column(cta_df, ['page_path', 'pagina', 'url', 'ruta'])
                cta_clicks_col = find_column(cta_df, ['cta_clicks', 'clicks', 'clics', 'clicks_cta', 'total de usuarios', 'total_usuarios'])
                users_page_col = find_column(users_df, ['page_path', 'pagina', 'url', 'ruta'])
                users_total_col = find_column(users_df, ['total_usuarios', 'usuarios', 'total users', 'total de usuarios', 'usuarios únicos', 'usuarios_unicos'])
                form_page_col = find_column(form_df, ['page_path', 'pagina', 'url', 'ruta'])
                form_submit_col = find_column(form_df, ['form_submit', 'formularios', 'envios', 'formularios_enviados', 'total de usuarios', 'total_usuarios', 'usuarios'])

                if not all([cta_page_col, cta_clicks_col, users_page_col, users_total_col, form_page_col, form_submit_col]):
                    st.error("No se encontraron las columnas necesarias en los archivos CSV.")
                    return

                # Filtrar solo las columnas necesarias y limpiar datos
                cta_df = cta_df[[cta_page_col, cta_clicks_col]].copy()
                users_df = users_df[[users_page_col, users_total_col]].copy()
                form_df = form_df[[form_page_col, form_submit_col]].copy()
                
                cta_df.columns = ['landing_page', 'cta_clicks']
                users_df.columns = ['landing_page', 'total_users']
                form_df.columns = ['landing_page', 'form_submissions']

                # Limpiar espacios y convertir a minúsculas para merge
                cta_df['landing_page'] = clean_column(cta_df, 'landing_page')
                users_df['landing_page'] = clean_column(users_df, 'landing_page')
                form_df['landing_page'] = clean_column(form_df, 'landing_page')

                # Eliminar filas vacías o con valores nulos
                cta_df = cta_df.dropna(subset=['landing_page', 'cta_clicks'])
                users_df = users_df.dropna(subset=['landing_page', 'total_users'])
                form_df = form_df.dropna(subset=['landing_page', 'form_submissions'])

                # Convertir a numérico los valores (si hay error, poner 0)
                cta_df['cta_clicks'] = pd.to_numeric(cta_df['cta_clicks'], errors='coerce').fillna(0).astype(int)
                users_df['total_users'] = pd.to_numeric(users_df['total_users'], errors='coerce').fillna(0).astype(int)
                form_df['form_submissions'] = pd.to_numeric(form_df['form_submissions'], errors='coerce').fillna(0).astype(int)

                # Unir los datos por landing_page
                merged_df = pd.merge(users_df, cta_df, on='landing_page', how='left')
                merged_df = pd.merge(merged_df, form_df, on='landing_page', how='left')
                
                # Rellenar valores nulos con 0
                merged_df['cta_clicks'] = merged_df['cta_clicks'].fillna(0).astype(int)
                merged_df['form_submissions'] = merged_df['form_submissions'].fillna(0).astype(int)
                
                # Calcular métricas
                merged_df['CTR'] = (merged_df['cta_clicks'] / merged_df['total_users'] * 100).round(2)
                merged_df['Conversión_Efectiva'] = (merged_df['form_submissions'] / merged_df['total_users'] * 100).round(2)

            # Métricas principales
            st.markdown('<div class="result-section">', unsafe_allow_html=True)
            st.subheader("📊 Métricas Principales")
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("Total Landing Pages", len(merged_df))
            with col2:
                st.metric("Total Clicks CTA", f"{merged_df['cta_clicks'].sum():,}")
            with col3:
                st.metric("Total Formularios", f"{merged_df['form_submissions'].sum():,}")
            with col4:
                st.metric("CTR Promedio", f"{merged_df['CTR'].mean():.2f}%")
            with col5:
                st.metric("Conversión Efectiva Promedio", f"{merged_df['Conversión_Efectiva'].mean():.2f}%")

            # Tabla de resultados
            st.subheader("📋 Resultados Detallados")
            
            display_df = merged_df[['landing_page', 'total_users', 'cta_clicks', 'CTR', 'form_submissions', 'Conversión_Efectiva']].copy()
            display_df.columns = ['Landing Page', 'Total Usuarios', 'Clicks CTA', 'CTR (%)', 'Formularios Enviados', 'Conversión Efectiva (%)']
            
            st.dataframe(
                display_df.style.format({
                    'Total Usuarios': '{:,.0f}',
                    'Clicks CTA': '{:,.0f}',
                    'CTR (%)': '{:.2f}%',
                    'Formularios Enviados': '{:,.0f}',
                    'Conversión Efectiva (%)': '{:.2f}%'
                }),
                use_container_width=True
            )

            # Opción para descargar
            st.download_button(
                label="📥 Descargar resultados como CSV",
                data=merged_df.to_csv(index=False),
                file_name="ctr_conversion_analysis_single.csv",
                mime="text/csv"
            )
            st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main() 