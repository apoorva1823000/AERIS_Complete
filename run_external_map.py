import sys
from core import HEURISTIC_NAMES, astar_with_heuristic
from map_io import load_faculty_map


def main(path):
    m=load_faculty_map(path)
    print(f"Map: {m['rows']} x {m['cols']}, battery={m['battery']}")
    print(f"Home: {m['home']}; goals: {sorted(m['goals'])}")
    for goal_id,goal in sorted(m['goals'].items()):
        print(f"\nGoal {goal_id}: {goal}")
        for h in HEURISTIC_NAMES:
            r=astar_with_heuristic(m['graph'],m['home'],goal,h)
            print(f"{h}: cost={r['cost']:.3f}, expanded={len(r['expanded'])}, path_len={len(r['path'])}")


if __name__=='__main__':
    main(sys.argv[1] if len(sys.argv)>1 else 'map_main.txt')
