"""
Interfaz web de LibrerIA: "Pregúntale a Lía".

    streamlit run app.py

Para cambiar textos, colores, imágenes o pictogramas NO hace falta tocar
este fichero: usa la carpeta personalizacion/.

Truco: la dirección acepta el idioma, p. ej.  ...?idioma=fr
"""

import html
import json

import streamlit as st

from libreria import config, goodreads, motor, voz
from libreria.interprete import interpretar_consulta, resumen
from libreria.marca import cargar_marca, imagen_data_uri, pictograma_data_uri, textos_marca
from libreria.textos import IDIOMAS, t

MARCA = cargar_marca()
LIA = MARCA["asistente"]
IDIOMAS_ACTIVOS = [i for i in MARCA["idiomas"] if i in IDIOMAS] or ["es"]

st.set_page_config(
    page_title=f"{LIA} · {MARCA['libreria']}",
    page_icon="📖",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# --------------------------------------------------
# ESTADO (preferencias de accesibilidad y conversación)
# --------------------------------------------------

def _estado(clave, valor):
    if clave not in st.session_state:
        st.session_state[clave] = valor


_idioma_url = st.query_params.get("idioma")
_estado("idioma", _idioma_url if _idioma_url in IDIOMAS_ACTIVOS else
        (MARCA["idioma_por_defecto"] if MARCA["idioma_por_defecto"] in IDIOMAS_ACTIVOS else IDIOMAS_ACTIVOS[0]))
_estado("letra_grande", False)
_estado("letra_legible", False)
_estado("alto_contraste", False)
_estado("sin_animaciones", False)
_estado("mostrar_pictogramas", True)
_estado("voz", True)
_estado("velocidad_voz", "normal")
_estado("conversacion", [])
_estado("clave_audio", 0)

IDIOMA = st.session_state.idioma
TX = textos_marca(MARCA, IDIOMA)


def T(clave, **valores):
    return t(IDIOMA, clave, lia=LIA, **valores)


# --------------------------------------------------
# CARGA ÚNICA (modelo + catálogo)
# --------------------------------------------------

@st.cache_resource(show_spinner=False)
def iniciar():
    catalogo, embeddings = motor.cargar_catalogo()
    motor.cargar_modelo()
    return catalogo, embeddings


@st.cache_data
def imagenes():
    return {nombre: imagen_data_uri(nombre) for nombre in ["lia", "logo", "fondo", "cabecera"]}


@st.cache_data
def pictogramas():
    return {p["id"]: pictograma_data_uri(p["id"]) for p in MARCA["pictogramas"]}


try:
    with st.spinner(T("cargando")):
        catalogo, embeddings = iniciar()
except (FileNotFoundError, ValueError) as error:
    st.error(str(error))
    st.stop()

IMG = imagenes()
PICTOS = pictogramas()
VOZ_DISPONIBLE = voz.disponible()


# --------------------------------------------------
# ESTILO
# --------------------------------------------------

ALTO_CONTRASTE = {
    "fondo": "#FFFFFF", "tarjeta": "#FFFFFF", "texto": "#000000",
    "texto_suave": "#1A1A1A", "acento": "#0B3D91", "suave": "#FFFFFF",
}


def _rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def iframe_html(contenido, alto):
    """HTML con JavaScript (botones de voz). st.iframe en Streamlit nuevo, components.html en el antiguo."""
    if hasattr(st, "iframe"):
        st.iframe(contenido, height=alto)
    else:
        import streamlit.components.v1 as components
        components.html(contenido, height=alto)


def md(contenido):
    """Muestra HTML. Se quitan saltos de línea para que Markdown no lo rompa."""
    st.markdown("".join(linea.strip() for linea in contenido.splitlines()), unsafe_allow_html=True)


def aplicar_estilo():
    s = st.session_state
    C = ALTO_CONTRASTE if s.alto_contraste else MARCA["colores"]

    fondo_img = ""
    if IMG["fondo"] and not s.alto_contraste:
        velo = _rgba(C["fondo"], MARCA["opacidad_fondo"])
        fondo_img = (
            f"background-image: linear-gradient({velo}, {velo}), url('{IMG['fondo']}');"
            "background-size: cover; background-position: center; background-attachment: fixed;"
        )

    tamano = "20px" if s.letra_grande else "16px"
    if s.letra_legible:
        f_texto = f_titulo = "'Atkinson Hyperlegible', Verdana, sans-serif"
        extra_letra = ".stApp p, .stApp li, .burbuja, .libro {{ letter-spacing:.02em; line-height:1.75 !important; }}"
    else:
        f_texto = "'Nunito', system-ui, sans-serif"
        f_titulo = "'Fraunces', Georgia, serif"
        extra_letra = ""
    extra_letra = extra_letra.replace("{{", "{").replace("}}", "}")

    borde = "2px solid #000" if s.alto_contraste else "1px solid var(--suave)"
    sombra = "none" if s.alto_contraste else f"0 3px 12px {_rgba(C['texto'], .06)}"
    sin_anim = ("*, *::before, *::after { animation:none !important; transition:none !important; "
                "scroll-behavior:auto !important; }") if s.sin_animaciones else ""

    md(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Nunito:wght@400;600;700&display=swap');
:root {{
  --fondo: {C['fondo']}; --tarjeta: {C['tarjeta']}; --texto: {C['texto']};
  --texto-suave: {C['texto_suave']}; --acento: {C['acento']}; --suave: {C['suave']};
}}
html {{ font-size: {tamano}; }}
.stApp {{ background-color: var(--fondo); {fondo_img} }}
.stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp button, .stApp summary {{
  font-family: {f_texto}; color: var(--texto);
}}
{extra_letra}
header[data-testid="stHeader"], #MainMenu, footer, .stDeployButton,
[data-testid="stToolbar"], [data-testid="stSidebarCollapsedControl"] {{ display: none !important; }}
.block-container {{ padding-top: 1.2rem; padding-bottom: 7rem; max-width: 780px; }}
:focus-visible {{ outline: 3px solid var(--acento) !important; outline-offset: 2px; }}

.lia-top {{ display:flex; align-items:center; gap:.7rem; min-height:44px; }}
.lia-top img {{ height: 44px; width:auto; }}
.lia-top .nombre {{ font-family:{f_titulo}; font-weight:700; font-size:1.15rem; }}

.lia-hero {{ text-align:center; margin: .5rem 0 1.2rem; }}
.lia-hero .ilustracion {{ width:100%; border-radius:18px; margin-bottom:1rem; }}
.lia-hero .avatar {{ width:112px; height:112px; border-radius:50%; object-fit:cover;
  border:4px solid var(--tarjeta); box-shadow: 0 6px 20px {_rgba(C['texto'], .15)}; }}
.lia-hero h1 {{ font-family:{f_titulo}; font-weight:700; font-size:2.3rem;
  margin:.6rem 0 .2rem; color:var(--texto); padding:0; }}
.lia-hero p {{ color:var(--texto-suave); font-size:1.05rem; max-width:34rem; margin:0 auto; }}

.msg {{ display:flex; gap:.7rem; margin: 1rem 0 .3rem; align-items:flex-start; }}
.msg .mini {{ width:42px; height:42px; border-radius:50%; object-fit:cover; flex-shrink:0; }}
.burbuja {{ background:var(--tarjeta); border:{borde}; border-radius: 4px 18px 18px 18px;
  padding:.8rem 1rem; line-height:1.55; box-shadow:{sombra}; max-width:100%; }}
.msg.usuario {{ justify-content:flex-end; margin-bottom:1rem; }}
.msg.usuario .burbuja {{ background:var(--acento); color:#fff; border:none;
  border-radius: 18px 4px 18px 18px; max-width:80%; }}
.entendido {{ display:inline-block; margin-top:.5rem; font-size:.85rem; color:var(--texto-suave);
  background:var(--suave); border:{borde if s.alto_contraste else 'none'}; border-radius:999px; padding:.15rem .7rem; }}

.libro {{ display:flex; gap:1rem; background:var(--tarjeta); border:{borde};
  border-radius:16px; padding:1rem; margin:.7rem 0 .7rem 3.2rem; box-shadow:{sombra}; }}
.libro .portada {{ width:88px; min-width:88px; height:132px; object-fit:cover; border-radius:6px;
  box-shadow: 2px 3px 8px {_rgba(C['texto'], .25)}; background:var(--suave);
  color:transparent; font-size:0; }}
.libro .sin-portada {{ display:flex; align-items:center; justify-content:center;
  font-family:{f_titulo}; font-size:2rem; color:var(--acento); }}
.libro .titulo {{ font-family:{f_titulo}; font-weight:700; font-size:1.2rem; line-height:1.25; }}
.libro .autor {{ color:var(--texto-suave); margin:.15rem 0 .45rem; }}
.chips span {{ display:inline-block; font-size:.8rem; background:var(--suave); border-radius:999px;
  border:{borde if s.alto_contraste else 'none'}; padding:.1rem .6rem; margin:0 .3rem .3rem 0; }}
.donde {{ margin-top:.3rem; font-weight:700; color:var(--acento); }}
.libro details {{ margin-top:.4rem; }}
.libro summary {{ cursor:pointer; color:var(--acento); font-weight:700; }}
.libro details p {{ font-size:.93rem; line-height:1.55; margin-top:.4rem; }}

.picto {{ text-align:center; font-size:3rem; line-height:1; height:84px; display:flex;
  align-items:center; justify-content:center; }}
.picto img {{ max-height:84px; max-width:100%; }}
.titulo-seccion {{ font-family:{f_titulo}; font-weight:700; font-size:1.15rem; margin:1.4rem 0 .6rem; }}

.stButton button {{ border-radius:999px; border:{'2px solid #000' if s.alto_contraste else '1.5px solid var(--acento)'};
  background:var(--tarjeta); color:var(--texto); font-weight:700; padding:.45rem 1rem; }}
.stButton button p {{ white-space:normal; line-height:1.3; }}
.stButton button:hover {{ background:var(--acento); color:#fff; border-color:var(--acento); }}

[data-testid="stBottom"] > div, [data-testid="stBottomBlockContainer"] {{ background: transparent; }}
[data-testid="stChatInput"] {{ border:2px solid var(--acento); border-radius:18px; background:var(--tarjeta); }}
[data-testid="stChatInput"] textarea {{ font-size:1.05rem; font-family:{f_texto}; }}
[data-testid="stChatInput"] > div, [data-testid="stChatInput"] textarea {{ background:var(--tarjeta) !important; color:var(--texto); }}
[data-testid="stPopover"] button, [data-testid="stButtonGroup"] button {{ background:var(--tarjeta); color:var(--texto); }}
[data-testid="stAudioInput"] > div {{ background:var(--tarjeta); border:{borde}; }}
[data-testid="stExpander"] details {{ background:var(--tarjeta); border:{borde}; border-radius:14px; }}
[data-testid="stAudioInput"] {{ border-radius:14px; }}

.aviso {{ text-align:center; color:var(--texto-suave); font-size:.9rem; margin-top:2rem; }}
{sin_anim}

@media (max-width: 640px) {{
  [data-testid="stHorizontalBlock"] {{ flex-wrap:wrap !important; gap:.5rem !important; }}
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
    min-width:calc(50% - .5rem) !important; flex:1 1 calc(50% - .5rem) !important; }}
  .picto {{ font-size:2.4rem; height:64px; }}
  .picto img {{ max-height:64px; }}
  .libro {{ margin-left:0; }}
  .libro .portada {{ width:70px; min-width:70px; height:105px; }}
  .lia-hero h1 {{ font-size:1.8rem; }}
}}
</style>
""")
    return C


# --------------------------------------------------
# VOZ: botones para escuchar (usa la voz del navegador, gratis)
# --------------------------------------------------

VELOCIDADES = {"lenta": 0.8, "normal": 1.0, "rapida": 1.2}


def boton_escuchar(texto, colores):
    if not st.session_state.voz or not texto:
        return
    lang = IDIOMAS[IDIOMA]["voz"]
    velocidad = VELOCIDADES[st.session_state.velocidad_voz]
    iframe_html(f"""
<style>
  body {{ margin:0; font-family: system-ui, sans-serif; }}
  button {{ font-size:15px; padding:6px 14px; margin-right:6px; border-radius:999px; cursor:pointer;
           border:1.5px solid {colores['acento']}; background:{colores['tarjeta']}; color:{colores['texto']}; }}
  button:hover, button:focus-visible {{ background:{colores['acento']}; color:#fff; outline:none; }}
</style>
<div id="caja">
  <button id="play" aria-label="{html.escape(T('escuchar'))}">{html.escape(T('escuchar'))}</button>
  <button id="stop" aria-label="{html.escape(T('parar'))}">{html.escape(T('parar'))}</button>
</div>
<script>
  const texto = {json.dumps(texto)}, lang = "{lang}", velocidad = {velocidad};
  const synth = window.speechSynthesis;
  if (!synth) {{ document.getElementById("caja").style.display = "none"; }}
  function elegirVoz() {{
    const voces = synth.getVoices();
    return voces.find(v => v.lang === lang) || voces.find(v => v.lang && v.lang.startsWith(lang.slice(0, 2)));
  }}
  document.getElementById("play").onclick = () => {{
    synth.cancel();
    const u = new SpeechSynthesisUtterance(texto);
    u.lang = lang; u.rate = velocidad;
    const v = elegirVoz(); if (v) u.voice = v;
    synth.speak(u);
  }};
  document.getElementById("stop").onclick = () => synth.cancel();
</script>""", 44)


def fijar_idioma_pagina():
    """Pone <html lang="..."> para que los lectores de pantalla usen la pronunciación correcta."""
    iframe_html(f"<script>window.parent.document.documentElement.lang = '{IDIOMA}';</script>", 1)


# --------------------------------------------------
# PIEZAS DE HTML
# --------------------------------------------------

def e(texto):
    return html.escape(str(texto)) if texto is not None else ""


def html_mensaje_lia(texto_html):
    avatar = f'<img class="mini" src="{IMG["lia"]}" alt="{e(LIA)}">' if IMG["lia"] else ""
    return f'<div class="msg" role="status">{avatar}<div class="burbuja">{texto_html}</div></div>'


def html_mensaje_usuario(texto):
    return f'<div class="msg usuario"><div class="burbuja">{e(texto)}</div></div>'


def html_libro(libro):
    if libro["portada"]:
        portada = f'<img class="portada" src="{e(libro["portada"])}" alt="">'
    else:
        portada = f'<div class="portada sin-portada" aria-hidden="true">{e(libro["titulo"][:1])}</div>'

    chips = []
    if libro["paginas"]:
        chips.append(f"{libro['paginas']} {T('paginas')}")
    if libro["rating"]:
        chips.append(f"★ {libro['rating']:.1f}")
    if libro["anio"]:
        chips.append(str(libro["anio"]))
    if libro["categoria"]:
        chips.append(libro["categoria"])
    chips_html = "".join(f"<span>{e(c)}</span>" for c in chips)

    donde = f'<div class="donde">📍 {e(T("donde"))}: {e(libro["seccion"])}</div>' if libro.get("seccion") else ""

    descripcion = libro["descripcion"] or ""
    if len(descripcion) > 900:
        descripcion = descripcion[:900].rsplit(" ", 1)[0] + "…"

    return f"""
<div class="libro" role="article" aria-label="{e(libro['titulo'])}">
  {portada}
  <div>
    <div class="titulo">{e(libro['titulo'])}</div>
    <div class="autor">{e(libro['autor'])}</div>
    <div class="chips">{chips_html}</div>
    {donde}
    <details><summary>{e(T('de_que_va'))}</summary><p>{e(descripcion)}</p></details>
  </div>
</div>"""


def texto_para_escuchar(intro, libros):
    partes = [intro]
    for n, libro in enumerate(libros, 1):
        frase = f"{n}. {libro['titulo']}"
        if libro["autor"]:
            frase += f", {T('de')} {libro['autor']}"
        if libro["paginas"]:
            frase += f". {libro['paginas']} {T('paginas')}"
        if libro.get("seccion"):
            frase += f". {T('donde')}: {libro['seccion']}"
        partes.append(frase + ".")
    return " ".join(partes)


# --------------------------------------------------
# BÚSQUEDA
# --------------------------------------------------

def responder(consulta, mostrado, perfil):
    pref = interpretar_consulta(consulta)
    resultados = motor.recomendar_libros(
        consulta=pref["consulta_semantica"],
        cantidad=config.RESULTADOS_POR_DEFECTO,
        max_paginas=pref["max_paginas"],
        min_paginas=pref["min_paginas"],
        min_rating=pref["min_rating"],
        excluir=pref["excluir"],
        perfil=perfil,
    )
    if not resultados:
        intro = "sin_resultados"
    elif perfil and not pref["consulta_semantica"]:
        intro = "intro_perfil"
    else:
        intro = "intro_resultados"

    st.session_state.conversacion.append({"rol": "usuario", "texto": mostrado})
    st.session_state.conversacion.append({"rol": "lia", "intro": intro, "pref": pref, "libros": resultados})


# ==================================================
# PÁGINA
# ==================================================

# ---------- Barra superior: marca · idioma · accesibilidad ----------
col_marca, col_idioma, col_acc = st.columns([4, 3, 3], vertical_alignment="center")

def _cambiar_idioma():
    nuevo = st.session_state.selector_idioma
    st.session_state.idioma = nuevo
    st.query_params["idioma"] = nuevo


with col_idioma:
    if len(IDIOMAS_ACTIVOS) > 1:
        st.segmented_control(
            T("idioma"), IDIOMAS_ACTIVOS, default=IDIOMA, required=True,
            format_func=lambda i: i.upper(), label_visibility="collapsed",
            key="selector_idioma", on_change=_cambiar_idioma,
        )

with col_acc:
    with st.popover(f"♿ {T('accesibilidad')}", width="stretch"):
        st.toggle(T("letra_grande"), key="letra_grande")
        st.toggle(T("letra_legible"), key="letra_legible")
        st.toggle(T("alto_contraste"), key="alto_contraste")
        st.toggle(T("sin_animaciones"), key="sin_animaciones")
        if MARCA["pictogramas"]:
            st.toggle(T("mostrar_pictogramas"), key="mostrar_pictogramas")
        st.toggle(T("voz"), key="voz")
        if st.session_state.voz:
            st.select_slider(
                T("velocidad_voz"), options=list(VELOCIDADES), key="velocidad_voz",
                format_func=lambda v: T(v),
            )

COLORES = aplicar_estilo()
fijar_idioma_pagina()

with col_marca:
    logo = f'<img src="{IMG["logo"]}" alt="{e(MARCA["libreria"])}">' if IMG["logo"] else ""
    md(f'<div class="lia-top">{logo}<span class="nombre">{e(MARCA["libreria"])}</span></div>')

# ---------- Cabecera ----------
cabecera = f'<img class="ilustracion" src="{IMG["cabecera"]}" alt="">' if IMG["cabecera"] else ""
avatar = f'<img class="avatar" src="{IMG["lia"]}" alt="{e(LIA)}">' if IMG["lia"] and not IMG["cabecera"] else ""
md(f"""
<div class="lia-hero">
  {cabecera}{avatar}
  <h1>{e(TX['titulo'])}</h1>
  <p>{e(TX['subtitulo'])}</p>
</div>""")

# ---------- Goodreads (opcional) ----------
with st.expander(T("goodreads_titulo")):
    st.caption(T("goodreads_ayuda"))
    archivo_gr = st.file_uploader("Goodreads CSV", type="csv", label_visibility="collapsed")
    if archivo_gr is None:
        st.session_state.pop("perfil", None)
    elif st.session_state.get("perfil_id") != archivo_gr.file_id:
        try:
            st.session_state["perfil"] = goodreads.crear_perfil(archivo_gr, catalogo, embeddings)
            st.session_state["perfil_id"] = archivo_gr.file_id
        except ValueError as error:
            st.error(str(error))
            st.session_state.pop("perfil", None)

    perfil = st.session_state.get("perfil")
    if perfil:
        if perfil["vector"] is None:
            st.warning(T("goodreads_nada"))
            perfil = None
        else:
            st.success(T("goodreads_ok", n=perfil["en_catalogo"], total=perfil["total"], g=len(perfil["gustados"])))
            if st.button(T("segun_lo_leido")):
                st.session_state.pendiente = ("", T("segun_lo_leido"))

# ---------- Entrada escrita ----------
escrito = st.chat_input(TX["placeholder"])
if escrito and escrito.strip():
    st.session_state.pendiente = (escrito.strip(), escrito.strip())

# ---------- Procesar lo pendiente (texto, sugerencia, pictograma o voz) ----------
if "pendiente" in st.session_state:
    consulta, mostrado = st.session_state.pop("pendiente")
    with st.spinner(T("buscando")):
        responder(consulta, mostrado, perfil)

# ---------- Saludo ----------
md(html_mensaje_lia(e(TX["saludo"])))
boton_escuchar(TX["saludo"], COLORES)

# ---------- Sugerencias escritas ----------
if not st.session_state.conversacion and TX.get("sugerencias"):
    columnas = st.columns(len(TX["sugerencias"]))
    for i, (columna, sugerencia) in enumerate(zip(columnas, TX["sugerencias"])):
        if columna.button(sugerencia, key=f"sug_{i}", width="stretch"):
            st.session_state.pendiente = (sugerencia, sugerencia)
            st.rerun()


# ---------- Pictogramas ----------
def cuadricula_pictogramas():
    por_fila = 4
    lista = MARCA["pictogramas"]
    for inicio in range(0, len(lista), por_fila):
        columnas = st.columns(por_fila)
        for columna, p in zip(columnas, lista[inicio:inicio + por_fila]):
            etiqueta = p.get(IDIOMA) or p.get(MARCA["idioma_por_defecto"]) or p["id"]
            with columna:
                if PICTOS.get(p["id"]):
                    md(f'<div class="picto"><img src="{PICTOS[p["id"]]}" alt=""></div>')
                else:
                    md(f'<div class="picto" aria-hidden="true">{e(p.get("emoji", "📘"))}</div>')
                if st.button(etiqueta, key=f"picto_{p['id']}", width="stretch"):
                    st.session_state.pendiente = (p["busqueda"], f"{p.get('emoji', '')} {etiqueta}".strip())
                    st.rerun()


if MARCA["pictogramas"] and st.session_state.mostrar_pictogramas:
    if not st.session_state.conversacion:
        md(f'<div class="titulo-seccion">{e(T("elige_dibujo"))}</div>')
        cuadricula_pictogramas()
    else:
        with st.expander(T("elige_dibujo")):
            cuadricula_pictogramas()

# ---------- Conversación ----------
for mensaje in st.session_state.conversacion:
    if mensaje["rol"] == "usuario":
        md(html_mensaje_usuario(mensaje["texto"]))
        continue
    intro = T(mensaje["intro"])
    texto_html = e(intro)
    entendido = resumen(mensaje["pref"], IDIOMA)
    if entendido:
        texto_html += f'<br><span class="entendido">{e(T("he_tenido_en_cuenta"))}: {e(entendido)}</span>'
    md(html_mensaje_lia(texto_html))
    boton_escuchar(texto_para_escuchar(intro, mensaje["libros"]), COLORES)
    md("".join(html_libro(libro) for libro in mensaje["libros"]))

# ---------- Hablar en vez de escribir ----------
if VOZ_DISPONIBLE:
    audio = st.audio_input(T("hablar"), help=T("hablar_ayuda"), key=f"audio_{st.session_state.clave_audio}")
    if audio is not None:
        datos = audio.getvalue()
        with st.spinner(T("transcribiendo")):
            try:
                texto_voz = voz.transcribir(datos, IDIOMA)
            except Exception as error:  # modelo sin descargar, audio vacío...
                print(f"[Voz] Error: {error}")
                texto_voz = ""
        st.session_state.clave_audio += 1  # vacía el micrófono para la próxima vez
        if texto_voz:
            st.session_state.pendiente = (texto_voz, f"🎤 {texto_voz}")
            st.rerun()
        else:
            st.warning(T("no_entendi_audio"))

if st.session_state.conversacion:
    if st.button(T("empezar_de_nuevo")):
        st.session_state.conversacion = []
        st.rerun()

md(f'<div class="aviso">{e(TX["aviso_librero"])}</div>')
