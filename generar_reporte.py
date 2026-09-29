import csv
import os
import re
import sys
from datetime import datetime
from collections import Counter
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    Image as RLImage,
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

# ============ CONFIGURACION ============
ARCHIVO_CSV = "EloisaWolf.csv"
ARCHIVO_SALIDA = "reporte_EloisaWolf.pdf"
CARPETA_MINIATURAS = "miniaturas"
INCLUIR_MINIATURAS = True
# =======================================

AZUL = colors.HexColor("#1F4E79")
ROJO = colors.HexColor("#C00000")
VERDE = colors.HexColor("#548235")
GRIS = colors.HexColor("#F2F2F2")


# ---------- Funciones auxiliares ----------
def limpiar(texto):
    """Prepara un texto para el PDF: quita emojis/simbolos raros que la
    fuente Helvetica no puede dibujar y escapa caracteres como & < >."""
    texto = str(texto or "")
    texto = "".join(
        c for c in texto
        if c == "\n" or (32 <= ord(c) <= 255) or (0x2018 <= ord(c) <= 0x201D)
    )
    texto = re.sub(r"\s+", " ", texto).strip()
    return escape(texto)


def a_entero(valor):
    """Convierte '1234' (o '1,234') en 1234. Si no se puede, devuelve 0."""
    txt = re.sub(r"[^\d]", "", str(valor or ""))
    return int(txt) if txt else 0


def mediana(lista):
    if not lista:
        return 0
    s = sorted(lista)
    n = len(s)
    if n % 2:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) // 2


def parse_duracion(iso):
    if not iso or not isinstance(iso, str):
        return 0
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    if not m:
        return 0
    h, mn, s = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mn * 60 + s


def parse_fecha(iso):
    try:
        return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        pass
    try:
        return datetime.strptime(str(iso)[:10], "%Y-%m-%d")
    except Exception:
        return None


def segundos_a_texto(seg):
    h, resto = divmod(seg, 3600)
    m, s = divmod(resto, 60)
    return f"{h}h {m}m" if h else f"{m}m {s}s"


def id_de_url(url):
    """Saca el ID de 11 caracteres de un enlace de YouTube."""
    m = re.search(r"(?:v=|youtu\.be/|shorts/|embed/)([A-Za-z0-9_-]{11})",
                  str(url or ""))
    if m:
        return m.group(1)
    return str(url or "").split("=")[-1][:11]


# ---------- Leer el CSV ----------
if not os.path.exists(ARCHIVO_CSV):
    print(f"ERROR: no encuentro el archivo '{ARCHIVO_CSV}'.")
    print("Ponlo en la misma carpeta que este script y vuelve a intentar.")
    sys.exit(1)

with open(ARCHIVO_CSV, encoding="utf-8-sig", newline="") as f:
    videos = list(csv.DictReader(f))

if not videos:
    print("ERROR: el CSV esta vacio.")
    sys.exit(1)

for v in videos:
    v["titulo"] = v.get("titulo", "") or ""
    v["url"] = v.get("url", "") or ""
    v["vistas"] = a_entero(v.get("vistas"))
    v["likes"] = a_entero(v.get("likes"))
    v["comentarios"] = a_entero(v.get("comentarios"))
    v["engagement"] = 0
    if v["vistas"]:
        v["engagement"] = round(
            (v["likes"] + v["comentarios"]) / v["vistas"] * 100, 2
        )
    v["segundos"] = parse_duracion(v.get("duracion", ""))
    v["fecha"] = parse_fecha(v.get("publicado", ""))

canal = videos[0].get("canal") or "Canal"

# Suscriptores: acepta la columna "suscriptores" o "suscriptores_canal"
suscriptores = 0
for v in videos:
    valor = a_entero(v.get("suscriptores")) or a_entero(
        v.get("suscriptores_canal")
    )
    if valor:
        suscriptores = valor
        break

# ---------- Calculos ----------
mediana_global = mediana([v["vistas"] for v in videos])
vistas_totales = sum(v["vistas"] for v in videos)
promedio = vistas_totales // len(videos)
eficiencia = 0
if suscriptores:
    eficiencia = round(mediana_global / suscriptores * 1000, 1)

mejor_video = max(videos, key=lambda x: x["vistas"])
mejor_eng = max(videos, key=lambda x: x["engagement"])

outliers = []
if mediana_global:
    outliers = [v for v in videos if v["vistas"] > mediana_global * 2]

stop = {
    "de", "la", "el", "en", "y", "a", "que", "los", "las", "un", "una",
    "para", "con", "por", "del", "al", "es", "se", "mi", "tu", "te",
    "lo", "como", "mas", "pero", "sin", "si", "no", "yo", "me",
    "the", "to", "of", "and", "in", "is", "you", "your",
    "más", "cómo", "qué", "así",
}

palabras = []
for v in videos:
    limpio = re.sub(r"[^\w\sáéíóúñü]", "", v["titulo"].lower())
    palabras += [
        p for p in limpio.split() if p not in stop and len(p) > 2
    ]
top_palabras = Counter(palabras).most_common(10)

cats_dur = [
    ("Shorts (0-60s)", lambda s: s <= 60),
    ("Cortos (1-5min)", lambda s: 60 < s <= 300),
    ("Medios (5-15min)", lambda s: 300 < s <= 900),
    ("Largos (15-30min)", lambda s: 900 < s <= 1800),
    ("Muy largos (+30min)", lambda s: s > 1800),
]

resumen_dur = []
for nombre, cond in cats_dur:
    grupo = [v for v in videos if cond(v["segundos"])]
    if grupo:
        med = mediana([x["vistas"] for x in grupo])
        eng = round(sum(x["engagement"] for x in grupo) / len(grupo), 2)
        resumen_dur.append((nombre, len(grupo), med, eng))

cubos_dia = {}
for v in videos:
    if v["fecha"]:
        cubos_dia.setdefault(v["fecha"].weekday(), []).append(v["vistas"])

dias = [
    "Lunes", "Martes", "Miércoles", "Jueves",
    "Viernes", "Sábado", "Domingo",
]
resumen_dia = []
for d in sorted(cubos_dia.keys()):
    vs = cubos_dia[d]
    resumen_dia.append((dias[d], len(vs), mediana(vs)))

top5 = sorted(videos, key=lambda x: x["vistas"], reverse=True)[:5]

# Miniaturas: se busca un archivo cuyo nombre contenga el ID del video
miniaturas_locales = {}
if INCLUIR_MINIATURAS and os.path.isdir(CARPETA_MINIATURAS):
    archivos = os.listdir(CARPETA_MINIATURAS)
    for v in top5:
        vid_id = id_de_url(v["url"])
        if not vid_id:
            continue
        for archivo in archivos:
            if vid_id in archivo:
                miniaturas_locales[v["url"]] = os.path.join(
                    CARPETA_MINIATURAS, archivo
                )
                break

# ---------- Estilos ----------
doc = SimpleDocTemplate(
    ARCHIVO_SALIDA, pagesize=A4,
    leftMargin=2 * cm, rightMargin=2 * cm,
    topMargin=2 * cm, bottomMargin=2 * cm,
)

estilos = getSampleStyleSheet()
e_titulo = ParagraphStyle(
    "t", parent=estilos["Title"],
    fontSize=28, textColor=AZUL, spaceAfter=20,
)
e_sub = ParagraphStyle(
    "s", parent=estilos["Heading1"],
    fontSize=18, textColor=AZUL, spaceAfter=12, spaceBefore=20,
)
e_texto = ParagraphStyle(
    "tx", parent=estilos["BodyText"],
    fontSize=10.5, alignment=TA_JUSTIFY, leading=15,
)
e_celda = ParagraphStyle(
    "ce", parent=estilos["BodyText"],
    fontSize=9, leading=12,
)
e_centrado = ParagraphStyle(
    "c", parent=estilos["BodyText"],
    fontSize=12, alignment=TA_CENTER,
)

historia = []

# ---------- Portada ----------
historia.append(Spacer(1, 5 * cm))
historia.append(Paragraph("Reporte de análisis de canal", e_titulo))
historia.append(Paragraph(limpiar(canal), e_sub))
historia.append(Spacer(1, 1.5 * cm))
historia.append(
    Paragraph(f"Análisis de los últimos {len(videos)} videos", e_centrado)
)
historia.append(Paragraph(f"Suscriptores: {suscriptores:,}", e_centrado))
historia.append(Spacer(1, 1 * cm))
historia.append(
    Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", e_centrado)
)
historia.append(PageBreak())

# ---------- 1. Resumen ejecutivo ----------
historia.append(Paragraph("1. Resumen ejecutivo", e_sub))
txt_res = (
    f"El canal {limpiar(canal)} cuenta con {suscriptores:,} suscriptores. "
    f"Se analizaron {len(videos)} videos recientes. "
    f"La mediana de vistas por video es {mediana_global:,}, "
    f"mientras que el promedio es {promedio:,}. "
    f"El video más exitoso alcanzó {mejor_video['vistas']:,} vistas."
)
historia.append(Paragraph(txt_res, e_texto))
historia.append(Spacer(1, 0.5 * cm))

tabla_res = [
    ["Métrica", "Valor"],
    ["Suscriptores", f"{suscriptores:,}"],
    ["Videos analizados", f"{len(videos)}"],
    ["Vistas totales", f"{vistas_totales:,}"],
    ["Mediana de vistas", f"{mediana_global:,}"],
    ["Promedio de vistas", f"{promedio:,}"],
    ["Vistas por 1000 subs", f"{eficiencia}"],
    ["Outliers (2x mediana)", f"{len(outliers)}"],
    ["Mejor video", Paragraph(limpiar(mejor_video["titulo"][:80]), e_celda)],
]
t = Table(tabla_res, colWidths=[6 * cm, 10 * cm])
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), AZUL),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 10),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ("TOPPADDING", (0, 0), (-1, -1), 6),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
]))
historia.append(t)
historia.append(PageBreak())

# ---------- 2. Top 5 videos ----------
historia.append(Paragraph("2. Top 5 videos con miniaturas", e_sub))
for i, v in enumerate(top5, 1):
    contenido = []
    ruta = miniaturas_locales.get(v["url"])
    if ruta and os.path.exists(ruta):
        try:
            contenido.append(
                RLImage(ruta, width=6 * cm, height=3.375 * cm)
            )
        except Exception:
            pass  # si la imagen esta daniada, se omite

    # OJO: en un Paragraph el salto de linea se escribe con <br/>
    datos_v = (
        f"<b>{i}. {limpiar(v['titulo'])}</b><br/><br/>"
        f"Vistas: {v['vistas']:,}<br/>"
        f"Likes: {v['likes']:,} · Comentarios: {v['comentarios']:,}<br/>"
        f"Engagement: {v['engagement']}%<br/>"
        f"Duración: {segundos_a_texto(v['segundos'])}"
    )
    contenido.append(Paragraph(datos_v, e_texto))

    if len(contenido) == 2:
        cols = [6.5 * cm, 9.5 * cm]
    else:
        cols = [16 * cm]
    t = Table([contenido], colWidths=cols)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    historia.append(t)
    historia.append(Spacer(1, 0.3 * cm))
historia.append(PageBreak())

# ---------- 3. Outliers ----------
if outliers:
    historia.append(Paragraph("3. Videos outlier", e_sub))
    txt_out = (
        f"Se detectaron {len(outliers)} videos con más del doble de "
        f"vistas que la mediana del canal. Son clave para entender "
        f"qué funciona."
    )
    historia.append(Paragraph(txt_out, e_texto))
    historia.append(Spacer(1, 0.4 * cm))

    tabla_out = [["Título", "Vistas", "Veces mediana", "Engagement"]]
    for v in sorted(outliers, key=lambda x: -x["vistas"])[:10]:
        tabla_out.append([
            Paragraph(limpiar(v["titulo"][:70]), e_celda),
            f"{v['vistas']:,}",
            f"{round(v['vistas'] / mediana_global, 1)}x",
            f"{v['engagement']}%",
        ])
    t = Table(tabla_out, colWidths=[9 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ROJO),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    historia.append(t)
    historia.append(PageBreak())

# ---------- 4. Palabras clave ----------
historia.append(Paragraph("4. Palabras clave en títulos", e_sub))
tabla_pal = [["Palabra", "Frecuencia"]]
for palabra, freq in top_palabras:
    tabla_pal.append([limpiar(palabra), str(freq)])
t = Table(tabla_pal, colWidths=[8 * cm, 5 * cm])
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), VERDE),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 10),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
]))
historia.append(t)
historia.append(PageBreak())

# ---------- 5. Rendimiento por duración ----------
historia.append(Paragraph("5. Rendimiento por duración", e_sub))
tabla_dur = [["Categoría", "Videos", "Mediana vistas", "Engagement"]]
for nombre, cant, med, eng in resumen_dur:
    tabla_dur.append([nombre, str(cant), f"{med:,}", f"{eng}%"])
t = Table(tabla_dur, colWidths=[6 * cm, 2.5 * cm, 4 * cm, 4 * cm])
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), AZUL),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 10),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
]))
historia.append(t)
historia.append(PageBreak())

# ---------- 6. Mejores días ----------
historia.append(Paragraph("6. Mejores días para publicar", e_sub))
tabla_dia = [["Día", "Videos", "Mediana vistas"]]
for nombre, cant, med in sorted(resumen_dia, key=lambda x: -x[2]):
    tabla_dia.append([nombre, str(cant), f"{med:,}"])
t = Table(tabla_dia, colWidths=[7 * cm, 3 * cm, 5 * cm])
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), VERDE),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 10),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
]))
historia.append(t)
historia.append(PageBreak())

# ---------- 7. Conclusiones ----------
historia.append(Paragraph("7. Conclusiones y recomendaciones", e_sub))
conclusiones = []

if resumen_dur:
    md = max(resumen_dur, key=lambda x: x[2])
    conclusiones.append(
        f"Duración óptima: la categoría {md[0]} tiene la mediana "
        f"más alta ({md[2]:,}). Producir más contenido en este rango."
    )
if resumen_dia:
    mdi = max(resumen_dia, key=lambda x: x[2])
    conclusiones.append(
        f"Mejor día: {mdi[0]}, con mediana de {mdi[2]:,} vistas. "
        f"Programar estrenos ese día."
    )
if outliers:
    conclusiones.append(
        f"Outliers: hay {len(outliers)} videos que superan 2x la "
        f"mediana. Analizar sus títulos, miniaturas y duración para "
        f"replicar la fórmula."
    )
if eficiencia > 100:
    conclusiones.append(
        f"Eficiencia excelente: {eficiencia} vistas por 1000 subs. "
        f"El contenido resuena con la audiencia."
    )
elif eficiencia < 30:
    conclusiones.append(
        f"Alerta de alcance: solo {eficiencia} vistas por 1000 subs. "
        f"Revisar títulos y miniaturas."
    )
else:
    conclusiones.append(
        f"Eficiencia saludable: {eficiencia} vistas por 1000 subs. "
        f"Margen de mejora en títulos y miniaturas."
    )
if promedio > mediana_global * 1.5:
    conclusiones.append(
        f"Distribución desigual: promedio ({promedio:,}) muy superior "
        f"a mediana ({mediana_global:,}). Unos pocos videos "
        f"concentran las vistas. Identificar y replicar esos casos."
    )
if top_palabras:
    pt = ", ".join(p for p, _ in top_palabras[:3])
    conclusiones.append(
        f"Identidad temática: palabras top en títulos: {limpiar(pt)}. "
        f"Reforzar estos temas."
    )
if mejor_eng["engagement"] > 5:
    conclusiones.append(
        f"Alto engagement: el video "
        f"{limpiar(mejor_eng['titulo'][:50])} alcanzó "
        f"{mejor_eng['engagement']}%. Considerar secuela."
    )

for c in conclusiones:
    historia.append(Paragraph(f"• {c}", e_texto))
    historia.append(Spacer(1, 0.3 * cm))

historia.append(Spacer(1, 1 * cm))
historia.append(Paragraph(
    "Reporte generado automáticamente a partir de datos "
    "públicos de YouTube.",
    e_centrado,
))

# ---------- Crear el PDF ----------
doc.build(historia)
print(f"Listo: {ARCHIVO_SALIDA}")
print(f"Reporte con {len(conclusiones)} conclusiones automáticas.")
