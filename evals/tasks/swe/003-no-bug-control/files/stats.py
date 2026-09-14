def median(numbers):
    if not numbers:
        raise ValueError("median of empty sequence")
    s = sorted(numbers)
    mid = len(s) // 2
    if len(s) % 2 == 1:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2
