# AERIS Medico Helper - CSE518 Course Project

AERIS is my course project for post-disaster medical and relief delivery. I kept the final implementation as one connected workflow rather than separate demonstrations of the course topics.

## Project flow

1. Define the disaster scenario and the delivery request.
2. Plan with A* and compare H1-H4.
3. Update a selected road using Bayesian evidence.
4. Refine the same road over time with the HMM.
5. Re-plan with the updated road state.
6. Estimate UAV delivery success when an aerial leg is considered.
7. Solve the MDP for the next action.
8. Compare ROAD, UAV and HYBRID as practical delivery modes and display the suggested plan on the map.

A confirmed field report of blockage is treated as a hard ground-routing constraint. Other uncertain observations update P(open) and the risk-aware edge cost.

## Run the app

```bash
pip install -r requirements.txt
streamlit run app.py
```


## A* heuristics

- `H1 - Zero` - UCS-equivalent baseline.
- `H2 - Geometric lower bound` - straight-line distance scaled by the minimum active cost per unit distance.
- `H3 - Risk-aware component lower bound` - an AERIS-specific lower bound that separates unavoidable travel/operating cost from the minimum unavoidable road-risk penalty over the remaining hops.
- `H4 - Dominant composite` - the maximum of H2, H3, and the relaxed-network lower bound.

All four are checked for admissibility and consistency, and their final path cost is compared with UCS.

## Faculty map format

The search code also reads the supplied `map_main.txt` format at run time. The start, goals, chargers, terrain and currents are parsed from the file rather than hard-coded.

```bash
python run_external_map.py map_main.txt
```

## Main files

- `app.py` - Streamlit interface and shared mission state
- `core.py` - A*/UCS, H1-H4, Bayesian inference, HMM, delivery probability, mode comparison and MDP solvers
- `map_io.py` - parser for the faculty map format
- `run_external_map.py` - command-line search check on an external map
- `tests/test_regression.py` - regression checks used before submission


## External map upload

The Streamlit app includes an **External map test** page. Upload any `.txt` file in the faculty `map_main.txt` format to parse it dynamically, visualize the map and compare H1-H4 for any numbered survey goal.

The command-line path remains available:

```bash
python run_external_map.py another_map.txt
```

The external-map adapter follows the assignment movement rules exactly: open water = 2, kelp = 6, reef = impassable; moving with the current halves the entry cost, moving against it doubles the cost, and moving across the current leaves the cost unchanged.

## Demonstration maps

The code package includes three demonstration map definitions under `maps/`:

- `aeris_default.json` — the default AERIS disaster-logistics road network used when the app first opens.
- `aeris_alternate.json` — a second AERIS-native road network with different nodes, roads, bridges, lowland links and default delivery requests. Select it from **Mission setup → AERIS network** and click **Apply scenario**.
- `faculty_external_map.txt` — a separate AUV-style grid map in the faculty `map_main.txt` format. Use it from **External map test** or run `python run_external_map.py maps/faculty_external_map.txt`.

The two AERIS maps use the complete AERIS pipeline (Bayesian road belief, HMM temporal update, risk-aware A*, delivery probability and MDP). The faculty map is intentionally kept as a separate compatibility path because it represents a different grid-world environment.


## Large AERIS stress-test map

`maps/aeris_large.json` is a larger AERIS-native road network for testing search,
road-belief updates, confirmed closures, rerouting and delivery-mode recommendations.
It uses the same Hospital / Relief Camp / Village workflow as the smaller AERIS maps,
so no algorithm changes are required when switching maps.
