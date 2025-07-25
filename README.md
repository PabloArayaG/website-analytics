# Analizador de CTR y Conversión Efectiva - Google Analytics

Esta aplicación permite analizar el Click Through Rate (CTR) y la **Conversión Efectiva** de diferentes landing pages basándose en datos de Google Analytics.

## 📊 Funcionalidades

✅ **Análisis de CTR**: Calcula el Click Through Rate (Clicks CTA / Total Usuarios) × 100  
✅ **Conversión Efectiva**: Calcula la tasa de conversión real (Formularios Enviados / Total Usuarios) × 100  
✅ **Interfaz moderna**: Diseño intuitivo con Streamlit  
✅ **Carga múltiple de CSV**: Procesamiento automático de hasta 3 archivos  
✅ **Métricas detalladas**: Análisis completo con rankings y comparativas  
✅ **Exportación de resultados**: Descarga en formato CSV  

## Requisitos

- Python 3.7 o superior
- pip (gestor de paquetes de Python)

## Instalación

1. Clona este repositorio o descarga los archivos
2. Instala las dependencias:
```bash
pip install -r requirements.txt
```

## Uso

1. Ejecuta la aplicación:
```bash
streamlit run app.py --server.port 3000
```

2. En la interfaz web podrás realizar dos tipos de análisis:

### 📈 Análisis Completo (CTR + Conversión Efectiva)
Necesitas **3 archivos CSV** exportados desde Google Analytics:

1. **Datos de Clicks CTA**: Usuarios que hicieron click en el Call to Action
2. **Datos de Usuarios**: Total de usuarios únicos que visitaron cada landing page  
3. **Datos de Formularios Enviados**: Usuarios únicos que completaron el formulario

**Métricas que obtienes:**
- CTR por landing page
- Conversión Efectiva por landing page  
- Ranking de mejores performers
- Métricas globales y promedios

### 📊 Análisis Básico (Solo CTR)
Si solo tienes **2 archivos CSV**:

1. **Datos de Clicks CTA**
2. **Datos de Usuarios**

**Métricas que obtienes:**
- Solo análisis de CTR
- Notificación para análisis completo

## 🔍 Resultados

La aplicación procesará automáticamente los archivos y mostrará:

- **Métricas principales**: Totales y promedios
- **Tabla detallada**: Resultados por cada landing page
- **Top 5 Rankings**: Mejores landing pages por CTR y Conversión Efectiva
- **Descarga CSV**: Exporta todos los resultados para análisis adicional

## 📝 Formato de Archivos CSV

Los archivos CSV deben contener:
- Una columna con la ruta de la página (page_path, pagina, url, ruta)
- Una columna con los valores numéricos correspondientes

**Ejemplos de nombres de columnas reconocidos:**
- **Páginas**: `page_path`, `pagina`, `url`, `ruta`
- **Clicks CTA**: `cta_clicks`, `clicks`, `clics`, `total_usuarios`
- **Usuarios**: `total_usuarios`, `usuarios`, `total users`, `usuarios únicos`
- **Formularios**: `form_submit`, `formularios`, `envios`, `formularios_enviados`

## 🌐 Acceso

Una vez ejecutada la aplicación, accede desde tu navegador a:
**http://localhost:3000**

## Notas

- Los archivos CSV deben ser exportados directamente desde Google Analytics
- La aplicación detecta automáticamente las columnas y el formato
- Se filtran automáticamente filas vacías y totales
- Compatible con delimitadores de coma (,) y punto y coma (;) 