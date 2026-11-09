# TWIND42 — Contexto del proyecto

> Documento de referencia para retomar el desarrollo desde esta carpeta. No contiene credenciales ni información privada.
> Para una presentación general del proyecto ver [`README.md`](README.md); para el recorrido guiado de las 4 pantallas, [`LEEME.md`](LEEME.md); para instalar y ejecutar paso a paso, [`INSTRUCCIONES.txt`](INSTRUCCIONES.txt).

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
| `.streamlit/config.toml` | Tema visual fijo (paleta de marca, ver sección 3) — evita depender del tema claro/oscuro del navegador del usuario. También fija `theme.paddingTop` (espacio extra arriba del primer elemento, para no quedar tapado por la barra de Fork/GitHub que agrega Streamlit Community Cloud sobre la app), `theme.sidebar.paddingTop` (espaciado normal del sidebar, independiente del anterior) y `client.toolbarMode = "minimal"` (oculta el menú propio de Streamlit: Deploy, Rerun, etc.; no controla la barra de Fork/GitHub, que la agrega la plataforma). |
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
   procesado: controles de reproducir/pausar/reiniciar, un slider "Recorrer muestras"
   que indica explícitamente su rango (`0 a N-1`) y, debajo, una leyenda en vivo
   ("Muestra X de N · minuto Y de Z del ensayo") para que el índice crudo del slider
   no quede sin contexto; tarjetas KPI de potencia instantánea por fuente, diagrama de
   flujo energético (Plotly Sankey) acumulado hasta el instante reproducido, tabla de
   mediciones y gráfico de potencia.
4. **Resultados** — Tarjeta "Duración del ensayo" (calculada dinámicamente a partir de
   las marcas temporales del ensayo seleccionado, nunca un valor fijo; ver sección 5.1),
   dos aclaraciones de alcance (el balance corresponde al período completo del ensayo,
   independiente de dónde quedó el cursor en Visualización; y esta pantalla muestra el
   ensayo de referencia procesado, no los escenarios hipotéticos del Dashboard), balance
   energético final del ensayo, diagrama de flujo completo, gráficos de potencia/energía
   (Plotly), comparación entre los ensayos cargados ("Comparar escenarios simulados": en
   este contexto puntual "escenarios" se refiere a los distintos *ensayos de ejemplo*
   procesados —eólico/fotovoltaico/híbrido—, no al escenario hipotético Modo/Nivel del
   Dashboard; ver nota de terminología en la sección 5) y descarga de `balance.csv` /
   `resumen.csv` / `mediciones_procesadas.csv`.

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

### Etiquetas, tooltips y leyendas del diagrama energético

El diagrama identifica sus 5 nodos (generación eólica, generación fotovoltaica,
distribución energética, batería, carga LED) con una barra de chips justo arriba del
SVG, en el mismo orden y colores que las conexiones del diagrama. Cada chip es a la vez
la etiqueta visible y el disparador de un tooltip (al pasar el cursor o enfocar con
teclado) que explica la función del nodo y muestra sus valores reales — potencia
instantánea (W) y energía acumulada en el mismo instante (Wh), tomados directamente del
payload ya calculado, sin interpolar ni inventar nada. Cuando el escenario simulado
tiene déficit, los chips de Distribución/Batería/Carga pasan a un estilo con borde
punteado de alerta, y su tooltip aclara explícitamente que esos valores son de
referencia del ensayo original, no un suministro efectivo garantizado. Los íconos SVG
también tienen un `<title>` nativo con el mismo texto, por si se pasa el cursor
directamente sobre el dibujo en vez de sobre un chip.

Las dos minigráficas inferiores ("Evolución de potencia (W)" y "Energía acumulada
(Wh)") tienen su propia leyenda de colores por serie, referencias de tiempo (minuto
inicial/final) y de unidad en los ejes, y un tooltip por cursor/teclado: al pasar el
mouse (o enfocar el gráfico y usar las flechas izquierda/derecha) se traza una línea
guía y se muestra, debajo del gráfico, el minuto exacto junto con el valor real de cada
serie en ese punto — siempre la muestra real más cercana, nunca un valor interpolado.

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
| Etiqueta en la UI | Ensayo normal (Visualización/Resultados) | Badge permanente "ESCENARIO SIMULADO" (con el detalle completo "Datos derivados de ensayos de referencia" como tooltip nativo `title`, para no ocupar tanto espacio visual) + aclaraciones explícitas (ver abajo) |

**Nota de terminología:** "escenario simulado" (singular, en el Dashboard) se refiere
siempre al par Modo/Nivel hipotético de `escenarios.py`. En Resultados, el subtítulo
"Comparar escenarios simulados" usa la misma palabra en un sentido distinto y ya
existente en el código (comparar los 3 *ensayos* de ejemplo entre sí, no escenarios
derivados) — es una coincidencia de vocabulario entre dos funcionalidades separadas,
no una funcionalidad compartida. Documentado para quien continúe el desarrollo; no se
modificó el código para no alterar los textos de la interfaz fuera del alcance pedido.

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

### 5.1 Duración del ensayo (pantalla Resultados)

`app.py` calcula la duración real de cada ensayo a partir de sus propias marcas
temporales ya validadas en `calcular()` (mismos instantes en los 4 puntos; `procesar.py`
ya rechaza intervalos distintos de 5 s):

```python
minutos_totales = (marcas.max() - marcas.min()).total_seconds() / 60
```

**Nunca se asume un valor fijo de 60 minutos** (los 3 ensayos de ejemplo duran 60 min
cada uno, pero eso es una propiedad de esos datos, no una regla del código). Se muestra
siempre en minutos y, si el total es ≥ 60, con un desglose adicional en horas y
minutos. Si faltaran marcas temporales válidas, se informa con un aviso en vez de
calcular o "corregir" un tiempo en silencio. Validado también con ensayos sintéticos
de 30 y 90 minutos (generados solo en memoria, sin tocar `datos_simulados/`), ver
sección 8.

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

- `probar_interfaz.py` — prueba funcional completa (`streamlit.testing.v1.AppTest`, sin
  navegador real): navegación por las 4 pantallas, carga de ejemplos, reproducción,
  balances esperados (`fuentes_wh = [28.8, 27.6, 30.6]` para SIM-EOL-01/FV-01/HIB-01),
  sincronización de ensayo entre pantallas, rechazo de CSV inválido. **Pasa**
  (última corrida: 2026-11-09).
- `probar_error.py` — confirma que `procesar.py` rechaza `mediciones_con_error.csv`
  por `tension_v` inválido. **Pasa** (última corrida: 2026-11-09).
- **Límite importante de `probar_interfaz.py`:** `AppTest` ejecuta el script Python de
  `app.py` y verifica estado/excepciones, pero **no renderiza** el componente
  `st.components.v2.component` del Dashboard (HTML/CSS/JS inline) ni Plotly como lo
  haría un navegador real. Por lo tanto, los tooltips del diagrama, las minigráficas
  del Dashboard, los tooltips de los gráficos de Visualización/Resultados y el diseño
  responsive **no quedan cubiertos** por esta prueba automática; solo se verifica que
  la aplicación no lance excepciones.
- Verificación manual en navegador (sesiones de desarrollo previas, antes de las
  últimas modificaciones documentales): las 4 pantallas, los 9 escenarios del
  simulador (3 modos × 3 niveles) con sus etiquetas, descargas CSV, diseño responsive
  (escritorio y móvil vía container queries), sin errores de consola.
- Validación ad hoc (script fuera del repo, no forma parte de la suite oficial) de la
  tarjeta "Duración del ensayo": confirmó 60.0 min para los 3 ensayos reales y, con
  ensayos sintéticos generados solo en memoria, 30.0 min y 90.0 min (este último con el
  desglose en horas), sin modificar `datos_simulados/`.

## 9. Restricciones vigentes para quien continúe el desarrollo

- No modificar `procesar.py` ni `generar_datos.py`.
- No modificar los CSV originales de `datos_simulados/`.
- No cambiar las fórmulas de `escenarios.py`.
- No presentar los datos simulados como mediciones en tiempo real ni afirmar
  comunicación con un ESP32.
- Esta carpeta (`C:\Proyectos\TWIND42_app`) es ahora la ubicación de desarrollo activo.
  La carpeta original en `C:\Users\ayulg\.codex\.chatgpt-projects\...\demo_twind42`
  queda como respaldo histórico y no debería seguir editándose.
- El repositorio está publicado en GitHub:
  <https://github.com/Ayulgabriel42/TWIND42_APP> (público, rama `master`). También hay
  una instancia desplegada en Streamlit Community Cloud
  (<https://twind42app.streamlit.app/>); al intentar acceder sin sesión iniciada en
  Streamlit, la plataforma redirige a una pantalla de autenticación propia de
  Streamlit Cloud — confirmar con el autor si el acceso público está habilitado antes
  de compartir ese enlace con la Comisión Académica Evaluadora. La vía de ejecución
  más confiable para una evaluación sigue siendo correr la app localmente (ver
  `INSTRUCCIONES.txt`).
