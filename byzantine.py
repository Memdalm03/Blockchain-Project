import random


def symbol_pair_attack(receiver_id, true_pair, attack_type="conflicting"):
    y_recv, y_self = true_pair

    if attack_type == "honest":
        return true_pair

    if attack_type == "silent":
        return (None, None)

    if attack_type == "fake":
        return ((y_recv + 13 + receiver_id) % 257, (y_self + 37) % 257)

    if attack_type == "conflicting":
        if receiver_id % 2 == 0:
            return ((y_recv + 100) % 257, (y_self + 100) % 257)
        return true_pair

    if attack_type == "random":
        choice = random.choice(["fake", "conflicting", "silent", "honest"])
        return symbol_pair_attack(receiver_id, true_pair, choice)

    raise ValueError(f"Unknown attack type: {attack_type!r}")
