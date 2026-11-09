"""Genera ensayos ficticios para verificar el procesador, no mediciones reales."""
import csv
from math import sin, pi
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "datos_simulados"
OUT.mkdir(exist_ok=True)

ensayos = [
    ("SIM-EOL-01", "eolico", 70),
    ("SIM-FV-01", "fotovoltaico", 70),
    ("SIM-HIB-01", "hibrido", 70),
]

with (OUT / "ensayos.csv").open("w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["id_ensayo", "fecha", "modo_operacion", "carga_w", "estado_inicial_bateria", "observaciones"])
    for ensayo_id, modo, bateria in ensayos:
        writer.writerow([ensayo_id, "2026-11-07", modo, 20, bateria, "DATOS SIMULADOS: prueba de software; batería cargando"])

campos = ["id_medicion", "id_ensayo", "fecha_hora", "punto_medido", "rpm", "tension_v", "corriente_a", "potencia_w", "energia_wh", "velocidad_viento", "irradiancia"]
inicio = datetime(2026, 11, 7, 10, 0, 0)
contador = 0
with (OUT / "mediciones.csv").open("w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(campos)
    for n, (ensayo_id, modo, _) in enumerate(ensayos):
        base = inicio + timedelta(hours=n)
        for paso in range(721):  # 60 minutos, con una muestra cada 5 segundos
            momento = (base + timedelta(seconds=5 * paso)).strftime("%Y-%m-%d %H:%M:%S")
            eolica = modo in {"eolico", "hibrido"}
            solar = modo in {"fotovoltaico", "hibrido"}
            # Variaciones ficticias y reproducibles: solo verifican la visualización.
            fase = 2 * pi * paso / 720
            viento_simulado = 5.2 + 0.7 * sin(2 * fase) if eolica else ""
            sol_simulado = 650 + 90 * sin(fase) if solar else ""
            corriente_eolica = round((2.4 + 0.25 * sin(2 * fase)) if modo == "eolico" else ((1.35 + 0.2 * sin(2 * fase)) if eolica else 0), 4)
            corriente_solar = round((2.3 + 0.2 * sin(fase)) if modo == "fotovoltaico" else ((1.2 + 0.2 * sin(fase)) if solar else 0), 4)
            # Balance ideal ficticio: generación = carga + energía que entra en batería.
            # No representa pérdidas reales ni eficiencia medida.
            corriente_bateria = round((12 * corriente_eolica + 12 * corriente_solar - 12 * 1.67) / 12.6, 6)
            assert corriente_bateria > 0
            lecturas = [
                ("eolico", round(110 + 9 * sin(2 * fase), 2) if eolica else "", 12 if eolica else 0, corriente_eolica, round(viento_simulado, 2) if eolica else "", ""),
                ("fotovoltaico", "", 12 if solar else 0, corriente_solar, "", round(sol_simulado, 2) if solar else ""),
                ("bateria", "", 12.6, corriente_bateria, "", ""),
                ("carga", "", 12, 1.67, "", ""),
            ]
            for punto, rpm, voltios, amperios, viento, irradiancia in lecturas:
                contador += 1
                writer.writerow([f"M{contador:05d}", ensayo_id, momento, punto, rpm, voltios, amperios, "", "", viento, irradiancia])

# Archivo deliberadamente incorrecto para mostrar la validación.
with (OUT / "mediciones_con_error.csv").open("w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(campos)
    writer.writerow(["ERR-01", "SIM-EOL-01", "2026-11-07 10:00:00", "carga", "", "dato_invalido", "1.67", "", "", "", ""])

print(f"Datos simulados creados en: {OUT}")
