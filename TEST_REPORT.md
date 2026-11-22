# Final regression test

The final source was tested after the heuristic redesign and the confirmed-closure/delivery-mode fixes.

Result:

- 108,734 checks
- 0 failures

The checks cover:

- Enumeration and Variable Elimination agreement
- HMM filtering and Viterbi normalization
- H1-H4 under several disaster scenarios, edge-cost weights, and confirmed closures
- the AERIS-specific H3 component lower bound remaining admissible and consistent
- H4 matching the maximum of H2, H3, and the relaxed-network lower bound node by node
- A* optimal-cost agreement with UCS
- confirmed blocked roads never appearing in ground routes
- the specific `I - Relief Camp` closure case
- HMM updates not reopening a confirmed field closure
- deliberate clearing of a field closure
- precision-delivery probability and Monte Carlo bounds
- editable request urgency
- ROAD/UAV/HYBRID feasibility and recommendation consistency
- MDP transition normalization and feasible actions
- Value Iteration and Policy Iteration convergence/agreement
- end-to-end evidence -> replanning -> decision behaviour
- runtime parsing of the faculty `map_main.txt` format

The supplied faculty map was also run separately. H1-H4 returned the same optimal path cost for every numbered goal; all four passed the admissibility and consistency checks.

## Streamlit session-state migration fix

The final deployment also sanitizes saved heuristic and destination widget values before rendering selectors. This prevents stale values from an older deployed version from causing `ValueError` after the heuristic names are changed. The final regression suite still passes 108734 checks with zero failures.
