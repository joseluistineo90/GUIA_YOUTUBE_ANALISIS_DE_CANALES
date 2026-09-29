# GUIA_YOUTUBE_ANALISIS_DE_CANALES
🎬 Automatización y Análisis Profesional de Canales de YouTube
> Sistema completo en Python para extraer datos públicos de YouTube, generar análisis avanzados en Excel (con métricas de mediana, distribución y colores de miniaturas) y reportes ejecutivos automatizados en PDF listos para clientes.

---

## 🚀 ¿Qué incluye este repositorio?

Este proyecto consta de tres scripts modulares desarrollados para tutoriales de ingeniería de sistemas y analítica:

1. **`scraper_canal.py`**: Conecta con la YouTube Data API v3 para extraer los últimos videos de cualquier canal, calcula estadísticas clave y exporta los datos crudos a CSV.
2. **`analisis_1canal.py`**: Procesa el archivo CSV, descarga las miniaturas de los videos, analiza su color dominante y genera un libro de **Excel (.xlsx) con 10 hojas de análisis**, gráficas y formato condicional.
3. **`generar_reporte.py`**: Compila un **informe ejecutivo en PDF** profesional utilizando ReportLab, integrando miniaturas embebidas y conclusiones automatizadas.

---

## 📋 Requisitos Previos e Instalación

Asegúrate de tener instalado **Python 3.8+** en tu equipo. Abre tu terminal y ejecuta los siguientes comandos para instalar las dependencias necesarias:

```bash
pip install openpyxl google-api-python-client pillow requests reportlab
⚙️ Configuración y Uso
Paso 1: Obtén tu API Key de YouTube (Gratis)
Entra a Google Cloud Console.

Crea un nuevo proyecto y habilita la YouTube Data API v3.

Genera tus credenciales (Clave de API).

Paso 2: Configura y Ejecuta el Scraper
Abre el archivo scraper_canal.py, añade tu API Key y el handle del canal que deseas analizar:

Python
API_KEY = "TU_API_KEY_AQUI"
CHANNEL_HANDLE = "NombreDelCanal"
MAX_VIDEOS = 30
Ejecuta el script en la terminal:

Bash
python scraper_canal.py
Paso 3: Genera el Análisis y el Reporte PDF
Una vez obtenido el archivo .csv, ejecuta secuencialmente:

Bash
python analisis_1canal.py
python generar_reporte.py
📂 Estructura del Proyecto
Plaintext
├── scraper_canal.py       # Extractor de datos vía API de YouTube
├── analisis_1canal.py     # Generador de Excel analítico (10 hojas)
├── generar_reporte.py     # Compilador de reporte ejecutivo en PDF
├── miniaturas/            # Carpeta autogenerada con las imágenes analizadas
└── README.md              # Documentación oficial del proyecto
🤝 Contribuciones y Soporte
¿Encontraste un error o quieres proponer una mejora? ¡Las pull requests son bienvenidas!

Si este material te ha sido útil para tus proyectos o aprendizaje:
⭐ ¡Regálale una estrella a este repositorio! Eso me ayuda enormemente a seguir creando contenido
 educativo gratuito sobre ingeniería y desarrollo.

Hecho con 💻 y Python por [Tu Nombre / Tu Canal]
