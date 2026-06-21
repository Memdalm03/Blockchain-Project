from dataclasses import dataclass, field


@dataclass
class Node:
    node_id: int
    value: str
    byzantine: bool = False

    msg_int: int = 0
    encoded_symbols: list = field(default_factory=list)
    link_indicators: dict = field(default_factory=dict)
    success_phase1: int = None
    success_phase2: int = None
    vote: int = 0
    output: str = None

    received_symbol_pairs: dict = field(default_factory=dict)
    received_si1: dict = field(default_factory=dict)
    received_si2: dict = field(default_factory=dict)
    received_correct: dict = field(default_factory=dict)

    def reset(self):
        self.msg_int = 0
        self.encoded_symbols = []
        self.link_indicators = {}
        self.success_phase1 = None
        self.success_phase2 = None
        self.vote = 0
        self.output = None
        self.received_symbol_pairs = {}
        self.received_si1 = {}
        self.received_si2 = {}
        self.received_correct = {}

    def symbol_for(self, node_j):
        if not self.encoded_symbols:
            return None
        return self.encoded_symbols[node_j - 1]

    def own_symbol(self):
        return self.symbol_for(self.node_id + 1)

    def set_link_indicator(self, sender_id, value):
        self.link_indicators[sender_id] = value

    def matched_link_count(self):
        return sum(self.link_indicators.values())

    def s0_set(self):
        return {j for j, s in self.received_si1.items() if s == 0}

    def s2_one_set(self):
        return {j for j, s in self.received_si2.items() if s == 1}

    def set_output(self, value):
        self.output = value

    def __str__(self):
        role = "Byzantine" if self.byzantine else "Honest   "
        return (f"Node {self.node_id:02d} | {role} | value={self.value!r:<12} | "
                f"s1={self.success_phase1} s2={self.success_phase2} | "
                f"vote={self.vote} | output={self.output!r}")

    __repr__ = __str__
