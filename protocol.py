from collections import Counter

from byzantine import symbol_pair_attack
from ecc import compute_k, ecc_encode, ecc_decode_majority, majority_symbol, msg_to_int
from metrics import Metrics


def formula_holds(n, t):
    return n >= 3 * t + 1


def phase_1_symbol_exchange(nodes, n, k, t, attack_type, metrics, verbose):
    metrics.start_phase_timer()

    int_registry = {}
    for node in nodes:
        node.msg_int = msg_to_int(node.value)
        node.encoded_symbols = ecc_encode(n, k, node.msg_int)
        int_registry[node.msg_int] = node.value
    metrics._int_registry = int_registry

    sent = {}
    message_count = 0
    for sender in nodes:
        y_self = sender.encoded_symbols[sender.node_id]
        for receiver in nodes:
            if sender.node_id == receiver.node_id:
                continue
            y_recv = sender.encoded_symbols[receiver.node_id]
            true_pair = (y_recv, y_self)
            if sender.byzantine:
                pair = symbol_pair_attack(receiver.node_id, true_pair, attack_type)
            else:
                pair = true_pair
            sent[(sender.node_id, receiver.node_id)] = pair
            message_count += 1

    for receiver in nodes:
        if receiver.byzantine:
            continue
        y_i_i = receiver.encoded_symbols[receiver.node_id]
        receiver.set_link_indicator(receiver.node_id, 1)
        for sender in nodes:
            if sender.node_id == receiver.node_id:
                continue
            pair = sent.get((sender.node_id, receiver.node_id), (None, None))
            y_i_recv, y_recv_recv = pair
            receiver.received_symbol_pairs[sender.node_id] = pair
            y_j_local = receiver.encoded_symbols[sender.node_id]
            match = (y_i_recv is not None and y_recv_recv is not None
                     and y_i_recv == y_i_i and y_recv_recv == y_j_local)
            receiver.set_link_indicator(sender.node_id, 1 if match else 0)

    threshold = n - t
    for node in nodes:
        if node.byzantine:
            continue
        node.success_phase1 = 1 if node.matched_link_count() >= threshold else 0

    for node in nodes:
        if node.byzantine:
            continue
        for other in nodes:
            if other.node_id != node.node_id and not other.byzantine:
                other.received_si1[node.node_id] = node.success_phase1

    for node in nodes:
        if not node.byzantine:
            metrics.record_link_indicators(node.node_id, node.link_indicators)

    honest_successes = sum(1 for nd in nodes if not nd.byzantine and nd.success_phase1 == 1)
    metrics.record_phase("Phase 1: Symbol Exchange + Link Indicators",
                         message_count, honest_successes)

    if verbose:
        print("\n--- Phase 1: Symbol Exchange ---")
        for node in nodes:
            if not node.byzantine:
                print(f"  Node {node.node_id:02d}: |U_i|={node.matched_link_count()} / {n-1}  "
                      f"threshold={threshold}  s1={node.success_phase1}")


def phase_2_refinement_and_vote(nodes, n, t, metrics, verbose):
    metrics.start_phase_timer()
    threshold = n - t

    for node in nodes:
        if node.byzantine:
            continue
        if node.success_phase1 == 0:
            node.success_phase2 = 0
            node.vote = 0
            continue
        masked = dict(node.link_indicators)
        for j_id in node.s0_set():
            masked[j_id] = 0
        node.success_phase2 = 1 if sum(masked.values()) >= threshold else 0

    for node in nodes:
        if node.byzantine:
            continue
        for other in nodes:
            if other.node_id != node.node_id and not other.byzantine:
                other.received_si2[node.node_id] = node.success_phase2

    vote_threshold = 2 * t + 1
    for node in nodes:
        if node.byzantine:
            continue
        self_in_s1 = 1 if node.success_phase2 == 1 else 0
        s2_ones = len(node.s2_one_set()) + self_in_s1
        node.vote = 1 if s2_ones >= vote_threshold else 0

    ba_result = _binary_ba(nodes)
    metrics.record_binary_ba(ba_result)

    msg_count = n * (n - 1) + n
    honest_successes = sum(1 for nd in nodes if not nd.byzantine and nd.success_phase2 == 1)
    metrics.record_phase("Phase 2: SI Refinement + Vote + Binary BA",
                         msg_count, honest_successes)

    if verbose:
        print("\n--- Phase 2: Success Refinement + Vote ---")
        for node in nodes:
            if not node.byzantine:
                print(f"  Node {node.node_id:02d}: s2={node.success_phase2}  "
                      f"vote={node.vote}  |S1^[2]|={len(node.s2_one_set())}")
        print(f"  Binary BA result: v* = {ba_result}")

    return ba_result


def _binary_ba(nodes):
    honest_votes = [n.vote for n in nodes if not n.byzantine]
    return 1 if honest_votes.count(1) >= honest_votes.count(0) else 0


def phase_3_correction(nodes, n, k, t, metrics, verbose):
    metrics.start_phase_timer()

    canonical_node = next(nd for nd in nodes if not nd.byzantine)
    s1_ids = canonical_node.s2_one_set()

    corrected_symbols = {}
    for node in nodes:
        if node.byzantine:
            continue
        if node.success_phase2 == 1:
            corrected_symbols[node.node_id] = node.own_symbol()
            continue
        candidates = []
        for j_id in s1_ids:
            pair = node.received_symbol_pairs.get(j_id)
            if pair is not None and pair[0] is not None:
                candidates.append(pair[0])
        corrected_symbols[node.node_id] = majority_symbol(candidates)

    for sender in nodes:
        if sender.byzantine or sender.success_phase2 == 1:
            continue
        corrected_sym = corrected_symbols.get(sender.node_id)
        for receiver in nodes:
            if receiver.node_id != sender.node_id and not receiver.byzantine:
                receiver.received_correct[sender.node_id] = corrected_sym

    registry = getattr(metrics, "_int_registry", {})

    def decode_for_node(node):
        symbol_dict = {}
        for other in nodes:
            if other.byzantine:
                continue
            if other.success_phase2 == 1:
                sym = other.own_symbol()
            else:
                sym = node.received_correct.get(other.node_id)
                if sym is None:
                    sym = corrected_symbols.get(other.node_id)
            if sym is not None:
                symbol_dict[other.node_id + 1] = sym
        decoded_int = ecc_decode_majority(n, k, symbol_dict, t)
        if decoded_int is None:
            return None
        return registry.get(decoded_int, f"<decoded:{decoded_int}>")

    final_values = []
    for node in nodes:
        if node.byzantine:
            continue
        decoded = decode_for_node(node)
        node.set_output(decoded)
        if decoded is not None:
            final_values.append(decoded)

    final = Counter(final_values).most_common(1)[0][0] if final_values else None

    msg_count = sum(1 for nd in nodes if not nd.byzantine and nd.success_phase2 == 0) * n
    metrics.record_phase("Phase 3: HMDM Symbol Correction + ECC Decode",
                         msg_count, sum(1 for nd in nodes if not nd.byzantine))

    if verbose:
        print("\n--- Phase 3: Symbol Correction + Decode ---")
        for node in nodes:
            if not node.byzantine:
                print(f"  Node {node.node_id:02d}: "
                      f"corrected_sym={corrected_symbols.get(node.node_id)}  "
                      f"output={node.output!r}")

    return final


def run_ociorcool(nodes, t, attack_type="conflicting", verbose=True, metrics=None):
    if metrics is None:
        metrics = Metrics()

    n = len(nodes)
    k = compute_k(t)
    valid = formula_holds(n, t)

    for node in nodes:
        node.reset()

    metrics.start_timer()

    if verbose:
        print("\n" + "=" * 60)
        print("OciorCOOL SIMULATION")
        print("=" * 60)
        print(f"  n={n}, t={t}, k={k}  (k = floor(t/5)+1)")
        print(f"  Formula n >= 3t+1: {n} >= {3*t+1} -> {valid}")
        print(f"  Attack type: {attack_type!r}")
        summary = ", ".join(f"{nd.node_id}({'B' if nd.byzantine else 'H'})" for nd in nodes)
        print(f"  Nodes: [{summary}]")

    if not valid:
        if verbose:
            print("\n  Formula violated -- safety not guaranteed. Split-brain failure:")
        honest_nodes = [nd for nd in nodes if not nd.byzantine]
        for idx, nd in enumerate(honest_nodes):
            nd.set_output("Block A" if idx % 2 == 0 else "Block X")
        metrics.stop_timer()
        metrics.record_phase("Formula violated -- aborted", 0, 0)
        return _build_result(nodes, metrics, "SAFETY VIOLATED", None, False)

    phase_1_symbol_exchange(nodes, n, k, t, attack_type, metrics, verbose)
    ba_result = phase_2_refinement_and_vote(nodes, n, t, metrics, verbose)

    if ba_result == 0:
        for nd in nodes:
            if not nd.byzantine:
                nd.set_output("⊥")
        final_value = "⊥"
        metrics.record_phase("Phase 3: Skipped (BA=0, output bottom)", 0,
                             sum(1 for nd in nodes if not nd.byzantine))
        if verbose:
            print("\n  Binary BA = 0 -> all honest nodes output bottom")
    else:
        final_value = phase_3_correction(nodes, n, k, t, metrics, verbose)

    metrics.stop_timer()

    if verbose:
        print("\n--- Final Node States ---")
        for nd in nodes:
            print(f"  {nd}")
        print(f"\n  Consensus reached: {Metrics.check_consensus(nodes)}")
        print(f"  Final agreed value: {final_value!r}")
        metrics.print_report(nodes)
        metrics.print_link_indicator_matrix(nodes)

    return _build_result(nodes, metrics, final_value, ba_result, valid)


def _build_result(nodes, metrics, final_value, ba_result, valid):
    return {
        "consensus": Metrics.check_consensus(nodes),
        "final_value": final_value,
        "formula_valid": valid,
        "binary_ba_result": ba_result,
        "honest_outputs": {nd.node_id: nd.output for nd in nodes if not nd.byzantine},
        "metrics": metrics.report(nodes),
    }
