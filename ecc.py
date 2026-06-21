import hashlib
from collections import Counter
from itertools import combinations

_PRIME = 257


def _poly_eval(coeffs, x):
    y = 0
    for i, c in enumerate(coeffs):
        y = (y + c * pow(x, i, _PRIME)) % _PRIME
    return y


def _make_coeffs(msg_int, k):
    coeffs = []
    seed = msg_int % _PRIME
    for _ in range(k):
        coeffs.append(seed)
        seed = (seed * 1_664_525 + 1_013_904_223) % _PRIME
    return coeffs


def _lagrange_at_zero(xs, ys):
    result = 0
    for i in range(len(xs)):
        num, den = ys[i], 1
        for j in range(len(xs)):
            if i != j:
                num = (num * (0 - xs[j])) % _PRIME
                den = (den * (xs[i] - xs[j])) % _PRIME
        result = (result + num * pow(den, _PRIME - 2, _PRIME)) % _PRIME
    return result


def msg_to_int(message):
    digest = hashlib.sha256(message.encode()).hexdigest()
    return int(digest, 16) % _PRIME


def compute_k(t):
    return t // 5 + 1


def ecc_encode(n, k, msg_int):
    coeffs = _make_coeffs(msg_int, k)
    return [_poly_eval(coeffs, x) for x in range(1, n + 1)]


def ecc_decode_majority(n, k, symbol_dict, t):
    if len(symbol_dict) < k:
        return None

    if k == 1:
        vals = list(symbol_dict.values())
        majority, count = Counter(vals).most_common(1)[0]
        return majority if count >= n - t else None

    for subset in combinations(symbol_dict.items(), k):
        xs = [p[0] for p in subset]
        ys = [p[1] for p in subset]
        candidate = _lagrange_at_zero(xs, ys)
        candidate_syms = ecc_encode(n, k, candidate)
        matches = sum(1 for x, y in symbol_dict.items() if candidate_syms[x - 1] == y)
        if matches >= n - t:
            return candidate
    return None


def majority_symbol(symbols):
    if not symbols:
        return None
    val, count = Counter(symbols).most_common(1)[0]
    return val if count > len(symbols) // 2 else None
