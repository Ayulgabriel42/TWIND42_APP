"""Interfaz local de la demo TWIND42: archivos simulados, sin conexión al ESP32."""
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import time

import altair as alt
import pandas as pd
import streamlit as st

from procesar import procesar

ROOT = Path(__file__).resolve().parent
NOMBRES = {"eolico": "Eólico", "fotovoltaico": "Fotovoltaico", "bateria": "Batería", "carga": "Carga LED"}
COLORES = ["#2FD9C6", "#F2B134", "#B38BFF", "#4ADE80"]


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
    st.success("Archivos validados y procesados.")


def grafico(datos, campo, titulo, unidad):
    chart = alt.Chart(datos).mark_line(strokeWidth=2.5).encode(
        x=alt.X("minutos:Q", title="Tiempo (min)", scale=alt.Scale(zero=True)),
        y=alt.Y(f"{campo}:Q", title=unidad, scale=alt.Scale(zero=True)),
        color=alt.Color("Punto:N", scale=alt.Scale(domain=list(NOMBRES.values()), range=COLORES), title=None),
        tooltip=[alt.Tooltip("minutos:Q", title="Minutos", format=".2f"), "Punto:N", alt.Tooltip(f"{campo}:Q", title=unidad, format=".3f")],
    ).properties(height=280, title=titulo)
    st.altair_chart(chart, width="stretch")


st.set_page_config(page_title="TWIND42 · Demo", page_icon="🌿", layout="wide")
# Los colores de fondo y de texto se emparejan siempre con las variables de tema de Streamlit
# (--text-color, --background-color, --secondary-background-color, --primary-color), que Streamlit
# recalcula de forma coherente según el tema claro/oscuro activo. Así ningún texto queda con un
# color fijo sobre un fondo fijo que pueda combinar mal si cambia el tema.
st.markdown("""<style>
    .block-container {max-width:1200px;padding-top:2rem;}
    h1,h2,h3 {color:var(--text-color);letter-spacing:0.01em;}
    h1 {font-weight:800;border-bottom:3px solid var(--primary-color);padding-bottom:0.3rem;display:inline-block;}
    h2,h3 {border-left:4px solid var(--primary-color);padding-left:0.6rem;}

    [data-testid="stMetric"] {
        background:var(--secondary-background-color);
        border:1px solid rgba(47,217,198,0.35);
        border-top:3px solid var(--primary-color);
        padding:16px;border-radius:12px;
    }
    [data-testid="stMetric"] label,
    [data-testid="stMetricValue"],
    [data-testid="stMetricDelta"] {color:var(--text-color) !important;}

    [data-testid="stSidebar"] {border-right:1px solid rgba(47,217,198,0.25);}
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {color:var(--primary-color);border:none;padding:0;}
    </style>""", unsafe_allow_html=True)
st.title("TWIND42")
st.caption("Prototipo híbrido eólico-fotovoltaico · Demostración del software")
st.warning("DATOS SIMULADOS · No hay conexión al ESP32 ni ensayos físicos. Los resultados verifican el procesamiento de archivos de prueba.")

st.sidebar.title("Panel de ensayos")
pantalla = st.sidebar.radio("Navegación", ["Configuración", "Visualización", "Resultados"])
st.sidebar.caption("Ejecución local · CSV → Python → resultados")
st.sidebar.caption("La adquisición física y la validación del prototipo permanecen pendientes.")
if pantalla != "Visualización":
    st.session_state["reproduciendo"] = False

if pantalla == "Configuración":
    st.header("1. Configuración del ensayo")
    origen = st.radio("Datos de entrada", ["Ejemplos incluidos", "Cargar CSV de prueba"], horizontal=True)
    if origen == "Ejemplos incluidos":
        st.write("Tres escenarios: eólico, fotovoltaico e híbrido. Cada uno contiene 60 minutos de muestras simuladas cada 5 segundos.")
        if st.button("Cargar y procesar ejemplos", type="primary"):
            cargar((ROOT / "datos_simulados/ensayos.csv").read_bytes(), (ROOT / "datos_simulados/mediciones.csv").read_bytes(), "Ejemplos incluidos")
        if st.button("Probar rechazo de archivo inválido"):
            cargar((ROOT / "datos_simulados/ensayos.csv").read_bytes(), (ROOT / "datos_simulados/mediciones_con_error.csv").read_bytes(), "Prueba de error")
    else:
        st.info("Seleccioná ambos CSV con la estructura del TFG. Esta versión está destinada a datos de prueba simulados.")
        eb = st.file_uploader("Configuración: ensayos.csv", type="csv")
        mb = st.file_uploader("Mediciones: mediciones.csv", type="csv")
        confirmado = st.checkbox("Confirmo que estos archivos contienen datos simulados")
        if st.button("Validar y procesar CSV", type="primary", disabled=not (eb and mb and confirmado)):
            cargar(eb.getvalue(), mb.getvalue(), "CSV de prueba cargados")

    if "resultado" in st.session_state:
        r = st.session_state["resultado"]
        st.caption(f"Datos activos: {st.session_state['origen']}")
        eid = st.selectbox("Ensayo a configurar", r["ensayos"]["id_ensayo"].tolist())
        fila = r["ensayos"].set_index("id_ensayo").loc[eid]
        a, b, c = st.columns(3)
        a.metric("Modo", NOMBRES.get(fila["modo_operacion"], "Híbrido"))
        b.metric("Carga nominal", f"{float(fila['carga_w']):g} W")
        c.metric("Fecha del archivo", str(fila["fecha"]))
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
        st.info("Continuá en Visualización o Resultados desde el menú lateral. Al cerrar o recargar la sesión, cargá los archivos nuevamente.")
    st.stop()

if "resultado" not in st.session_state:
    st.info("Primero cargá y procesá los ejemplos o tus CSV desde Configuración.")
    st.stop()

r = st.session_state["resultado"]
ids = r["ensayos"]["id_ensayo"].tolist()

if pantalla == "Visualización":
    st.header("2. Visualización de variables")
    st.caption("Reproducción de un CSV previamente procesado; no representa adquisición en tiempo real.")
    eid = st.selectbox("Ensayo", ids)
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
        st.progress(cursor / (len(instantes)-1))
        st.dataframe(muestra[["Punto", "rpm", "tension_v", "corriente_a", "potencia_w", "energia_wh"]].rename(columns={"rpm":"Giro (rpm)", "tension_v":"Tensión (V)", "corriente_a":"Corriente (A)", "potencia_w":"Potencia (W)", "energia_wh":"Energía neta (Wh)"}), hide_index=True, width="stretch")
        grafico(datos[datos["fecha_hora"] <= instante], "potencia_w", "Potencia durante la reproducción", "Potencia (W)")
        st.caption("Batería: corriente positiva = carga; negativa = descarga. No se estima el porcentaje actual de batería.")
        if cursor == len(instantes)-1 and st.session_state.get("reproduciendo"):
            st.session_state["reproduciendo"] = False
            st.rerun()
    mostrar_muestra()

else:
    st.header("3. Consulta y comparación de resultados")
    eid = st.selectbox("Ensayo a consultar", ids)
    datos = r["datos"][r["datos"]["id_ensayo"] == eid]
    balance = r["balance"].set_index("id_ensayo").loc[eid]
    columnas = st.columns(4)
    for columna, campo, nombre in zip(columnas, ["fuentes_wh", "carga_wh", "bateria_wh", "residuo_wh"], ["Fuentes", "Carga LED", "Batería (neta)", "Residuo"]):
        columna.metric(nombre, f"{balance[campo]:.2f} Wh")
    st.caption("Fuentes = carga + batería + residuo. Los ejemplos incluidos suponen un balance ideal sin pérdidas; el residuo no equivale automáticamente a pérdidas físicas.")
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
