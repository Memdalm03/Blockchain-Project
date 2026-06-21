import argparse

from node import Node
from protocol import formula_holds, run_ociorcool


def create_network(total_nodes, byzantine_count, honest_values=None):
    honest_count = total_nodes - byzantine_count
    if honest_values is None:
        honest_values = ["Block A"]

    nodes = []
    for idx in range(honest_count):
        value = honest_values[min(idx, len(honest_values) - 1)]
        nodes.append(Node(node_id=idx, value=value, byzantine=False))
    for idx in range(honest_count, total_nodes):
        nodes.append(Node(node_id=idx, value=f"BYZANTINE_{idx}", byzantine=True))
    return nodes


def run_scenario(scenario_name, total_nodes, t, byzantine_count,
                 honest_values=None, attack_type="conflicting", verbose=False):
    nodes = create_network(total_nodes, byzantine_count, honest_values)
    result = run_ociorcool(nodes, t, attack_type, verbose)
    result["scenario"] = scenario_name
    result["total_nodes"] = total_nodes
    result["t"] = t
    result["byzantine_count"] = byzantine_count
    result["formula_valid"] = formula_holds(total_nodes, t)
    result["attack_type"] = attack_type
    return result


def print_summary(results):
    col = {"Scenario": 18, "n": 5, "t": 5, "Byz": 5, "Formula": 9, "Attack": 14,
           "Consensus": 11, "Final Value": 18, "Msgs": 7, "Rounds": 8, "Time(s)": 10}
    header = "".join(f"{h:<{w}}" for h, w in col.items())
    divider = "-" * len(header)

    print("\n" + divider)
    print("OciorCOOL MULTI-SCENARIO RESULTS")
    print(divider)
    print(header)
    print(divider)
    for r in results:
        m = r["metrics"]
        print(f"{r['scenario']:<18}{r['total_nodes']:<5}{r['t']:<5}{r['byzantine_count']:<5}"
              f"{'YES' if r['formula_valid'] else 'NO':<9}{r['attack_type']:<14}"
              f"{str(r['consensus']):<11}{str(r['final_value']):<18}"
              f"{m['message_count']:<7}{m['round_count']:<8}{m['execution_time_seconds']:<10}")
    print(divider)
    print("\nNotes:"
          "\n  Formula: n >= 3t+1  (required for protocol guarantees)"
          "\n  k = floor(t/5)+1   (ECC polynomial degree)")


SCENARIOS = [
    {"scenario_name": "Valid n=7 t=2", "total_nodes": 7, "t": 2,
     "byzantine_count": 2, "attack_type": "conflicting"},
    {"scenario_name": "Valid n=10 t=3", "total_nodes": 10, "t": 3,
     "byzantine_count": 3, "attack_type": "conflicting"},
    {"scenario_name": "Valid n=13 t=4", "total_nodes": 13, "t": 4,
     "byzantine_count": 4, "attack_type": "conflicting"},
    {"scenario_name": "Silent attack", "total_nodes": 7, "t": 2,
     "byzantine_count": 2, "attack_type": "silent"},
    {"scenario_name": "Fake attack", "total_nodes": 7, "t": 2,
     "byzantine_count": 2, "attack_type": "fake"},
    {"scenario_name": "Random attack", "total_nodes": 7, "t": 2,
     "byzantine_count": 2, "attack_type": "random"},
    {"scenario_name": "INVALID n=7 t=3", "total_nodes": 7, "t": 3,
     "byzantine_count": 3, "attack_type": "conflicting"},
]


def main():
    parser = argparse.ArgumentParser(description="OciorCOOL simulation")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print per-phase logs for every scenario.")
    args = parser.parse_args()

    results = [run_scenario(verbose=args.verbose, **s) for s in SCENARIOS]
    print_summary(results)


if __name__ == "__main__":
    main()
