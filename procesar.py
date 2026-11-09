"""Procesamiento local de mediciones TWIND42. No simula el hardware ESP32."""
import argparse
import csv
from collections import defaultdict
from datetime import datetime
from html import escape
from pathlib import Path

CAMPOS_ENSAYO = ["id_ensayo", "fecha", "modo_operacion", "carga_w", "estado_inicial_bateria", "observaciones"]
CAMPOS_MEDICION = ["id_medicion", "id_ensayo", "fecha_hora", "punto_medido", "rpm", "tension_v", "corriente_a", "potencia_w", "energia_wh", "velocidad_viento", "irradiancia"]
PUNTOS = ["eolico", "fotovoltaico", "bateria", "carga"]
MODOS = {"eolico", "fotovoltaico", "hibrido"}


def leer_csv(ruta, campos):
    with ruta.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != campos:
            raise ValueError(f"{ruta.name}: columnas incorrectas. Se esperan: {', '.join(campos)}")
        return list(reader)


def numero(valor, nombre, fila, opcional=False):
    if valor == "" and opcional:
        return None
    try:
        n = float(valor)
    except ValueError as exc:
        raise ValueError(f"Fila {fila}: {nombre} debe ser numérico; se recibió {valor!r}") from exc
    if not -1e12 < n < 1e12:
        raise ValueError(f"Fila {fila}: {nombre} está fuera de rango")
    return n


def procesar(carpeta, salida):
    ensayos = leer_csv(carpeta / "ensayos.csv", CAMPOS_ENSAYO)
    mediciones = leer_csv(carpeta / "mediciones.csv", CAMPOS_MEDICION)
    if not ensayos or not mediciones:
        raise ValueError("Los archivos de entrada no pueden estar vacíos")
    por_id = {}
    for i, e in enumerate(ensayos, 2):
        eid = e["id_ensayo"]
        if not eid or eid in por_id:
            raise ValueError(f"Fila {i} de ensayos: id_ensayo vacío o duplicado")
        if e["modo_operacion"] not in MODOS:
            raise ValueError(f"Fila {i} de ensayos: modo_operacion desconocido")
        carga = numero(e["carga_w"], "carga_w", i)
        bateria = numero(e["estado_inicial_bateria"], "estado_inicial_bateria", i)
        if carga <= 0 or not 0 <= bateria <= 100:
            raise ValueError(f"Fila {i} de ensayos: carga o porcentaje de batería inválido")
        por_id[eid] = e

    vistos = set()
    grupos = defaultdict(list)
    tiempos = defaultdict(set)
    for i, m in enumerate(mediciones, 2):
        if not m["id_medicion"] or m["id_medicion"] in vistos:
            raise ValueError(f"Fila {i}: id_medicion vacío o duplicado")
        vistos.add(m["id_medicion"])
        eid, punto = m["id_ensayo"], m["punto_medido"]
        if eid not in por_id or punto not in PUNTOS:
            raise ValueError(f"Fila {i}: ensayo o punto_medido desconocido")
        try:
            fecha = datetime.strptime(m["fecha_hora"], "%Y-%m-%d %H:%M:%S")
        except ValueError as exc:
            raise ValueError(f"Fila {i}: fecha_hora inválida") from exc
        v = numero(m["tension_v"], "tension_v", i)
        a = numero(m["corriente_a"], "corriente_a", i)
        if v < 0 or (a < 0 and punto != "bateria"):
            raise ValueError(f"Fila {i}: tensión o corriente fuera de la convención definida")
        for campo in ("rpm", "velocidad_viento", "irradiancia"):
            x = numero(m[campo], campo, i, opcional=True)
            if x is not None and x < 0:
                raise ValueError(f"Fila {i}: {campo} no puede ser negativo")
        clave = (eid, punto)
        if fecha in tiempos[clave]:
            raise ValueError(f"Fila {i}: medición duplicada para el mismo instante y punto")
        tiempos[clave].add(fecha)
        grupos[clave].append((fecha, m, v * a))

    salida.mkdir(parents=True, exist_ok=True)
    resumen = []
    procesadas = []
    series = []
    for eid, ensayo in por_id.items():
        for punto in PUNTOS:
            muestras = sorted(grupos[(eid, punto)])
            if len(muestras) < 2:
                raise ValueError(f"{eid}/{punto}: se requieren al menos dos mediciones")
            energia = 0.0
            anterior = None
            energia_puntos = []
            for fecha, original, potencia in muestras:
                if anterior is not None:
                    dt = (fecha - anterior[0]).total_seconds()
                    if dt != 5:
                        raise ValueError(f"{eid}/{punto}: intervalo de {dt:g} s; se esperan 5 s sin interrupciones")
                    energia += (anterior[1] + potencia) / 2 * dt / 3600
                fila = dict(original)
                fila["potencia_w"] = f"{potencia:.4f}"
                fila["energia_wh"] = f"{energia:.6f}"
                procesadas.append(fila)
                energia_puntos.append((fecha, energia))
                anterior = (fecha, potencia)
            duracion = (muestras[-1][0] - muestras[0][0]).total_seconds()
            resumen.append({"id_ensayo": eid, "modo_operacion": ensayo["modo_operacion"], "punto_medido": punto,
                            "duracion_min": f"{duracion / 60:.1f}", "energia_wh": f"{energia:.4f}",
                            "sentido_bateria": "cargando" if punto == "bateria" and energia > 0 else ("descargando" if punto == "bateria" and energia < 0 else "—")})
            series.append((eid, punto, [(m[0], m[2]) for m in muestras], energia_puntos))

    with (salida / "mediciones_procesadas.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CAMPOS_MEDICION)
        writer.writeheader(); writer.writerows(procesadas)
    with (salida / "resumen.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(resumen[0]))
        writer.writeheader(); writer.writerows(resumen)
    balances = []
    for eid, ensayo in por_id.items():
        energias = {r["punto_medido"]: float(r["energia_wh"]) for r in resumen if r["id_ensayo"] == eid}
        fuentes = energias["eolico"] + energias["fotovoltaico"]
        # Energía positiva de batería = carga; negativa = aporte desde batería.
        residuo = fuentes - energias["carga"] - energias["bateria"]
        balances.append({"id_ensayo": eid, "modo_operacion": ensayo["modo_operacion"],
                         "fuentes_wh": f"{fuentes:.4f}", "carga_wh": f"{energias['carga']:.4f}",
                         "bateria_wh": f"{energias['bateria']:.4f}", "residuo_wh": f"{residuo:.4f}"})
    with (salida / "balance.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(balances[0]))
        writer.writeheader(); writer.writerows(balances)
    crear_html(resumen, balances, series, salida / "resultados.html")
    return resumen


def crear_html(resumen, balances, series, ruta):
    colores = {"eolico": "#0b7285", "fotovoltaico": "#ce6c08", "bateria": "#7950a8", "carga": "#198754"}
    partes = ['<!doctype html><html lang="es"><meta charset="utf-8"><title>TWIND42 · Demo de software</title>',
              '<style>body{font:16px Arial,sans-serif;max-width:1050px;margin:35px auto;color:#17232d;line-height:1.45}h1,h2{color:#173e54}table{border-collapse:collapse;width:100%}th,td{padding:9px;border-bottom:1px solid #ccd5db;text-align:left}tr:nth-child(even){background:#f4f7f9}svg{display:block;width:100%;height:auto;background:white;border:1px solid #d5dfe5;border-radius:8px} .aviso{background:#fff2d6;padding:14px;border-left:5px solid #c98500}.ensayo{margin:36px 0;padding:22px;border:1px solid #d5dfe5;border-radius:10px}.leyenda{display:flex;gap:24px;flex-wrap:wrap;margin:10px 0 16px}.leyenda span{font-weight:600}</style>',
              '<h1>TWIND42 · Verificación del software</h1><p class="aviso"><b>DATOS SIMULADOS.</b> Estos gráficos verifican cálculos y lectura de CSV; no representan ensayos físicos ni producción real del prototipo.</p>',
              '<h2>Resumen por ensayo y punto</h2><table><tr><th>Ensayo</th><th>Modo</th><th>Punto</th><th>Duración (min)</th><th>Energía (Wh)</th><th>Batería</th></tr>']
    for r in resumen:
        partes.append('<tr>'+''.join(f'<td>{escape(str(r[k]))}</td>' for k in r)+'</tr>')
    partes.append('</table><p>Convención: corriente positiva en batería = carga; negativa = descarga. Potencia = tensión × corriente. Energía = integración trapezoidal entre muestras.</p>')
    partes.append('<h2>Balance energético por ensayo</h2><p><b>Fuentes = carga + batería + residuo.</b> Para estos datos simulados se supuso un balance ideal sin pérdidas. El residuo se informa como diferencia entre puntos; con mediciones reales no debe interpretarse automáticamente como una pérdida.</p>')
    partes.append('<table><tr><th>Ensayo</th><th>Modo</th><th>Fuentes (Wh)</th><th>Carga (Wh)</th><th>Batería (Wh)</th><th>Residuo (Wh)</th></tr>')
    for b in balances:
        partes.append('<tr>'+''.join(f'<td>{escape(str(b[k]))}</td>' for k in b)+'</tr>')
    partes.append('</table>')

    def grafico(datos, indice, unidad, titulo):
        maximo = max(max(v for _, v in serie[indice]) for serie in datos)
        limite = max(5, int(maximo / 5 + 1) * 5)
        # 0 a 60 minutos y eje vertical con cinco divisiones explícitas.
        lineas = [f'<svg viewBox="0 0 900 310" role="img" aria-label="{escape(titulo)}">',
                  f'<text x="62" y="25" font-size="16" font-weight="bold" fill="#173e54">{escape(titulo)}</text>',
                  f'<text x="816" y="290" font-size="13" fill="#43525c">minutos</text>']
        for tick in range(6):
            y = 255 - tick * 42
            lineas.append(f'<line x1="62" y1="{y}" x2="860" y2="{y}" stroke="#e0e7eb"/>')
            lineas.append(f'<text x="51" y="{y+5}" text-anchor="end" font-size="13" fill="#43525c">{limite*tick/5:g}</text>')
        for minuto in (0, 15, 30, 45, 60):
            x = 62 + minuto * 798 / 60
            lineas.append(f'<line x1="{x:.1f}" y1="45" x2="{x:.1f}" y2="255" stroke="#eef2f4"/>')
            lineas.append(f'<text x="{x:.1f}" y="276" text-anchor="middle" font-size="13" fill="#43525c">{minuto}</text>')
        lineas.append(f'<text x="13" y="38" font-size="13" fill="#43525c">{unidad}</text>')
        for punto, potencia, energia in datos:
            valores = potencia if indice == 1 else energia
            if all(v == 0 for _, v in valores):
                continue  # la fuente desactivada se explica fuera del gráfico
            coords = ' '.join(f'{62 + i * 798 / (len(valores)-1):.1f},{255 - v / limite * 210:.1f}' for i, (_, v) in enumerate(valores))
            lineas.append(f'<polyline points="{coords}" fill="none" stroke="{colores[punto]}" stroke-width="2.8"/>')
        lineas.append('</svg>')
        return ''.join(lineas)

    for eid in sorted({s[0] for s in series}):
        datos = [(punto, potencia, energia) for e, punto, potencia, energia in series if e == eid]
        activos = [(p, pot, ene) for p, pot, ene in datos if any(v != 0 for _, v in pot)]
        partes.append(f'<section class="ensayo"><h2>{escape(eid)}</h2>')
        partes.append('<div class="leyenda">'+''.join(f'<span style="color:{colores[p]}">■ {p}</span>' for p,_,_ in activos)+'</div>')
        partes.append(grafico(datos, 1, 'W', 'Potencia instantánea por punto'))
        partes.append('<p>La línea de la carga permanece estable para verificar un consumo cercano a 20 W. Las variaciones de generación son ficticias.</p>')
        partes.append(grafico(datos, 2, 'Wh', 'Energía acumulada por punto'))
        partes.append('</section>')
    partes.append('</html>')
    ruta.write_text('\n'.join(partes), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Procesa datos simulados TWIND42 según la estructura del TFG")
    parser.add_argument("--datos", type=Path, default=Path(__file__).resolve().parent / "datos_simulados")
    parser.add_argument("--salida", type=Path, default=Path(__file__).resolve().parent / "salida")
    args = parser.parse_args()
    try:
        resultado = procesar(args.datos, args.salida)
    except (OSError, ValueError) as error:
        parser.exit(1, f"ERROR: {error}\n")
    print(f"Procesados {len(resultado) // 4} ensayos. Resultados: {args.salida / 'resultados.html'}")
