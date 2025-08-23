from typing import Union

def normalize_timestamp(ts: Union[int, float]) -> float:
    """
    Normalize a Unix timestamp in seconds, milliseconds,
    microseconds, or nanoseconds to seconds (float).
    """
    if not ts:
        return None

    # allow float (fractional seconds)
    if isinstance(ts, float):
        return ts  

    # count digits to infer unit
    digits = len(str(abs(int(ts))))
    if digits >= 19:   # nanoseconds
        return ts / 1_000_000_000
    elif digits >= 16: # microseconds
        return ts / 1_000_000
    elif digits >= 13: # milliseconds
        return ts / 1_000
    else:              # seconds
        return ts