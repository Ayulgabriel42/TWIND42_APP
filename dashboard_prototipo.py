"""FASE 1 · Prototipo visual del nuevo Dashboard TWIND42 (ya integrado en app.py en FASE 2).

Se conserva como referencia aislada hasta confirmar que la integración funciona.
NO modifica app.py, procesar.py, generar_datos.py ni los CSV originales. Solo los LEE,
a través de la función procesar() ya existente, para construir la vista con datos
reales de los ejemplos simulados incluidos.

Ejecutar con: streamlit run dashboard_prototipo.py
"""
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
import streamlit as st

from dashboard import imagen_base64, render_dashboard
from escenarios import MODOS as MODOS_ESCENARIO, NIVELES as NIVELES_ESCENARIO, balance_escenario, construir_escenario
from procesar import procesar

ROOT = Path(__file__).resolve().parent
LOGO = ROOT / "assets/twind42_logo.png"

EID_PROTOTIPO = "SIM-HIB-01"  # ensayo híbrido: ambas fuentes activas, ilustra mejor el diagrama
SNAPSHOT_MIN = 30.0  # instante "actual" simulado para los KPI de potencia (no es tiempo real)


@st.cache_data
def procesar_ejemplos():
    """Corre el procesamiento real (sin tocar procesar.py) sobre los CSV de ejemplo incluidos."""
    with TemporaryDirectory(prefix="twind42_dash_") as tmp:
        salida = Path(tmp) / "salida"
        procesar(ROOT / "datos_simulados", salida)
        mediciones = pd.read_csv(salida / "mediciones_procesadas.csv", dtype={"id_ensayo": str})
        balance = pd.read_csv(salida / "balance.csv", dtype={"id_ensayo": str})
    ensayos = pd.read_csv(ROOT / "datos_simulados/ensayos.csv", dtype={"id_ensayo": str})
    mediciones["fecha_hora"] = pd.to_datetime(mediciones["fecha_hora"])
    return mediciones, balance, ensayos


st.set_page_config(page_title="TWIND42 · Dashboard (prototipo)", page_icon="🌬️", layout="wide")
st.caption("FASE 1 · Prototipo visual para revisión — ya integrado en app.py; esto se conserva solo como referencia.")

vista = st.sidebar.radio("Simular viewport (solo para esta revisión)", ["Escritorio (1440px)", "Móvil (390px)"])
ancho = 390 if vista.startswith("Móvil") else 1400

mediciones, balance, ensayos = procesar_ejemplos()
datos_eid = mediciones[mediciones["id_ensayo"] == EID_PROTOTIPO]
modo = ensayos.set_index("id_ensayo").loc[EID_PROTOTIPO, "modo_operacion"]

guardados = st.session_state.get("dashboard_escenario", {})
modo_sim = guardados.get("modo", "hibrido") if guardados.get("modo") in MODOS_ESCENARIO else "hibrido"
nivel_sim = guardados.get("nivel", 100) if guardados.get("nivel") in NIVELES_ESCENARIO else 100
datos_escenario = construir_escenario(datos_eid, modo_sim, nivel_sim)
balance_sim = balance_escenario(datos_escenario)

render_dashboard(imagen_base64(LOGO), EID_PROTOTIPO, modo, datos_escenario, balance_sim, ancho=ancho,
                  snapshot_min=SNAPSHOT_MIN, controles={"modo": modo_sim, "nivel": nivel_sim}, key="dashboard_escenario")
