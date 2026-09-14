def chunk(items, size):
    """Split items into lists of length `size`. Last chunk may be shorter."""
    out = []
    for i in range(0, len(items) - size, size):
        out.append(items[i:i + size])
    return out
