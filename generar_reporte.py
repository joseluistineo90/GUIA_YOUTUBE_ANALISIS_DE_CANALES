import csv, os, re
from datetime import datetime
from collections import Counter
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Table,
    TableStyle,
    Image as RLImage,
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

ARCHIVO_CSV = "EloisaWolf.csv"
ARCHIVO_SALIDA = "reporte_EloisaWolf.pdf"
CARPETA_MINIATURAS = "miniaturas"
INCLUIR_MINIATURAS = True

AZUL = colors.HexColor("#1F4E79")
ROJO = colors.HexColor("#C00000")
VERDE = colors.HexColor("#548235")
GRIS = colors.HexColor("#F2F2F2")


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
        return None


def segundos_a_texto(seg):
    h, resto = divmod(seg, 3600)
    m, s = divmod(resto, 60)
    return f"{h}h {m}m" if h else f"{m}m {s}s"


with open(ARCHIVO_CSV, encoding="utf-8") as f:
    videos = list(csv.DictReader(f))

for v in videos:
    v["vistas"] = int(v["vistas"]) if str(v["vistas"]).isdigit() else 0
    v["likes"] = int(v["likes"]) if str(v["likes"]).isdigit() else 0
    v["comentarios"] = int(v["comentarios"]) if str(v["comentarios"]).isdigit() else 0
    v["engagement"] = 0
    if v["vistas"]:
        v["engagement"] = round((v["likes"] + v["comentarios"]) / v["vistas"] * 100, 2)
    v["segundos"] = parse_duracion(v.get("duracion", ""))
    v["fecha"] = parse_fecha(v.get("publicado", ""))
    v["suscriptores"] = 0
    if str(v.get("suscriptores_canal", "")).isdigit():
        v["suscriptores"] = int(v["suscriptores_canal"])

canal = videos[0].get("canal", "Canal") if videos else "Canal"
suscriptores = videos[0].get("suscriptores", 0) if videos else 0

vistas_ordenadas = sorted(v["vistas"] for v in videos)
mediana_global = 0
if vistas_ordenadas:
    mediana_global = vistas_ordenadas[len(vistas_ordenadas) // 2]

vistas_totales = sum(v["vistas"] for v in videos)
promedio = vistas_totales // len(videos) if videos else 0
eficiencia = 0
if suscriptores:
    eficiencia = round(mediana_global / suscriptores * 1000, 1)

mejor_video = max(videos, key=lambda x: x["vistas"]) if videos else {}
mejor_eng = max(videos, key=lambda x: x["engagement"]) if videos else {}

outliers = []
if mediana_global:
    outliers = [v for v in videos if v["vistas"] > mediana_global * 2]

stop = {
    "de",
    "la",
    "el",
    "en",
    "y",
    "a",
    "que",
    "los",
    "las",
    "un",
    "una",
    "para",
    "con",
    "por",
    "del",
    "al",
    "es",
    "se",
    "mi",
    "tu",
    "te",
    "lo",
    "como",
    "mas",
    "pero",
    "sin",
    "si",
    "no",
    "yo",
    "me",
    "the",
    "to",
    "of",
    "and",
    "in",
    "is",
    "you",
    "your",
    "más",
    "cómo",
    "qué",
    "así",
}

palabras = []
for v in videos:
    limpio = re.sub(r"[^\w\sáéíóúñü]", "", v["titulo"].lower())
    palabras += [p for p in limpio.split() if p not in stop and len(p) > 2]
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
        med = sorted(x["vistas"] for x in grupo)[len(grupo) // 2]
        eng = round(sum(x["engagement"] for x in grupo) / len(grupo), 2)
        resumen_dur.append((nombre, len(grupo), med, eng))

cubos_dia = {}
for v in videos:
    if v["fecha"]:
        d = v["fecha"].weekday()
        cubos_dia.setdefault(d, []).append(v["vistas"])

dias = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]
resumen_dia = []
for d in sorted(cubos_dia.keys()):
    vs = sorted(cubos_dia[d])
    resumen_dia.append((dias[d], len(vs), vs[len(vs) // 2]))

miniaturas_locales = []
if INCLUIR_MINIATURAS and os.path.isdir(CARPETA_MINIATURAS):
    top5 = sorted(videos, key=lambda x: x["vistas"], reverse=True)[:5]
    for v in top5:
        vid_id = v["url"].split("=")[-1]
        for archivo in os.listdir(CARPETA_MINIATURAS):
            if vid_id[:11] in archivo:
                ruta = os.path.join(CARPETA_MINIATURAS, archivo)
                miniaturas_locales.append((v["url"], ruta))
                break

doc = SimpleDocTemplate(
    ARCHIVO_SALIDA,
    pagesize=A4,
    leftMargin=2 * cm,
    rightMargin=2 * cm,
    topMargin=2 * cm,
    bottomMargin=2 * cm,
)

estilos = getSampleStyleSheet()
e_titulo = ParagraphStyle(
    "t", parent=estilos["Title"], fontSize=28, textColor=AZUL, spaceAfter=20
)
e_sub = ParagraphStyle(
    "s",
    parent=estilos["Heading1"],
    fontSize=18,
    textColor=AZUL,
    spaceAfter=12,
    spaceBefore=20,
)
e_texto = ParagraphStyle(
    "tx", parent=estilos["BodyText"], fontSize=10.5, alignment=TA_JUSTIFY, leading=15
)
e_centrado = ParagraphStyle(
    "c", parent=estilos["BodyText"], fontSize=12, alignment=TA_CENTER
)

historia = []

historia.append(Spacer(1, 5 * cm))
historia.append(Paragraph("Reporte de análisis de canal", e_titulo))
historia.append(Paragraph(canal, e_sub))
historia.append(Spacer(1, 1.5 * cm))

txt1 = f"Análisis de los últimos {len(videos)} videos"
historia.append(Paragraph(txt1, e_centrado))

txt2 = f"Suscriptores: {suscriptores:,}"
historia.append(Paragraph(txt2, e_centrado))
historia.append(Spacer(1, 1 * cm))

fecha_hoy = datetime.now().strftime("%d/%m/%Y")
historia.append(Paragraph(f"Fecha: {fecha_hoy}", e_centrado))
historia.append(PageBreak())

historia.append(Paragraph("1. Resumen ejecutivo", e_sub))
txt_res = (
    f"El canal {canal} cuenta con {suscriptores:,} suscriptores. "
    f"Se analizaron {len(videos)} videos recientes. "
    f"La mediana de vistas por video es {mediana_global:,}, "
    f"mientras que el promedio es {promedio:,}. "
    f"El video más exitoso alcanzó "
    f"{mejor_video.get('vistas', 0):,} vistas."
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
    ["Mejor video", mejor_video.get("titulo", "")[:60]],
]
t = Table(tabla_res, colWidths=[6 * cm, 10 * cm])
t.setStyle(
    TableStyle(
        [
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
        ]
    )
)
historia.append(t)
historia.append(PageBreak())

historia.append(Paragraph("2. Top 5 videos con miniaturas", e_sub))
top5 = sorted(videos, key=lambda x: x["vistas"], reverse=True)[:5]
for i, v in enumerate(top5, 1):
    contenido = []
    miniatura_encontrada = None
    for url_m, ruta in miniaturas_locales:
        if url_m == v["url"]:
            miniatura_encontrada = ruta
            break
    if miniatura_encontrada and os.path.exists(miniatura_encontrada):
        img = RLImage(miniatura_encontrada, width=6 * cm, height=3.375 * cm)
        contenido.append(img)

        datos_v = (
            f"<b>{i}. {v['titulo']}</b><br/>"
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
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    historia.append(t)
    historia.append(Spacer(1, 0.3 * cm))
historia.append(PageBreak())

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
    for v in outliers[:10]:
        tabla_out.append(
            [
                Paragraph(v["titulo"][:70], e_texto),
                f"{v['vistas']:,}",
                f"{round(v['vistas'] / mediana_global, 1)}x",
                f"{v['engagement']}%",
            ]
        )
    t = Table(tabla_out, colWidths=[9 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), ROJO),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ]
        )
    )
    historia.append(t)
    historia.append(PageBreak())

historia.append(Paragraph("4. Palabras clave en títulos", e_sub))
tabla_pal = [["Palabra", "Frecuencia"]]
for palabra, freq in top_palabras:
    tabla_pal.append([palabra, str(freq)])
t = Table(tabla_pal, colWidths=[8 * cm, 5 * cm])
t.setStyle(
    TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), VERDE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ]
    )
)
historia.append(t)
historia.append(PageBreak())

historia.append(Paragraph("5. Rendimiento por duración", e_sub))
tabla_dur = [["Categoría", "Videos", "Mediana vistas", "Engagement"]]
for nombre, cant, med, eng in resumen_dur:
    tabla_dur.append([nombre, str(cant), f"{med:,}", f"{eng}%"])
t = Table(tabla_dur, colWidths=[6 * cm, 2.5 * cm, 4 * cm, 4 * cm])
t.setStyle(
    TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), AZUL),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ]
    )
)
historia.append(t)
historia.append(PageBreak())

historia.append(Paragraph("6. Mejores días para publicar", e_sub))
tabla_dia = [["Día", "Videos", "Mediana vistas"]]
for nombre, cant, med in sorted(resumen_dia, key=lambda x: -x[2]):
    tabla_dia.append([nombre, str(cant), f"{med:,}"])
t = Table(tabla_dia, colWidths=[7 * cm, 3 * cm, 5 * cm])
t.setStyle(
    TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), VERDE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ]
    )
)
historia.append(t)
historia.append(PageBreak())

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
    pt = ", ".join([p for p, _ in top_palabras[:3]])
    conclusiones.append(
        f"Identidad temática: palabras top en títulos: {pt}. " f"Reforzar estos temas."
    )
if mejor_eng and mejor_eng.get("engagement", 0) > 5:
    conclusiones.append(
        f"Alto engagement: el video "
        f"{mejor_eng.get('titulo', '')[:50]} alcanzó "
        f"{mejor_eng.get('engagement', 0)}%. Considerar secuela."
    )

for c in conclusiones:
    historia.append(Paragraph(f"• {c}", e_texto))
    historia.append(Spacer(1, 0.3 * cm))

historia.append(Spacer(1, 1 * cm))
historia.append(
    Paragraph(
        "Reporte generado automáticamente a partir de datos " "públicos de YouTube.",
        e_centrado,
    )
)

doc.build(historia)
print(f"Listo: {ARCHIVO_SALIDA}")
print(f"Reporte con {len(conclusiones)} conclusiones automáticas.")
