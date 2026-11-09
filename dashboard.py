"""Componente TWIND42 (Streamlit Custom Components V2): diagrama energético animado,
KPI e indicadores del Dashboard. Módulo compartido entre app.py y dashboard_prototipo.py
para que ambos usen exactamente la misma identidad visual aprobada en FASE 1.

No contiene fórmulas propias: todos los valores que recibe ya fueron calculados por
procesar.py. Este módulo solo los organiza en el formato que consume el componente.
"""
import base64
from pathlib import Path

import streamlit as st

PUNTOS = ["eolico", "fotovoltaico", "bateria", "carga"]
COLOR_CLASE = {"eolico": "c-cian", "fotovoltaico": "c-verde", "bateria": "c-violeta", "carga": "c-ambar"}
# Equivalencia entre el modo_operacion del ensayo (como viene en ensayos.csv) y las
# claves de escenarios.MODOS, para saber si el escenario elegido coincide exactamente
# con el ensayo de referencia sin ninguna escala aplicada.
_EQUIV_MODO_ENSAYO = {"hibrido": "hibrido", "eolico": "eolico", "fotovoltaico": "solar"}


def imagen_base64(ruta: Path) -> str:
    return base64.b64encode(ruta.read_bytes()).decode("ascii")


def payload_desde_datos(logo_b64, eid, modo, datos, balance_fila, snapshot_min=None, controles=None):
    """Arma el payload del componente a partir de datos YA calculados por procesar.py
    (o, si se usa junto con escenarios.py, de una variante derivada de esos datos).

    datos: filas de mediciones_procesadas de un solo ensayo (columnas fecha_hora,
        punto_medido, potencia_w, energia_wh).
    balance_fila: fila (o dict) con fuentes_wh/carga_wh/bateria_wh/residuo_wh.
    snapshot_min: si se indica, usa el instante más cercano a ese minuto para las
        potencias instantáneas; si no, usa el último instante disponible.
    controles: dict opcional {"modo": "hibrido"|"eolico"|"solar", "nivel": 100|50|1}
        con la selección activa de escenario simulado, para resaltar los botones
        correspondientes y graduar la intensidad visual de las fuentes.
    """
    datos = datos.copy()
    datos["minutos"] = (datos["fecha_hora"] - datos["fecha_hora"].min()).dt.total_seconds() / 60

    if snapshot_min is None:
        instante = datos["fecha_hora"].max()
    else:
        instante = datos.iloc[(datos["minutos"] - snapshot_min).abs().argsort().iloc[0]]["fecha_hora"]
    muestra = datos[datos["fecha_hora"] == instante].set_index("punto_medido")
    potencias = {p: float(muestra.loc[p, "potencia_w"]) if p in muestra.index else 0.0 for p in PUNTOS}
    # Energía acumulada (ya calculada por procesar.py) en el mismo instante que las
    # potencias de arriba: se usa en los tooltips del diagrama, sin inventar ni
    # interpolar nada nuevo.
    energias = {p: float(muestra.loc[p, "energia_wh"]) if p in muestra.index else 0.0 for p in PUNTOS}

    # Series ya calculadas por procesar.py, sub-muestreadas a ~60 puntos como mucho solo
    # para aligerar las minigráficas; los valores en sí no se modifican ni se inventan.
    series = {}
    for p in PUNTOS:
        serie_p = datos[datos["punto_medido"] == p].sort_values("minutos")
        paso = max(1, len(serie_p) // 60) if len(serie_p) else 1
        serie_p = serie_p.iloc[::paso]
        series[p] = {
            "t": serie_p["minutos"].round(1).tolist(),
            "potencia": serie_p["potencia_w"].round(3).tolist(),
            "energia": serie_p["energia_wh"].round(4).tolist(),
        }

    payload = {
        "logo_b64": logo_b64,
        "id_ensayo": eid,
        "modo": modo,
        "snapshot_min": round(float(muestra["minutos"].iloc[0]), 1),
        "potencias": potencias,
        "energias": energias,
        "balance": {"fuentes": float(balance_fila["fuentes_wh"]), "carga": float(balance_fila["carga_wh"]),
                    "bateria": float(balance_fila["bateria_wh"]), "residuo": float(balance_fila["residuo_wh"])},
        "series": series,
        "colores": COLOR_CLASE,
    }
    if controles is not None:
        es_base = controles["nivel"] == 100 and _EQUIV_MODO_ENSAYO.get(modo) == controles["modo"]
        payload["controles"] = {"modo": controles["modo"], "nivel": controles["nivel"], "es_base": es_base}
    return payload


HTML = """
<div class="tw-dash" data-motion="auto">
  <header class="tw-head">
    <div class="tw-brand">
      <img class="tw-logo" alt="TWIND42" />
      <div class="tw-brand-text">
        <span class="tw-name">TWIND42</span>
        <span class="tw-sub">Centro de monitoreo energético</span>
      </div>
    </div>
    <div class="tw-head-right">
      <span class="tw-badge">DEMO · DATOS SIMULADOS</span>
      <span class="tw-ensayo v-ensayo-ref"></span>
      <button class="tw-motion-btn" type="button">⏸ Pausar flujo</button>
    </div>
  </header>

  <section class="tw-controles">
    <span class="tw-escenario-badge">ESCENARIO SIMULADO — Datos derivados de ensayos de referencia</span>
    <span class="tw-ensayo tw-ensayo-escenario v-ensayo-escenario"></span>
    <div class="tw-control-grupo">
      <span class="tw-control-label">Modo</span>
      <div class="tw-segmentado" data-grupo="modo">
        <button type="button" data-valor="hibrido">Híbrido</button>
        <button type="button" data-valor="eolico">Eólico</button>
        <button type="button" data-valor="solar">Solar</button>
      </div>
    </div>
    <div class="tw-control-grupo">
      <span class="tw-control-label">Nivel</span>
      <div class="tw-segmentado" data-grupo="nivel">
        <button type="button" data-valor="100">100%</button>
        <button type="button" data-valor="50">50%</button>
        <button type="button" data-valor="1">1%</button>
      </div>
    </div>
  </section>

  <section class="tw-flow-card">
    <div class="tw-node-tags" role="group" aria-label="Nodos del diagrama energético: tocá o enfocá cada uno para ver su función y sus valores">
      <button type="button" class="tw-node-tag" data-nodo="eolico" aria-describedby="tw-tip">
        <i class="dot c-cian" aria-hidden="true"></i>Generación eólica
      </button>
      <button type="button" class="tw-node-tag" data-nodo="fotovoltaico" aria-describedby="tw-tip">
        <i class="dot c-verde" aria-hidden="true"></i>Generación fotovoltaica
      </button>
      <button type="button" class="tw-node-tag" data-nodo="distribucion" aria-describedby="tw-tip">
        <i class="dot c-sec" aria-hidden="true"></i>Distribución energética
      </button>
      <button type="button" class="tw-node-tag" data-nodo="bateria" aria-describedby="tw-tip">
        <i class="dot c-violeta" aria-hidden="true"></i><span class="v-tagname-bateria">Batería</span>
      </button>
      <button type="button" class="tw-node-tag" data-nodo="carga" aria-describedby="tw-tip">
        <i class="dot c-ambar" aria-hidden="true"></i><span class="v-tagname-carga">Carga LED</span>
      </button>
    </div>
    <div class="tw-tip" id="tw-tip" role="tooltip" hidden></div>
    <svg class="tw-flow" viewBox="0 0 760 240" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
      <path class="tw-path" data-path="eolico" d="M118,66 C250,66 250,120 368,120"></path>
      <path class="tw-path" data-path="fotovoltaico" d="M118,174 C250,174 250,120 368,120"></path>
      <path class="tw-path" data-path="bateria" d="M372,120 C490,120 490,58 622,58"></path>
      <path class="tw-path" data-path="carga" d="M372,120 C490,120 490,182 622,182"></path>

      <g class="tw-node" transform="translate(90,66)">
        <title data-title="eolico"></title>
        <circle r="34" class="tw-node-bg"></circle>
        <line x1="0" y1="26" x2="0" y2="40" class="tw-pole"></line>
        <g class="tw-blades" data-blades="eolico">
          <line x1="0" y1="0" x2="0" y2="-20"></line>
          <line x1="0" y1="0" x2="17.3" y2="10"></line>
          <line x1="0" y1="0" x2="-17.3" y2="10"></line>
        </g>
      </g>

      <g class="tw-node" transform="translate(90,174)">
        <title data-title="fotovoltaico"></title>
        <circle r="34" class="tw-node-bg"></circle>
        <g class="tw-glow" data-glow="fotovoltaico">
          <rect x="-16" y="-12" width="32" height="24" rx="3" class="tw-panel"></rect>
          <line x1="-16" y1="-4" x2="16" y2="-4"></line>
          <line x1="-16" y1="4" x2="16" y2="4"></line>
          <line x1="-6" y1="-12" x2="-6" y2="12"></line>
          <line x1="6" y1="-12" x2="6" y2="12"></line>
        </g>
      </g>

      <g class="tw-node tw-hub" transform="translate(370,120)">
        <title data-title="distribucion"></title>
        <circle r="18" class="tw-node-bg"></circle>
      </g>

      <g class="tw-node" transform="translate(644,58)">
        <title data-title="bateria"></title>
        <circle r="34" class="tw-node-bg"></circle>
        <rect x="-14" y="-18" width="28" height="36" rx="5" class="tw-bateria-cuerpo"></rect>
        <rect x="-5" y="-23" width="10" height="5" rx="1" class="tw-bateria-cuerpo"></rect>
        <path class="tw-bateria-flecha" data-flecha="bateria" d="M0,10 L0,-10 M-6,-4 L0,-10 L6,-4"></path>
      </g>

      <g class="tw-node" transform="translate(644,182)">
        <title data-title="carga"></title>
        <circle r="34" class="tw-node-bg"></circle>
        <circle r="12" cy="-2" class="tw-bulbo" data-bulbo="carga"></circle>
        <line x1="-5" y1="10" x2="5" y2="10" class="tw-bulbo-base"></line>
        <line x1="-7" y1="14" x2="7" y2="14" class="tw-bulbo-base"></line>
      </g>
    </svg>
    <p class="tw-flow-caption">Instantánea simulada · minuto <b class="v-min"></b> del ensayo (no es una medición en tiempo real)</p>
  </section>

  <section class="tw-kpis">
    <div class="tw-kpi" data-accent="c-cian"><span class="l">Potencia eólica</span><span class="v v-pot-eolico"></span></div>
    <div class="tw-kpi" data-accent="c-verde"><span class="l">Potencia fotovoltaica</span><span class="v v-pot-fotovoltaico"></span></div>
    <div class="tw-kpi" data-accent="c-violeta">
      <span class="l v-lbl-bateria">Potencia batería</span><span class="v v-pot-bateria"></span><span class="tag v-tag-bateria"></span>
      <span class="tw-aclaracion v-aclaracion-bateria"></span>
    </div>
    <div class="tw-kpi" data-accent="c-ambar"><span class="l v-lbl-carga">Potencia carga LED</span><span class="v v-pot-carga"></span></div>
  </section>

  <section class="tw-lower">
    <div class="tw-card">
      <h4>Evolución de potencia (W)</h4>
      <div class="tw-chart-legend">
        <span><i class="dot c-cian"></i>Eólico</span>
        <span><i class="dot c-verde"></i>Fotovoltaico</span>
        <span><i class="dot c-violeta"></i>Batería</span>
        <span><i class="dot c-ambar"></i>Carga LED</span>
      </div>
      <svg class="tw-spark" data-series="potencia" viewBox="0 0 300 128" preserveAspectRatio="none" tabindex="0" role="img"
           aria-label="Gráfico de evolución de potencia en vatios. Se puede recorrer con el mouse o con las flechas izquierda y derecha del teclado."></svg>
      <p class="tw-chart-readout" data-readout="potencia">Pasá el cursor o enfocá el gráfico para ver los valores puntuales.</p>
    </div>
    <div class="tw-card">
      <h4>Energía acumulada (Wh)</h4>
      <div class="tw-chart-legend">
        <span><i class="dot c-cian"></i>Eólico</span>
        <span><i class="dot c-verde"></i>Fotovoltaico</span>
        <span><i class="dot c-violeta"></i>Batería</span>
        <span><i class="dot c-ambar"></i>Carga LED</span>
      </div>
      <svg class="tw-spark" data-series="energia" viewBox="0 0 300 128" preserveAspectRatio="none" tabindex="0" role="img"
           aria-label="Gráfico de energía acumulada en watt-hora. Se puede recorrer con el mouse o con las flechas izquierda y derecha del teclado."></svg>
      <p class="tw-chart-readout" data-readout="energia">Pasá el cursor o enfocá el gráfico para ver los valores puntuales.</p>
    </div>
    <div class="tw-card tw-balance">
      <h4>Balance energético (Wh)</h4>
      <div class="tw-bar">
        <span class="seg c-ambar" data-seg="carga"></span>
        <span class="seg c-violeta" data-seg="bateria"></span>
        <span class="seg c-sec" data-seg="residuo"></span>
      </div>
      <ul class="tw-bal-list">
        <li><i class="dot c-cian"></i>Fuentes <b class="v-bal-fuentes"></b></li>
        <li><i class="dot c-ambar"></i>Carga <b class="v-bal-carga"></b></li>
        <li><i class="dot c-violeta"></i>Batería <b class="v-bal-bateria"></b></li>
        <li><i class="dot c-sec" data-dot="residuo"></i><span class="lbl-residuo">Residuo</span> <b class="v-bal-residuo"></b></li>
      </ul>
      <p class="tw-aclaracion v-aclaracion-residuo"></p>
    </div>
  </section>
  <p class="tw-legend-colors">
    <span><i class="dot c-cian"></i>Eólico</span>
    <span><i class="dot c-verde"></i>Fotovoltaico</span>
    <span><i class="dot c-violeta"></i>Batería</span>
    <span><i class="dot c-ambar"></i>Carga LED</span>
  </p>
</div>
"""

CSS = """
:host, .tw-dash { all: initial; }
.tw-dash {
    --fondo:#080F21; --panel:#111E34; --panel-2:#16263d; --texto:#F4F7FC; --texto-sec:#A8B7CB;
    --cian:#27D3F1; --verde:#5CE3A0; --violeta:#A685FA; --ambar:#F2B134; --alerta:#F2546B;
    display:block; font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif; color:var(--texto);
    background:var(--fondo); border:1px solid rgba(39,211,241,0.18); border-radius:16px; padding:18px 20px 22px;
    box-sizing:border-box; container-type:inline-size; container-name:twdash;
}
.tw-dash * { box-sizing:border-box; }
.tw-dash .c-cian { color:var(--cian); } .tw-dash .c-verde { color:var(--verde); }
.tw-dash .c-violeta { color:var(--violeta); } .tw-dash .c-ambar { color:var(--ambar); }
.tw-dash .c-alerta { color:var(--alerta); } .tw-dash .c-sec { color:var(--texto-sec); }
.tw-dash .dot { display:inline-block; width:9px; height:9px; border-radius:50%; background:currentColor; margin-right:6px; vertical-align:middle; }

.tw-head { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:10px; margin-bottom:14px; }
.tw-brand { display:flex; align-items:center; gap:10px; }
.tw-logo { height:30px; width:auto; display:block; border-radius:6px; }
.tw-brand-text { display:flex; flex-direction:column; line-height:1.15; }
.tw-name { font-weight:800; letter-spacing:.04em; font-size:1rem; }
.tw-sub { font-size:.72rem; color:var(--texto-sec); }
.tw-head-right { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
.tw-badge { background:rgba(242,177,52,0.15); color:var(--ambar); border:1px solid rgba(242,177,52,0.4);
    font-size:.68rem; font-weight:700; letter-spacing:.03em; padding:4px 8px; border-radius:999px; }
.tw-ensayo { background:var(--panel-2); color:var(--texto-sec); font-size:.72rem; padding:4px 10px; border-radius:999px; border:1px solid rgba(168,183,203,0.2); }
.tw-ensayo-escenario { color:var(--violeta); border-color:rgba(166,133,250,0.35); font-weight:600; }
.tw-motion-btn { background:var(--panel-2); color:var(--texto-sec); border:1px solid rgba(168,183,203,0.25);
    font-size:.72rem; padding:5px 10px; border-radius:8px; cursor:pointer; }
.tw-motion-btn:hover { color:var(--texto); border-color:var(--cian); }

.tw-controles { display:flex; align-items:center; gap:14px; flex-wrap:wrap; margin-bottom:14px; }
.tw-escenario-badge { background:rgba(166,133,250,0.15); color:var(--violeta); border:1px solid rgba(166,133,250,0.4);
    font-size:.64rem; font-weight:700; letter-spacing:.02em; padding:4px 8px; border-radius:999px; }
.tw-control-grupo { display:flex; align-items:center; gap:7px; }
.tw-control-label { font-size:.68rem; color:var(--texto-sec); text-transform:uppercase; letter-spacing:.04em; }
.tw-segmentado { display:flex; background:var(--panel-2); border:1px solid rgba(168,183,203,0.18); border-radius:8px; padding:2px; gap:2px; }
.tw-segmentado button { background:transparent; border:none; color:var(--texto-sec); font-size:.72rem; font-weight:600;
    padding:4px 10px; border-radius:6px; cursor:pointer; font-family:inherit; }
.tw-segmentado button:hover { color:var(--texto); }
.tw-segmentado button.activo { background:var(--cian); color:#06131f; }

.tw-flow-card { background:var(--panel); border:1px solid rgba(39,211,241,0.15); border-radius:14px; padding:6px 10px 2px; margin-bottom:14px; position:relative; }
.tw-flow { width:100%; height:auto; display:block; max-height:230px; }
.tw-flow-caption { text-align:center; font-size:.7rem; color:var(--texto-sec); margin:2px 0 8px; }

.tw-node-tags { display:flex; flex-wrap:wrap; gap:6px; justify-content:center; margin:6px 0 8px; }
.tw-node-tag { display:inline-flex; align-items:center; gap:6px; background:var(--panel-2); border:1px solid rgba(168,183,203,0.22);
    color:var(--texto-sec); font-family:inherit; font-size:.68rem; font-weight:600; padding:5px 9px; border-radius:999px; cursor:pointer; }
.tw-node-tag:hover, .tw-node-tag:focus-visible { color:var(--texto); border-color:var(--cian); }
.tw-node-tag:focus-visible { outline:2px solid var(--cian); outline-offset:2px; }
.tw-node-tag.referencia { border-color:rgba(242,84,107,0.55); border-style:dashed; }
.tw-node-tag.referencia .dot { box-shadow:0 0 0 2px rgba(242,84,107,0.35); }
.tw-tip { position:absolute; z-index:5; max-width:230px; background:#0c1830; color:var(--texto); border:1px solid rgba(39,211,241,0.35);
    border-radius:8px; padding:8px 10px; font-size:.7rem; line-height:1.35; box-shadow:0 6px 18px rgba(0,0,0,0.35); pointer-events:none; }
.tw-tip[hidden] { display:none; }

.tw-path { fill:none; stroke-width:4; stroke:#2a3a52; stroke-linecap:round; opacity:.4; transition:opacity .3s, stroke .3s; }
.tw-path.active { opacity:1; stroke-dasharray:9 7; animation:tw-flow .9s linear infinite; }
.tw-path.active.c-cian { stroke:var(--cian); } .tw-path.active.c-verde { stroke:var(--verde); }
.tw-path.active.c-violeta { stroke:var(--violeta); } .tw-path.active.c-ambar { stroke:var(--ambar); }
.tw-path.reverse { animation-direction:reverse; }
@keyframes tw-flow { to { stroke-dashoffset:-32; } }

.tw-node-bg { fill:var(--panel-2); stroke:rgba(244,247,252,0.12); stroke-width:1; }
.tw-pole { stroke:#5a6b84; stroke-width:3; }
.tw-blades line { stroke:#5a6b84; stroke-width:3; stroke-linecap:round; transition:stroke .3s; }
.tw-blades { transform-origin:0px 0px; animation:tw-spin 2.1s linear infinite; animation-play-state:paused; }
.tw-blades.activo line { stroke:var(--cian); }
.tw-blades.activo { animation-play-state:running; }
@keyframes tw-spin { to { transform:rotate(360deg); } }

.tw-panel { fill:#243550; stroke:#5a6b84; stroke-width:1.5; }
.tw-glow line { stroke:#5a6b84; stroke-width:1.2; }
.tw-glow.activo .tw-panel { fill:rgba(92,227,160,0.18); stroke:var(--verde); }
.tw-glow.activo line { stroke:var(--verde); }
.tw-glow.activo { animation:tw-pulse 2.4s ease-in-out infinite; }
@keyframes tw-pulse { 0%,100% { opacity:.75; } 50% { opacity:1; } }

.tw-bateria-cuerpo { fill:#243550; stroke:#5a6b84; stroke-width:1.5; }
.tw-bateria-flecha { stroke:#5a6b84; stroke-width:2.4; fill:none; stroke-linecap:round; stroke-linejoin:round; }
.tw-bateria-flecha.cargando { stroke:var(--violeta); }
.tw-bateria-flecha.descargando { stroke:var(--violeta); transform:rotate(180deg); transform-origin:center; }

.tw-bulbo { fill:#243550; stroke:#5a6b84; stroke-width:1.5; }
.tw-bulbo-base { stroke:#5a6b84; stroke-width:2; }
.tw-bulbo.activo { fill:rgba(242,177,52,0.35); stroke:var(--ambar); }

[data-motion="paused"] .tw-path.active, [data-motion="paused"] .tw-blades, [data-motion="paused"] .tw-glow.activo {
    animation-play-state:paused !important;
}
@media (prefers-reduced-motion: reduce) {
    .tw-path.active, .tw-blades, .tw-glow.activo { animation:none !important; }
}

.tw-kpis { display:grid; grid-template-columns:repeat(4, minmax(130px,1fr)); gap:12px; margin-bottom:14px; }
.tw-kpi { background:var(--panel); border:1px solid rgba(168,183,203,0.14); border-radius:12px; padding:12px 14px;
    border-top:3px solid var(--cian); display:flex; flex-direction:column; gap:4px; position:relative; }
.tw-kpi[data-accent="c-verde"] { border-top-color:var(--verde); }
.tw-kpi[data-accent="c-violeta"] { border-top-color:var(--violeta); }
.tw-kpi[data-accent="c-ambar"] { border-top-color:var(--ambar); }
.tw-kpi .l { font-size:.68rem; text-transform:uppercase; letter-spacing:.04em; color:var(--texto-sec); }
.tw-kpi .v { font-size:1.35rem; font-weight:700; }
.tw-kpi .tag { font-size:.66rem; color:var(--texto-sec); }
.tw-aclaracion { display:block; font-size:.64rem; color:var(--texto-sec); font-style:italic; margin-top:4px; line-height:1.3; }

.tw-lower { display:grid; grid-template-columns:repeat(3, minmax(190px,1fr)); gap:12px; }
.tw-card { background:var(--panel); border:1px solid rgba(168,183,203,0.14); border-radius:12px; padding:10px 14px 12px; }
.tw-card h4 { margin:0 0 6px; font-size:.78rem; color:var(--texto-sec); font-weight:600; }
.tw-chart-legend { display:flex; flex-wrap:wrap; gap:8px; font-size:.62rem; color:var(--texto-sec); margin-bottom:4px; }
.tw-chart-legend .dot { margin-right:3px; }
.tw-spark { width:100%; height:92px; display:block; }
.tw-spark:focus-visible { outline:2px solid var(--cian); outline-offset:2px; border-radius:4px; }
.tw-spark polyline { fill:none; stroke-width:2; }
.tw-spark .tw-axis-text { font-size:9px; fill:var(--texto-sec); opacity:.75; }
.tw-spark .tw-crosshair { stroke:rgba(168,183,203,0.45); stroke-width:1; }
.tw-spark .tw-crosshair-dot { stroke:var(--fondo); stroke-width:1; }
.tw-chart-readout { margin:6px 0 0; font-size:.66rem; color:var(--texto-sec); min-height:1.3em; }

.tw-bar { display:flex; height:14px; border-radius:7px; overflow:hidden; background:#0c1830; margin-bottom:10px; }
.tw-bar .seg { height:100%; }
.tw-bar .c-ambar { background:var(--ambar); } .tw-bar .c-violeta { background:var(--violeta); } .tw-bar .c-sec { background:var(--texto-sec); }
.tw-bar .c-verde { background:var(--verde); } .tw-bar .c-alerta { background:var(--alerta); }
.tw-bal-list .lbl-residuo { font-weight:600; }
.tw-bal-list { list-style:none; margin:0; padding:0; font-size:.78rem; display:flex; flex-direction:column; gap:5px; }
.tw-bal-list b { float:right; }

.tw-legend-colors { display:flex; gap:16px; flex-wrap:wrap; font-size:.7rem; color:var(--texto-sec); margin:12px 2px 0; }

@container twdash (max-width:780px) {
    .tw-kpis { grid-template-columns:repeat(2, 1fr); }
    .tw-lower { grid-template-columns:1fr; }
    .tw-flow { max-height:190px; }
    .tw-head { flex-direction:column; align-items:flex-start; }
}
@container twdash (max-width:460px) {
    .tw-kpis { grid-template-columns:1fr 1fr; }
    .tw-kpi .v { font-size:1.1rem; }
    .tw-head-right { width:100%; justify-content:space-between; }
    .tw-controles { flex-direction:column; align-items:flex-start; gap:8px; }
    .tw-node-tag { font-size:.62rem; padding:4px 7px; }
    .tw-chart-legend { gap:6px; }
}
"""

JS = """
export default function (component) {
    const { data, parentElement, setStateValue } = component;
    const el = parentElement.querySelector('.tw-dash');
    const q = (sel) => el.querySelector(sel);
    const qa = (sel) => Array.from(el.querySelectorAll(sel));

    el.querySelector('.tw-logo').src = 'data:image/png;base64,' + data.logo_b64;
    q('.v-min').textContent = data.snapshot_min;

    // Controles de escenario simulado (modo de generación / nivel de potencia).
    const controles = data.controles || { modo: 'hibrido', nivel: 100 };
    const NOMBRE_MODO = { hibrido: 'Híbrido', eolico: 'Eólico', solar: 'Solar' };

    // El ensayo de referencia (dato real cargado) y el escenario simulado (modo/nivel
    // elegidos) se muestran por separado: elegir un modo nunca cambia el ensayo base.
    q('.v-ensayo-ref').textContent = 'Ensayo de referencia: ' + data.id_ensayo;
    q('.v-ensayo-escenario').textContent = 'Escenario seleccionado: '
        + (NOMBRE_MODO[controles.modo] || controles.modo) + ' · ' + controles.nivel + '%';
    el.querySelectorAll('.tw-segmentado').forEach((grupo) => {
        const nombre = grupo.getAttribute('data-grupo');
        const actual = String(controles[nombre]);
        grupo.querySelectorAll('button').forEach((boton) => {
            boton.classList.toggle('activo', boton.getAttribute('data-valor') === actual);
            boton.onclick = () => {
                const valor = boton.getAttribute('data-valor');
                setStateValue(nombre, nombre === 'nivel' ? Number(valor) : valor);
            };
        });
    });
    const eolicoHabilitado = controles.modo !== 'solar';
    const solarHabilitado = controles.modo !== 'eolico';
    const nivelFactor = controles.nivel / 100;
    const esBase = data.controles ? !!data.controles.es_base : true;

    const fmtW = (v) => (v >= 0 ? '+' : '') + v.toFixed(2) + ' W';
    const fmtWh = (v) => v.toFixed(2) + ' Wh';
    const pot = data.potencias;

    q('.v-pot-eolico').textContent = pot.eolico.toFixed(2) + ' W';
    q('.v-pot-fotovoltaico').textContent = pot.fotovoltaico.toFixed(2) + ' W';
    q('.v-pot-carga').textContent = pot.carga.toFixed(2) + ' W';
    q('.v-pot-bateria').textContent = fmtW(pot.bateria);
    q('.v-tag-bateria').textContent = pot.bateria > 0 ? 'Cargando' : (pot.bateria < 0 ? 'Descargando' : 'Sin intercambio');

    // La batería nunca se recalcula al escalar un escenario (ver escenarios.py): fuera
    // del escenario base, el valor mostrado sigue siendo el medido en el ensayo original.
    q('.v-lbl-bateria').textContent = esBase ? 'Potencia batería' : 'Batería de referencia';
    q('.v-aclaracion-bateria').textContent = esBase ? '' : 'Valor del ensayo original · No recalculado';

    const bal = data.balance;
    q('.v-bal-fuentes').textContent = fmtWh(bal.fuentes);
    q('.v-bal-carga').textContent = fmtWh(bal.carga);
    q('.v-bal-bateria').textContent = fmtWh(bal.bateria);

    // El residuo (fuentes - carga - batería medida) es un desbalance HIPOTÉTICO: el
    // modelo no reinterpreta la batería ni la carga para "cerrarlo", solo expone la
    // cuenta tal cual queda al escalar las fuentes. No representa una descarga real de
    // batería (déficit) ni energía efectivamente almacenada (excedente).
    const residuo = bal.residuo;
    const umbral = 0.05;
    const hayDeficit = residuo < -umbral;
    const hayExcedente = residuo > umbral;
    const etiquetaResiduo = q('.lbl-residuo');
    const puntoResiduo = q('[data-dot="residuo"]');
    const segResiduo = q('[data-seg="residuo"]');
    const aclaracionResiduo = q('.v-aclaracion-residuo');
    let claseResiduo = 'c-sec';
    let texto = 'Balance equilibrado';
    if (hayDeficit) { claseResiduo = 'c-alerta'; texto = 'Déficit de balance'; }
    else if (hayExcedente) { claseResiduo = 'c-verde'; texto = 'Excedente de balance'; }
    etiquetaResiduo.textContent = texto;
    puntoResiduo.className = 'dot ' + claseResiduo;
    segResiduo.className = 'seg ' + claseResiduo;
    q('.v-bal-residuo').textContent = fmtWh(Math.abs(residuo));
    aclaracionResiduo.textContent = (hayDeficit || hayExcedente)
        ? 'Desbalance hipotético respecto de la carga y batería del ensayo de referencia'
        : '';

    // Si la generación escalada no alcanza a cubrir carga + batería, el diagrama no debe
    // sugerir que el LED recibe toda su demanda: se relabela como demanda de referencia.
    q('.v-lbl-carga').textContent = hayDeficit ? 'Demanda de referencia' : 'Potencia carga LED';

    const totalBar = Math.max(bal.carga + Math.abs(bal.bateria) + Math.abs(residuo), 0.0001);
    q('[data-seg="carga"]').style.width = (100 * bal.carga / totalBar) + '%';
    q('[data-seg="bateria"]').style.width = (100 * Math.abs(bal.bateria) / totalBar) + '%';
    segResiduo.style.width = (100 * Math.abs(residuo) / totalBar) + '%';

    // Activar / colorear las líneas y los íconos según la potencia real de cada punto.
    const activo = (v) => Math.abs(v) > 0.01;

    // La intensidad visual (opacidad) de una fuente habilitada baja con el nivel de
    // generación simulado, para distinguir "apagada por el modo" de "encendida pero baja".
    const intensidad = 0.3 + 0.7 * nivelFactor;

    const eolicoActivo = eolicoHabilitado && activo(pot.eolico);
    const pathEolico = q('[data-path="eolico"]');
    pathEolico.classList.toggle('active', eolicoActivo);
    pathEolico.classList.toggle('c-cian', eolicoActivo);
    pathEolico.style.opacity = eolicoActivo ? intensidad : '';
    const blades = q('[data-blades="eolico"]');
    blades.classList.toggle('activo', eolicoActivo);
    blades.style.opacity = eolicoActivo ? intensidad : '';

    const solarActivo = solarHabilitado && activo(pot.fotovoltaico);
    const pathSolar = q('[data-path="fotovoltaico"]');
    pathSolar.classList.toggle('active', solarActivo);
    pathSolar.classList.toggle('c-verde', solarActivo);
    pathSolar.style.opacity = solarActivo ? intensidad : '';
    const glow = q('[data-glow="fotovoltaico"]');
    glow.classList.toggle('activo', solarActivo);
    glow.style.opacity = solarActivo ? intensidad : '';

    const pathCarga = q('[data-path="carga"]');
    pathCarga.classList.toggle('active', activo(pot.carga));
    pathCarga.classList.toggle('c-ambar', activo(pot.carga));
    q('[data-bulbo="carga"]').classList.toggle('activo', activo(pot.carga));

    const pathBateria = q('[data-path="bateria"]');
    pathBateria.classList.toggle('active', activo(pot.bateria));
    pathBateria.classList.toggle('c-violeta', activo(pot.bateria));
    pathBateria.classList.toggle('reverse', pot.bateria < 0);
    const flecha = q('[data-flecha="bateria"]');
    flecha.classList.toggle('cargando', pot.bateria > 0);
    flecha.classList.toggle('descargando', pot.bateria < 0);

    // Etiquetas y tooltips de los 5 nodos del diagrama (eólico, fotovoltaico,
    // distribución, batería, carga LED). Reutilizan los mismos potencias/energias/
    // balance ya calculados arriba; no inventan ni interpolan ningún valor.
    const energias = data.energias || { eolico: 0, fotovoltaico: 0, bateria: 0, carga: 0 };
    const fmtWAbs = (v) => v.toFixed(2) + ' W';
    const estadoBateria = pot.bateria > 0 ? 'cargando' : (pot.bateria < 0 ? 'descargando' : 'sin intercambio');
    const nombreBateria = esBase ? 'Batería' : 'Batería de referencia';
    const nombreCarga = hayDeficit ? 'Demanda de referencia' : 'Carga LED';
    q('.v-tagname-bateria').textContent = nombreBateria;
    q('.v-tagname-carga').textContent = nombreCarga;

    // Nota IMPORTANTE: en un escenario con déficit, lo que el diagrama muestra hacia la
    // carga y la batería son los valores MEDIDOS del ensayo de referencia (nunca se
    // recalculan), no un suministro efectivo garantizado por la generación escalada.
    const descripciones = {
        eolico: 'Generación eólica — turbina eólica simulada. Potencia instantánea: ' + fmtWAbs(pot.eolico)
            + ' · Energía acumulada: ' + fmtWh(energias.eolico) + ' (minuto ' + data.snapshot_min + ').',
        fotovoltaico: 'Generación fotovoltaica — panel solar simulado. Potencia instantánea: ' + fmtWAbs(pot.fotovoltaico)
            + ' · Energía acumulada: ' + fmtWh(energias.fotovoltaico) + ' (minuto ' + data.snapshot_min + ').',
        distribucion: 'Distribución energética — reparte la generación eólica y fotovoltaica simuladas hacia la batería y la carga LED.'
            + ' Generación total instantánea: ' + fmtWAbs(pot.eolico + pot.fotovoltaico) + '.'
            + (hayDeficit ? ' En este escenario la generación no alcanza a cubrir la demanda: lo que llega a batería y carga es un valor de referencia, no un suministro efectivo garantizado.' : ''),
        bateria: nombreBateria + ' — intercambio de energía con la batería del ensayo (' + estadoBateria + ').'
            + ' Potencia: ' + fmtW(pot.bateria) + ' · Energía acumulada: ' + fmtWh(energias.bateria) + '.'
            + (esBase ? '' : ' Valor del ensayo de referencia, no recalculado para este escenario simulado.')
            + (hayDeficit ? ' En un escenario con déficit no debe interpretarse como una descarga efectiva garantizada.' : ''),
        carga: nombreCarga + ' — consumo simulado de la carga LED.'
            + ' Potencia: ' + fmtWAbs(pot.carga) + ' · Energía acumulada: ' + fmtWh(energias.carga) + '.'
            + (hayDeficit ? ' En este escenario la generación simulada no alcanza a cubrir esta demanda: el valor no representa un suministro efectivo garantizado.' : ''),
    };

    qa('.tw-node-tag').forEach((boton) => {
        const nodo = boton.getAttribute('data-nodo');
        boton.classList.toggle('referencia', hayDeficit && nodo !== 'eolico' && nodo !== 'fotovoltaico');
        const titulo = el.querySelector('[data-title="' + nodo + '"]');
        if (titulo) titulo.textContent = descripciones[nodo];
    });

    const tip = q('#tw-tip');
    const flowCard = q('.tw-flow-card');
    function mostrarTip(boton) {
        const nodo = boton.getAttribute('data-nodo');
        tip.textContent = descripciones[nodo];
        tip.hidden = false;
        const rb = boton.getBoundingClientRect();
        const rc = flowCard.getBoundingClientRect();
        const maxLeft = Math.max(8, rc.width - tip.offsetWidth - 8);
        const left = Math.min(Math.max(8, rb.left - rc.left), maxLeft);
        tip.style.left = left + 'px';
        // Se ubica arriba del chip si hay lugar; si no (por ejemplo, con la barra
        // pegada al borde superior de la tarjeta), se ubica debajo.
        const arriba = rb.top - rc.top - tip.offsetHeight - 8;
        tip.style.top = (arriba >= 4 ? arriba : rb.bottom - rc.top + 8) + 'px';
    }
    function ocultarTip() { tip.hidden = true; }
    qa('.tw-node-tag').forEach((boton) => {
        boton.addEventListener('mouseenter', () => mostrarTip(boton));
        boton.addEventListener('focus', () => mostrarTip(boton));
        boton.addEventListener('mouseleave', ocultarTip);
        boton.addEventListener('blur', ocultarTip);
    });

    // Minigráficas de evolución: se dibujan a partir de las series ya calculadas (sub-muestreadas).
    const NOMBRE_PUNTO = { eolico: 'Eólico', fotovoltaico: 'Fotovoltaico', bateria: 'Batería', carga: 'Carga LED' };
    const colorVar = (p) => (p === 'eolico' ? '--cian' : p === 'fotovoltaico' ? '--verde' : p === 'bateria' ? '--violeta' : '--ambar');

    function dibujarSpark(svg, campo) {
        const puntos = Object.keys(data.series);
        let minV = 0, maxV = 0;
        puntos.forEach((p) => {
            data.series[p][campo].forEach((v) => { if (v < minV) minV = v; if (v > maxV) maxV = v; });
        });
        const rango = (maxV - minV) || 1;
        const w = 300, h = 100, padY = 6, ejeY = 118;
        svg.innerHTML = '';
        const coordsPorPunto = {};
        let tMax = 1;
        puntos.forEach((p) => {
            const serie = data.series[p];
            const t = serie.t;
            tMax = t[t.length - 1] || 1;
            const vals = serie[campo];
            const coords = vals.map((v, i) => [
                (t[i] / tMax) * w,
                h - padY - ((v - minV) / rango) * (h - 2 * padY),
            ]);
            coordsPorPunto[p] = coords;
            const poly = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
            poly.setAttribute('points', coords.map((c) => c[0].toFixed(1) + ',' + c[1].toFixed(1)).join(' '));
            poly.setAttribute('class', data.colores[p]);
            poly.style.stroke = getComputedStyle(el).getPropertyValue(colorVar(p));
            svg.appendChild(poly);
        });

        // Referencias de tiempo (eje X, en minutos del ensayo) y de unidad (eje Y),
        // tomadas de los datos ya calculados: no son valores inventados ni interpolados.
        const unidad = campo === 'potencia' ? 'W' : 'Wh';
        const ejeTexto = (x, y, texto, anchor) => {
            const t = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            t.setAttribute('x', x); t.setAttribute('y', y);
            t.setAttribute('text-anchor', anchor);
            t.setAttribute('class', 'tw-axis-text');
            t.textContent = texto;
            svg.appendChild(t);
        };
        ejeTexto(2, ejeY, '0 min', 'start');
        ejeTexto(w - 2, ejeY, tMax.toFixed(0) + ' min', 'end');
        ejeTexto(w - 2, padY + 8, maxV.toFixed(1) + ' ' + unidad, 'end');
        if (minV < 0) ejeTexto(w - 2, h - padY, minV.toFixed(1) + ' ' + unidad, 'end');

        // Línea y marcadores de cruce (ocultos hasta que se interactúe), para el
        // tooltip por cursor/teclado que se activa más abajo.
        const crosshair = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        crosshair.setAttribute('class', 'tw-crosshair');
        crosshair.setAttribute('y1', '0');
        crosshair.setAttribute('y2', String(h));
        crosshair.style.display = 'none';
        svg.appendChild(crosshair);
        const marcadores = {};
        puntos.forEach((p) => {
            const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            c.setAttribute('r', '3');
            c.setAttribute('class', 'tw-crosshair-dot');
            c.style.fill = getComputedStyle(el).getPropertyValue(colorVar(p));
            c.style.display = 'none';
            svg.appendChild(c);
            marcadores[p] = c;
        });

        const tArray = data.series[puntos[0]].t;
        const card = svg.closest('.tw-card');
        const readout = card ? card.querySelector('.tw-chart-readout') : null;
        const textoPorDefecto = readout ? readout.textContent : '';

        function actualizar(indice) {
            const i = Math.max(0, Math.min(indice, tArray.length - 1));
            const x = coordsPorPunto[puntos[0]][i][0];
            crosshair.setAttribute('x1', x.toFixed(1));
            crosshair.setAttribute('x2', x.toFixed(1));
            crosshair.style.display = '';
            puntos.forEach((p) => {
                const punto = coordsPorPunto[p][i];
                marcadores[p].setAttribute('cx', punto[0].toFixed(1));
                marcadores[p].setAttribute('cy', punto[1].toFixed(1));
                marcadores[p].style.display = '';
            });
            if (readout) {
                const partes = puntos.map((p) => (NOMBRE_PUNTO[p] || p) + ': ' + data.series[p][campo][i].toFixed(2) + ' ' + unidad);
                readout.textContent = 'Minuto ' + tArray[i].toFixed(1) + ' — ' + partes.join(' · ');
            }
            return i;
        }
        function ocultar() {
            crosshair.style.display = 'none';
            puntos.forEach((p) => { marcadores[p].style.display = 'none'; });
            if (readout) readout.textContent = textoPorDefecto;
        }
        // Siempre toma la muestra real más cercana al cursor/foco: nunca interpola
        // entre dos puntos ni genera un valor que no esté en la serie.
        function indicePorPosicionX(xRel) {
            let mejor = 0, mejorDist = Infinity;
            coordsPorPunto[puntos[0]].forEach((c, i) => {
                const d = Math.abs(c[0] - xRel);
                if (d < mejorDist) { mejorDist = d; mejor = i; }
            });
            return mejor;
        }

        svg.onpointermove = (ev) => {
            const rect = svg.getBoundingClientRect();
            if (rect.width <= 0) return;
            const xRel = ((ev.clientX - rect.left) / rect.width) * w;
            actualizar(indicePorPosicionX(xRel));
        };
        svg.onpointerleave = ocultar;
        let indiceFoco = tArray.length - 1;
        svg.onfocus = () => { indiceFoco = actualizar(indiceFoco); };
        svg.onblur = ocultar;
        svg.onkeydown = (ev) => {
            if (ev.key === 'ArrowRight') { ev.preventDefault(); indiceFoco = actualizar(indiceFoco + 1); }
            else if (ev.key === 'ArrowLeft') { ev.preventDefault(); indiceFoco = actualizar(indiceFoco - 1); }
        };
    }
    dibujarSpark(q('[data-series="potencia"]'), 'potencia');
    dibujarSpark(q('[data-series="energia"]'), 'energia');

    // Preferencia de movimiento reducido del sistema operativo: arranca pausado si corresponde.
    const prefiereReducido = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefiereReducido) el.dataset.motion = 'paused';

    const boton = q('.tw-motion-btn');
    boton.textContent = el.dataset.motion === 'paused' ? '▶ Reanudar flujo' : '⏸ Pausar flujo';
    boton.onclick = () => {
        const pausado = el.dataset.motion === 'paused';
        el.dataset.motion = pausado ? 'auto' : 'paused';
        boton.textContent = pausado ? '⏸ Pausar flujo' : '▶ Reanudar flujo';
    };
}
"""

dashboard_component = st.components.v2.component("twind42_dashboard", html=HTML, css=CSS, js=JS)


def render_dashboard(logo_b64, eid, modo, datos, balance_fila, ancho="stretch", snapshot_min=None,
                      controles=None, key=None):
    """Arma el payload y monta el componente. datos/balance_fila: ver payload_desde_datos().

    controles/key: si se pasan ambos, los botones de Modo/Nivel del componente quedan
    habilitados (comunicación bidireccional vía Components V2): la selección del usuario
    se guarda en st.session_state[key] = {"modo": ..., "nivel": ...} para la próxima
    ejecución. Sin key, los controles se muestran pero no disparan una actualización.
    """
    payload = payload_desde_datos(logo_b64, eid, modo, datos, balance_fila, snapshot_min, controles)
    kwargs = {}
    if key is not None and controles is not None:
        kwargs = {
            "key": key,
            "default": {"modo": controles["modo"], "nivel": controles["nivel"]},
            "on_modo_change": lambda: None,
            "on_nivel_change": lambda: None,
        }
    return dashboard_component(data=payload, width=ancho, height="content", **kwargs)
