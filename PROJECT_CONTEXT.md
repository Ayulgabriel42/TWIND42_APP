# TWIND42 — Contexto del proyecto

> Documento de referencia para retomar el desarrollo desde esta carpeta. No contiene credenciales ni información privada.

## 1. Descripción y objetivos

TWIND42 es un prototipo tecnológico académico para el Trabajo Final de Graduación de la
Licenciatura en Inteligencia Artificial y Robótica (Universidad Siglo 21). El título
académico del proyecto es:

> "Desarrollo de un sistema inteligente para generación, monitoreo y análisis energético urbano".

El proyecto simula el funcionamiento energético de un sistema híbrido eólico-solar con
almacenamiento en batería y una carga LED, usando **datos simulados** (no hay conexión a
hardware real ni a un ESP32). La aplicación es una interfaz Streamlit que permite cargar,
procesar y explorar esos datos, y un simulador de escenarios derivados para comparar
distintos niveles de generación.

**Importante para cualquier persona que retome este proyecto:** en ningún lugar de la
app se debe representar la generación simulada como una medición en tiempo real, ni
afirmar que existe telemetría/comunicación con un ESP32 u otro hardware.

## 2. Arquitectura y archivos principales

Aplicación Python + Streamlit, de un solo proceso, sin backend ni base de datos
adicionales. Todo el cálculo energético corre localmente al procesar los CSV.

| Archivo | Rol |
|---|---|
| `app.py` | Punto de entrada (`streamlit run app.py`). Define la navegación de las 4 pantallas, el tema visual, y la lógica de Configuración/Visualización/Resultados. |
| `dashboard.py` | Módulo compartido del componente **Streamlit Custom Components V2** (`st.components.v2.component`) que renderiza el Dashboard: HTML/CSS/JS inline, sin build de frontend. Expone `render_dashboard()` y `payload_desde_datos()`. |
| `escenarios.py` | Lógica de los **escenarios de generación derivados** (ver sección 5). No contiene ninguna fórmula propia de `procesar.py`; solo reescala series ya calculadas. |
| `procesar.py` | **No modificar.** Motor de cálculo energético validado: lee `ensayos.csv`/`mediciones.csv`, calcula potencia, integra energía (regla trapezoidal) y arma el balance (`fuentes = carga + batería + residuo`). |
| `generar_datos.py` | **No modificar.** Genera los CSV de ejemplo en `datos_simulados/`. |
| `dashboard_prototipo.py` | Script standalone de referencia (útil para ver el Dashboard aislado, con un selector de ancho de ventana para QA visual). No es parte de la app principal. |
| `app_backup.py`, `app_backup_pre_dashboard.py` | Copias de seguridad de `app.py` en distintos hitos del desarrollo (antes del rediseño visual y antes de integrar el Dashboard). Se conservan como historial. |
| `probar_interfaz.py` | Prueba funcional end-to-end con `streamlit.testing.v1.AppTest` (sin navegador). |
| `probar_error.py` | Prueba de que `procesar.py` rechaza correctamente un CSV con datos inválidos. |
| `.streamlit/config.toml` | Tema visual fijo (paleta de marca, ver sección 3) — evita depender del tema claro/oscuro del navegador del usuario. |
| `assets/` | `twind42_logo.png`, `twind42_turbina.png` — recursos gráficos oficiales, usados por `app.py` (hero/sidebar) y embebidos en base64 dentro del componente del Dashboard. |
| `datos_simulados/` | `ensayos.csv`, `mediciones.csv` (3 ensayos de ejemplo: eólico, fotovoltaico, híbrido) y `mediciones_con_error.csv` (para la demo de rechazo de archivo inválido). |

### Identidad visual

Paleta de marca fija: fondo `#080F21`, tarjetas `#111E34`, cian `#27D3F1`, verde
`#5CE3A0`, violeta `#A685FA`, ámbar `#F2B134`, alerta `#F2546B`, texto `#F4F7FC` /
`#A8B7CB`. Definida en `.streamlit/config.toml` (componentes nativos de Streamlit) y
replicada como variables CSS dentro del componente del Dashboard (`dashboard.py`).

## 3. Las cuatro pantallas

1. **Dashboard** (pantalla de inicio) — Panel de control visual: diagrama energético
   animado (turbina, panel solar, batería, carga LED), tarjetas KPI de potencia, mini
   gráficas de evolución de potencia/energía, balance resumido, y el **simulador de
   escenarios** (ver sección 5). Si todavía no se cargó ningún ensayo, muestra el
   ejemplo incluido `SIM-HIB-01`, claramente identificado como ilustrativo.
2. **Configuración** — En 3 pasos visuales: (1) elegir origen de datos (ejemplos
   incluidos o CSV propio) y ejecutar el procesamiento; (2) revisar qué ensayo quedó
   cargado; (3) ajustar parámetros declarados de la sesión (estado inicial de batería,
   observaciones) y descargar `ensayos.csv`.
3. **Visualización** — Reproducción (acelerada, no en tiempo real) de un ensayo ya
   procesado: controles de reproducir/pausar/reiniciar, tarjetas KPI de potencia
   instantánea por fuente, diagrama de flujo energético (Plotly Sankey) acumulado hasta
   el instante reproducido, tabla de mediciones y gráfico de potencia.
4. **Resultados** — Balance energético final del ensayo, diagrama de flujo completo,
   gráficos de potencia/energía (Plotly), comparación entre los ensayos cargados y
   descarga de `balance.csv` / `resumen.csv` / `mediciones_procesadas.csv`.

El ensayo seleccionado se sincroniza entre las 4 pantallas vía
`st.session_state["ensayo_seleccionado"]`.

## 4. Tecnología del Dashboard: Streamlit Custom Components V2

El Dashboard **no** usa widgets convencionales de Streamlit para sus controles: está
construido con `st.components.v2.component()` (HTML + CSS + JS inline, sin build de
frontend ni iframe). Se investigó y confirmó que esta API:
- Está oficialmente documentada en docs.streamlit.io.
- Está disponible en la versión fijada en `requirements.txt` (confirmado contra la API
  real de PyPI al momento de implementarla).

La comunicación es bidireccional: los botones de Modo/Nivel del simulador llaman
`setStateValue(...)` en JS, que actualiza `st.session_state["dashboard_escenario"]` en
Python y dispara un rerun con los datos recalculados.

## 5. Simulador de escenarios derivados (`escenarios.py`)

Permite, **solo en el Dashboard**, elegir:
- **Modo de generación**: Híbrido (eólico + fotovoltaico) / Eólico / Solar.
- **Nivel de generación eléctrica simulada**: 100% / 50% / 1%.

### Cómo funciona

`escenarios.construir_escenario(datos_ensayo, modo, nivel)` toma los datos **ya
calculados por `procesar.py`** para un ensayo de referencia y:
- Escala `potencia_w` de eólico y/o fotovoltaico por el nivel elegido (y la pone en
  cero si esa fuente está desactivada por el modo).
- Reintegra `energia_wh` con la **misma regla trapezoidal** de `procesar.py`.
- **No toca** `rpm`, `velocidad_viento`, `irradiancia`, `tensión_v` ni `corriente_a`
  (son condiciones físicas medidas, no se reinterpretan).
- **No toca carga ni batería**: quedan exactamente como fueron medidas en el ensayo de
  referencia.

`escenarios.balance_escenario(...)` recalcula `fuentes/carga/batería/residuo` con la
misma fórmula de `procesar.py`, sobre los datos ya escalados.

### Datos simulados originales vs. escenarios derivados — diferencia clave

| | Datos simulados originales | Escenario derivado |
|---|---|---|
| Origen | `datos_simulados/*.csv`, procesados por `procesar.py` | Transformación hipotética de un ensayo ya procesado |
| Qué representa | Una medición simulada completa (los 4 puntos tal como se generaron) | "¿Qué pasaría si la generación fuera el X% de este mismo ensayo, en este modo?" |
| Battería/Carga | Medidas, forman parte del balance real del ensayo | **Idénticas al ensayo de referencia**, nunca recalculadas |
| Etiqueta en la UI | Ensayo normal (Visualización/Resultados) | Badge permanente "ESCENARIO SIMULADO — Datos derivados de ensayos de referencia" + aclaraciones explícitas (ver abajo) |

### Limitación del modelo energético (importante conservar esta interpretación)

`bateria_wh`, en `procesar.py`, es una magnitud **medida** (integrada de tensión ×
corriente en el punto "batería" del CSV) — **no** es una variable que el balance
recalcule para "cerrar" la ecuación. La fórmula es:

```
residuo = fuentes - carga - batería
```

Por lo tanto, los escenarios derivados **nunca** hacen que la batería compense un
déficit de generación: eso sería un comportamiento que los datos no contienen. El
desbalance se expone únicamente a través de `residuo`, interpretado en la UI como:

- `residuo ≈ 0` → "Balance equilibrado".
- `residuo < 0` → "Déficit de balance" (no se representa como descarga real de batería).
- `residuo > 0` → "Excedente de balance" (no se representa como energía efectivamente almacenada).

Para evitar ambigüedad visual, cuando el escenario simulado **no** coincide con el
ensayo de referencia sin escalar (es decir, cuando `modo`/`nivel` elegidos difieren del
100% en el modo real del ensayo):
- La tarjeta de batería se relabela "Batería de referencia" con la aclaración "Valor
  del ensayo original · No recalculado".
- Si hay déficit, la tarjeta de carga LED se relabela "Demanda de referencia" (en vez
  de "Potencia carga LED"), para no sugerir que toda la demanda está siendo abastecida.
- Aparece la aclaración "Desbalance hipotético respecto de la carga y batería del
  ensayo de referencia".

El header del Dashboard distingue explícitamente **"Ensayo de referencia: <id>"**
(cambia solo al elegir otro ensayo) de **"Escenario seleccionado: <modo> · <nivel>%"**
(cambia con los controles del simulador, sin alterar el ensayo de referencia).

## 6. Dependencias

Ver `requirements.txt`:

```
streamlit==1.67.0
pandas==3.1.1
plotly==5.24.1
```

Python usado y probado: **3.12** (local: 3.12.14). `st.components.v2` requiere esta
versión de Streamlit o posterior; no requiere Node/npm ni build de frontend.

## 7. Instalación y ejecución

```powershell
cd C:\Proyectos\TWIND42_app
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

**Nota sobre `py -3.12`:** en esta máquina el lanzador `py` no tiene registrada la
3.12 (`py -0p` solo lista 3.13 y 3.14); el `.venv` incluido en esta carpeta se creó con
el intérprete 3.12.14 en
`C:\Users\ayulg\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`.
Si `py -3.12` falla en un entorno nuevo, instalar Python 3.12 desde python.org (o con
`winget install Python.Python.3.12`) y volver a crear el venv con ese intérprete; o, en
esta misma máquina, usar la ruta de arriba directamente en vez de `py -3.12`.

Para el procesador sin interfaz (opcional, genera `salida/` con los CSV de resultado):

```powershell
.\.venv\Scripts\python.exe generar_datos.py
.\.venv\Scripts\python.exe procesar.py
```

## 8. Estado de las pruebas

- `probar_interfaz.py` — prueba funcional completa (AppTest): navegación por las 4
  pantallas, carga de ejemplos, reproducción, balances esperados
  (`fuentes_wh = [28.8, 27.6, 30.6]` para SIM-EOL-01/FV-01/HIB-01), sincronización de
  ensayo entre pantallas, rechazo de CSV inválido. **Pasa.**
- `probar_error.py` — confirma que `procesar.py` rechaza `mediciones_con_error.csv`
  por `tension_v` inválido. **Pasa.**
- Verificación manual en navegador: las 4 pantallas, los 9 escenarios del simulador
  (3 modos × 3 niveles) con sus etiquetas, descargas CSV, diseño responsive
  (escritorio y móvil vía container queries), sin errores de consola.

## 9. Restricciones vigentes para quien continúe el desarrollo

- No modificar `procesar.py` ni `generar_datos.py`.
- No modificar los CSV originales de `datos_simulados/`.
- No cambiar las fórmulas de `escenarios.py`.
- No presentar los datos simulados como mediciones en tiempo real ni afirmar
  comunicación con un ESP32.
- Esta carpeta (`C:\Proyectos\TWIND42_app`) es ahora la ubicación de desarrollo activo.
  La carpeta original en `C:\Users\ayulg\.codex\.chatgpt-projects\...\demo_twind42`
  queda como respaldo histórico y no debería seguir editándose.
- Todavía no se publicó en GitHub ni en Streamlit Community Cloud.
