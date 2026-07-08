_PRIME = 257


# Defines how a byzantine node lies: sends a different, bad symbol pair to each receiver.
def corrupt_pair(receiver_id, true_pair):
    """
A Byzantine node sends fake symbol pairs instead of the true ECC values.
It may also send **different fake values to different honest nodes**, 
which causes the Phase 1 symbol checks to fail for that Byzantine sender.
"""
    y_recv, y_self = true_pair
    if y_recv is None or y_self is None:
        return true_pair
    return ((y_recv + 100 + receiver_id) % _PRIME, (y_self + 100) % _PRIME)
