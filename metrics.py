import time
from dataclasses import dataclass


@dataclass
class PhaseRecord:
    name: str
    messages_sent: int
    honest_successes: int
    duration_seconds: float


class Metrics:
    def __init__(self):
        self._start = None
        self._end = None
        self._phase_start = None
        self.message_count = 0
        self.phases = []
        self.binary_ba_result = None
        self.link_indicator_matrix = {}

    def start_timer(self):
        self._start = time.perf_counter()

    def stop_timer(self):
        self._end = time.perf_counter()

    def start_phase_timer(self):
        self._phase_start = time.perf_counter()

    def phase_elapsed(self):
        if self._phase_start is None:
            return 0.0
        return time.perf_counter() - self._phase_start

    def record_phase(self, name, messages, honest_successes):
        self.phases.append(PhaseRecord(name, messages, honest_successes,
                                       round(self.phase_elapsed(), 8)))
        self.message_count += messages

    def record_binary_ba(self, result):
        self.binary_ba_result = result

    def record_link_indicators(self, node_id, indicators):
        self.link_indicator_matrix[node_id] = dict(indicators)

    def execution_time(self):
        if self._start is None or self._end is None:
            return 0.0
        return self._end - self._start

    def round_count(self):
        return len(self.phases)

    def average_messages_per_round(self):
        if not self.phases:
            return 0.0
        return round(self.message_count / len(self.phases), 2)

    @staticmethod
    def check_consensus(nodes):
        outputs = {n.output for n in nodes if not n.byzantine}
        return len(outputs) == 1

    @staticmethod
    def honest_outputs(nodes):
        return {n.node_id: n.output for n in nodes if not n.byzantine}

    @staticmethod
    def byzantine_node_ids(nodes):
        return [n.node_id for n in nodes if n.byzantine]

    def report(self, nodes):
        byzantine_ids = self.byzantine_node_ids(nodes)
        total = len(nodes)
        byz_pct = round(len(byzantine_ids) / total * 100, 2) if total else 0.0
        return {
            "total_nodes": total,
            "honest_nodes": [n.node_id for n in nodes if not n.byzantine],
            "byzantine_nodes": byzantine_ids,
            "byzantine_percentage": byz_pct,
            "message_count": self.message_count,
            "round_count": self.round_count(),
            "average_messages_per_round": self.average_messages_per_round(),
            "binary_ba_result": self.binary_ba_result,
            "phases": [
                {"name": p.name, "messages": p.messages_sent,
                 "honest_successes": p.honest_successes, "duration_s": p.duration_seconds}
                for p in self.phases
            ],
            "execution_time_seconds": round(self.execution_time(), 8),
            "consensus_reached": self.check_consensus(nodes),
            "honest_outputs": self.honest_outputs(nodes),
        }

    def print_report(self, nodes):
        r = self.report(nodes)
        print("\n=== SIMULATION METRICS ===")
        print(f"Total nodes         : {r['total_nodes']}")
        print(f"Honest nodes        : {r['honest_nodes']}")
        print(f"Byzantine nodes     : {r['byzantine_nodes']} ({r['byzantine_percentage']}%)")
        print(f"Messages sent total : {r['message_count']}")
        print(f"Avg messages/round  : {r['average_messages_per_round']}")
        print(f"Rounds (phases)     : {r['round_count']}")
        print(f"Binary BA result    : {r['binary_ba_result']}")
        print(f"Execution time      : {r['execution_time_seconds']}s")
        print(f"Consensus reached   : {r['consensus_reached']}")
        print(f"Honest outputs      : {r['honest_outputs']}")
        print("\nPhase breakdown:")
        for p in r["phases"]:
            print(f"  [{p['name']}]  msgs={p['messages']}  "
                  f"successes={p['honest_successes']}  ({p['duration_s']}s)")
        print("==========================\n")

    def print_link_indicator_matrix(self, nodes):
        if not self.link_indicator_matrix:
            return
        n = len(nodes)
        print("\nLink Indicator Matrix u_i(j)  [row=node i, col=node j]")
        print("     " + "  ".join(f"{i:02d}" for i in range(n)))
        print("     " + "--" * n * 2)
        for i in range(n):
            row = self.link_indicator_matrix.get(i, {})
            cells = [" —" if i == j else f" {row.get(j, '?')}" for j in range(n)]
            role = "B" if nodes[i].byzantine else "H"
            print(f"  {i:02d}{role} {''.join(cells)}")
        print()
