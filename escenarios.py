"""Simulación de escenarios derivados para el Dashboard de TWIND42.

IMPORTANTE: este módulo NO modifica procesar.py ni los CSV. Toma los resultados YA
calculados por procesar.py para un ensayo de referencia y construye una variante
hipotética, escalando la potencia eléctrica de las fuentes de generación (eólica y/o
fotovoltaica). Carga y batería quedan siempre exactamente como fueron medidas.

Limitación conocida del modelo (ver procesar.py): la energía de batería es una
magnitud MEDIDA, no una variable que el balance ajuste para "cerrar" la ecuación.
Por eso estos escenarios nunca hacen que la batería cubra un déficit de generación:
el desbalance se refleja únicamente en el residuo (excedente/déficit), igual que en
los ensayos originales. No se tocan rpm, velocidad_viento, irradiancia, tensión ni
corriente: solo se reescala la potencia eléctrica resultante, nunca las condiciones
físicas que la originaron.
"""
import pandas as pd

MODOS = {
    "hibrido": {"eolico": True, "fotovoltaico": True},
    "eolico": {"eolico": True, "fotovoltaico": False},
    "solar": {"eolico": False, "fotovoltaico": True},
}
NIVELES = [100, 50, 1]


def _reintegrar_energia(datos_punto):
    """Misma regla trapezoidal que procesar.py, aplicada a una potencia ya escalada.
    Devuelve una Series alineada al índice original de datos_punto."""
    orden = datos_punto.sort_values("fecha_hora")
    energia = 0.0
    anterior = None
    resultados = {}
    for idx, fila in orden.iterrows():
        potencia = fila["potencia_w"]
        if anterior is not None:
            dt = (fila["fecha_hora"] - anterior[0]).total_seconds()
            energia += (anterior[1] + potencia) / 2 * dt / 3600
        resultados[idx] = energia
        anterior = (fila["fecha_hora"], potencia)
    return pd.Series(resultados)


def construir_escenario(datos_ensayo, modo, nivel):
    """datos_ensayo: filas de mediciones_procesadas de UN ensayo (salida real de
    procesar.py, ya con columna fecha_hora como datetime). modo: 'hibrido' | 'eolico'
    | 'solar'. nivel: 100 | 50 | 1 (porcentaje de potencia eléctrica simulada).

    Devuelve una copia con potencia_w/energia_wh de eólico y fotovoltaico escalados
    (y puestos en cero si esa fuente está desactivada en el modo elegido). Carga y
    batería no se tocan."""
    if modo not in MODOS:
        modo = "hibrido"
    if nivel not in NIVELES:
        nivel = 100
    activos = MODOS[modo]
    factor = nivel / 100.0
    datos = datos_ensayo.copy()
    for punto, activo in activos.items():
        mascara = datos["punto_medido"] == punto
        escala = factor if activo else 0.0
        datos.loc[mascara, "potencia_w"] = datos.loc[mascara, "potencia_w"] * escala
        datos.loc[mascara, "energia_wh"] = _reintegrar_energia(datos.loc[mascara])
    return datos


def balance_escenario(datos_escenario):
    """Recalcula fuentes/carga/batería/residuo con la misma fórmula de procesar.py,
    sobre los datos ya escalados por construir_escenario(). residuo negativo = déficit
    (la generación escalada no alcanza a cubrir carga + batería medida); positivo =
    excedente."""
    ultimas = (datos_escenario.sort_values("fecha_hora").groupby("punto_medido").tail(1)
               .set_index("punto_medido")["energia_wh"].astype(float))
    eolico_wh = float(ultimas.get("eolico", 0.0))
    fv_wh = float(ultimas.get("fotovoltaico", 0.0))
    carga_wh = float(ultimas.get("carga", 0.0))
    bateria_wh = float(ultimas.get("bateria", 0.0))
    fuentes_wh = eolico_wh + fv_wh
    residuo_wh = fuentes_wh - carga_wh - bateria_wh
    return {"fuentes_wh": fuentes_wh, "carga_wh": carga_wh, "bateria_wh": bateria_wh,
            "residuo_wh": residuo_wh}
