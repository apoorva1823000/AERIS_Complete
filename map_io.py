from pathlib import Path
import networkx as nx


def load_faculty_map_text(text):
    lines=[x.rstrip("\\n") for x in text.splitlines() if x.strip()]
    if len(lines) < 6:
        raise ValueError("Map file is incomplete")
    if not lines[0].startswith("ROWS ") or not lines[1].startswith("COLS ") or not lines[2].startswith("BATTERY "):
        raise ValueError("Expected ROWS, COLS and BATTERY headers")

    rows=int(lines[0].split()[1]); cols=int(lines[1].split()[1]); battery=int(lines[2].split()[1])
    if "TERRAIN" not in lines or "CURRENTS" not in lines:
        raise ValueError("Map must contain TERRAIN and CURRENTS sections")
    terrain_start=lines.index("TERRAIN")+1; current_start=lines.index("CURRENTS")+1
    terrain=lines[terrain_start:terrain_start+rows]; currents=lines[current_start:current_start+rows]
    if len(terrain)!=rows or len(currents)!=rows: raise ValueError("Map dimensions do not match ROWS")
    if any(len(r)!=cols for r in terrain+currents): raise ValueError("A terrain/current row does not match COLS")

    allowed_terrain=set(".~#HC123456789"); allowed_currents=set(".^>v<")
    if any(ch not in allowed_terrain for row in terrain for ch in row): raise ValueError("Terrain contains an unsupported symbol")
    if any(ch not in allowed_currents for row in currents for ch in row): raise ValueError("Current grid contains an unsupported symbol")

    G=nx.DiGraph(); goals={}; chargers=[]; home=None
    for r in range(rows):
        for c in range(cols):
            ch=terrain[r][c]
            if ch=='#': continue
            node=(r,c); G.add_node(node,pos=(c,-r),terrain=ch,current=currents[r][c])
            if ch=='H':
                if home is not None: raise ValueError("Map must contain only one H (home)")
                home=node
            elif ch=='C': chargers.append(node)
            elif ch.isdigit():
                goal_id=int(ch)
                if goal_id in goals: raise ValueError(f"Duplicate survey goal {goal_id}")
                goals[goal_id]=node
    if home is None: raise ValueError("Map does not contain H (home/start)")
    if not goals: raise ValueError("Map does not contain any numbered survey goals")

    direction={(0,1):'>',(0,-1):'<',(-1,0):'^',(1,0):'v'}
    opposite={'>':'<','<':'>','^':'v','v':'^'}
    for r,c in list(G.nodes):
        for dr,dc in direction:
            nr,nc=r+dr,c+dc
            if (nr,nc) not in G: continue
            destination_symbol=terrain[nr][nc]
            base=6.0 if destination_symbol=='~' else 2.0
            move=direction[(dr,dc)]; current=currents[nr][nc]
            if current=='.': factor=1.0
            elif move==current: factor=.5
            elif move==opposite[current]: factor=2.0
            else: factor=1.0
            movement_cost=base*factor
            G.add_edge((r,c),(nr,nc),cost=movement_cost,distance=1.0,time=movement_cost,money=0.0,
                       p_open=1.0,risk=0.0,base_component=movement_cost,risk_component=0.0,
                       asset='grid',field_blocked=False)
    return {'graph':G,'home':home,'goals':goals,'chargers':chargers,'battery':battery,
            'rows':rows,'cols':cols,'terrain':terrain,'currents':currents}


def load_faculty_map(path):
    return load_faculty_map_text(Path(path).read_text(encoding='utf-8'))
