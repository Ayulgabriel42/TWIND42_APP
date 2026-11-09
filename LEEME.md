# Demo de software TWIND42

Esta carpeta verifica el procesamiento local de archivos CSV. **Todos los datos incluidos son simulados.** No se ha conectado un ESP32 ni se han realizado ensayos físicos.

## Interfaz Streamlit

Con Python 3.12, desde esta carpeta:

```text
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

La interfaz abre en el navegador. En **Configuración**, pulsá **Cargar y procesar ejemplos**. Después usá **Visualización** para reproducir las muestras y **Resultados** para consultar, comparar y descargar los cálculos. También podés cargar un par de CSV de prueba o probar el rechazo del archivo inválido.

El estado inicial de batería y las observaciones se pueden guardar en la sesión y descargar en `ensayos.csv`; no alteran las mediciones simuladas. No se calcula el porcentaje final de batería. La reproducción avanza un minuto de ensayo por segundo de pantalla: no hay adquisición desde ESP32.

Los archivos cargados se procesan en una carpeta temporal independiente que se elimina al terminar. Los resultados permanecen en la sesión hasta cerrarla o recargarla; descargalos para conservarlos. Una carga inválida elimina de la sesión los resultados anteriores. La versión local funciona sin internet una vez instaladas las dependencias. La eventual versión publicada requiere internet y procesará los CSV en su servidor.

## Ejecución del procesador sin interfaz

Se requiere Python 3.10 o posterior. Abrí esta carpeta en VS Code y ejecutá en la terminal:

```text
python generar_datos.py
python procesar.py
```

Abrí `salida/resultados.html` en el navegador. `salida/mediciones_procesadas.csv` conserva potencia y energía calculadas; `salida/resumen.csv` reúne los valores finales por punto y `salida/balance.csv` presenta el balance por ensayo.

En Windows, si `python` no está disponible, probá `py` en su lugar. No se necesitan paquetes externos ni conexión a internet.

## Qué se muestra

`ensayos.csv` guarda la configuración de cada ensayo. `estado_inicial_bateria` es un porcentaje numérico, sin `%`. `mediciones.csv` usa los campos definidos en la Estructura de datos del TFG. Las muestras simuladas cubren 60 minutos por modo, a intervalos de 5 segundos. `potencia_w` y `energia_wh` se dejan vacíos en la entrada; el programa los calcula.

Para el punto `bateria`, corriente positiva significa **carga** y corriente negativa, **descarga**. Un campo vacío en `rpm`, `velocidad_viento` o `irradiancia` significa que esa variable no corresponde a ese punto; un `0` significa valor medido o supuesto igual a cero.

Para mostrar un error de validación, ejecutá `python probar_error.py`. La prueba utiliza el archivo `mediciones_con_error.csv`, informa que `tension_v` es inválida y confirma que fue rechazado. Los resultados correctos permanecen intactos.

La energía se integra mediante la regla trapezoidal entre mediciones consecutivas. La carga simulada se mantiene cerca de 20 W durante una hora, por lo que el resultado esperado es cercano a 20 Wh. La generación y la carga de batería varían de manera ficticia y reproducible para comprobar los gráficos. Para este caso se supuso un balance ideal sin pérdidas: fuentes = carga + energía que entra en batería. El programa muestra además el residuo calculado entre estos puntos. Con datos reales, ese residuo exigirá investigación y no podrá atribuirse automáticamente a pérdidas. Se muestran potencia instantánea y energía acumulada, con ejes y unidades. Las fuentes inactivas se omiten de cada gráfico. Los datos no predicen el desempeño de los equipos cotizados. La incorporación posterior de datos ESP32 deberá respetar esta estructura y comprobarse con instrumentos de referencia.
