# TWIND42

Prototipo académico desarrollado para el Trabajo Final de Graduación (TFG) de la
Licenciatura en Inteligencia Artificial y Robótica (Universidad Siglo 21), titulado:

> "Microgeneración híbrida eólico-fotovoltaica para el aprovechamiento de recursos
> renovables en el corredor urbano-vial de la Ruta Nacional N.º 3, Comodoro Rivadavia".

> **Datos simulados.** Esta versión del proyecto trabaja exclusivamente con archivos
> CSV simulados. No hay conexión a un ESP32 ni a ningún sensor físico, y nada de lo que
> muestra la aplicación representa una medición en tiempo real ni un ensayo físico.

## Descripción

TWIND42 modela el funcionamiento de un sistema híbrido de microgeneración eólica y
fotovoltaica, con almacenamiento en batería y una carga demostrativa LED de 20 W. Esta
entrega es una aplicación web que permite cargar, procesar, reproducir y analizar
registros de ese sistema, además de simular escenarios hipotéticos de generación
(distintos modos y niveles de potencia) sobre un ensayo ya procesado.

## Objetivo tecnológico

Construir, de forma incremental y verificable, el software de procesamiento y
visualización energética que eventualmente recibirá datos reales de una etapa de
adquisición electrónica basada en ESP32. Esta fase se concentra en tener un motor de
cálculo validado (lectura de CSV, cómputo de potencia y energía, balance energético) y
una interfaz clara para explorarlo, antes de integrar hardware.

## Estado actual del desarrollo

| Implementado | Pendiente |
|---|---|
| Aplicación web (Streamlit) con 4 pantallas funcionales | Adquisición física mediante ESP32 y sensores |
| Motor de cálculo validado (potencia, energía, balance) | Calibración de sensores |
| Procesamiento y validación de archivos CSV | Integración electrónica del prototipo |
| Simulador de escenarios hipotéticos de generación | Ensayos y validación experimental |
| Pruebas automáticas de la interfaz y del procesador | Comparación datos simulados vs. reales |

Todo lo que no está en la columna "Implementado" **no** debe interpretarse como
funcionando: esta documentación evita deliberadamente dar esa impresión en cualquier
sección.

## Arquitectura general

Aplicación Python de un solo proceso, sin backend ni base de datos separados: todo el
cálculo energético corre localmente al procesar los CSV, dentro del mismo proceso de
Streamlit.

```
CSV (ensayos.csv + mediciones.csv)
        │
        ▼
  procesar.py   ← valida filas, calcula potencia y energía, arma el balance
        │
        ▼
  app.py (Streamlit)  ← 4 pantallas: Dashboard · Configuración · Visualización · Resultados
        │                           │
        │                           └─ dashboard.py (componente HTML/CSS/JS del Dashboard)
        │                           └─ escenarios.py (escenarios hipotéticos derivados)
        ▼
  Navegador del usuario
```

## Tecnologías utilizadas

| Tecnología | Función en el proyecto |
|---|---|
| **Python 3.12** | Lenguaje del motor de cálculo y de la aplicación. |
| **Streamlit** | Framework de la interfaz web: navegación, formularios, estado de sesión. |
| **pandas** | Manejo de los DataFrames de mediciones y balances dentro de la app. |
| **Plotly** | Gráficos interactivos (series de potencia/energía, diagramas de flujo Sankey). |
| **Streamlit Custom Components V2** | Base del componente del Dashboard: HTML, CSS y JavaScript inline, sin build de frontend ni iframe. |
| **CSV + stdlib de Python** | El procesador (`procesar.py`, `generar_datos.py`) no usa ninguna dependencia externa. |

## Las cuatro pantallas

1. **Dashboard** — Panel de control inicial: diagrama energético con sus 5 nodos
   identificados y con tooltips (generación eólica, generación fotovoltaica,
   distribución energética, batería, carga LED), tarjetas de potencia, minigráficas de
   evolución, balance resumido, y un simulador de escenarios hipotéticos de generación
   (Modo: Híbrido/Eólico/Solar; Nivel: 100 %/50 %/1 %).
2. **Configuración** — Elegir el origen de los datos (ejemplos incluidos o CSV
   propios), procesarlos, revisar qué ensayo quedó cargado y declarar parámetros de la
   sesión (estado inicial de batería, observaciones).
3. **Visualización** — Reproducción acelerada (no en tiempo real) de un ensayo ya
   procesado, con controles de reproducir/pausar/reiniciar y un slider para recorrer
   las muestras manualmente.
4. **Resultados** — Balance energético final, duración real del ensayo, gráficos de
   potencia y energía, comparación entre los ensayos cargados y descarga de los CSV de
   resultados.

Descripción detallada de cada pantalla, con todas sus funciones, en
[`LEEME.md`](LEEME.md).

## Flujo general de procesamiento de datos

1. `ensayos.csv` declara cada ensayo (modo de operación, carga nominal, estado inicial
   de batería declarado).
2. `mediciones.csv` trae tensión y corriente por instante y por punto medido (eólico,
   fotovoltaico, batería, carga).
3. `procesar.py` valida cada fila, calcula `potencia_w = tensión × corriente`, integra
   `energia_wh` con la regla trapezoidal entre muestras consecutivas, y arma el
   balance: `fuentes = eólico + fotovoltaico`, `residuo = fuentes − carga − batería`.
4. La aplicación Streamlit consume esos resultados ya calculados; no reimplementa
   ninguna fórmula propia fuera de `procesar.py` (los escenarios hipotéticos del
   Dashboard solo reescalan la potencia de generación ya calculada, con la misma
   regla de integración).

## Estructura de carpetas y archivos

```
TWIND42_app/
├── app.py                      Punto de entrada de la app Streamlit (4 pantallas)
├── dashboard.py                Componente del Dashboard (HTML/CSS/JS inline)
├── escenarios.py                Escenarios hipotéticos derivados (Dashboard)
├── procesar.py                  Motor de cálculo energético (CSV → resultados)
├── generar_datos.py             Genera los CSV de ejemplo en datos_simulados/
├── dashboard_prototipo.py       Script de referencia para QA visual del Dashboard
├── probar_interfaz.py           Prueba funcional end-to-end de la app (AppTest)
├── probar_error.py              Prueba de rechazo de CSV inválido
├── requirements.txt             Dependencias de la app (streamlit, pandas, plotly)
├── datos_simulados/             CSV de ejemplo (ensayos.csv, mediciones.csv, caso con error)
├── assets/                      Logo y recursos gráficos de marca
├── .streamlit/config.toml       Tema visual y configuración del cliente de Streamlit
├── README.md                    Este archivo
├── LEEME.md                     Guía de uso, pantalla por pantalla
├── INSTRUCCIONES.txt            Instalación y ejecución, paso a paso
└── PROJECT_CONTEXT.md           Referencia técnica detallada (arquitectura, fórmulas, decisiones)
```

(`app_backup.py` y `app_backup_pre_dashboard.py` son copias históricas de `app.py` en
hitos previos del desarrollo; se conservan como respaldo, no son parte de la app activa.)

## Requisitos de instalación

- Python 3.12 (recomendado; probado en Windows).
- Las dependencias de `requirements.txt` (streamlit, pandas, plotly).
- Conexión a internet solo para la descarga inicial.

## Ejecución (resumen)

```powershell
git clone https://github.com/Ayulgabriel42/TWIND42_APP.git
cd TWIND42_APP
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

La aplicación abre en `http://localhost:8501`. Instrucciones completas, con requisitos
detallados y resolución de problemas habituales, en
[`INSTRUCCIONES.txt`](INSTRUCCIONES.txt).

## Pruebas

```powershell
.\.venv\Scripts\python.exe probar_interfaz.py   # prueba funcional de las 4 pantallas
.\.venv\Scripts\python.exe probar_error.py      # rechazo de un CSV inválido
```

Ambas pasan sobre el estado actual del repositorio. Sus alcances y limitaciones están
detallados en `LEEME.md` e `INSTRUCCIONES.txt`.

## Datos simulados: aclaración importante

Todos los CSV incluidos en `datos_simulados/` son generados por `generar_datos.py` con
valores ficticios y reproducibles, pensados únicamente para verificar el software (la
lectura de archivos, los cálculos y los gráficos). No provienen de un ensayo físico, no
predicen el desempeño de ningún equipo real, y el balance energético "ideal" que
presentan (sin pérdidas) es una propiedad de cómo se construyeron esos datos de
ejemplo, no un resultado experimental.

## Limitaciones actuales y evolución prevista

- No hay adquisición de datos en tiempo real ni comunicación con hardware: todo
  depende de archivos CSV cargados manualmente.
- No se calcula el porcentaje de batería restante (requeriría la capacidad real de la
  batería y un modelo de almacenamiento que esta versión no incluye).
- El informe HTML standalone que genera el procesador por línea de comandos
  (`salida/resultados.html`) asume ensayos de 60 minutos para el eje de tiempo de sus
  gráficos; funciona bien con los ejemplos incluidos, pero no se adapta automáticamente
  a ensayos de otra duración (limitación conocida, documentada en
  `PROJECT_CONTEXT.md`, no corregida en esta entrega).
- Próxima etapa prevista: capa de adquisición electrónica con ESP32, calibración de
  sensores, e incorporación de mediciones reales respetando la misma estructura de
  datos ya validada por el software actual.

---

Para profundizar: [`LEEME.md`](LEEME.md) (uso detallado), [`INSTRUCCIONES.txt`](INSTRUCCIONES.txt)
(instalación paso a paso) y [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) (referencia
técnica para quien continúe el desarrollo).
