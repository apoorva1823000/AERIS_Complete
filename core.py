import math, random, heapq, itertools
from dataclasses import dataclass
from collections import deque
import numpy as np
import pandas as pd
import networkx as nx

@dataclass
class Supply:
    name: str
    urgency: float

SUPPLIES = {
    "Bandage kit": Supply("Bandage kit", .55),
    "Trauma kit": Supply("Trauma kit", .96),
    "Blood units": Supply("Blood units", 1.00),
    "Insulin cold box": Supply("Insulin cold box", .92),
    "Water pack": Supply("Water pack", .45),
}

UAV_MAX_WIND = 12.0

def normalized_severity(p):
    if p["type"]=="Earthquake":
        mag=np.clip((p["mw"]-4.0)/5.0,0,1)
        shallow=np.clip((35-p["depth_km"])/35,0,1)
        return float(np.clip(.35*mag+.15*shallow+.35*p["local_shaking"]+.15*p["secondary_hazard"],0,1))
    if p["type"]=="Flood":
        return float(np.clip(.50*min(1,p["water_depth_m"]/1.5)+.25*p["flow"]+.25*p["rain"],0,1))
    return float(np.clip(.45*min(1,p["wind"]/20)+.25*min(1,p["gust"]/30)+.15*p["rain"]+.15*p["debris"],0,1))

def build_world_from_spec(p, spec):
    rng=random.Random(int(p["seed"]))
    sev=normalized_severity(p)
    coords={k:tuple(v) for k,v in spec["coords"].items()}
    edges=[tuple(x) for x in spec["edges"]]
    G=nx.Graph()
    for n,pos in coords.items():
        G.add_node(n,pos=pos)
    for a,b,asset in edges:
        dist=math.dist(coords[a],coords[b])
        local=rng.random()
        asset_penalty=0.0
        if asset=="bridge":
            asset_penalty={"Earthquake":.18,"Flood":.15,"Cyclone":.05}[p["type"]]
        elif asset=="lowland":
            asset_penalty={"Earthquake":.03,"Flood":.24,"Cyclone":.10}[p["type"]]
        if p["type"]=="Earthquake":
            hazard=np.clip(.54*sev+.26*local+.12*p["secondary_hazard"]+asset_penalty,0,1.4)
            p_open=1/(1+math.exp(6*(hazard-.63)))
            speed=max(.20,1-.62*hazard)
        elif p["type"]=="Flood":
            midy=(coords[a][1]+coords[b][1])/2
            lowland=max(0,(3.2-midy)/3.2)
            hazard=np.clip(.42*sev+.24*local+.24*lowland*min(1,p["water_depth_m"]/1.1)+asset_penalty,0,1.4)
            p_open=1/(1+math.exp(7*(hazard-.56)))
            speed=max(.10,1-.78*hazard)
        else:
            hazard=np.clip(.44*sev+.26*local+.22*p["debris"]+asset_penalty,0,1.4)
            p_open=1/(1+math.exp(6*(hazard-.66)))
            speed=max(.18,1-.60*hazard)
        p_open=float(np.clip(p_open,.02,.995))
        travel_time=dist/max(.07,speed)
        money=.35*dist
        risk=-math.log(p_open)
        time_component=travel_time
        risk_component=2.3*risk
        operating_component=.45*money
        base_component=time_component+operating_component
        cost=base_component+risk_component
        G.add_edge(a,b,distance=dist,time=travel_time,money=money,p_open=p_open,
                   risk=risk,cost=cost,time_component=time_component,
                   risk_component=risk_component,operating_component=operating_component,
                   base_component=base_component,asset=asset,visual_damage=float(local),field_blocked=False)
    requests={k:dict(v) for k,v in spec["requests"].items()}
    return {"params":dict(p),"severity":sev,"coords":coords,"road":G,"requests":requests,"map_name":spec.get("name","AERIS Network")}

def default_aeris_spec():
    return {
        "name":"AERIS Default Network",
        "coords":{"Depot":[0,3],"A":[2,5],"B":[2,2],"C":[4,6],"D":[4,3],"E":[4,.8],
                  "F":[6,5.2],"G":[6,2.2],"H":[8,6],"I":[8,3],"J":[8,.6],
                  "Hospital":[10,5.5],"Relief Camp":[10,2.5],"Village":[10,.5]},
        "edges":[["Depot","A","road"],["Depot","B","road"],["A","C","road"],["A","D","road"],
                 ["B","D","road"],["B","E","road"],["C","F","road"],["D","F","road"],
                 ["D","G","road"],["E","G","lowland"],["F","H","road"],["F","I","road"],
                 ["G","I","road"],["G","J","road"],["H","Hospital","road"],["I","Hospital","road"],
                 ["I","Relief Camp","road"],["J","Relief Camp","road"],["J","Village","road"],
                 ["I","Village","road"],["Depot","D","bridge"],["B","G","lowland"],["D","I","bridge"],["G","Hospital","bridge"]],
        "requests":{"Hospital":{"supply":"Trauma kit","quantity":3,"priority":1.0},
                    "Relief Camp":{"supply":"Water pack","quantity":10,"priority":.62},
                    "Village":{"supply":"Bandage kit","quantity":3,"priority":.76}}
    }

def build_world(p):
    return build_world_from_spec(p, default_aeris_spec())

def ground_edge_available(d):
    return not bool(d.get("field_blocked", False))

def ground_graph(G):
    H=nx.DiGraph() if G.is_directed() else nx.Graph()
    H.add_nodes_from(G.nodes(data=True))
    for a,b,d in G.edges(data=True):
        if ground_edge_available(d):
            H.add_edge(a,b,**dict(d))
    return H

def recompute_edge_cost(G,a,b,w_t=1.0,w_r=2.3,w_c=.45):
    d=G[a][b]
    d["p_open"]=float(np.clip(d["p_open"],.02,.995))
    d["risk"]=-math.log(d["p_open"])
    d["time_component"]=float(w_t)*float(d["time"])
    d["risk_component"]=float(w_r)*d["risk"]
    d["operating_component"]=float(w_c)*float(d.get("money",.35*d["distance"]))
    d["base_component"]=d["time_component"]+d["operating_component"]
    d["cost"]=d["base_component"]+d["risk_component"]

def recompute_all_edge_costs(G,w_t=1.0,w_r=2.3,w_c=.45):
    for a,b in G.edges:
        recompute_edge_cost(G,a,b,w_t,w_r,w_c)

def min_cost_per_distance(G):
    vals=[]
    for a,b,d in G.edges(data=True):
        vals.append(float(d["cost"])/max(float(d["distance"]),1e-9))
    return min(vals) if vals else 0.0

def heuristic(G,n,goal):
    p1=G.nodes[n]["pos"];p2=G.nodes[goal]["pos"]
    return math.dist(p1,p2)*min_cost_per_distance(G)

def astar(G,start,goal):
    return astar_with_heuristic(G,start,goal,"H2 - Geometric lower bound")

def ucs(G,start,goal):
    g={start:0.0}; parent={start:None}; closed=set(); counter=0
    pq=[(0.0,counter,start)]; expanded=[]
    while pq:
        _,_,n=heapq.heappop(pq)
        if n in closed:
            continue
        closed.add(n); expanded.append(n)
        if n==goal:
            break
        for nb in G.neighbors(n):
            if not ground_edge_available(G[n][nb]):
                continue
            ng=g[n]+float(G[n][nb]["cost"])
            if ng<g.get(nb,float("inf")):
                g[nb]=ng; parent[nb]=n; counter+=1
                heapq.heappush(pq,(ng,counter,nb))
    if goal not in parent:
        return {"path":[],"cost":float("inf"),"expanded":expanded}
    path=[]; cur=goal
    while cur is not None:
        path.append(cur); cur=parent[cur]
    path=path[::-1]
    return {"path":path,"cost":sum(G[a][b]["cost"] for a,b in zip(path,path[1:])),"expanded":expanded}

HEURISTIC_NAMES = [
    "H1 - Zero",
    "H2 - Geometric lower bound",
    "H3 - Risk-aware component lower bound",
    "H4 - Dominant composite",
]

def risk_h2_geometric(G, goal):
    ratios=[]
    for a,b,d in G.edges(data=True):
        if not ground_edge_available(d):
            continue
        dist=max(float(d.get("distance",math.dist(G.nodes[a]["pos"],G.nodes[b]["pos"]))),1e-9)
        ratios.append(float(d["cost"])/dist)
    k=min(ratios) if ratios else 0.0
    gp=G.nodes[goal]["pos"]
    return {n:math.dist(G.nodes[n]["pos"],gp)*k for n in G.nodes}

def risk_h3_component(G, goal):
    """Lower bound that follows the AERIS edge-cost structure.

    The remaining cost is split into a travel/operating part and a risk part.
    Straight-line distance lower-bounds the first part, while the minimum number
    of remaining ground edges lower-bounds how many risk penalties are unavoidable.
    """
    H=ground_graph(G)
    available=[(a,b,d) for a,b,d in G.edges(data=True) if ground_edge_available(d)]
    if not available:
        return {n:0.0 for n in G.nodes}

    base_ratios=[]
    risk_terms=[]
    for a,b,d in available:
        dist=max(float(d.get("distance",math.dist(G.nodes[a]["pos"],G.nodes[b]["pos"]))),1e-9)
        risk_term=float(d.get("risk_component",0.0))
        base_term=float(d.get("base_component",float(d["cost"])-risk_term))
        base_ratios.append(base_term/dist)
        risk_terms.append(max(0.0,risk_term))

    min_base_per_distance=min(base_ratios) if base_ratios else 0.0
    min_risk_per_edge=min(risk_terms) if risk_terms else 0.0
    gp=G.nodes[goal]["pos"]

    if G.is_directed():
        reverse=H.reverse(copy=False)
        hop_to_goal=nx.single_source_shortest_path_length(reverse,goal) if goal in reverse else {}
    else:
        hop_to_goal=nx.single_source_shortest_path_length(H,goal) if goal in H else {}

    h={}
    for n in G.nodes:
        if n not in hop_to_goal:
            h[n]=0.0
            continue
        geometric=math.dist(G.nodes[n]["pos"],gp)*min_base_per_distance
        unavoidable_risk=hop_to_goal[n]*min_risk_per_edge
        h[n]=float(geometric+unavoidable_risk)
    return h

def risk_h_relaxed(G, goal):
    H=nx.DiGraph() if G.is_directed() else nx.Graph()
    H.add_nodes_from(G.nodes(data=True))
    for a,b,d in G.edges(data=True):
        if not ground_edge_available(d):
            continue
        geo=math.dist(G.nodes[a]["pos"],G.nodes[b]["pos"])
        H.add_edge(a,b,cost=min(float(d["cost"]),float(geo)))
    h={}
    for n in G.nodes:
        try:
            h[n]=float(nx.shortest_path_length(H,n,goal,weight="cost"))
        except Exception:
            h[n]=0.0
    return h

def risk_heuristic_map(G, goal, name):
    if name=="H1 - Zero":
        return {n:0.0 for n in G.nodes}
    if name=="H2 - Geometric lower bound":
        return risk_h2_geometric(G,goal)
    if name=="H3 - Risk-aware component lower bound":
        return risk_h3_component(G,goal)
    if name=="H4 - Dominant composite":
        h2=risk_h2_geometric(G,goal)
        h3=risk_h3_component(G,goal)
        hr=risk_h_relaxed(G,goal)
        return {n:max(h2[n],h3[n],hr[n]) for n in G.nodes}
    raise ValueError(f"Unknown heuristic: {name}")

def risk_heuristic_diagnostics(G, goal, hmap):
    H=ground_graph(G)
    exact={}
    for n in G.nodes:
        try:
            exact[n]=float(nx.shortest_path_length(H,n,goal,weight="cost"))
        except Exception:
            exact[n]=float("inf")
    admissible=all(hmap[n]<=exact[n]+1e-9 for n in G.nodes if np.isfinite(exact[n]))
    consistent=True
    for a,b,d in G.edges(data=True):
        if not ground_edge_available(d):
            continue
        c=float(d["cost"])
        if hmap[a]>c+hmap[b]+1e-9:
            consistent=False; break
        if not G.is_directed() and hmap[b]>c+hmap[a]+1e-9:
            consistent=False; break
    return admissible,consistent

def astar_with_heuristic(G, start, goal, heuristic_name="H2 - Geometric lower bound"):
    hmap=risk_heuristic_map(G,goal,heuristic_name)
    g={start:0.0}; parent={start:None}; closed=set(); expanded=[]; steps=[]; counter=0
    pq=[(hmap[start],counter,start)]
    while pq:
        _,_,n=heapq.heappop(pq)
        if n in closed:
            continue
        closed.add(n); expanded.append(n)
        steps.append({"expanded":n,"frontier":[x[2] for x in pq],"closed":list(closed),"g":dict(g),"h":dict(hmap)})
        if n==goal:
            break
        for nb in G.neighbors(n):
            if not ground_edge_available(G[n][nb]):
                continue
            ng=g[n]+float(G[n][nb]["cost"])
            if ng<g.get(nb,float("inf")):
                g[nb]=ng; parent[nb]=n; counter+=1
                heapq.heappush(pq,(ng+hmap[nb],counter,nb))
    if goal not in parent:
        adm,cons=risk_heuristic_diagnostics(G,goal,hmap)
        return {"path":[],"cost":float("inf"),"expanded":expanded,"steps":steps,"reliability":0.0,"admissible":adm,"consistent":cons}
    path=[]; cur=goal
    while cur is not None:
        path.append(cur); cur=parent[cur]
    path=path[::-1]
    cost=sum(float(G[a][b]["cost"]) for a,b in zip(path,path[1:]))
    reliability=float(np.prod([float(G[a][b]["p_open"]) for a,b in zip(path,path[1:])]))
    adm,cons=risk_heuristic_diagnostics(G,goal,hmap)
    return {"path":path,"cost":cost,"expanded":expanded,"steps":steps,"reliability":reliability,"admissible":adm,"consistent":cons}

BN_ORDER=["HazardSevere","VisualDamage","FieldBlocked","RoadOpen"]
BN_PARENTS={
    "HazardSevere":[],
    "VisualDamage":[],
    "FieldBlocked":[],
    "RoadOpen":["HazardSevere","VisualDamage","FieldBlocked"],
}
BN_CPT={
    "HazardSevere":{():.45},
    "VisualDamage":{():.35},
    "FieldBlocked":{():.25},
    "RoadOpen":{
        (False,False,False):.96,(False,False,True):.38,
        (False,True,False):.58,(False,True,True):.18,
        (True,False,False):.72,(True,False,True):.24,
        (True,True,False):.36,(True,True,True):.08,
    },
}
def bn_p(var,val,e):
    p=BN_CPT[var][tuple(e[x] for x in BN_PARENTS[var])]
    return p if val else 1-p

def enum_all(vars_,e):
    if not vars_:return 1.0
    y=vars_[0]
    if y in e:return bn_p(y,e[y],e)*enum_all(vars_[1:],e)
    return sum(bn_p(y,v,{**e,y:v})*enum_all(vars_[1:],{**e,y:v}) for v in [True,False])

def enumeration_ask(query,evidence):
    d={q:enum_all(BN_ORDER,{**evidence,query:q}) for q in [True,False]}
    z=sum(d.values())
    return {k:v/z for k,v in d.items()}

def _factor_from_cpt(var,evidence):
    scope=[x for x in BN_PARENTS[var]+[var] if x not in evidence]
    rows={}
    full=BN_PARENTS[var]+[var]
    for vals in itertools.product([False,True],repeat=len(full)):
        a=dict(zip(full,vals))
        if any(k in evidence and a[k]!=evidence[k] for k in evidence if k in a):continue
        rows[tuple(a[x] for x in scope)]=bn_p(var,a[var],a)
    return {"scope":scope,"rows":rows}

def _factor_product(factors):
    if not factors:return {"scope":[],"rows":{():1.0}}
    out=factors[0]
    for f in factors[1:]:
        scope=list(dict.fromkeys(out["scope"]+f["scope"]))
        rows={}
        for vals in itertools.product([False,True],repeat=len(scope)):
            a=dict(zip(scope,vals))
            k1=tuple(a[x] for x in out["scope"]);k2=tuple(a[x] for x in f["scope"])
            if k1 in out["rows"] and k2 in f["rows"]:
                rows[vals]=out["rows"][k1]*f["rows"][k2]
        out={"scope":scope,"rows":rows}
    return out

def _sum_out(var,f):
    if var not in f["scope"]:return f
    scope=[x for x in f["scope"] if x!=var];rows={}
    for vals in itertools.product([False,True],repeat=len(scope)):
        a=dict(zip(scope,vals));total=0.0
        for v in [False,True]:
            aa={**a,var:v};total+=f["rows"].get(tuple(aa[x] for x in f["scope"]),0.0)
        rows[vals]=total
    return {"scope":scope,"rows":rows}

def variable_elimination(query,evidence):
    factors=[_factor_from_cpt(v,evidence) for v in BN_ORDER];trace=[]
    hidden=[v for v in BN_ORDER if v not in evidence and v!=query]
    for h in hidden:
        hit=[f for f in factors if h in f["scope"]]
        factors=[f for f in factors if h not in f["scope"]]
        prod=_factor_product(hit);red=_sum_out(h,prod);factors.append(red)
        trace.append({"eliminated":h,"combined_factors":len(hit),
                      "product_scope":", ".join(prod["scope"]) or "scalar",
                      "result_scope":", ".join(red["scope"]) or "scalar"})
    final=_factor_product(factors);qi=final["scope"].index(query);scores={}
    for qv in [False,True]:
        scores[qv]=sum(val for key,val in final["rows"].items() if key[qi]==qv)
    z=sum(scores.values())
    return {k:v/z for k,v in scores.items()},trace

def edge_default_evidence(world,a,b):
    d=world["road"][a][b]
    return {
        "HazardSevere":bool(world["severity"]>=.58),
        "VisualDamage":bool(float(d.get("visual_damage",0))>=.55),
        "FieldBlocked":bool(d.get("field_blocked",False))
    }

def apply_bn(world,a,b,evidence,w_t=1.0,w_r=2.3,w_c=.45):
    en=enumeration_ask("RoadOpen",evidence)
    ve,trace=variable_elimination("RoadOpen",evidence)
    world["road"][a][b]["p_open"]=float(ve[True])
    world["road"][a][b]["field_blocked"]=bool(evidence["FieldBlocked"])
    world["road"][a][b]["evidence_source"]="Bayesian Network"
    recompute_edge_cost(world["road"],a,b,w_t,w_r,w_c)
    return en,ve,trace

HMM_STATES=["Open","Degraded","Blocked"]
T=np.array([[.80,.17,.03],[.18,.63,.19],[.05,.24,.71]],dtype=float)
E={
    "Clear":np.array([.84,.14,.02]),
    "Slow":np.array([.17,.66,.17]),
    "Obstructed":np.array([.03,.22,.75])
}
HMM_PRIOR=np.array([.52,.33,.15],dtype=float)

def hmm_filter(obs,prior=None):
    b=np.array(HMM_PRIOR if prior is None else prior,dtype=float);hist=[]
    for o in obs:
        b=(b@T)*E[o]
        b=b/b.sum()
        hist.append(b.copy())
    return hist

def viterbi(obs):
    if not obs:return []
    dp=np.log(HMM_PRIOR+1e-12)+np.log(E[obs[0]]+1e-12);backs=[]
    for o in obs[1:]:
        nd=np.zeros(3);bp=np.zeros(3,dtype=int)
        for j in range(3):
            scores=dp+np.log(T[:,j]+1e-12)
            bp[j]=int(np.argmax(scores))
            nd[j]=scores[bp[j]]+np.log(E[o][j]+1e-12)
        dp=nd;backs.append(bp)
    last=int(np.argmax(dp));path=[last]
    for bp in backs[::-1]:
        last=int(bp[last]);path.append(last)
    return [HMM_STATES[i] for i in path[::-1]]

def apply_hmm(world,a,b,obs,w_t=1.0,w_r=2.3,w_c=.45):
    hist=hmm_filter(obs)
    if not hist:raise ValueError("At least one observation is required.")
    belief=hist[-1]
    p_open=float(np.clip(belief[0]+.45*belief[1],.02,.995))
    d=world["road"][a][b]
    d["p_open"]=p_open
    d["hmm_belief"]={HMM_STATES[i]:float(belief[i]) for i in range(3)}
    d["evidence_source"]="HMM"
    recompute_edge_cost(world["road"],a,b,w_t,w_r,w_c)
    return d["hmm_belief"]





GRAVITY = 9.81

def drop_fall_time(altitude_m):
    altitude_m=max(0.0,float(altitude_m))
    return math.sqrt(2.0*altitude_m/GRAVITY) if altitude_m>0 else 0.0

def drop_drift_m(altitude_m, wind_mps, compensation_fraction=0.0):
    """
    compensation_fraction in [0,1] represents how much horizontal drift
    the controller predicts/corrects before release.
    """
    t=drop_fall_time(altitude_m)
    raw=float(wind_mps)*t
    comp=float(np.clip(compensation_fraction,0,1))
    return raw*(1.0-comp)

def precision_drop_success_probability(
    altitude_m,
    wind_mps,
    target_radius_m=3.0,
    compensation_fraction=.65,
    release_uncertainty_m=.8,
):
    """
    Returns a probability in [0.01,0.99].

    The effective miss distance combines residual wind drift and a fixed
    release/positioning uncertainty term. Probability decreases smoothly
    as miss distance grows relative to the safe target radius.
    """
    radius=max(.25,float(target_radius_m))
    residual=drop_drift_m(altitude_m,wind_mps,compensation_fraction)
    sigma=max(.05,float(release_uncertainty_m))
    effective_miss=math.sqrt(residual**2 + sigma**2)
    ratio=effective_miss/radius
    p=math.exp(-0.5*ratio**2)
    return float(np.clip(p,.01,.99))

def precision_drop_metrics(
    altitude_m,
    wind_mps,
    target_radius_m=3.0,
    compensation_fraction=.65,
    release_uncertainty_m=.8,
):
    t=drop_fall_time(altitude_m)
    raw=float(wind_mps)*t
    residual=drop_drift_m(altitude_m,wind_mps,compensation_fraction)
    p=precision_drop_success_probability(
        altitude_m,wind_mps,target_radius_m,compensation_fraction,release_uncertainty_m
    )
    return {
        "fall_time_s":t,
        "raw_drift_m":raw,
        "residual_drift_m":residual,
        "success_probability":p,
    }




def road_status_label(d):
    """
    Short road status used in the interface.
    """
    if bool(d.get("field_blocked", False)):
        return "CONFIRMED BLOCKED"
    p=float(d.get("p_open",1.0))
    if p < .25: return "VERY LOW CONFIDENCE"
    if p < .50: return "LOW CONFIDENCE"
    if p < .75: return "UNCERTAIN"
    return "LIKELY OPEN"

def landing_test_samples(
    altitude_m,
    wind_mps,
    target_radius_m=3.0,
    compensation_fraction=.65,
    release_uncertainty_m=.8,
    n=250,
    seed=17,
):
    """
    Course-level Monte Carlo visualization of precision delivery.

    Coordinates are landing error relative to the target centre.
    Residual wind drift is applied along +x. Independent Gaussian release/
    positioning noise is added in x and y.
    """
    rng=np.random.default_rng(int(seed))
    residual=drop_drift_m(altitude_m,wind_mps,compensation_fraction)
    sigma=max(.05,float(release_uncertainty_m))
    x=residual+rng.normal(0,sigma,int(n))
    y=rng.normal(0,sigma,int(n))
    r=np.sqrt(x*x+y*y)
    success=r<=float(target_radius_m)
    return pd.DataFrame({"x_m":x,"y_m":y,"distance_m":r,"success":success})

def empirical_drop_success(samples):
    if samples is None or len(samples)==0:
        return 0.0
    return float(samples["success"].mean())


def best_hybrid_plan(world,target,battery_pct,wind_mps,drop_success,heuristic_name="H2 - Geometric lower bound"):
    G=world["road"]
    wind_bin=bin_wind(wind_mps) if "bin_wind" in globals() else ("SAFE" if wind_mps<7 else ("MARGINAL" if wind_mps<=UAV_MAX_WIND else "UNSAFE"))
    batt_bin=bin_battery(battery_pct) if "bin_battery" in globals() else ("LOW" if battery_pct<40 else ("MEDIUM" if battery_pct<75 else "HIGH"))
    if batt_bin=="LOW" or wind_bin=="UNSAFE":
        return None
    candidates=[]
    target_pos=G.nodes[target]["pos"]
    for handoff in G.nodes:
        if handoff in {"Depot",target}:
            continue
        route=astar_with_heuristic(G,"Depot",handoff,heuristic_name)
        if not route["path"]:
            continue
        air_distance=math.dist(G.nodes[handoff]["pos"],target_pos)
        candidates.append((air_distance,-route["reliability"],handoff,route))
    if not candidates:
        return None
    _,_,handoff,route=min(candidates)
    success=hybrid_success(bin_road(route["reliability"]),batt_bin,wind_bin,drop_success)
    return {"mode":"HYBRID","feasible":True,"success":success,"ground_path":route["path"],"air_from":handoff,"air_to":target,
            "description":f"Road to {handoff}, then UAV to {target}"}

def delivery_mode_candidates(world,target,battery_pct,wind_mps,drop_success,heuristic_name="H2 - Geometric lower bound"):
    G=world["road"]
    road=astar_with_heuristic(G,"Depot",target,heuristic_name)
    batt=bin_battery(battery_pct)
    wind=bin_wind(wind_mps)
    rows=[]
    rows.append({"mode":"ROAD","feasible":bool(road["path"]),"success":road["reliability"] if road["path"] else 0.0,
                 "ground_path":road["path"],"air_from":None,"air_to":None,
                 "description":"Use the current ground route" if road["path"] else "No feasible ground route under confirmed closures"})
    uav_ok=batt!="LOW" and wind!="UNSAFE"
    rows.append({"mode":"UAV","feasible":uav_ok,"success":uav_success(batt,wind,drop_success) if uav_ok else 0.0,
                 "ground_path":[],"air_from":"Depot","air_to":target,
                 "description":f"Direct UAV delivery from Depot to {target}" if uav_ok else "UAV is not feasible with the current battery/wind state"})
    hybrid=best_hybrid_plan(world,target,battery_pct,wind_mps,drop_success,heuristic_name)
    if hybrid is None:
        rows.append({"mode":"HYBRID","feasible":False,"success":0.0,"ground_path":[],"air_from":None,"air_to":None,
                     "description":"No feasible road-UAV handoff is available"})
    else:
        rows.append(hybrid)
    return rows

def recommended_delivery_mode(world,target,battery_pct,wind_mps,drop_success,heuristic_name="H2 - Geometric lower bound"):
    candidates=delivery_mode_candidates(world,target,battery_pct,wind_mps,drop_success,heuristic_name)
    feasible=[c for c in candidates if c["feasible"]]
    return max(feasible,key=lambda x:x["success"]) if feasible else None, candidates

ROAD=["LOW","MEDIUM","HIGH"]
BATTERY=["LOW","MEDIUM","HIGH"]
WIND=["SAFE","MARGINAL","UNSAFE"]
URGENCY=["NORMAL","CRITICAL"]
CHARGE=["NO","YES"]
STAGE=["DEPOT","ENROUTE"]
ACTIONS=["ROAD","UAV","HYBRID","VERIFY","RECHARGE","REROUTE","WAIT"]
TERMINALS=["DELIVERED","FAILED"]

def mdp_states():
    return list(itertools.product(ROAD,BATTERY,WIND,URGENCY,CHARGE,STAGE))+TERMINALS

def bin_road(p):return "LOW" if p<.40 else ("MEDIUM" if p<.75 else "HIGH")
def bin_battery(p):return "LOW" if p<40 else ("MEDIUM" if p<75 else "HIGH")
def bin_wind(w):return "SAFE" if w<7 else ("MARGINAL" if w<=UAV_MAX_WIND else "UNSAFE")

def mdp_state_from_world(world,target,battery_pct,wind_mps):
    route=astar(world["road"],"Depot",target)
    rel=route["reliability"] if route["path"] else 0.0
    req=world["requests"][target]
    urg=max(float(req["priority"]),SUPPLIES[req["supply"]].urgency)
    return (
        bin_road(rel),bin_battery(battery_pct),bin_wind(wind_mps),
        "CRITICAL" if urg>=.8 else "NORMAL","YES","DEPOT"
    )

def feasible_actions(s):
    if s in TERMINALS:return []
    road,batt,wind,urg,charge,stage=s
    out=["ROAD","VERIFY","REROUTE","WAIT"]
    if batt!="LOW" and wind!="UNSAFE":out.append("UAV")
    if road!="LOW" and batt!="LOW" and wind!="UNSAFE":out.append("HYBRID")
    if charge=="YES" and batt!="HIGH":out.append("RECHARGE")
    return out

def road_success(r):return {"LOW":.25,"MEDIUM":.62,"HIGH":.90}[r]
def uav_success(b,w,drop_success=1.0):
    return float(np.clip(
        {"LOW":.32,"MEDIUM":.72,"HIGH":.94}[b]
        *{"SAFE":1.0,"MARGINAL":.78,"UNSAFE":.08}[w]
        *float(np.clip(drop_success,.01,1.0)),
        .02,.98
    ))

def hybrid_success(r,b,w,drop_success=1.0):
    return float(np.clip(
        (road_success(r)**.55)
        *(uav_success(b,w,drop_success)**.55),
        .02,.96
    ))
def delivery_reward(u,ok=True):
    if ok:return 160. if u=="CRITICAL" else 100.
    return -190. if u=="CRITICAL" else -120.

def transitions(s,a,drop_success=1.0):
    if s in TERMINALS:return [(s,1.0,0.0)]
    if a not in feasible_actions(s):
        return [(s,1.0,-100.0)]
    road,batt,wind,urg,charge,stage=s
    if a=="ROAD":
        ps=road_success(road);fail=(road,batt,wind,urg,charge,"ENROUTE")
        out=[("DELIVERED",ps,delivery_reward(urg,True)-8),(fail,1-ps,delivery_reward(urg,False)*.22-16)]
    elif a=="UAV":
        ps=uav_success(batt,wind,drop_success);nb="LOW" if batt in ["LOW","MEDIUM"] else "MEDIUM"
        fail=(road,nb,wind,urg,charge,"ENROUTE")
        out=[("DELIVERED",ps,delivery_reward(urg,True)-14),(fail,1-ps,delivery_reward(urg,False)*.28-20)]
    elif a=="HYBRID":
        ps=hybrid_success(road,batt,wind,drop_success);nb="LOW" if batt=="MEDIUM" else ("MEDIUM" if batt=="HIGH" else "LOW")
        fail=(road,nb,wind,urg,charge,"ENROUTE")
        out=[("DELIVERED",ps,delivery_reward(urg,True)-18),(fail,1-ps,delivery_reward(urg,False)*.24-22)]
    elif a=="VERIFY":
        if road=="MEDIUM":out=[(("HIGH",batt,wind,urg,charge,stage),.58,-7),(("LOW",batt,wind,urg,charge,stage),.42,-7)]
        elif road=="LOW":out=[(("LOW",batt,wind,urg,charge,stage),.82,-7),(("MEDIUM",batt,wind,urg,charge,stage),.18,-7)]
        else:out=[(("HIGH",batt,wind,urg,charge,stage),.86,-7),(("MEDIUM",batt,wind,urg,charge,stage),.14,-7)]
    elif a=="RECHARGE":
        out=[((road,"HIGH",wind,urg,charge,stage),1.0,-10)]
    elif a=="REROUTE":
        if road=="LOW":out=[(("MEDIUM",batt,wind,urg,charge,"ENROUTE"),.58,-9),(("LOW",batt,wind,urg,charge,"ENROUTE"),.42,-9)]
        elif road=="MEDIUM":out=[(("HIGH",batt,wind,urg,charge,"ENROUTE"),.45,-9),(("MEDIUM",batt,wind,urg,charge,"ENROUTE"),.55,-9)]
        else:out=[((road,batt,wind,urg,charge,"ENROUTE"),1.0,-9)]
    else:
        road_next={
            "LOW":[("LOW",.68),("MEDIUM",.27),("HIGH",.05)],
            "MEDIUM":[("LOW",.20),("MEDIUM",.60),("HIGH",.20)],
            "HIGH":[("LOW",.05),("MEDIUM",.22),("HIGH",.73)]
        }[road]
        urg_next=[(urg,1.0)] if urg=="CRITICAL" else [("NORMAL",.82),("CRITICAL",.18)]
        out=[((nr,batt,wind,nu,charge,stage),pr*pu,-6) for nr,pr in road_next for nu,pu in urg_next]
    z=sum(p for _,p,_ in out)
    return [(sp,p/z,r) for sp,p,r in out]

def q_value(s,a,V,gamma,drop_success=1.0):
    return sum(p*(r+gamma*V[sp]) for sp,p,r in transitions(s,a,drop_success))

def value_iteration(gamma=.92,epsilon=1e-6,max_iter=500,drop_success=1.0):
    states=mdp_states();V={s:0.0 for s in states};hist=[]
    for k in range(max_iter):
        NV={};delta=0.0
        for s in states:
            if s in TERMINALS:NV[s]=0.0
            else:
                acts=feasible_actions(s)
                NV[s]=max(q_value(s,a,V,gamma,drop_success) for a in acts)
            delta=max(delta,abs(NV[s]-V[s]))
        V=NV;hist.append({"iteration":k+1,"max_delta":delta})
        if delta<epsilon:break
    policy={s:("TERMINAL" if s in TERMINALS else max(feasible_actions(s),key=lambda a:q_value(s,a,V,gamma,drop_success))) for s in states}
    return V,policy,pd.DataFrame(hist)

def policy_iteration(gamma=.92,eval_epsilon=1e-7,max_iter=100,drop_success=1.0):
    states=mdp_states()
    policy={s:("TERMINAL" if s in TERMINALS else feasible_actions(s)[0]) for s in states}
    trace=[]
    for outer in range(max_iter):
        V={s:0.0 for s in states}
        for _ in range(1000):
            NV={};delta=0.0
            for s in states:
                NV[s]=0.0 if s in TERMINALS else q_value(s,policy[s],V,gamma,drop_success)
                delta=max(delta,abs(NV[s]-V[s]))
            V=NV
            if delta<eval_epsilon:break
        changes=0
        for s in states:
            if s in TERMINALS:continue
            new=max(feasible_actions(s),key=lambda a:q_value(s,a,V,gamma,drop_success))
            if new!=policy[s]:changes+=1
            policy[s]=new
        trace.append({"iteration":outer+1,"policy_changes":changes})
        if changes==0:break
    return V,policy,pd.DataFrame(trace)

def simulate_policy(start,policy,steps=10,seed=1,drop_success=1.0):
    rng=np.random.default_rng(seed);s=start;rows=[];total=0.0
    for t in range(steps):
        if s in TERMINALS:break
        a=policy[s];tr=transitions(s,a,drop_success);probs=np.array([x[1] for x in tr]);probs/=probs.sum()
        idx=int(rng.choice(len(tr),p=probs));sp,p,r=tr[idx];total+=r
        rows.append({"t":t,"state":str(s),"action":a,"reward":round(r,2),"next_state":str(sp)})
        s=sp
    return pd.DataFrame(rows),total
