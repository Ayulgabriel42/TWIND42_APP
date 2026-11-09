"""Interfaz local de la demo TWIND42: archivos simulados, sin conexión al ESP32."""
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard import imagen_base64, render_dashboard
from escenarios import MODOS as MODOS_ESCENARIO, NIVELES as NIVELES_ESCENARIO, balance_escenario, construir_escenario
from procesar import procesar

ROOT = Path(__file__).resolve().parent
LOGO = ROOT / "assets/twind42_logo.png"
EID_EJEMPLO_DASHBOARD = "SIM-HIB-01"  # usado en el Dashboard solo mientras no se cargó ningún ensayo

NOMBRES = {"eolico": "Eólico", "fotovoltaico": "Fotovoltaico", "bateria": "Batería", "carga": "Carga LED"}

# Paleta de marca TWIND42: fondo azul oscuro, tarjetas, texto y tres acentos (uno por tipo de flujo).
FONDO = "#080F21"
TARJETA = "#111E34"
CIAN = "#27D3F1"
VERDE = "#5CE3A0"
VIOLETA = "#A685FA"
AMBAR = "#F2B134"
TEXTO = "#F4F7FC"
TEXTO_SEC = "#A8B7CB"
COLORES = [CIAN, VERDE, VIOLETA, AMBAR]  # eólico, fotovoltaico, batería, carga (mismo orden que NOMBRES)


def calcular(ensayos_bytes, mediciones_bytes):
    """Cada ejecución usa una carpeta temporal propia y conserva los originales."""
    with TemporaryDirectory(prefix="twind42_") as tmp:
        base = Path(tmp)
        (base / "ensayos.csv").write_bytes(ensayos_bytes)
        (base / "mediciones.csv").write_bytes(mediciones_bytes)
        procesar(base, base / "salida")
        archivos = {p.name: p.read_bytes() for p in (base / "salida").glob("*.csv")}
    ensayos = pd.read_csv(BytesIO(ensayos_bytes), dtype={"id_ensayo": str}).fillna("")
    datos = pd.read_csv(BytesIO(archivos["mediciones_procesadas.csv"]), dtype={"id_ensayo": str})
    datos["fecha_hora"] = pd.to_datetime(datos["fecha_hora"])
    # Un balance requiere comparar puntos medidos en los mismos instantes.
    for eid, grupo in datos.groupby("id_ensayo"):
        tiempos = [tuple(g.sort_values("fecha_hora")["fecha_hora"]) for _, g in grupo.groupby("punto_medido")]
        if any(t != tiempos[0] for t in tiempos[1:]):
            raise ValueError(f"{eid}: los cuatro puntos deben compartir los mismos instantes.")
    datos["minutos"] = (datos["fecha_hora"] - datos.groupby("id_ensayo")["fecha_hora"].transform("min")).dt.total_seconds() / 60
    datos["Punto"] = datos["punto_medido"].map(NOMBRES)
    return {"ensayos": ensayos, "datos": datos, "archivos": archivos,
            "balance": pd.read_csv(BytesIO(archivos["balance.csv"]), dtype={"id_ensayo": str})}


def cargar(eb, mb, origen):
    # Si falla una carga, se quitan resultados anteriores para evitar confusiones.
    st.session_state.pop("resultado", None)
    st.session_state["reproduciendo"] = False
    try:
        resultado = calcular(eb, mb)
    except (ValueError, OSError, TypeError, KeyError, UnicodeError) as exc:
        st.error(f"Archivo rechazado. No se generaron resultados: {exc}")
        return
    st.session_state["resultado"] = resultado
    st.session_state["origen"] = origen
    st.session_state["cursor"] = 0
    st.session_state.pop("ensayo_reproduccion", None)
    st.session_state.pop("ensayo_seleccionado", None)
    st.success("Archivos validados y procesados.")


@st.cache_data
def ejemplo_para_dashboard():
    """Datos del ejemplo incluido, solo para la pantalla Dashboard antes de cargar un ensayo propio."""
    with TemporaryDirectory(prefix="twind42_dash_") as tmp:
        salida = Path(tmp) / "salida"
        procesar(ROOT / "datos_simulados", salida)
        mediciones = pd.read_csv(salida / "mediciones_procesadas.csv", dtype={"id_ensayo": str})
        balance = pd.read_csv(salida / "balance.csv", dtype={"id_ensayo": str})
    ensayos = pd.read_csv(ROOT / "datos_simulados/ensayos.csv", dtype={"id_ensayo": str})
    mediciones["fecha_hora"] = pd.to_datetime(mediciones["fecha_hora"])
    return mediciones, balance, ensayos


def ensayo_sincronizado(ids, default=None):
    """Índice del ensayo activo compartido entre pantallas, para que el selectbox de cada
    una arranque en el mismo ensayo que se eligió en otra."""
    actual = st.session_state.get("ensayo_seleccionado", default or ids[0])
    return ids.index(actual) if actual in ids else 0


def mostrar_dashboard():
    st.header("Dashboard")
    if "resultado" in st.session_state:
        r = st.session_state["resultado"]
        ids = r["ensayos"]["id_ensayo"].tolist()
        eid = st.selectbox("Ensayo", ids, index=ensayo_sincronizado(ids), key="dash_eid")
        st.session_state["ensayo_seleccionado"] = eid
        datos_eid = r["datos"][r["datos"]["id_ensayo"] == eid]
        modo = r["ensayos"].set_index("id_ensayo").loc[eid, "modo_operacion"]
        st.caption(f"Datos activos: {st.session_state.get('origen', '—')}")
    else:
        mediciones, _balance, ensayos = ejemplo_para_dashboard()
        eid = EID_EJEMPLO_DASHBOARD
        datos_eid = mediciones[mediciones["id_ensayo"] == eid]
        modo = ensayos.set_index("id_ensayo").loc[eid, "modo_operacion"]
        st.caption(f"Mostrando el ejemplo incluido {eid} (ilustrativo). Cargá tus propios datos desde Configuración para ver tu ensayo.")

    # Controles de escenario simulado (ver escenarios.py): la selección vive en
    # st.session_state bajo esta misma clave, actualizada por el componente V2.
    guardados = st.session_state.get("dashboard_escenario", {})
    modo_sim = guardados.get("modo", "hibrido")
    nivel_sim = guardados.get("nivel", 100)
    if modo_sim not in MODOS_ESCENARIO:
        modo_sim = "hibrido"
    if nivel_sim not in NIVELES_ESCENARIO:
        nivel_sim = 100

    datos_escenario = construir_escenario(datos_eid, modo_sim, nivel_sim)
    balance_sim = balance_escenario(datos_escenario)
    render_dashboard(imagen_base64(LOGO), eid, modo, datos_escenario, balance_sim,
                      controles={"modo": modo_sim, "nivel": nivel_sim}, key="dashboard_escenario")


def rgba(color_hex, alpha):
    h = color_hex.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def tarjeta_kpi(columna, titulo, valor, color):
    columna.markdown(
        f"""<div class="tw-kpi" style="border-top-color:{color}">
                <div class="tw-kpi-label">{titulo}</div>
                <div class="tw-kpi-value">{valor}</div>
            </div>""",
        unsafe_allow_html=True,
    )


def grafico(datos, campo, titulo, unidad):
    """Gráfico interactivo (Plotly) de un campo por punto medido. Mismos datos y series que antes."""
    fig = go.Figure()
    for nombre, color in zip(NOMBRES.values(), COLORES):
        serie = datos[datos["Punto"] == nombre].sort_values("minutos")
        if serie.empty:
            continue
        fig.add_trace(go.Scatter(
            x=serie["minutos"], y=serie[campo], mode="lines", name=nombre,
            line=dict(color=color, width=2.5),
            hovertemplate=f"Minutos: %{{x:.2f}}<br>{nombre}: %{{y:.3f}} {unidad}<extra></extra>",
        ))
    fig.update_layout(
        title=dict(text=titulo, font=dict(color=TEXTO, size=16)),
        height=320,
        paper_bgcolor=TARJETA, plot_bgcolor=TARJETA,
        font=dict(color=TEXTO_SEC),
        xaxis=dict(title="Tiempo (min)", color=TEXTO_SEC, gridcolor="rgba(168,183,203,0.15)", zeroline=False),
        yaxis=dict(title=unidad, color=TEXTO_SEC, gridcolor="rgba(168,183,203,0.15)", zeroline=False, rangemode="tozero"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXTO_SEC)),
        margin=dict(l=10, r=10, t=45, b=10),
        hovermode="x unified",
    )
    st.plotly_chart(fig, width="stretch", theme=None)


def flujo_energia(eolico_wh, fv_wh, carga_wh, bateria_wh, residuo_wh, titulo):
    """Diagrama de flujo (Sankey) construido solo con energías ya calculadas por procesar.py:
    eólico y fotovoltaico hacia 'Fuentes', y de ahí hacia carga y batería (o desde la batería
    hacia la carga si el ensayo está en descarga neta). No agrega sensores ni valores nuevos."""
    etiquetas, colores_nodo = [], []
    indice = {}

    def nodo(nombre, color):
        if nombre not in indice:
            indice[nombre] = len(etiquetas)
            etiquetas.append(nombre)
            colores_nodo.append(color)
        return indice[nombre]

    fuentes = nodo("Fuentes", TEXTO_SEC)
    enlaces = []
    if eolico_wh > 1e-6:
        enlaces.append((nodo("Eólico", CIAN), fuentes, eolico_wh, CIAN))
    if fv_wh > 1e-6:
        enlaces.append((nodo("Fotovoltaico", VERDE), fuentes, fv_wh, VERDE))

    carga = nodo("Carga LED", AMBAR)
    bateria = nodo("Batería", VIOLETA)
    if bateria_wh >= 0:
        if carga_wh > 1e-6:
            enlaces.append((fuentes, carga, carga_wh, AMBAR))
        if bateria_wh > 1e-6:
            enlaces.append((fuentes, bateria, bateria_wh, VIOLETA))
    else:
        aporte_bateria = -bateria_wh
        directo = max(carga_wh - aporte_bateria, 0.0)
        if aporte_bateria > 1e-6:
            enlaces.append((bateria, carga, aporte_bateria, VIOLETA))
        if directo > 1e-6:
            enlaces.append((fuentes, carga, directo, AMBAR))
    if residuo_wh > 1e-6:
        enlaces.append((fuentes, nodo("Residuo", TEXTO_SEC), residuo_wh, TEXTO_SEC))

    if not enlaces:
        return None

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(label=etiquetas, color=colores_nodo, pad=18, thickness=16,
                  line=dict(color=FONDO, width=0.5)),
        link=dict(source=[s for s, _, _, _ in enlaces], target=[t for _, t, _, _ in enlaces],
                  value=[v for _, _, v, _ in enlaces], color=[rgba(c, 0.35) for *_, c in enlaces]),
    ))
    fig.update_layout(
        title=dict(text=titulo, font=dict(color=TEXTO, size=15)),
        paper_bgcolor=FONDO, plot_bgcolor=FONDO,
        font=dict(color=TEXTO, size=13),
        margin=dict(l=10, r=10, t=45, b=10), height=260,
    )
    return fig


st.set_page_config(page_title="TWIND42 · Demo", page_icon="🌬️", layout="wide")
# Los colores de fondo y de texto de los componentes nativos de Streamlit se atan a las variables
# de tema (--text-color, --background-color, --secondary-background-color, --primary-color), fijadas
# en .streamlit/config.toml con la paleta TWIND42. Así ningún texto queda con un color fijo sobre un
# fondo fijo que pueda combinar mal, y toda la interfaz respeta la misma identidad de marca.
st.markdown(f"""<style>
    :root {{ --twind-text-secondary:{TEXTO_SEC}; }}
    .block-container {{max-width:1200px;padding-top:1.5rem;}}
    h2,h3 {{color:var(--text-color);letter-spacing:0.01em;border-left:4px solid var(--primary-color);padding-left:0.6rem;}}
    .tw-tagline {{color:var(--twind-text-secondary);font-size:1.05rem;margin-top:-0.3rem;}}

    [data-testid="stMetric"] {{
        background:var(--secondary-background-color);
        border:1px solid rgba(39,211,241,0.25);
        border-top:3px solid var(--primary-color);
        padding:16px;border-radius:12px;
    }}
    [data-testid="stMetric"] label,
    [data-testid="stMetricValue"],
    [data-testid="stMetricDelta"] {{color:var(--text-color) !important;}}

    .tw-kpi {{
        background:var(--secondary-background-color);
        border:1px solid rgba(39,211,241,0.18);
        border-top:3px solid var(--primary-color);
        border-radius:12px;padding:14px 16px;margin-bottom:0.6rem;
    }}
    .tw-kpi-label {{color:var(--twind-text-secondary);font-size:0.8rem;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:6px;}}
    .tw-kpi-value {{color:var(--text-color);font-size:1.6rem;font-weight:700;}}

    [data-testid="stSidebar"] {{border-right:1px solid rgba(39,211,241,0.2);}}
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {{color:var(--primary-color);border:none;padding:0;}}

    [data-testid="stImage"] img {{border-radius:14px;}}
    </style>""", unsafe_allow_html=True)

st.sidebar.image(str(LOGO), width=170)
st.sidebar.subheader("Panel de ensayos")
pantalla = st.sidebar.radio("Navegación", ["Dashboard", "Configuración", "Visualización", "Resultados"])
st.sidebar.caption("Ejecución local · CSV → Python → resultados")
st.sidebar.caption("La adquisición física y la validación del prototipo permanecen pendientes.")
if pantalla != "Visualización":
    st.session_state["reproduciendo"] = False

st.warning("DATOS SIMULADOS · No hay conexión al ESP32 ni ensayos físicos. Los resultados verifican el procesamiento de archivos de prueba.")

if pantalla == "Dashboard":
    mostrar_dashboard()
    st.stop()

if pantalla == "Configuración":
    st.header("1. Configuración del ensayo")
    st.markdown('<p class="tw-tagline">Prototipo híbrido eólico-fotovoltaico · Demostración del software</p>', unsafe_allow_html=True)
    st.caption("Tres pasos: elegí el origen de los datos y procesalos, revisá qué ensayo quedó cargado, "
               "y ajustá los parámetros de esa sesión.")

    with st.container(border=True):
        st.subheader("Paso 1 · Origen de los datos y procesamiento")
        st.caption("Acá se ejecuta el programa Python que procesa los CSV (cálculo de potencia, energía y balance).")
        origen = st.radio("Datos de entrada", ["Ejemplos incluidos", "Cargar CSV de prueba"], horizontal=True)
        if origen == "Ejemplos incluidos":
            st.write("Tres escenarios en un mismo archivo: eólico, fotovoltaico e híbrido. Cada uno contiene 60 minutos de muestras simuladas cada 5 segundos.")
            if st.button("Cargar y procesar ejemplos", type="primary"):
                cargar((ROOT / "datos_simulados/ensayos.csv").read_bytes(), (ROOT / "datos_simulados/mediciones.csv").read_bytes(), "Ejemplos incluidos")
            if st.button("Probar rechazo de archivo inválido"):
                cargar((ROOT / "datos_simulados/ensayos.csv").read_bytes(), (ROOT / "datos_simulados/mediciones_con_error.csv").read_bytes(), "Prueba de error")
            st.caption("El segundo botón es una demostración de validación: carga un archivo con un dato inválido a propósito para mostrar que el sistema lo rechaza sin romperse.")
        else:
            st.info("Seleccioná ambos CSV con la estructura del TFG. Esta versión está destinada a datos de prueba simulados.")
            eb = st.file_uploader("Configuración: ensayos.csv", type="csv")
            mb = st.file_uploader("Mediciones: mediciones.csv", type="csv")
            confirmado = st.checkbox("Confirmo que estos archivos contienen datos simulados")
            if st.button("Validar y procesar CSV", type="primary", disabled=not (eb and mb and confirmado)):
                cargar(eb.getvalue(), mb.getvalue(), "CSV de prueba cargados")

    if "resultado" in st.session_state:
        r = st.session_state["resultado"]
        with st.container(border=True):
            st.subheader("Paso 2 · Ensayo cargado")
            st.caption(f"Datos activos: {st.session_state['origen']}. Un mismo procesamiento puede incluir varios ensayos: elegí cuál revisar.")
            ids_config = r["ensayos"]["id_ensayo"].tolist()
            eid = st.selectbox("Ensayo a revisar", ids_config, index=ensayo_sincronizado(ids_config))
            st.session_state["ensayo_seleccionado"] = eid
            fila = r["ensayos"].set_index("id_ensayo").loc[eid]
            a, b, c = st.columns(3)
            a.metric("Modo", NOMBRES.get(fila["modo_operacion"], "Híbrido"))
            b.metric("Carga nominal", f"{float(fila['carga_w']):g} W")
            c.metric("Fecha del archivo", str(fila["fecha"]))

        with st.container(border=True):
            st.subheader("Paso 3 · Parámetros de esta sesión")
            st.caption("Estos valores se guardan solo en esta sesión del navegador; no modifican las mediciones ni los cálculos.")
            with st.form(f"config_{eid}"):
                porcentaje = st.number_input("Estado inicial de batería (%)", 0.0, 100.0, float(fila["estado_inicial_bateria"]), step=1.0)
                observaciones = st.text_area("Observaciones", str(fila["observaciones"]))
                if st.form_submit_button("Guardar configuración de la sesión"):
                    indice = r["ensayos"]["id_ensayo"] == eid
                    r["ensayos"].loc[indice, "estado_inicial_bateria"] = porcentaje
                    r["ensayos"].loc[indice, "observaciones"] = observaciones
                    st.success("Configuración guardada para esta sesión. Podés descargarla abajo.")
            st.caption("El porcentaje inicial es un dato declarado: no modifica las mediciones ni calcula un porcentaje final. Modo, carga e identificador provienen del CSV para conservar su correspondencia.")
            st.download_button("Descargar ensayos.csv", r["ensayos"].to_csv(index=False).encode("utf-8"), "ensayos.csv", "text/csv")

        st.info("Con el procesamiento listo, continuá en Visualización o Resultados desde el menú lateral. Al cerrar o recargar la sesión, cargá los archivos nuevamente.")
    st.stop()

if "resultado" not in st.session_state:
    st.info("Primero cargá y procesá los ejemplos o tus CSV desde Configuración.")
    st.stop()

r = st.session_state["resultado"]
ids = r["ensayos"]["id_ensayo"].tolist()

if pantalla == "Visualización":
    st.header("2. Visualización de variables")
    st.caption("Reproducción de un CSV previamente procesado; no representa adquisición en tiempo real.")
    eid = st.selectbox("Ensayo", ids, index=ensayo_sincronizado(ids))
    st.session_state["ensayo_seleccionado"] = eid
    datos = r["datos"][r["datos"]["id_ensayo"] == eid]
    instantes = sorted(datos["fecha_hora"].unique())
    if st.session_state.get("ensayo_reproduccion") != eid:
        st.session_state.update(ensayo_reproduccion=eid, cursor=0, reproduciendo=False)
    c1, c2, c3 = st.columns(3)
    if c1.button("Reproducir", type="primary"):
        if st.session_state["cursor"] >= len(instantes) - 1:
            st.session_state["cursor"] = 0
        st.session_state.update(reproduciendo=True, reloj=time.monotonic(), base_cursor=st.session_state["cursor"])
    if c2.button("Pausar"):
        st.session_state["reproduciendo"] = False
    if c3.button("Reiniciar"):
        st.session_state.update(cursor=0, reproduciendo=False)
    if not st.session_state.get("reproduciendo", False):
        st.session_state["cursor"] = st.slider("Recorrer muestras", 0, len(instantes)-1, st.session_state["cursor"])
    st.caption("Reproducción acelerada: 1 segundo de pantalla equivale a 1 minuto del ensayo. Cada muestra original representa 5 segundos.")

    @st.fragment(run_every=1 if st.session_state.get("reproduciendo") else None)
    def mostrar_muestra():
        if st.session_state.get("reproduciendo"):
            avance = int((time.monotonic() - st.session_state["reloj"]) * 12)
            st.session_state["cursor"] = min(len(instantes)-1, st.session_state["base_cursor"] + avance)
        cursor = st.session_state["cursor"]
        instante = instantes[cursor]
        muestra = datos[datos["fecha_hora"] == instante]
        bateria = muestra[muestra["punto_medido"] == "bateria"].iloc[0]
        amperios = float(bateria["corriente_a"])
        estado = "Cargando" if amperios > 0 else ("Descargando" if amperios < 0 else "Sin intercambio")
        inicial = r["ensayos"].set_index("id_ensayo").loc[eid, "estado_inicial_bateria"]
        a, b, c = st.columns(3)
        a.metric("Tiempo reproducido", f"{float(muestra['minutos'].iloc[0]):.2f} min")
        b.metric("Batería inicial (declarada)", f"{float(inicial):g} %")
        c.metric("Batería en esta muestra", estado)

        potencias = muestra.set_index("Punto")["potencia_w"]
        cols_kpi = st.columns(4)
        for columna, nombre, color in zip(cols_kpi, NOMBRES.values(), COLORES):
            tarjeta_kpi(columna, f"Potencia · {nombre}", f"{float(potencias.get(nombre, 0.0)):.2f} W", color)

        energias = muestra.set_index("punto_medido")["energia_wh"].astype(float)
        eolico_wh, fv_wh = float(energias.get("eolico", 0.0)), float(energias.get("fotovoltaico", 0.0))
        carga_wh, bateria_wh = float(energias.get("carga", 0.0)), float(energias.get("bateria", 0.0))
        residuo_wh = eolico_wh + fv_wh - carga_wh - bateria_wh
        fig_flujo = flujo_energia(eolico_wh, fv_wh, carga_wh, bateria_wh, residuo_wh, "Flujo energético acumulado hasta este instante")
        if fig_flujo is None:
            st.caption("El flujo energético se mostrará a medida que avance la reproducción.")
        else:
            st.plotly_chart(fig_flujo, width="stretch", theme=None)

        st.dataframe(muestra[["Punto", "rpm", "tension_v", "corriente_a", "potencia_w", "energia_wh"]].rename(columns={"rpm":"Giro (rpm)", "tension_v":"Tensión (V)", "corriente_a":"Corriente (A)", "potencia_w":"Potencia (W)", "energia_wh":"Energía neta (Wh)"}), hide_index=True, width="stretch")
        grafico(datos[datos["fecha_hora"] <= instante], "potencia_w", "Potencia durante la reproducción", "Potencia (W)")
        st.caption("Batería: corriente positiva = carga; negativa = descarga. No se estima el porcentaje actual de batería.")
        if cursor == len(instantes)-1 and st.session_state.get("reproduciendo"):
            st.session_state["reproduciendo"] = False
            st.rerun()
    mostrar_muestra()

else:
    st.header("3. Consulta y comparación de resultados")
    eid = st.selectbox("Ensayo a consultar", ids, index=ensayo_sincronizado(ids))
    st.session_state["ensayo_seleccionado"] = eid
    datos = r["datos"][r["datos"]["id_ensayo"] == eid]
    balance = r["balance"].set_index("id_ensayo").loc[eid]
    columnas = st.columns(4)
    for columna, campo, nombre, color in zip(columnas, ["fuentes_wh", "carga_wh", "bateria_wh", "residuo_wh"], ["Fuentes", "Carga LED", "Batería (neta)", "Residuo"], [CIAN, AMBAR, VIOLETA, TEXTO_SEC]):
        tarjeta_kpi(columna, nombre, f"{balance[campo]:.2f} Wh", color)
    st.caption("Fuentes = carga + batería + residuo. Los ejemplos incluidos suponen un balance ideal sin pérdidas; el residuo no equivale automáticamente a pérdidas físicas.")

    ultimas = datos.sort_values("fecha_hora").groupby("punto_medido").tail(1).set_index("punto_medido")["energia_wh"].astype(float)
    eolico_wh, fv_wh = float(ultimas.get("eolico", 0.0)), float(ultimas.get("fotovoltaico", 0.0))
    fig_flujo = flujo_energia(eolico_wh, fv_wh, float(balance["carga_wh"]), float(balance["bateria_wh"]), float(balance["residuo_wh"]), "Flujo energético del ensayo")
    if fig_flujo is not None:
        st.plotly_chart(fig_flujo, width="stretch", theme=None)

    grafico(datos, "potencia_w", "Potencia instantánea por punto", "Potencia (W)")
    grafico(datos, "energia_wh", "Energía acumulada neta por punto", "Energía (Wh)")
    st.subheader("Comparar escenarios simulados")
    seleccion = st.multiselect("Ensayos a comparar", ids, default=ids)
    comparacion = r["balance"][r["balance"]["id_ensayo"].isin(seleccion)]
    if seleccion:
        st.dataframe(comparacion.rename(columns={"id_ensayo":"Ensayo", "modo_operacion":"Modo", "fuentes_wh":"Fuentes (Wh)", "carga_wh":"Carga (Wh)", "bateria_wh":"Batería (Wh)", "residuo_wh":"Residuo (Wh)"}), hide_index=True, width="stretch")
    else:
        st.info("Seleccioná al menos un ensayo.")
    st.caption("Esta comparación comprueba el software. No determina qué tecnología genera más energía en condiciones reales.")
    st.subheader("Descargar resultados")
    for nombre, contenido in r["archivos"].items():
        st.download_button(nombre, contenido, nombre, "text/csv", key=nombre)
