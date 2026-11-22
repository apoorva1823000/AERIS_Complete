import base64, json, itertools
from pathlib import Path
from PIL import Image
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from core import *
from map_io import load_faculty_map_text

BASE=Path(__file__).resolve().parent
LOGO=BASE/"assets"/"aeris_circular.png"
FAV=BASE/"assets"/"favicon.png"
def b64(path):
    return base64.b64encode(Path(path).read_bytes()).decode("utf-8")
def load_aeris_spec(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

AERIS_MAP_FILES={
    "Default AERIS network": BASE/"maps"/"aeris_default.json",
    "Alternate AERIS network": BASE/"maps"/"aeris_alternate.json",
    "Large AERIS stress-test network": BASE/"maps"/"aeris_large.json",
}

LOGO_B64=b64(LOGO) if LOGO.exists() else None
PAGE_ICON=Image.open(FAV) if FAV.exists() else "A"

st.set_page_config(page_title="AERIS Medico Helper",page_icon=PAGE_ICON,layout="wide")

st.markdown("""
<style>
:root{--bg:#060c17;--bg2:#0b1426;--line:rgba(129,140,248,.18);--text:#f5f7ff;
--muted:#a9b4cb;--blue:#4f8cff;--cyan:#58d9ff;--violet:#9b7cff;}
html{scroll-behavior:smooth}
.stApp{
 background:
 linear-gradient(rgba(255,255,255,.016) 1px,transparent 1px),
 linear-gradient(90deg,rgba(255,255,255,.016) 1px,transparent 1px),
 radial-gradient(circle at 88% 4%,rgba(79,140,255,.13),transparent 25%),
 radial-gradient(circle at 5% 15%,rgba(155,124,255,.09),transparent 22%),
 linear-gradient(180deg,var(--bg),var(--bg2));
 background-size:32px 32px,32px 32px,auto,auto,auto;color:var(--text)}
.block-container{max-width:1280px;padding-top:1.15rem;padding-bottom:2rem;animation:fade .25s ease}
@keyframes fade{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:none}}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#091426,#101a31);border-right:1px solid var(--line)}
h1{font-size:clamp(2.05rem,3.2vw,3.4rem)!important;letter-spacing:-.045em!important;font-weight:800!important}
h1,h2,h3,h4,p,label,li,.stMarkdown,.stCaption,span{color:var(--text)!important;overflow-wrap:anywhere;word-break:normal}
div[data-testid="stMetricValue"]{font-size:clamp(1rem,1.7vw,1.55rem)!important;white-space:normal!important;overflow-wrap:anywhere}
div[data-testid="stMetricLabel"]{white-space:normal!important}
[data-testid="stVerticalBlock"]{min-width:0}
[data-testid="column"]{min-width:0}
.stCodeBlock, code, pre{white-space:pre-wrap!important;overflow-wrap:anywhere!important}
.panel{overflow:hidden}

.muted{color:var(--muted)!important}
.hero,.panel,.card{border:1px solid var(--line);background:linear-gradient(180deg,rgba(255,255,255,.052),rgba(255,255,255,.027));border-radius:13px}
.hero{padding:.95rem 1.05rem;margin:.2rem 0 1.1rem;position:relative;overflow:hidden}
.hero:before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:linear-gradient(var(--cyan),var(--violet))}
.panel{padding:.8rem .95rem;margin:.25rem 0 .85rem}
.card{padding:.85rem .95rem;height:100%}
.logo-orb{width:80px;height:80px;border-radius:50%;display:flex;align-items:center;justify-content:center;
border:1px solid rgba(88,217,255,.28);background:rgba(255,255,255,.025);margin:0 auto .7rem}
.logo-orb img{width:70px;height:70px;object-fit:contain;border-radius:50%}
div[data-testid="stMetric"],div[data-testid="stDataFrame"],div[data-testid="stPlotlyChart"]{
border:1px solid var(--line);border-radius:11px;background:rgba(255,255,255,.025)}
.stButton>button{border-radius:999px;border:1px solid rgba(88,217,255,.22);background:rgba(79,140,255,.07);font-weight:700}
.stButton>button[kind="primary"]{background:linear-gradient(90deg,var(--blue),var(--violet));border:none;color:white}
.pipeline{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:#dff5ff!important;
background:#07101d;border:1px solid rgba(88,217,255,.14);padding:.7rem .8rem;border-radius:9px}
.footer{text-align:center;color:var(--muted)!important;font-size:.88rem;padding-top:.8rem;margin-top:1.3rem;border-top:1px solid rgba(88,217,255,.10)}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important;scroll-behavior:auto!important}}
</style>
<style>
.center-card{
    min-height:118px;
    display:flex;
    flex-direction:column;
    align-items:center;
    justify-content:center;
    text-align:center;
    border:1px solid rgba(129,140,248,.18);
    background:linear-gradient(180deg,rgba(255,255,255,.052),rgba(255,255,255,.026));
    border-radius:14px;
    padding:1rem .85rem;
    box-shadow:0 10px 26px rgba(0,0,0,.11);
}
.center-card-label{
    width:100%;
    text-align:center;
    color:#9eb0c8 !important;
    font-size:.77rem;
    text-transform:uppercase;
    letter-spacing:.055em;
    margin-bottom:.38rem;
}
.center-card-value{
    width:100%;
    text-align:center;
    color:#f5f8ff !important;
    font-size:1.55rem;
    font-weight:700;
    line-height:1.12;
    overflow-wrap:anywhere;
}
.center-card-sub{
    width:100%;
    text-align:center;
    color:#a8b6ca !important;
    font-size:.78rem;
    margin-top:.36rem;
}
.explain-box{
    text-align:left;
    border:1px solid rgba(129,140,248,.15);
    background:rgba(255,255,255,.024);
    border-radius:12px;
    padding:1rem 1.05rem;
    line-height:1.65;
    margin:.55rem 0;
}
.explain-box b{color:#eef5ff !important;}
.decision-box{
    text-align:center;
    border:1px solid rgba(88,217,255,.22);
    background:linear-gradient(135deg,rgba(79,140,255,.08),rgba(155,124,255,.055));
    border-radius:14px;
    padding:1.05rem 1.2rem;
    margin:.6rem 0;
}
.decision-title{
    color:#9fb2ca !important;
    text-transform:uppercase;
    letter-spacing:.06em;
    font-size:.76rem;
}
.decision-action{
    color:#ffffff !important;
    font-size:1.8rem;
    font-weight:800;
    margin:.25rem 0;
}
.decision-explain{
    color:#c7d4e6 !important;
    font-size:.9rem;
}
</style>

<style>
/* Premium course-project refinement */
.status-strip{
    display:grid;
    grid-template-columns:repeat(5,minmax(0,1fr));
    gap:.85rem;
    margin:.5rem 0 1.15rem 0;
}
.status-box{
    min-width:0;
    min-height:104px;
    display:flex;
    flex-direction:column;
    align-items:center;
    justify-content:center;
    text-align:center;
    border:1px solid rgba(129,140,248,.18);
    background:
      linear-gradient(180deg,rgba(255,255,255,.055),rgba(255,255,255,.026));
    border-radius:14px;
    padding:.85rem .8rem;
    box-shadow:0 10px 28px rgba(0,0,0,.14);
}
.status-label{
    width:100%;
    text-align:center;
    font-size:.74rem;
    letter-spacing:.06em;
    text-transform:uppercase;
    color:#91a3bd !important;
    margin-bottom:.38rem;
}
.status-value{
    width:100%;
    text-align:center;
    font-size:1.03rem;
    font-weight:700;
    line-height:1.22;
    white-space:normal;
    overflow-wrap:anywhere;
}
.status-chip{
    display:inline-block;
    text-align:center;
    border-radius:999px;
    padding:.26rem .62rem;
    border:1px solid rgba(88,217,255,.24);
    background:linear-gradient(90deg,rgba(79,140,255,.10),rgba(155,124,255,.08));
    font-size:.78rem;
    font-weight:750;
}
.mission-summary{
    text-align:center;
    border:1px solid rgba(129,140,248,.15);
    background:linear-gradient(180deg,rgba(255,255,255,.038),rgba(255,255,255,.022));
    border-radius:12px;
    padding:.9rem 1.05rem;
    line-height:1.65;
    overflow-wrap:anywhere;
    box-shadow:0 8px 24px rgba(0,0,0,.10);
}
.course-note{
    text-align:center;
    border:1px solid rgba(88,217,255,.14);
    background:rgba(79,140,255,.045);
    border-radius:10px;
    padding:.68rem .85rem;
    margin:.25rem 0 .85rem 0;
    color:#c7d5e8 !important;
    font-size:.88rem;
}
.course-note b{color:#eef5ff !important;}
div[data-testid="stMetric"]{
    text-align:center !important;
}
div[data-testid="stMetricLabel"]{
    justify-content:center !important;
    text-align:center !important;
}
div[data-testid="stMetricLabel"] p{
    text-align:center !important;
    width:100%;
}
div[data-testid="stMetricValue"]{
    text-align:center !important;
    justify-content:center !important;
}
[data-testid="stMetricDelta"]{
    justify-content:center !important;
}
.stButton>button{
    min-height:2.7rem;
    box-shadow:0 5px 16px rgba(0,0,0,.10);
}
div[data-testid="stDataFrame"], div[data-testid="stPlotlyChart"]{
    box-shadow:0 10px 28px rgba(0,0,0,.10);
}
h1,h2,h3{
    text-align:left;
}
.hero{
    padding:1rem 1.15rem;
}
.hero b{
    font-size:1.02rem;
}
.sidebar-section-title{
    text-align:left;
}
@media(max-width:1050px){
  .status-strip{grid-template-columns:repeat(2,minmax(0,1fr));}
}
@media(max-width:680px){
  .status-strip{grid-template-columns:1fr;}
}
</style>

<style>
/* Final overflow and readability fixes */
div[data-testid="stMetric"] {
    min-width: 0 !important;
    overflow: hidden !important;
}
div[data-testid="stMetricLabel"] {
    min-width: 0 !important;
    overflow: hidden !important;
}
div[data-testid="stMetricLabel"] p {
    white-space: normal !important;
    overflow-wrap: anywhere !important;
    word-break: break-word !important;
}
div[data-testid="stMetricValue"] {
    min-width: 0 !important;
    max-width: 100% !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    white-space: nowrap !important;
    font-size: clamp(.95rem, 1.45vw, 1.45rem) !important;
}
.status-strip {
    display:grid;
    grid-template-columns:repeat(5,minmax(0,1fr));
    gap:.75rem;
    margin:.4rem 0 1rem 0;
}
.status-box {
    min-width:0;
    border:1px solid rgba(129,140,248,.18);
    background:linear-gradient(180deg,rgba(255,255,255,.045),rgba(255,255,255,.025));
    border-radius:11px;
    padding:.72rem .8rem;
}
.status-label {
    font-size:.78rem;
    color:#9fb0ca !important;
    margin-bottom:.18rem;
}
.status-value {
    font-size:1.12rem;
    font-weight:700;
    line-height:1.15;
    white-space:normal;
    overflow-wrap:anywhere;
}
.status-chip {
    display:inline-block;
    border-radius:999px;
    padding:.24rem .58rem;
    border:1px solid rgba(88,217,255,.22);
    background:rgba(79,140,255,.08);
    font-size:.82rem;
    font-weight:700;
    letter-spacing:.01em;
}
.sidebar-section-title {
    font-size:.78rem;
    text-transform:uppercase;
    letter-spacing:.08em;
    color:#8fa1bb !important;
    margin:.2rem 0 .35rem 0;
}
.mission-summary {
    border:1px solid rgba(129,140,248,.15);
    background:rgba(255,255,255,.025);
    border-radius:11px;
    padding:.8rem .9rem;
    line-height:1.6;
    overflow-wrap:anywhere;
}
@media(max-width:1050px) {
    .status-strip {grid-template-columns:repeat(2,minmax(0,1fr));}
}
@media(max-width:680px) {
    .status-strip {grid-template-columns:1fr;}
}
</style>

""",unsafe_allow_html=True)

DEFAULT={"type":"Earthquake","seed":17,"mw":6.7,"depth_km":14,"local_shaking":.60,"secondary_hazard":.30,"wind":3.0}
if "aeris_map_choice" not in st.session_state:
    st.session_state.aeris_map_choice="Default AERIS network"
if "world" not in st.session_state:
    spec=load_aeris_spec(AERIS_MAP_FILES[st.session_state.aeris_map_choice])
    st.session_state.world=build_world_from_spec(DEFAULT,spec)
if "revision" not in st.session_state:st.session_state.revision=0
if "last_change" not in st.session_state:st.session_state.last_change="Initial scenario"
if "battery" not in st.session_state:st.session_state.battery=82.0
if "monitored_edge" not in st.session_state:
    st.session_state.monitored_edge=list(st.session_state.world["road"].edges)[0]
if "drop_altitude" not in st.session_state:st.session_state.drop_altitude=18.0
if "drop_radius" not in st.session_state:st.session_state.drop_radius=3.0
if "drop_comp" not in st.session_state:st.session_state.drop_comp=.65
if "drop_uncertainty" not in st.session_state:st.session_state.drop_uncertainty=.8


def changed(reason):
    st.session_state.revision+=1
    st.session_state.last_change=reason

def graph_fig(world,path=None):
    G=world["road"]; pos={n:G.nodes[n]["pos"] for n in G.nodes}
    selected={tuple(sorted(x)) for x in zip(path,path[1:])} if path else set()
    fig=go.Figure()
    for a,b,d in G.edges(data=True):
        chosen=tuple(sorted((a,b))) in selected
        blocked=bool(d.get("field_blocked",False))
        if blocked:
            line=dict(width=3,dash="dash",color="#ef5350"); opacity=.9
            status="CONFIRMED BLOCKED - excluded from ground planning"
        elif chosen:
            line=dict(width=6,dash="solid",color="#45a3ff"); opacity=1
            status="Selected ground route"
        else:
            line=dict(width=2,dash="solid" if d["p_open"]>=.55 else "dot",color="#587694"); opacity=.48
            status="Available road"
        fig.add_trace(go.Scatter(
            x=[pos[a][0],pos[b][0]],y=[pos[a][1],pos[b][1]],mode="lines",line=line,opacity=opacity,showlegend=False,
            hovertemplate=f"{a} ↔ {b}<br>{status}<br>P(open)={d['p_open']:.3f}<br>Risk={d['risk']:.3f}<br>Belief cost={d['cost']:.2f}<extra></extra>"
        ))
    special={"Depot"}|set(world["requests"])
    fig.add_trace(go.Scatter(
        x=[pos[n][0] for n in G],y=[pos[n][1] for n in G],mode="markers+text",
        marker=dict(size=[23 if n in special else 12 for n in G]),text=list(G.nodes),textposition="top center",showlegend=False
    ))
    fig.update_layout(height=500,margin=dict(l=5,r=5,t=5,b=5),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                      xaxis=dict(visible=False),yaxis=dict(visible=False,scaleanchor="x"))
    return fig

def mode_plan_fig(world,plan):
    G=world["road"]; pos={n:G.nodes[n]["pos"] for n in G.nodes}
    ground_path=plan.get("ground_path",[]) if plan else []
    selected={tuple(sorted(x)) for x in zip(ground_path,ground_path[1:])}
    fig=go.Figure()
    for a,b,d in G.edges(data=True):
        blocked=bool(d.get("field_blocked",False)); chosen=tuple(sorted((a,b))) in selected
        if blocked:
            line=dict(width=3,dash="dash",color="#ef5350"); opacity=.9
        elif chosen:
            line=dict(width=6,color="#45a3ff"); opacity=1
        else:
            line=dict(width=2,color="#49657f"); opacity=.35
        fig.add_trace(go.Scatter(x=[pos[a][0],pos[b][0]],y=[pos[a][1],pos[b][1]],mode="lines",line=line,opacity=opacity,showlegend=False))
    if plan and plan.get("air_from") and plan.get("air_to"):
        a=plan["air_from"]; b=plan["air_to"]
        fig.add_trace(go.Scatter(x=[pos[a][0],pos[b][0]],y=[pos[a][1],pos[b][1]],mode="lines",
                                 line=dict(width=5,dash="dot",color="#a78bfa"),name="UAV leg"))
    fig.add_trace(go.Scatter(x=[pos[n][0] for n in G],y=[pos[n][1] for n in G],mode="markers+text",
                             marker=dict(size=[23 if n in ({"Depot"}|set(world["requests"])) else 12 for n in G]),
                             text=list(G.nodes),textposition="top center",showlegend=False))
    fig.update_layout(height=470,margin=dict(l=5,r=5,t=5,b=5),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                      xaxis=dict(visible=False),yaxis=dict(visible=False,scaleanchor="x"),legend=dict(orientation="h"))
    return fig

def faculty_map_fig(m,path=None):
    terrain=m["terrain"]; currents=m["currents"]; rows,cols=m["rows"],m["cols"]
    path=path or []
    fig=go.Figure(); palette={"open":"#22324a","kelp":"#2f6f59","reef":"#5b6474","special":"#4f8cff"}
    for r in range(rows):
        for c in range(cols):
            symbol=terrain[r][c]; x,y=c,-r
            if symbol=='#': fill=palette['reef']; label='#'; hover='Reef · impassable'
            elif symbol=='~': fill=palette['kelp']; label='~'; hover='Kelp · base entry cost 6'
            elif symbol in 'HC123456789':
                fill=palette['special']; label=symbol
                hover='Home' if symbol=='H' else ('Charging dock' if symbol=='C' else f'Survey goal {symbol}')
            else: fill=palette['open']; label=''; hover='Open water · base entry cost 2'
            current=currents[r][c]; current_text='none' if current=='.' else current
            fig.add_trace(go.Scatter(x=[x],y=[y],mode='markers+text',
                marker=dict(symbol='square',size=31,color=fill,line=dict(width=1,color='#111827')),
                text=[label],textfont=dict(size=12),textposition='middle center',
                hovertemplate=f'row={r}, col={c}<br>{hover}<br>current={current_text}<extra></extra>',showlegend=False))
    if path:
        fig.add_trace(go.Scatter(x=[n[1] for n in path],y=[-n[0] for n in path],mode='lines+markers',
            line=dict(width=5,color='#58d9ff'),marker=dict(size=8,color='#ffffff'),name='A* path'))
    fig.update_layout(height=max(430,rows*38),margin=dict(l=10,r=10,t=15,b=10),
        paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(visible=False,range=[-.7,cols-.3],constrain='domain'),
        yaxis=dict(visible=False,range=[-rows+.3,.7],scaleanchor='x',scaleratio=1),
        legend=dict(orientation='h',y=1.02,x=.5,xanchor='center'))
    return fig


def bn_fig():
    pos={"HazardSevere":(0,1.5),"VisualDamage":(0,.75),"FieldBlocked":(0,0),"RoadOpen":(2,.75)}
    fig=go.Figure()
    for a in ["HazardSevere","VisualDamage","FieldBlocked"]:
        fig.add_trace(go.Scatter(x=[pos[a][0],pos["RoadOpen"][0]],y=[pos[a][1],pos["RoadOpen"][1]],mode="lines",showlegend=False))
    fig.add_trace(go.Scatter(x=[v[0] for v in pos.values()],y=[v[1] for v in pos.values()],
                             mode="markers+text",marker=dict(size=32),text=list(pos),textposition="top center",showlegend=False))
    fig.update_layout(height=300,margin=dict(l=5,r=5,t=5,b=5),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                      xaxis=dict(visible=False),yaxis=dict(visible=False))
    return fig





def compact_status(d):
    if bool(d.get("field_blocked",False)):
        return "CONFIRMED BLOCKED"
    p=float(d.get("p_open",1.0))
    if p < .25: return "VERY LOW"
    if p < .50: return "LOW"
    if p < .75: return "UNCERTAIN"
    return "LIKELY OPEN"


def center_card(label, value, subtext=None):
    sub = f'<div class="center-card-sub">{subtext}</div>' if subtext else ''
    st.markdown(
        f'<div class="center-card">'
        f'<div class="center-card-label">{label}</div>'
        f'<div class="center-card-value">{value}</div>'
        f'{sub}'
        f'</div>',
        unsafe_allow_html=True
    )

def explain_action(action):
    mapping={
        "ROAD":"Use the road network for the delivery.",
        "UAV":"Use UAV delivery because the current state gives it the highest expected utility.",
        "HYBRID":"Combine road and UAV delivery because neither mode alone is best for the current state.",
        "VERIFY":"Collect more information before committing to a delivery mode.",
        "RECHARGE":"Recharge before continuing because battery state is limiting the safer options.",
        "REROUTE":"Recompute the ground route around confirmed closures or high-risk roads before choosing the delivery mode.",
        "WAIT":"Delay the next action because waiting has the highest expected utility in the current state.",
        "TERMINAL":"The mission is already in a terminal state."
    }
    return mapping.get(action,action)

def safe_index(options, value, default=0):
    try:
        return options.index(value)
    except ValueError:
        return default


def sanitize_session_choice(state_key, options, default, widget_keys=()):
    value=st.session_state.get(state_key, default)
    if value not in options:
        st.session_state[state_key]=default
    for widget_key in widget_keys:
        if widget_key in st.session_state and st.session_state[widget_key] not in options:
            del st.session_state[widget_key]


# Keep mission choices across Streamlit reruns.
defaults = {
    "risk_w_t":1.0, "risk_w_r":2.3, "risk_w_c":.45,
    "battery":82.0, "drop_altitude":18.0, "drop_radius":3.0,
    "drop_comp":.65, "drop_uncertainty":.8,
    "active_target":"Hospital", "landing_seed":17, "active_heuristic":"H2 - Geometric lower bound",
}
for k,v in defaults.items():
    if k not in st.session_state:
        st.session_state[k]=v

sanitize_session_choice(
    "active_heuristic",
    HEURISTIC_NAMES,
    "H2 - Geometric lower bound",
    widget_keys=("global_heuristic", "route_heuristic"),
)

if "last_risk_weights" not in st.session_state:
    st.session_state.last_risk_weights=(st.session_state.risk_w_t,st.session_state.risk_w_r,st.session_state.risk_w_c)

current_weights=(st.session_state.risk_w_t,st.session_state.risk_w_r,st.session_state.risk_w_c)
if current_weights != st.session_state.last_risk_weights:
    recompute_all_edge_costs(
        st.session_state.world["road"],
        st.session_state.risk_w_t,st.session_state.risk_w_r,st.session_state.risk_w_c
    )
    st.session_state.last_risk_weights=current_weights
    changed("Risk-cost weights updated")

w=st.session_state.world
target_options=list(w["requests"].keys())
sanitize_session_choice(
    "active_target",
    target_options,
    target_options[0],
    widget_keys=("global_target",),
)

# Road currently receiving evidence updates.
if not w["road"].has_edge(*st.session_state.monitored_edge):
    st.session_state.monitored_edge=list(w["road"].edges)[0]
ma,mb=st.session_state.monitored_edge
md=w["road"][ma][mb]

# Recompute values shown across all pages.
current_route=astar_with_heuristic(w["road"],"Depot",st.session_state.active_target,st.session_state.active_heuristic)
current_wind=float(w["params"].get("wind",3.0))
drop_metrics=precision_drop_metrics(
    st.session_state.drop_altitude,current_wind,st.session_state.drop_radius,
    st.session_state.drop_comp,st.session_state.drop_uncertainty
)
current_mdp_state=mdp_state_from_world(
    w,st.session_state.active_target,st.session_state.battery,current_wind
)


hero1,hero2=st.columns([.15,1.85],vertical_alignment="center")
with hero1:
    if LOGO_B64:
        st.markdown(f'<div class="logo-orb"><img src="data:image/png;base64,{LOGO_B64}"></div>',unsafe_allow_html=True)
with hero2:
    st.markdown('<span class="muted">CSE518 · ARTIFICIAL INTELLIGENCE · COURSE PROJECT</span>',unsafe_allow_html=True)
    st.title("AERIS Medico Helper")
    st.markdown(
        '<div class="hero"><b>Uncertainty-Aware Relief Routing</b><br>'
        '<span class="muted">I use one connected AI pipeline to update the mission from uncertain evidence to route planning and sequential decision making.</span>'
        '</div>',
        unsafe_allow_html=True
    )


with st.sidebar:
    if LOGO_B64:
        st.markdown(f'<div class="logo-orb"><img src="data:image/png;base64,{LOGO_B64}"></div>',unsafe_allow_html=True)

    st.markdown("### Project modules")
    page=st.radio(
        "Module",
        ["1. Mission setup","2. Bayesian road belief","3. HMM temporal update","4. Risk-aware A*","5. Precision delivery","6. MDP decision","7. Evaluation","8. External map test"],
        label_visibility="collapsed"
    )

    st.divider()
    st.markdown('<div class="sidebar-section-title">Current mission</div>',unsafe_allow_html=True)
    st.session_state.active_target=st.selectbox(
        "Mission destination",list(w["requests"].keys()),
        index=safe_index(list(w["requests"].keys()), st.session_state.active_target),
        key="global_target"
    )
    st.caption(f"Selected road for belief updates: {ma} — {mb}")
    st.caption(f"Road belief category: {compact_status(md)}")
    st.caption(f"P(open): {md['p_open']:.3f}")
    st.caption(f"Current route reliability: {current_route['reliability']:.3f}")
    st.caption(f"Current drop success: {drop_metrics['success_probability']:.3f}")

    st.markdown('<div class="sidebar-section-title">A* search setting</div>',unsafe_allow_html=True)
    st.session_state.active_heuristic=st.selectbox(
        "Active A* heuristic",
        HEURISTIC_NAMES,
        index=safe_index(HEURISTIC_NAMES, st.session_state.active_heuristic, 1),
        key="global_heuristic"
    )

    st.divider()
    st.markdown('<div class="sidebar-section-title">Risk-aware A* weights</div>',unsafe_allow_html=True)
    st.session_state.risk_w_t=st.slider("Travel-time weight",0.0,3.0,float(st.session_state.risk_w_t),.1,key="side_wt")
    st.session_state.risk_w_r=st.slider("Road-risk weight",0.0,5.0,float(st.session_state.risk_w_r),.1,key="side_wr")
    st.session_state.risk_w_c=st.slider("Operating-cost weight",0.0,2.0,float(st.session_state.risk_w_c),.05,key="side_wc")

    st.divider()
    st.caption(f"Revision {st.session_state.revision}")
    st.caption(st.session_state.last_change)

# Sidebar changes may alter the active mission.
w=st.session_state.world
target=st.session_state.active_target
if not w["road"].has_edge(*st.session_state.monitored_edge):
    st.session_state.monitored_edge=list(w["road"].edges)[0]
ma,mb=st.session_state.monitored_edge
md=w["road"][ma][mb]
current_route=astar_with_heuristic(w["road"],"Depot",target,st.session_state.active_heuristic)
current_wind=float(w["params"].get("wind",3.0))
drop_metrics=precision_drop_metrics(
    st.session_state.drop_altitude,current_wind,st.session_state.drop_radius,
    st.session_state.drop_comp,st.session_state.drop_uncertainty
)
current_mdp_state=mdp_state_from_world(w,target,st.session_state.battery,current_wind)
mode_recommendation, mode_candidates = recommended_delivery_mode(
    w,target,st.session_state.battery,current_wind,drop_metrics["success_probability"],st.session_state.active_heuristic
)

# Keep the current AERIS mission status visible on its workflow pages.
if page!="8. External map test":
    st.markdown(
        f"""
        <div class="status-strip">
          <div class="status-box"><div class="status-label">Monitored road</div><div class="status-value">{ma} — {mb}</div></div>
          <div class="status-box"><div class="status-label">Road belief</div><div class="status-value"><span class="status-chip">{compact_status(md)}</span> &nbsp; P(open)={md['p_open']:.3f}</div></div>
          <div class="status-box"><div class="status-label">Current route</div><div class="status-value">Reliability {current_route['reliability']:.3f}</div></div>
          <div class="status-box"><div class="status-label">Precision delivery</div><div class="status-value">P(success)={drop_metrics['success_probability']:.3f}</div></div>
          <div class="status-box"><div class="status-label">UAV state</div><div class="status-value">{st.session_state.battery:.0f}% battery</div></div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        f'<div class="mission-summary"><b>Current mission state</b><br>'
        f'Road <b>{ma} — {mb}</b> · P(open) <b>{md["p_open"]:.3f}</b> · '
        f'edge cost <b>{md["cost"]:.2f}</b> · route <b>{" → ".join(current_route["path"]) if current_route["path"] else "No feasible ground route"}</b> · '
        f'route reliability <b>{current_route["reliability"]:.3f}</b> · '
        f'precision-delivery P(success) <b>{drop_metrics["success_probability"]:.3f}</b> · suggested mode <b>{mode_recommendation["mode"] if mode_recommendation else "None"}</b>'
        f'</div>',
        unsafe_allow_html=True
    )

if page=="1. Mission setup":
    st.header("Mission setup")
    st.markdown('<div class="course-note"><b>Course focus:</b> environment definition, state representation, observability and the inputs used by later probabilistic and decision modules.</div>',unsafe_allow_html=True)
    st.caption("I define the current disaster scenario and mission conditions here. These values are reused by every later module.")
    left,right=st.columns([.88,1.52],gap="large")
    with left:
        map_choice=st.selectbox(
            "AERIS network",
            list(AERIS_MAP_FILES.keys()),
            index=safe_index(list(AERIS_MAP_FILES.keys()),st.session_state.aeris_map_choice),
            help="Default opens automatically. Alternate and Large use different AERIS-native road graphs while keeping the same AI pipeline."
        )
        dtype=st.selectbox("Disaster type",["Earthquake","Flood","Cyclone"],
                           index=["Earthquake","Flood","Cyclone"].index(w["params"]["type"]))
        seed=st.number_input("Scenario seed",1,9999,int(w["params"]["seed"]))

        if dtype=="Earthquake":
            mw=st.slider("Magnitude Mw",4.0,9.0,float(w["params"].get("mw",6.7)),.1)
            depth=st.slider("Depth (km)",2.0,60.0,float(w["params"].get("depth_km",14)),1.0)
            shake=st.slider("Local shaking",0.0,1.0,float(w["params"].get("local_shaking",.60)),.05)
            secondary=st.slider("Secondary hazard",0.0,1.0,float(w["params"].get("secondary_hazard",.30)),.05)
            wind=st.slider("Wind (m/s)",0.0,18.0,float(w["params"].get("wind",3.0)),.5)
            params={"type":dtype,"seed":int(seed),"mw":mw,"depth_km":depth,
                    "local_shaking":shake,"secondary_hazard":secondary,"wind":wind}
        elif dtype=="Flood":
            water=st.slider("Water depth (m)",0.0,2.5,float(w["params"].get("water_depth_m",.7)),.05)
            flow=st.slider("Flow severity",0.0,1.0,float(w["params"].get("flow",.45)),.05)
            rain=st.slider("Rainfall severity",0.0,1.0,float(w["params"].get("rain",.55)),.05)
            wind=st.slider("Wind (m/s)",0.0,18.0,float(w["params"].get("wind",4.0)),.5)
            params={"type":dtype,"seed":int(seed),"water_depth_m":water,"flow":flow,"rain":rain,"wind":wind}
        else:
            wind=st.slider("Sustained wind (m/s)",0.0,25.0,float(w["params"].get("wind",9.0)),.5)
            gust=st.slider("Gust speed (m/s)",0.0,35.0,float(w["params"].get("gust",14.0)),.5)
            rain=st.slider("Rainfall severity",0.0,1.0,float(w["params"].get("rain",.45)),.05)
            debris=st.slider("Debris severity",0.0,1.0,float(w["params"].get("debris",.35)),.05)
            params={"type":dtype,"seed":int(seed),"wind":wind,"gust":gust,"rain":rain,"debris":debris}

        st.session_state.battery=st.slider("UAV battery (%)",20,100,int(st.session_state.battery))

        if st.button("Apply scenario",type="primary",use_container_width=True):
            st.session_state.aeris_map_choice=map_choice
            spec=load_aeris_spec(AERIS_MAP_FILES[map_choice])
            st.session_state.world=build_world_from_spec(params,spec)
            recompute_all_edge_costs(
                st.session_state.world["road"],
                st.session_state.risk_w_t,st.session_state.risk_w_r,st.session_state.risk_w_c
            )
            st.session_state.monitored_edge=list(st.session_state.world["road"].edges)[0]
            st.session_state.active_target=list(st.session_state.world["requests"])[0]
            for key in ["global_target","request_destination"]:
                st.session_state.pop(key,None)
            changed(f"Mission setup updated · {map_choice}")
            st.rerun()

        st.markdown("### Delivery request")
        st.caption("I define the required supply, quantity and priority for each destination here. These values feed into the MDP urgency state.")

        req_dest=st.selectbox(
            "Request destination",
            list(w["requests"].keys()),
            key="request_destination"
        )
        req=w["requests"][req_dest]

        req_supply=st.selectbox(
            "Supply",
            list(SUPPLIES.keys()),
            index=list(SUPPLIES.keys()).index(req["supply"]) if req["supply"] in SUPPLIES else 0,
            key="request_supply"
        )
        req_qty=st.number_input(
            "Quantity",
            min_value=1,
            max_value=100,
            value=int(req["quantity"]),
            key="request_quantity"
        )
        req_priority=st.slider(
            "Mission priority",
            min_value=0.0,
            max_value=1.0,
            value=float(req["priority"]),
            step=.05,
            key="request_priority"
        )

        if st.button("Update delivery request",use_container_width=True):
            w["requests"][req_dest]={
                "supply":req_supply,
                "quantity":int(req_qty),
                "priority":float(req_priority)
            }
            changed(f"Delivery request updated for {req_dest}")
            st.rerun()

        st.markdown("#### Current delivery requests")
        st.dataframe(pd.DataFrame([
            {"Destination":k,"Supply":v["supply"],"Quantity":v["quantity"],"Priority":v["priority"]}
            for k,v in w["requests"].items()
        ]),use_container_width=True,hide_index=True)

    with right:
        st.markdown("### Current road network")
        st.caption(f"{w.get('map_name','AERIS network')} · The same AI pipeline runs on either AERIS-native graph.")
        st.plotly_chart(graph_fig(w,current_route["path"]),use_container_width=True)
        roads=pd.DataFrame([
            {
                "Road":f"{a} — {b}",
                "Status":road_status_label(d),
                "P(open)":d["p_open"],
                "Risk":d["risk"],
                "Belief cost":d["cost"],
                "Ground planning":"Blocked" if d.get("field_blocked",False) else "Available"
            }
            for a,b,d in w["road"].edges(data=True)
        ])
        st.dataframe(
            roads.style.format({"P(open)":"{:.3f}","Risk":"{:.3f}","Belief cost":"{:.2f}"}),
            use_container_width=True,hide_index=True,height=280
        )

elif page=="2. Bayesian road belief":
    st.header("Bayesian road belief")
    st.markdown('<div class="course-note"><b>Course focus:</b> Bayesian Networks, conditional dependence, exact inference by Enumeration and Variable Elimination.</div>',unsafe_allow_html=True)
    st.caption("I update the selected road belief here using the evidence I provide for hazard severity, visual damage and the field report.")
    edges=list(w["road"].edges)
    labels=[f"{a} — {b}" for a,b in edges]
    idx=edges.index(st.session_state.monitored_edge) if st.session_state.monitored_edge in edges else 0
    label=st.selectbox("Road to assess",labels,index=idx)
    a,b=edges[labels.index(label)]
    st.session_state.monitored_edge=(a,b)
    d=w["road"][a][b]

    c1,c2,c3,c4=st.columns(4)
    c1.metric("Status",road_status_label(d))
    c2.metric("P(open)",f"{d['p_open']:.3f}")
    c3.metric("Risk",f"{d['risk']:.3f}")
    c4.metric("Edge cost",f"{d['cost']:.2f}")

    l,r=st.columns([.86,1.14],gap="large")
    with l:
        defaults=edge_default_evidence(w,a,b)
        severe=st.toggle("Hazard severe",value=defaults["HazardSevere"])
        visual=st.toggle("Visible road damage",value=defaults["VisualDamage"])
        blocked=st.toggle("Field report: road blocked",value=defaults["FieldBlocked"])
        ev={"HazardSevere":severe,"VisualDamage":visual,"FieldBlocked":blocked}

        en=enumeration_ask("RoadOpen",ev)
        ve,trace=variable_elimination("RoadOpen",ev)

        x1,x2=st.columns(2)
        x1.metric("Enumeration",f"{en[True]:.3f}")
        x2.metric("Variable Elimination",f"{ve[True]:.3f}")
        st.caption(f"Agreement error: {abs(en[True]-ve[True]):.2e}")

        if blocked:
            st.warning("I have marked this road as blocked from a confirmed field report. I still keep P(open) for the uncertainty model, but this road is removed from ground-route planning until I clear the field report.")

        if st.button("Apply Bayesian update",type="primary",use_container_width=True):
            apply_bn(
                w,a,b,ev,
                st.session_state.risk_w_t,st.session_state.risk_w_r,st.session_state.risk_w_c
            )
            changed(f"Bayesian road belief committed: {a}-{b}")
            st.rerun()

    with r:
        st.plotly_chart(graph_fig(w,current_route["path"]),use_container_width=True)
        if trace:
            st.markdown("### Variable Elimination steps")
            st.dataframe(pd.DataFrame(trace),use_container_width=True,hide_index=True)
        else:
            st.markdown(
                '<div class="explain-box"><b>Variable Elimination:</b> '
                'there are no hidden variables left to eliminate for this evidence combination, '
                'so no intermediate factor table is needed. The posterior is computed directly.</div>',
                unsafe_allow_html=True
            )

elif page=="3. HMM temporal update":
    st.header("HMM temporal update")
    st.markdown('<div class="course-note"><b>Course focus:</b> first-order Markov assumption, transition model, sensor model, filtering and Viterbi decoding.</div>',unsafe_allow_html=True)
    st.caption("I refine the same road over time here using a sequence of observations rather than treating each observation separately.")
    a,b=st.session_state.monitored_edge
    if bool(w["road"][a][b].get("field_blocked",False)):
        st.info("The HMM can update the belief for this road, but a confirmed field blockage remains a hard ground-routing constraint until the field report is cleared.")
    st.markdown(f"Monitoring **{a} — {b}**. Current status: **{road_status_label(w['road'][a][b])}**")

    l,r=st.columns([.82,1.18],gap="large")
    with l:
        obs=st.multiselect(
            "Sequential observations",
            ["Clear","Slow","Obstructed"],
            default=["Clear","Slow","Obstructed"]
        )
        if obs:
            hist=hmm_filter(obs)
            vit=viterbi(obs)
            final=hist[-1]
            implied=float(final[0]+.45*final[1])
            h1,h2=st.columns(2)
            with h1:
                center_card("Open state",f"{final[0]:.3f}","Filtered probability")
            with h2:
                center_card("Degraded state",f"{final[1]:.3f}","Filtered probability")
            h3,h4=st.columns(2)
            with h3:
                center_card("Blocked state",f"{final[2]:.3f}","Filtered probability")
            with h4:
                center_card("Road belief after commit",f"{implied:.3f}","P(open) used by the graph")

            if st.button("Apply HMM update",type="primary",use_container_width=True):
                apply_hmm(
                    w,a,b,obs,
                    st.session_state.risk_w_t,st.session_state.risk_w_r,st.session_state.risk_w_c
                )
                changed(f"HMM temporal belief committed: {a}-{b}")
                st.rerun()
        else:
            st.warning("Select one or more observations.")

    with r:
        if obs:
            trace=pd.DataFrame([
                {
                    "t":i+1,"Observation":o,
                    "P(Open)":bel[0],"P(Degraded)":bel[1],"P(Blocked)":bel[2],
                    "Viterbi state":vit[i]
                }
                for i,(o,bel) in enumerate(zip(obs,hist))
            ])
            st.dataframe(
                trace.style.format({"P(Open)":"{:.3f}","P(Degraded)":"{:.3f}","P(Blocked)":"{:.3f}"}),
                use_container_width=True,hide_index=True
            )
            st.line_chart(trace.set_index("t")[["P(Open)","P(Degraded)","P(Blocked)"]])

elif page=="4. Risk-aware A*":
    sanitize_session_choice(
        "active_heuristic",
        HEURISTIC_NAMES,
        "H2 - Geometric lower bound",
        widget_keys=("route_heuristic",),
    )
    st.header("Risk-aware A* route")
    st.markdown('<div class="course-note"><b>Course focus:</b> informed search with A*, heuristic guidance and optimal-cost verification against UCS while edge costs depend on current belief.</div>',unsafe_allow_html=True)
    st.caption("I use the latest road beliefs directly in the edge-cost function. Changing evidence can therefore change the A* route.")
    st.caption("Confirmed field blockages are excluded from A* and UCS. Other uncertain roads remain available with belief-dependent cost.")
    st.session_state.active_heuristic=st.selectbox(
        "A* heuristic",
        HEURISTIC_NAMES,
        index=safe_index(HEURISTIC_NAMES, st.session_state.active_heuristic, 1),
        key="route_heuristic"
    )

    planning_mode=st.selectbox(
        "Planning cost model",
        ["Risk-aware current belief","Deterministic baseline"],
        key="planning_cost_model"
    )

    with st.expander("What the four heuristics use", expanded=False):
        st.markdown(
            "**H1 - Zero:** no estimate; this is the UCS-equivalent baseline.  \n"
            "**H2 - Geometric lower bound:** straight-line distance scaled by the cheapest current cost per unit distance.  \n"
            "**H3 - Risk-aware component lower bound:** lower-bounds travel/operating cost from geometry and adds the minimum unavoidable risk penalty for the remaining ground hops.  \n"
            "**H4 - Dominant composite:** uses the largest safe lower bound among H2, H3, and the relaxed-network estimate."
        )

    search_graph=w["road"].copy()
    if planning_mode=="Deterministic baseline":
        for ea,eb,ed in search_graph.edges(data=True):
            ed["cost"]=st.session_state.risk_w_t*float(ed["time"])+st.session_state.risk_w_c*float(ed.get("money",.35*ed["distance"]))
            ed["risk"]=0.0
            ed["p_open"]=1.0

    r_astar=astar_with_heuristic(search_graph,"Depot",target,st.session_state.active_heuristic)
    r_ucs=ucs(search_graph,"Depot",target)

    plot_world=dict(w)
    plot_world["road"]=search_graph

    left,right=st.columns([.72,1.28],gap="large")
    with left:
        if planning_mode=="Deterministic baseline":
            st.code(
                f"c_det(e) = {st.session_state.risk_w_t:.2f}·T(e) + "
                f"{st.session_state.risk_w_c:.2f}·C(e)",
                language=None
            )
        else:
            st.code(
                f"c(e) = {st.session_state.risk_w_t:.2f}·T(e) + "
                f"{st.session_state.risk_w_r:.2f}·[-log P(open)] + "
                f"{st.session_state.risk_w_c:.2f}·C(e)",
                language=None
            )
        rr1,rr2=st.columns(2)
        with rr1:
            center_card("Path cost",f"{r_astar['cost']:.2f}")
        with rr2:
            center_card("Route reliability",f"{r_astar['reliability']:.3f}")
        rr3,rr4=st.columns(2)
        with rr3:
            center_card("A* nodes expanded",str(len(r_astar["expanded"])))
        with rr4:
            center_card("A* / UCS check","PASS" if abs(r_astar["cost"]-r_ucs["cost"])<1e-8 else "FAIL","Same optimal path cost")
        rr5,rr6=st.columns(2)
        with rr5:
            center_card("Admissible","YES" if r_astar["admissible"] else "NO",st.session_state.active_heuristic)
        with rr6:
            center_card("Consistent","YES" if r_astar["consistent"] else "NO",st.session_state.active_heuristic)
        st.markdown("**Route**")
        st.write(" → ".join(r_astar["path"]) if r_astar["path"] else "No feasible ground route under the current confirmed closures.")
    with right:
        st.plotly_chart(graph_fig(plot_world,r_astar["path"]),use_container_width=True)
        st.dataframe(pd.DataFrame([
            {
                "Road":f"{a} — {b}",
                "Status":"DETERMINISTIC" if planning_mode=="Deterministic baseline" else road_status_label(search_graph[a][b]),
                "P(open)":search_graph[a][b]["p_open"],
                "Risk":search_graph[a][b]["risk"],
                "Cost":search_graph[a][b]["cost"]
            }
            for a,b in zip(r_astar["path"],r_astar["path"][1:])
        ]).style.format({"P(open)":"{:.3f}","Risk":"{:.3f}","Belief cost":"{:.2f}"}),
        use_container_width=True,hide_index=True)


    st.markdown("### Heuristic comparison on the current planning graph")
    comparison_rows=[]
    for hname in HEURISTIC_NAMES:
        hr=astar_with_heuristic(search_graph,"Depot",target,hname)
        comparison_rows.append({
            "Heuristic":hname,
            "Path cost":hr["cost"],
            "Expanded nodes":len(hr["expanded"]),
            "Admissible":hr["admissible"],
            "Consistent":hr["consistent"],
            "Route":" → ".join(hr["path"])
        })
    st.dataframe(
        pd.DataFrame(comparison_rows).style.format({"Path cost":"{:.2f}"}),
        use_container_width=True,
        hide_index=True
    )

elif page=="5. Precision delivery":
    st.header("Precision-delivery calibration")
    st.markdown('<div class="course-note"><b>Supporting model:</b> this is not a separate AI topic. I use it only to estimate a delivery-success probability that becomes an input to the MDP transition model.</div>',unsafe_allow_html=True)
    st.caption("I tune the release parameters here and use the resulting probability as the delivery-success input to the MDP.")
    left,right=st.columns([.72,1.28],gap="large")

    with left:
        st.session_state.drop_altitude=st.slider("Release altitude (m)",5.0,50.0,float(st.session_state.drop_altitude),1.0)
        st.session_state.drop_radius=st.slider("Target radius (m)",1.0,10.0,float(st.session_state.drop_radius),.5)
        st.session_state.drop_comp=st.slider("Wind compensation",0.0,.95,float(st.session_state.drop_comp),.05)
        st.session_state.drop_uncertainty=st.slider("Positioning uncertainty (m)",.1,3.0,float(st.session_state.drop_uncertainty),.1)
        test_n=st.slider("Landing trials",50,1000,300,50)
        st.session_state.landing_seed=st.number_input("Trial seed",1,9999,int(st.session_state.landing_seed))

        dm=precision_drop_metrics(
            st.session_state.drop_altitude,current_wind,st.session_state.drop_radius,
            st.session_state.drop_comp,st.session_state.drop_uncertainty
        )
        samples=landing_test_samples(
            st.session_state.drop_altitude,current_wind,st.session_state.drop_radius,
            st.session_state.drop_comp,st.session_state.drop_uncertainty,test_n,st.session_state.landing_seed
        )
        empirical=empirical_drop_success(samples)

        p1,p2=st.columns(2)
        with p1:
            center_card("Analytical success",f"{dm['success_probability']:.3f}","Model estimate")
        with p2:
            center_card("Monte Carlo success",f"{empirical:.3f}",f"{test_n} landing trials")
        p3,p4=st.columns(2)
        with p3:
            center_card("Residual drift",f"{dm['residual_drift_m']:.2f} m")
        with p4:
            center_card("Fall time",f"{dm['fall_time_s']:.2f} s")

    with right:
        st.markdown("### Landing-test map")
        fig=go.Figure()
        succ=samples[samples["success"]]
        fail=samples[~samples["success"]]
        fig.add_trace(go.Scatter(
            x=succ["x_m"],y=succ["y_m"],mode="markers",name="Inside target",
            marker=dict(size=6,opacity=.65)
        ))
        fig.add_trace(go.Scatter(
            x=fail["x_m"],y=fail["y_m"],mode="markers",name="Miss",
            marker=dict(size=6,opacity=.65)
        ))
        theta=np.linspace(0,2*np.pi,240)
        rr=st.session_state.drop_radius
        fig.add_trace(go.Scatter(
            x=rr*np.cos(theta),y=rr*np.sin(theta),mode="lines",name="Target boundary"
        ))
        fig.add_trace(go.Scatter(x=[0],y=[0],mode="markers",name="Target centre",marker=dict(size=12)))
        fig.update_layout(
            height=520,
            xaxis_title="Cross-range error (m)",
            yaxis_title="Along-range error (m)",
            yaxis=dict(scaleanchor="x",scaleratio=1),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20,r=20,t=15,b=20)
        )
        st.plotly_chart(fig,use_container_width=True)

    st.markdown("### Parameter sensitivity")
    sensitivity=[]
    for alt in [5,10,15,20,25,30,35,40,45,50]:
        m=precision_drop_metrics(
            alt,current_wind,st.session_state.drop_radius,
            st.session_state.drop_comp,st.session_state.drop_uncertainty
        )
        sensitivity.append({"Altitude (m)":alt,"P(success)":m["success_probability"]})
    st.line_chart(pd.DataFrame(sensitivity).set_index("Altitude (m)"))

elif page=="6. MDP decision":
    st.header("MDP decision policy")
    st.markdown('<div class="course-note"><b>Course focus:</b> MDP state, actions, transition model, reward, Bellman optimality, Value Iteration and Policy Iteration.</div>',unsafe_allow_html=True)
    st.caption("I form the current MDP state from road reliability, battery, wind, urgency, charging and mission stage, then solve for the next action.")
    state=mdp_state_from_world(w,target,st.session_state.battery,current_wind)
    ds=drop_metrics["success_probability"]
    req=w["requests"][target]
    effective_urgency=max(float(req["priority"]),SUPPLIES[req["supply"]].urgency)

    st.markdown(
        f'<div class="explain-box"><b>Current delivery request</b><br>'
        f'Destination: <b>{target}</b> · Supply: <b>{req["supply"]}</b> · '
        f'Quantity: <b>{req["quantity"]}</b> · Mission priority: <b>{req["priority"]:.2f}</b> · '
        f'Effective urgency used by the MDP: <b>{effective_urgency:.2f}</b>'
        f'</div>',
        unsafe_allow_html=True
    )

    state_names=["Road belief","Battery","Wind","Urgency","Charging","Mission stage"]
    st.dataframe(pd.DataFrame([dict(zip(state_names,state))]),use_container_width=True,hide_index=True)

    c1,c2,c3=st.columns(3)
    gamma=c1.slider("Discount factor γ",.50,.99,.92,.01)
    eps=c2.select_slider("VI tolerance ε",options=[1e-2,1e-3,1e-4,1e-5,1e-6],value=1e-5)
    c3.metric("Delivery success input",f"{ds:.3f}")

    Vvi,Pvi,hvi=value_iteration(gamma,eps,drop_success=ds)
    Vpi,Ppi,hpi=policy_iteration(gamma,drop_success=ds)
    feasible=feasible_actions(state)

    qdf=pd.DataFrame([
        {
            "Action":a,
            "Feasible":a in feasible,
            "Q(s,a)":q_value(state,a,Vvi,gamma,ds) if a in feasible else np.nan
        }
        for a in ACTIONS
    ]).sort_values("Q(s,a)",ascending=False,na_position="last")

    l,r=st.columns([.76,1.24],gap="large")
    with l:
        st.dataframe(qdf,use_container_width=True,hide_index=True)
        st.metric("Value Iteration action",Pvi[state])
        st.metric("Policy Iteration action",Ppi[state])
        st.metric("Agreement","PASS" if Pvi[state]==Ppi[state] else "DIFFERENT")
    with r:
        st.line_chart(hvi.set_index("iteration")["max_delta"])
        st.caption(f"Policy Iteration stabilized after {len(hpi)} improvement rounds.")

    st.markdown("### Suggested delivery mode")
    mode_df=pd.DataFrame([{
        "Mode":c["mode"],
        "Feasible":"Yes" if c["feasible"] else "No",
        "Estimated success":c["success"],
        "Plan":c["description"]
    } for c in mode_candidates])
    st.dataframe(mode_df.style.format({"Estimated success":"{:.3f}"}),use_container_width=True,hide_index=True)

    if mode_recommendation:
        st.markdown(
            f'<div class="decision-box"><div class="decision-title">Suggested delivery mode</div>'
            f'<div class="decision-action">{mode_recommendation["mode"]}</div>'
            f'<div class="decision-explain">{mode_recommendation["description"]} · estimated success {mode_recommendation["success"]:.3f}</div></div>',
            unsafe_allow_html=True
        )
        st.plotly_chart(mode_plan_fig(w,mode_recommendation),use_container_width=True)

    if st.button("Run policy simulation",type="primary"):
        sim,total=simulate_policy(state,Pvi,10,int(w["params"]["seed"])+1000,drop_success=ds)
        st.dataframe(sim,use_container_width=True,hide_index=True)
        st.metric("Trajectory reward",f"{total:.2f}")

elif page=="7. Evaluation":
    st.header("Integrated system evaluation")
    st.markdown('<div class="course-note"><b>Course check:</b> I verify exact-inference agreement, A* optimal-cost agreement with UCS, delivery-probability behaviour and VI/PI policy agreement.</div>',unsafe_allow_html=True)
    st.caption("I use this page to verify both algorithm-level correctness and end-to-end propagation through the complete project pipeline.")

    # Enumeration and Variable Elimination should agree.
    bn_rows=[]
    for vals in itertools.product([False,True],repeat=3):
        ev=dict(zip(["HazardSevere","VisualDamage","FieldBlocked"],vals))
        en=enumeration_ask("RoadOpen",ev)
        ve,_=variable_elimination("RoadOpen",ev)
        bn_rows.append({
            "Evidence":str(ev),
            "Enumeration":en[True],
            "VE":ve[True],
            "Difference":abs(en[True]-ve[True])
        })
    bdf=pd.DataFrame(bn_rows)

    # A* should match UCS on optimal path cost.
    route_rows=[]
    for t in w["requests"]:
        ar=astar_with_heuristic(w["road"],"Depot",t,st.session_state.active_heuristic)
        ur=ucs(w["road"],"Depot",t)
        route_rows.append({
            "Destination":t,
            "A* cost":ar["cost"],
            "UCS cost":ur["cost"],
            "Equal":abs(ar["cost"]-ur["cost"])<1e-8,
            "A* expanded":len(ar["expanded"]),
            "UCS expanded":len(ur["expanded"])
        })

    # Compare analytical and Monte Carlo delivery estimates.
    samples=landing_test_samples(
        st.session_state.drop_altitude,current_wind,st.session_state.drop_radius,
        st.session_state.drop_comp,st.session_state.drop_uncertainty,1000,2026
    )
    empirical=empirical_drop_success(samples)

    # Value Iteration and Policy Iteration should agree.
    ds=drop_metrics["success_probability"]
    V1,P1,_=value_iteration(.92,1e-6,drop_success=ds)
    V2,P2,_=policy_iteration(.92,drop_success=ds)
    normal=[s for s in mdp_states() if s not in TERMINALS]
    agree=sum(P1[s]==P2[s] for s in normal)

    k1,k2,k3,k4=st.columns(4)
    with k1:
        center_card("BN inference agreement",f"{bdf['Difference'].max():.1e}","maximum absolute error")
    with k2:
        center_card("A* / UCS verification",f"{sum(x['Equal'] for x in route_rows)}/{len(route_rows)}","destinations passed")
    with k3:
        center_card("Delivery model",f"{ds:.3f} / {empirical:.3f}","analytical / Monte Carlo")
    with k4:
        center_card("VI / PI agreement",f"{agree}/{len(normal)}","MDP states")

    st.markdown("### Bayesian inference check")
    st.dataframe(bdf.style.format({"Enumeration":"{:.4f}","VE":"{:.4f}","Difference":"{:.2e}"}),
                 use_container_width=True,hide_index=True)

    st.markdown("### A* optimality check")
    st.dataframe(pd.DataFrame(route_rows),use_container_width=True,hide_index=True)

    st.markdown("### Current mission outcome")
    recommended=P1[current_mdp_state]

    a1,a2,a3=st.columns(3)
    with a1:
        center_card("Monitored road",f"{ma} — {mb}",compact_status(md))
    with a2:
        center_card("Current route reliability",f"{current_route['reliability']:.3f}",f"P(open) on monitored road = {md['p_open']:.3f}")
    with a3:
        center_card("Precision delivery success",f"{ds:.3f}","Input used by UAV / HYBRID actions")

    st.markdown(
        f'<div class="decision-box">'
        f'<div class="decision-title">Recommended next action</div>'
        f'<div class="decision-action">{recommended}</div>'
        f'<div class="decision-explain">{explain_action(recommended)}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    if mode_recommendation:
        st.markdown(
            f'<div class="decision-box"><div class="decision-title">Suggested delivery mode</div>'
            f'<div class="decision-action">{mode_recommendation["mode"]}</div>'
            f'<div class="decision-explain">{mode_recommendation["description"]} · estimated success {mode_recommendation["success"]:.3f}</div></div>',
            unsafe_allow_html=True
        )
        st.markdown("### Suggested route / mode map")
        st.plotly_chart(mode_plan_fig(w,mode_recommendation),use_container_width=True)

    route_text=" → ".join(current_route["path"]) if current_route["path"] else "No feasible ground route"
    road_text=compact_status(md)
    st.markdown(
        f'<div class="explain-box"><b>How I reached this recommendation</b><br>'
        f'I am currently monitoring <b>{ma} — {mb}</b>, which is classified as <b>{road_text}</b> '
        f'with P(open)=<b>{md["p_open"]:.3f}</b>. '
        f'Using the current risk-aware edge costs, A* selects the route <b>{route_text}</b> '
        f'with route reliability <b>{current_route["reliability"]:.3f}</b>. '
        f'The precision-delivery model currently estimates P(success)=<b>{ds:.3f}</b>. '
        f'These values are converted into the MDP state and the optimal policy selects <b>{recommended}</b> as the next action. '
        f'The separate mode comparison suggests <b>{mode_recommendation["mode"] if mode_recommendation else "no feasible mode"}</b> for delivery under the current conditions.'
        f'</div>',
        unsafe_allow_html=True
    )

elif page=="8. External map test":
    st.header("External faculty-map test")
    st.markdown('<div class="course-note"><b>Course requirement:</b> the search code must run on maps in the supplied <code>map_main.txt</code> format without hard-coding the sample map.</div>',unsafe_allow_html=True)
    st.caption("Upload any compatible text map. I parse it at runtime, detect H/C/numbered goals and rerun the same four A* heuristics.")
    uploaded_map=st.file_uploader("Upload map_main.txt-format file",type=["txt"],key="faculty_map_upload")
    if uploaded_map is None:
        default_path=BASE/"map_main.txt"
        map_text=default_path.read_text(encoding="utf-8") if default_path.exists() else None
        source_name="Bundled map_main.txt" if map_text else None
        if map_text: st.info("No file uploaded yet. I am showing the bundled map_main.txt so this page is immediately testable.")
    else:
        map_text=uploaded_map.getvalue().decode("utf-8"); source_name=uploaded_map.name
    if map_text:
        try:
            fm=load_faculty_map_text(map_text); goal_ids=sorted(fm["goals"])
            selected_goal=st.selectbox("Survey goal",goal_ids,key="faculty_goal")
            selected_heuristic=st.selectbox("Heuristic used for the highlighted path",HEURISTIC_NAMES,
                index=safe_index(HEURISTIC_NAMES,st.session_state.active_heuristic,1),key="faculty_heuristic")
            chosen=astar_with_heuristic(fm["graph"],fm["home"],fm["goals"][selected_goal],selected_heuristic)
            m1,m2,m3,m4=st.columns(4)
            with m1: center_card("Map",f"{fm['rows']} × {fm['cols']}",source_name)
            with m2: center_card("Battery",str(fm["battery"]),"capacity from file")
            with m3: center_card("Survey goals",str(len(goal_ids)),", ".join(map(str,goal_ids)))
            with m4: center_card("Chargers",str(len(fm["chargers"])),"plus home H")
            left,right=st.columns([1.25,.75],gap="large")
            with left: st.plotly_chart(faculty_map_fig(fm,chosen["path"]),use_container_width=True)
            with right:
                center_card("Highlighted heuristic",selected_heuristic)
                center_card("Path cost",f"{chosen['cost']:.3f}")
                center_card("Expanded nodes",str(len(chosen["expanded"])))
                center_card("Path length",str(len(chosen["path"])))
            comparison=[]
            for hname in HEURISTIC_NAMES:
                result=astar_with_heuristic(fm["graph"],fm["home"],fm["goals"][selected_goal],hname)
                comparison.append({"Heuristic":hname,"Path cost":result["cost"],"Expanded nodes":len(result["expanded"]),
                    "Path length":len(result["path"]),"Admissible":result["admissible"],"Consistent":result["consistent"]})
            st.markdown("### Four-heuristic comparison")
            st.dataframe(pd.DataFrame(comparison).style.format({"Path cost":"{:.3f}"}),use_container_width=True,hide_index=True)
            st.markdown("### Parsed map summary")
            st.write(f"Home: `{fm['home']}` · Chargers: `{fm['chargers']}` · Goals: `{fm['goals']}`")
            with st.expander("Show uploaded map text"): st.code(map_text,language=None)
        except Exception as exc:
            st.error(f"Map could not be parsed: {exc}")

st.markdown(
    '<div class="footer">AERIS Medico Helper · CSE518 Artificial Intelligence · Prepared by <b>Apoorva Mehta</b></div>',
    unsafe_allow_html=True
)
