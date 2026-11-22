import itertools
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from core import *
from map_io import load_faculty_map

checks=0
failures=[]

def check(condition,message):
    global checks
    checks+=1
    if not condition:
        failures.append(message)

def uses_edge(path,a,b):
    wanted={a,b}
    return any({x,y}==wanted for x,y in zip(path,path[1:]))

# Exact Bayesian inference.
for values in itertools.product([False,True],repeat=3):
    evidence=dict(zip(["HazardSevere","VisualDamage","FieldBlocked"],values))
    enum=enumeration_ask("RoadOpen",evidence)
    ve,_=variable_elimination("RoadOpen",evidence)
    check(abs(enum[True]-ve[True])<1e-12,f"BN methods disagree: {evidence}")
    check(abs(sum(enum.values())-1)<1e-12,"Enumeration is not normalized")
    check(abs(sum(ve.values())-1)<1e-12,"VE is not normalized")

# HMM filtering and Viterbi.
obs_values=["Clear","Slow","Obstructed"]
for length in range(1,5):
    for obs in itertools.product(obs_values,repeat=length):
        hist=hmm_filter(list(obs)); path=viterbi(list(obs))
        check(len(hist)==length,"HMM history length mismatch")
        check(len(path)==length,"Viterbi path length mismatch")
        for belief in hist:
            check(abs(float(np.sum(belief))-1)<1e-12,"HMM belief is not normalized")
            check(np.all(belief>=0),"HMM returned a negative probability")

scenarios=[
    lambda seed:{"type":"Earthquake","seed":seed,"mw":6.7,"depth_km":14,"local_shaking":.6,"secondary_hazard":.3,"wind":3.0},
    lambda seed:{"type":"Flood","seed":seed,"water_depth_m":.8,"flow":.5,"rain":.6,"wind":4.0},
    lambda seed:{"type":"Cyclone","seed":seed,"wind":9.0,"gust":15.0,"rain":.5,"debris":.4},
]
weights=[(1,.5,.2),(1,2.3,.45),(1,5,1),(.5,3,.8),(2,1,.1)]

# Search under uncertainty with random confirmed closures.
for make in scenarios:
    for seed in range(1,31):
        world=build_world(make(seed))
        edges=list(world["road"].edges)
        closures=[[],[edges[(seed*3)%len(edges)]],[edges[(seed*5)%len(edges)],edges[(seed*7)%len(edges)]]]
        for closed in closures:
            for a,b in edges:
                world["road"][a][b]["field_blocked"]=False
            for a,b in closed:
                world["road"][a][b]["field_blocked"]=True
            for wt,wr,wc in weights:
                recompute_all_edge_costs(world["road"],wt,wr,wc)
                for target in world["requests"]:
                    u=ucs(world["road"],"Depot",target)
                    for hname in HEURISTIC_NAMES:
                        result=astar_with_heuristic(world["road"],"Depot",target,hname)
                        for a,b in closed:
                            check(not uses_edge(result["path"],a,b),f"A* used confirmed blocked edge {a}-{b}")
                            check(not uses_edge(u["path"],a,b),f"UCS used confirmed blocked edge {a}-{b}")
                        if u["path"]:
                            check(bool(result["path"]),f"{hname} missed a feasible route")
                            check(abs(result["cost"]-u["cost"])<1e-8,f"{hname} differs from UCS")
                            check(result["admissible"],f"{hname} is not admissible")
                            check(result["consistent"],f"{hname} is not consistent")
                        else:
                            check(not result["path"],f"{hname} found a route when ground graph is disconnected")

# The AERIS-specific H3 must be a real component-wise lower bound, and H4 must dominate all component bounds.
for make in scenarios:
    for seed in [2,7,13,23]:
        world=build_world(make(seed))
        for wt,wr,wc in weights:
            recompute_all_edge_costs(world["road"],wt,wr,wc)
            for target in world["requests"]:
                h2=risk_h2_geometric(world["road"],target)
                h3=risk_h3_component(world["road"],target)
                hr=risk_h_relaxed(world["road"],target)
                h4=risk_heuristic_map(world["road"],target,"H4 - Dominant composite")
                for n in world["road"].nodes:
                    check(abs(h4[n]-max(h2[n],h3[n],hr[n]))<1e-10,"H4 is not the dominant composite")
                adm3,cons3=risk_heuristic_diagnostics(world["road"],target,h3)
                check(adm3,"AERIS risk-aware H3 is not admissible")
                check(cons3,"AERIS risk-aware H3 is not consistent")

# The exact reported bug: I-Relief Camp cannot remain on a ground path.
world=build_world(scenarios[0](17))
apply_bn(world,"I","Relief Camp",{"HazardSevere":True,"VisualDamage":True,"FieldBlocked":True},1,2.3,.45)
for hname in HEURISTIC_NAMES:
    route=astar_with_heuristic(world["road"],"Depot","Relief Camp",hname)
    check(not uses_edge(route["path"],"I","Relief Camp"),"Confirmed I-Relief Camp closure was used")
check(road_status_label(world["road"]["I"]["Relief Camp"])=="CONFIRMED BLOCKED","Blocked road label is wrong")

# An HMM update may revise belief but must not clear a confirmed field closure.
old_flag=world["road"]["I"]["Relief Camp"]["field_blocked"]
apply_hmm(world,"I","Relief Camp",["Clear","Clear","Clear"],1,2.3,.45)
check(old_flag and world["road"]["I"]["Relief Camp"]["field_blocked"],"HMM cleared a confirmed field closure")
route=astar_with_heuristic(world["road"],"Depot","Relief Camp","H2 - Geometric lower bound")
check(not uses_edge(route["path"],"I","Relief Camp"),"HMM update reopened blocked edge in search")

# Clearing the field report intentionally restores the edge to probabilistic planning.
apply_bn(world,"I","Relief Camp",{"HazardSevere":False,"VisualDamage":False,"FieldBlocked":False},1,2.3,.45)
check(not world["road"]["I"]["Relief Camp"]["field_blocked"],"Field closure did not clear")

# Delivery physics.
for altitude in [5,10,20,30,50]:
    for wind in [0,3,8,12,18]:
        for radius in [1,3,6]:
            for comp in [0,.5,.9]:
                metrics=precision_drop_metrics(altitude,wind,radius,comp,.8)
                check(.01<=metrics["success_probability"]<=.99,"Drop probability outside bounds")
                samples=landing_test_samples(altitude,wind,radius,comp,.8,500,2026)
                check(len(samples)==500,"Wrong landing sample count")
                check(0<=empirical_drop_success(samples)<=1,"Monte Carlo success outside bounds")

# Editable delivery requests must affect urgency.
world=build_world(scenarios[0](12))
for supply,priority,expected in [
    ("Water pack",.1,"NORMAL"),("Bandage kit",.4,"NORMAL"),("Trauma kit",.1,"CRITICAL"),
    ("Blood units",.2,"CRITICAL"),("Water pack",.95,"CRITICAL")]:
    world["requests"]["Hospital"]={"supply":supply,"quantity":4,"priority":priority}
    state=mdp_state_from_world(world,"Hospital",82,3)
    check(state[3]==expected,f"Urgency mismatch for {supply}/{priority}")

# Delivery-mode recommendations must be feasible and consistent with closures.
for make in scenarios:
    for seed in range(1,31):
        world=build_world(make(seed))
        target=list(world["requests"])[seed%3]
        if seed%3==0:
            path=astar_with_heuristic(world["road"],"Depot",target,"H2 - Geometric lower bound")["path"]
            if len(path)>1:
                world["road"][path[-2]][path[-1]]["field_blocked"]=True
        for battery in [30,55,85]:
            for wind in [3,9,15]:
                best,candidates=recommended_delivery_mode(world,target,battery,wind,.75,"H2 - Geometric lower bound")
                check(len(candidates)==3,"Mode comparison did not return three modes")
                if best is not None:
                    check(best["feasible"],"Recommended mode is infeasible")
                    check(best["mode"] in {"ROAD","UAV","HYBRID"},"Invalid delivery mode")
                    check(abs(best["success"]-max(c["success"] for c in candidates if c["feasible"]))<1e-12,"Mode recommendation is not the best feasible candidate")
                road=next(c for c in candidates if c["mode"]=="ROAD")
                for a,b,d in world["road"].edges(data=True):
                    if d.get("field_blocked"):
                        check(not uses_edge(road["ground_path"],a,b),"Road-mode suggestion used a confirmed closure")

# MDP transitions and solver agreement.
states=mdp_states()
for state in states:
    if state in TERMINALS:
        continue
    actions=feasible_actions(state)
    check(bool(actions),"Non-terminal MDP state has no feasible action")
    for action in ACTIONS:
        tr=transitions(state,action,.6)
        check(abs(sum(p for _,p,_ in tr)-1)<1e-12,"MDP transitions are not normalized")
        check(all(p>=0 for _,p,_ in tr),"MDP has negative transition probability")
for gamma in [.70,.85,.92,.97]:
    for drop in [.10,.30,.60,.85,.98]:
        V1,P1,h1=value_iteration(gamma,1e-7,drop_success=drop)
        V2,P2,h2=policy_iteration(gamma,drop_success=drop)
        normal=[s for s in states if s not in TERMINALS]
        agreement=sum(P1[s]==P2[s] for s in normal)/len(normal)
        check(h1.iloc[-1]["max_delta"]<1e-7,"Value Iteration did not converge")
        check(h2.iloc[-1]["policy_changes"]==0,"Policy Iteration did not stabilize")
        check(agreement>.98,"VI/PI policy agreement is too low")

# End-to-end mission update.
for make in scenarios:
    for seed in [3,11,29,41]:
        world=build_world(make(seed))
        target="Hospital"
        path=astar_with_heuristic(world["road"],"Depot",target,"H2 - Geometric lower bound")["path"]
        if len(path)>1:
            a,b=path[-2],path[-1]
            apply_bn(world,a,b,{"HazardSevere":True,"VisualDamage":True,"FieldBlocked":True},1,4,.45)
            new_path=astar_with_heuristic(world["road"],"Depot",target,"H2 - Geometric lower bound")["path"]
            check(not uses_edge(new_path,a,b),"End-to-end replan used the confirmed closure")
        dm=precision_drop_metrics(20,float(world["params"].get("wind",3.0)),3,.65,.8)
        state=mdp_state_from_world(world,target,70,float(world["params"].get("wind",3.0)))
        _,policy,_=value_iteration(.92,1e-6,drop_success=dm["success_probability"])
        check(policy[state] in feasible_actions(state),"End-to-end MDP action is infeasible")
        mode,_=recommended_delivery_mode(world,target,70,float(world["params"].get("wind",3.0)),dm["success_probability"],"H2 - Geometric lower bound")
        check(mode is not None,"No delivery mode was recommended")

# Faculty map parser must derive map content at run time.
map_path=Path(__file__).resolve().parents[1]/"map_main.txt"
parsed=load_faculty_map(map_path)
check(parsed["rows"]>0 and parsed["cols"]>0,"Faculty map dimensions not parsed")
check(parsed["battery"]>0,"Faculty map battery not parsed")
G=parsed["graph"]; start=parsed["home"]; goals=parsed["goals"]
check(start in G,"Faculty map start node missing")
check(len(goals)>0,"Faculty map goals not detected")

print(f"FINAL_CHECKS={checks}")
print(f"FINAL_FAILURES={len(failures)}")
if failures:
    for f in failures[:100]:
        print("FAIL:",f)
    raise SystemExit(1)
print("FINAL_REGRESSION_PASS")

# Alternate AERIS map must work through the same pipeline
from pathlib import Path as _Path
import json as _json
_alt_spec=_json.loads((_Path(__file__).resolve().parents[1]/"maps"/"aeris_alternate.json").read_text(encoding="utf-8"))
_alt_params={"type":"Earthquake","seed":17,"mw":6.7,"depth_km":14,"local_shaking":.60,"secondary_hazard":.30,"wind":3.0}
_alt_world=build_world_from_spec(_alt_params,_alt_spec)
check(_alt_world.get("map_name")=="AERIS Alternate Network","alternate AERIS map name")
check(set(_alt_world["requests"])=={"Hospital","Relief Camp","Village"},"alternate AERIS destinations")
for _target in _alt_world["requests"]:
    _u=ucs(_alt_world["road"],"Depot",_target)
    for _h in HEURISTIC_NAMES:
        _a=astar_with_heuristic(_alt_world["road"],"Depot",_target,_h)
        check(abs(_a["cost"]-_u["cost"])<1e-8,f"alternate map {_h} optimality")
        check(_a["admissible"],f"alternate map {_h} admissibility")
        check(_a["consistent"],f"alternate map {_h} consistency")

print(f"THREE_MAP_FINAL_CHECKS={checks}")
print(f"THREE_MAP_FINAL_FAILURES={len(failures)}")
if failures:
    raise SystemExit(1)
