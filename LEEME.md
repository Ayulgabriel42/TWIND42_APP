# TWIND42 — Guía de uso de la aplicación

> **Datos simulados.** Todo lo que muestra esta aplicación proviene de archivos CSV de
> ejemplo o cargados por el usuario, procesados localmente. No hay conexión a un ESP32
> ni a ningún sensor físico, y nada de lo que se ve representa una adquisición en
> tiempo real. Ver también [`README.md`](README.md) (presentación general del
> proyecto), [`INSTRUCCIONES.txt`](INSTRUCCIONES.txt) (instalación y ejecución paso a
> paso) y [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) (referencia técnica detallada).

## Instalación rápida

Con Python 3.12 instalado, desde esta carpeta:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Esto abre la aplicación en el navegador (`http://localhost:8501`). El instructivo
completo, con requisitos y resolución de problemas, está en `INSTRUCCIONES.txt`.

La aplicación tiene cuatro pantallas, accesibles desde el menú lateral
("Panel de ensayos → Navegación"): **Dashboard**, **Configuración**, **Visualización**
y **Resultados**. El ensayo elegido en cualquiera de ellas queda sincronizado en las
demás (`st.session_state["ensayo_seleccionado"]`).

## 1. Dashboard

Es la pantalla de inicio. Si todavía no se cargó ningún ensayo propio, muestra
automáticamente el ejemplo incluido `SIM-HIB-01`, identificado como ilustrativo, para
que la pantalla no aparezca vacía.

**Diagrama energético.** Representa los 5 nodos del sistema: generación eólica
(turbina), generación fotovoltaica (panel solar), distribución energética (nodo
central que reparte la generación), batería y carga LED. Una barra de etiquetas arriba
del diagrama identifica cada nodo por su nombre y color; al pasar el cursor o enfocar
cada etiqueta con el teclado aparece un tooltip con la función del nodo y sus valores
reales en ese instante (potencia en W, energía acumulada en Wh) — nunca valores
inventados o interpolados.

**Simulador de escenarios.** Permite, solo en esta pantalla, elegir un **Modo**
(Híbrido, Eólico o Solar) y un **Nivel** de generación simulada (100 %, 50 % o 1 %).
Esto construye un *escenario hipotético derivado* del ensayo de referencia
seleccionado (badge "ESCENARIO SIMULADO"): reescala la potencia eólica y/o
fotovoltaica del ensayo real, pero **nunca toca la carga ni la batería**, que quedan
exactamente como fueron medidas. El header distingue siempre "Ensayo de referencia:
`<id>`" (el ensayo real elegido) de "Escenario seleccionado: `<modo>` · `<nivel>`%" (el
recorte hipotético sobre ese ensayo).

Cuando la generación simulada no alcanza a cubrir la demanda (escenario con déficit),
los nodos de Distribución/Batería/Carga pasan a un estilo con borde punteado de alerta,
sus etiquetas cambian a "Batería de referencia" / "Demanda de referencia", y sus
tooltips aclaran explícitamente que esos valores no representan un suministro efectivo
garantizado — son los valores medidos del ensayo original, no recalculados.

**Tarjetas e indicadores.** Potencia eólica, potencia fotovoltaica, potencia batería
(con tag "Cargando"/"Descargando"/"Sin intercambio") y potencia carga LED, cada una con
su color de marca. Debajo, dos minigráficas ("Evolución de potencia (W)" y "Energía
acumulada (Wh)") con leyenda de colores por serie, referencias de tiempo y unidad en
los ejes, y un tooltip por cursor/teclado que muestra el minuto exacto y el valor real
de cada serie en ese punto. Por último, un balance resumido (Fuentes / Carga / Batería
/ Residuo) con la misma lógica de "Balance equilibrado / Déficit / Excedente" descripta
más abajo para Resultados.

## 2. Configuración

Tres pasos, cada uno en su propia tarjeta:

1. **Origen de los datos y procesamiento.** Elegir entre "Ejemplos incluidos" (tres
   ensayos en un mismo archivo: eólico, fotovoltaico e híbrido, 60 minutos de muestras
   cada 5 segundos) o "Cargar CSV de prueba" (subir `ensayos.csv` y `mediciones.csv`
   propios, con la estructura definida en el proyecto, confirmando explícitamente que
   son datos simulados). El botón "Cargar y procesar ejemplos" ejecuta el motor de
   cálculo (`procesar.py`) sobre los CSV de ejemplo. El botón "Probar rechazo de
   archivo inválido" hace lo mismo pero con un archivo con un dato inválido a
   propósito, para mostrar que el sistema lo rechaza sin romperse (mismo mecanismo que
   usa `probar_error.py`, ver más abajo).
2. **Ensayo cargado.** Una vez procesado, muestra de qué ensayo se trata (modo, carga
   nominal declarada, fecha del archivo) y permite elegir cuál revisar si el
   procesamiento incluyó varios.
3. **Parámetros de esta sesión.** Permite declarar el estado inicial de batería (%) y
   observaciones, que se guardan solo en la sesión del navegador — **no modifican las
   mediciones ni los cálculos**, y se pueden descargar en un `ensayos.csv` actualizado.

Una carga inválida retira de la sesión cualquier resultado anterior, para evitar
confusiones entre un procesamiento fallido y uno exitoso previo.

## 3. Visualización

Reproduce, de forma acelerada (1 segundo de pantalla equivale a 1 minuto del ensayo,
cada muestra original representa 5 segundos reales), un ensayo ya procesado. **No es
una adquisición en tiempo real**: es la reproducción de un CSV ya cargado.

Controles: **Reproducir**, **Pausar**, **Reiniciar**, y un slider "Recorrer muestras"
que indica su propio rango (`0 a N-1`, donde `N` es la cantidad de muestras del ensayo
elegido — 721 para los ejemplos incluidos, pero varía con la duración real de cada
ensayo). Debajo del slider aparece una leyenda en vivo, por ejemplo "Muestra 140 de 720
· minuto 11.7 de 60.0 del ensayo", para que el número del slider nunca quede sin
contexto de tiempo.

Para la muestra actual se muestran: tiempo reproducido (minutos), batería inicial
declarada, estado de la batería en esa muestra (Cargando/Descargando/Sin intercambio),
tarjetas de potencia instantánea por fuente, un diagrama de flujo energético (Sankey)
acumulado **hasta ese instante** de la reproducción, la tabla de mediciones de ese
instante y un gráfico de potencia con todo lo reproducido hasta ahí.

## 4. Resultados

Permite consultar y comparar los ensayos ya procesados, con los valores completos del
ensayo (no solo hasta donde llegó la reproducción en Visualización).

- **Duración del ensayo**: se calcula automáticamente a partir de las marcas
  temporales reales del ensayo elegido (nunca un valor fijo de 60 minutos), mostrada
  en minutos y, si corresponde, con el desglose en horas y minutos.
- Dos aclaraciones fijas: (1) los indicadores y balances corresponden al período
  **completo** del ensayo, independientemente de dónde haya quedado el cursor en
  Visualización; (2) esta pantalla muestra el **ensayo de referencia procesado** — los
  escenarios hipotéticos Modo/Nivel del Dashboard no modifican estos valores.
- **Balance energético**: Fuentes, Carga LED, Batería (neta) y Residuo, en Wh
  (Fuentes = Carga + Batería + Residuo). Para los ejemplos incluidos se supuso un
  balance ideal sin pérdidas; con datos reales el residuo exigiría investigación y no
  equivale automáticamente a una pérdida física.
- Diagrama de flujo energético (Sankey) del ensayo completo, y gráficos de potencia
  instantánea y energía acumulada por punto medido.
- **Comparar escenarios simulados**: una tabla comparativa entre los distintos
  *ensayos* procesados en la misma sesión (eólico / fotovoltaico / híbrido, por
  ejemplo). *Nota de vocabulario*: acá "escenarios" se refiere a los ensayos de
  ejemplo entre sí, no al escenario hipotético Modo/Nivel del Dashboard — son dos usos
  distintos de la misma palabra en partes separadas de la aplicación.
- **Descargar resultados**: botones para bajar `mediciones_procesadas.csv`,
  `resumen.csv` y `balance.csv` (las salidas de `procesar.py` para ese procesamiento).

## Procesamiento de datos: de CSV a resultados

1. `ensayos.csv` declara cada ensayo (`id_ensayo`, `fecha`, `modo_operacion`, `carga_w`,
   `estado_inicial_bateria`, `observaciones`).
2. `mediciones.csv` trae una fila por instante y por punto medido (`eolico`,
   `fotovoltaico`, `bateria`, `carga`), con tensión y corriente ya registradas;
   `potencia_w` y `energia_wh` se dejan vacíos en la entrada, el programa los calcula.
3. `procesar.py` valida cada fila (tipos numéricos, rangos, convenciones de signo),
   calcula `potencia_w = tensión × corriente`, integra `energia_wh` por la regla
   trapezoidal entre muestras consecutivas (exige exactamente 5 segundos entre
   muestras del mismo punto, sin interrupciones) y arma el balance final:
   `fuentes = eólico + fotovoltaico`, `residuo = fuentes − carga − batería`.
4. Para el punto `bateria`, corriente positiva significa **carga** y corriente
   negativa, **descarga**.

## Ejecución del procesador sin interfaz (opcional)

Además de la aplicación web (la vía principal), el motor de cálculo se puede correr
por línea de comandos, sin Streamlit:

```powershell
.\.venv\Scripts\python.exe generar_datos.py
.\.venv\Scripts\python.exe procesar.py
```

Esto genera `salida/mediciones_procesadas.csv`, `salida/resumen.csv`,
`salida/balance.csv` y un informe standalone `salida/resultados.html` (con sus propias
tablas y gráficos en SVG, independiente de la app Streamlit). No requiere paquetes
externos ni conexión a internet. *Nota:* ese informe HTML dibuja el eje de tiempo de
sus gráficos con marcas fijas en 0/15/30/45/60 minutos; funciona correctamente con los
3 ensayos de ejemplo incluidos (que duran 60 minutos cada uno), pero un ensayo de otra
duración quedaría con el eje mal etiquetado en ese informe puntual — ver
`PROJECT_CONTEXT.md` para el detalle de esta limitación conocida (no corregida en esta
intervención, por no modificar `procesar.py`).

## Pruebas disponibles

- **`probar_interfaz.py`** — prueba funcional de extremo a extremo, usando
  `streamlit.testing.v1.AppTest` (sin abrir un navegador real). Recorre las 4
  pantallas, carga los ejemplos, reproduce en Visualización, verifica los balances
  esperados y la sincronización del ensayo elegido entre pantallas, y confirma el
  rechazo de un CSV inválido. Se ejecuta con:
  ```powershell
  .\.venv\Scripts\python.exe probar_interfaz.py
  ```
  Resultado esperado (última línea impresa):
  `PRUEBA SUPERADA: dashboard, configuración, reproducción, resultados, balances, sincronización de ensayo y rechazo de CSV.`
  *Limitación:* al no renderizar el navegador, no cubre el componente visual del
  Dashboard (HTML/CSS/JS inline), los tooltips, ni el diseño responsive — solo
  verifica que la aplicación no lance excepciones y que el estado sea el esperado.
- **`probar_error.py`** — comprueba, a nivel del motor `procesar.py`, que un CSV con
  un dato de tensión inválido (`mediciones_con_error.csv`) se rechaza con un mensaje
  claro y sin afectar los resultados correctos existentes. Se ejecuta con:
  ```powershell
  .\.venv\Scripts\python.exe probar_error.py
  ```
  Resultado esperado: confirma el error detectado y termina con
  `PRUEBA SUPERADA: el archivo inválido fue rechazado.`

## Estado del desarrollo

Esta es una demostración de software con datos simulados. La adquisición física
mediante ESP32, la calibración de sensores y la validación experimental del prototipo
energético **permanecen pendientes** y no están representadas en ningún lugar de esta
aplicación como si ya existieran.
