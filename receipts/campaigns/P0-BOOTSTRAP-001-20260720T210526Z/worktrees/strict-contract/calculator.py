import math


def classify(value):
    """Classify a finite int or float by sign."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("value must be an int or float, excluding bool")
    if isinstance(value, float) and math.isnan(value):
        raise ValueError("NaN has no sign")
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "zero"
