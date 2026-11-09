"""Prueba funcional de la interfaz sin abrir un navegador."""
from pathlib import Path
from streamlit.testing.v1 import AppTest

app = AppTest.from_file(str(Path(__file__).with_name("app.py")), default_timeout=30).run()
assert not app.exception, app.exception
# La pantalla de inicio ahora es el Dashboard; sin datos cargados debe mostrar el ejemplo ilustrativo sin fallar.
assert app.session_state.get("resultado") is None

app.sidebar.radio[0].set_value("Configuración").run()
assert not app.exception, app.exception
app.button[0].click().run()
assert not app.exception, app.exception
assert len(app.session_state["resultado"]["datos"]) == 8652
app.number_input[0].set_value(65.0)
app.button[2].click().run()
assert not app.exception, app.exception
assert app.session_state["resultado"]["ensayos"].iloc[0]["estado_inicial_bateria"] == 65

app.sidebar.radio[0].set_value("Dashboard").run()
assert not app.exception, app.exception
assert app.session_state["ensayo_seleccionado"] == app.session_state["resultado"]["ensayos"]["id_ensayo"].tolist()[0]

app.sidebar.radio[0].set_value("Visualización").run()
assert not app.exception, app.exception
app.slider[0].set_value(360).run()
assert app.session_state["cursor"] == 360
app.button[0].click().run()
assert app.session_state["reproduciendo"]
app.button[1].click().run()
assert not app.session_state["reproduciendo"]
app.button[2].click().run()
assert app.session_state["cursor"] == 0
app.sidebar.radio[0].set_value("Resultados").run()
assert not app.exception, app.exception
balances = app.session_state["resultado"]["balance"]
assert list(balances["fuentes_wh"]) == [28.8, 27.6, 30.6]
assert list(balances["bateria_wh"]) == [8.76, 7.56, 10.56]
assert (balances["residuo_wh"].abs() < 0.0001).all()
app.selectbox[0].select("SIM-HIB-01").run()
assert app.session_state["ensayo_seleccionado"] == "SIM-HIB-01"
app.multiselect[0].set_value([]).run()
assert not app.exception, app.exception

# El ensayo elegido en Resultados debe quedar sincronizado al volver al Dashboard.
app.sidebar.radio[0].set_value("Dashboard").run()
assert not app.exception, app.exception
assert app.session_state["ensayo_seleccionado"] == "SIM-HIB-01"

app.sidebar.radio[0].set_value("Configuración").run()
assert not app.exception, app.exception
app.button[1].click().run()
assert app.error and "tension_v" in app.error[0].value
assert "resultado" not in app.session_state
app.button[0].click().run()
assert "resultado" in app.session_state
assert not app.exception, app.exception
print("PRUEBA SUPERADA: dashboard, configuración, reproducción, resultados, balances, sincronización de ensayo y rechazo de CSV.")
